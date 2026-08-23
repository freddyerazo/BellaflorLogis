"""API del modulo Armellini Post.

Genera el XML AelisShipperEDI de Armellini a partir del XML de operaciones
de Expoflor, que se importa a expoflor_operaciones_cajas.

Reemplaza los scripts sueltos del proyecto externo "ArmelliniFormat", donde
el codigo de producto, el consignee, el shipper y la fecha estaban
hardcodeados en cada script y no quedaba registro de lo enviado.
"""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import text

from app.database.connection import engine
from app.schemas.armellini import (
    ConsigneeIn,
    GenerarIn,
    GenerarOut,
    PreviewOut,
    ResumenImportacion,
)
from app.services import armellini_xml as ax
from app.services import expoflor_operaciones as ops

router = APIRouter(prefix="/armellini-post", tags=["Armellini Post"])


@router.post("/importar", response_model=ResumenImportacion)
async def importar_operaciones(file: UploadFile = File(...)):
    """Sube el XML de operaciones de Expoflor (ReservasExportadores).

    Reimportar el mismo archivo actualiza las cajas, no las duplica.
    """
    contenido = await file.read()
    nombre = file.filename or "operaciones.xml"

    try:
        cajas, avisos = ops.parse(contenido, nombre)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    resultado = ops.importar(cajas)
    resumen = ops.resumen(cajas)

    return ResumenImportacion(
        archivo=nombre,
        avisos=avisos,
        conciliacion=ops.conciliar_con_ventas(resumen["facturas"]),
        **resumen,
        **resultado,
    )


@router.get("/preview", response_model=PreviewOut)
def preview(
    fecha: Optional[date_type] = Query(
        default=None,
        description="Fecha de salida desde Miami (caja_fecha_transportador del XML de operaciones)",
    ),
):
    """Cajas candidatas al XML: las de destinos con consignee de Armellini cargado."""
    cajas = ax.buscar_cajas(fecha_carrier=fecha)

    fechas = sorted({c["fecha_carrier"] for c in cajas if c["fecha_carrier"]})

    return PreviewOut(
        total_cajas=len(cajas),
        shipdate_sugerido=fechas[0] if fechas else None,
        avisos=ax.validar(cajas),
        cajas=cajas,
    )


@router.post("/generar", response_model=GenerarOut)
def generar(payload: GenerarIn):
    """Arma el XML y lo deja registrado en armellini_exports."""
    cajas = ax.buscar_cajas(barcodes=payload.barcodes)

    if not cajas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ninguna de las cajas indicadas esta importada.",
        )

    faltantes = set(payload.barcodes) - {c["codigo_pieza"] for c in cajas}
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cajas no encontradas: {', '.join(sorted(faltantes))}",
        )

    # PO digitado a mano para las cajas que llegaron sin el.
    digitados = {p.codigo_pieza: p.po.strip() for p in payload.pos}
    if digitados:
        with engine.begin() as conn:
            for codigo, po in digitados.items():
                conn.execute(
                    text("UPDATE expoflor_operaciones_cajas SET po = :po WHERE codigo_pieza = :cp"),
                    {"po": po, "cp": codigo},
                )
        for caja in cajas:
            if caja["codigo_pieza"] in digitados:
                caja["po"] = digitados[caja["codigo_pieza"]]

    avisos = ax.validar(cajas)
    shipper = payload.shipper or ax.SHIPPER_POR_DEFECTO

    try:
        xml = ax.construir(cajas, payload.shipdate, shipper)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    filename = f"XML Armellini Delivery {payload.shipdate.strftime('%m%d%Y')}.xml"
    export_id = ax.registrar_export(xml, cajas, payload.shipdate, shipper, filename, avisos)

    return GenerarOut(
        export_id=export_id,
        filename=filename,
        total_cajas=len(cajas),
        avisos=avisos,
        xml=xml,
    )


@router.get("/exports")
def historial(limite: int = Query(default=30, le=200)):
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT id, filename, shipdate, shipper_code, total_cajas, awbs, pos, avisos, created_at
            FROM armellini_exports ORDER BY created_at DESC LIMIT :limite
        """), {"limite": limite}).mappings().all()


@router.get("/exports/{export_id}")
def ver_export(export_id: int):
    with engine.connect() as conn:
        fila = conn.execute(
            text("SELECT * FROM armellini_exports WHERE id = :id"), {"id": export_id}
        ).mappings().first()

    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export no encontrado")
    return fila


@router.get("/consignees")
def listar_consignees():
    with engine.connect() as conn:
        return conn.execute(text(
            "SELECT * FROM armellini_consignees ORDER BY destinatario"
        )).mappings().all()


@router.post("/consignees", status_code=status.HTTP_201_CREATED)
def crear_consignee(payload: ConsigneeIn):
    with engine.begin() as conn:
        return conn.execute(text("""
            INSERT INTO armellini_consignees (destinatario, consignee_code, descripcion)
            VALUES (:destinatario, :consignee_code, :descripcion)
            ON CONFLICT (destinatario) DO UPDATE SET
                consignee_code = EXCLUDED.consignee_code,
                descripcion    = EXCLUDED.descripcion,
                updated_at     = now()
            RETURNING *
        """), payload.model_dump()).mappings().first()

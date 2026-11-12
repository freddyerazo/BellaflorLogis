"""API del modulo Entregas Locales: recibos de bodega vs dartis_ventas.

Vive como sub-pestaña dentro de la pagina "Ingresos Locales", pero no toca
nada de lo que ya habia ahi: la pestaña vieja sigue siendo un proxy de solo
lectura al Apps Script del bot (`ingresos_locales.py`), y esta es una via
completamente separada -- lee el mismo Google Sheet con la API oficial,
reinterpreta el OCR con Claude y lo cruza contra Dartis.

El pipeline esta partido en tres endpoints en vez de uno solo, a proposito:
son ~3.500 recibos y la interpretacion tarda ~3 s cada una. Un unico
"sincronizar todo" seria una peticion HTTP de horas que ningun timeout de
Render sobrevive. La pantalla los encadena y muestra el avance.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import entregas_locales_cruce as cruce
from app.services import entregas_locales_llm as llm
from app.services import entregas_locales_sheet as sheet

router = APIRouter(prefix="/entregas-locales", tags=["Entregas Locales"])


class RawUpdate(BaseModel):
    """Solo las columnas A-O del Sheet (ver `COLUMNA_LETRA` en
    entregas_locales_sheet.py) -- la foto y el texto OCR no se editan a
    mano. `exclude_unset` en el endpoint hace que mandar solo 1-2 campos no
    borre el resto."""
    fecha_registro: str | None = None
    hora_registro: str | None = None
    fecha_documento: str | None = None
    hora_documento: str | None = None
    empresa_logistica: str | None = None
    nombre_chofer: str | None = None
    cedula: str | None = None
    placa: str | None = None
    finca_exportador: str | None = None
    nombre_cliente: str | None = None
    numero_guia_ingreso: str | None = None
    detalle_cajas: str | None = None
    total_fulls_pcs: str | None = None
    temperatura: str | None = None
    observaciones: str | None = None


@router.get("/resumen")
def resumen(desde: str | None = None, hasta: str | None = None):
    """Contadores de la pantalla: universo de Dartis, estados del cruce y
    cuantos recibos quedan por interpretar.

    `desde`/`hasta` acotan los contadores al mismo rango de fechas que la
    tabla de `/cruce` -- sin ellos, cuenta todo el historico.
    """
    return {**cruce.resumen(desde=desde, hasta=hasta), "sheet_configurado": sheet.configurado()}


@router.get("/cruce")
def obtener_cruce(
    estado: str | None = Query(None, description="OK, SIN RECIBO, AMBIGUO o SIN PROCESAR"),
    texto: str | None = Query(None, description="Busca en pedido, empresa, agencia o N de ingreso"),
    desde: str | None = None,
    hasta: str | None = None,
    limite: int = Query(500, le=2000),
):
    """Una fila por pedido de Dartis, con su recibo si lo tiene.

    El universo lo manda dartis_ventas: los pedidos que todavia no se
    procesaron salen como "SIN PROCESAR" en vez de desaparecer, para que la
    cobertura del 100% sea visible y no un hueco silencioso.
    """
    return cruce.obtener_cruce(estado=estado, texto=texto, desde=desde,
                               hasta=hasta, limite=limite)


@router.get("/recibo/{entrega_id}")
def detalle_recibo(entrega_id: int):
    """Cabecera + lineas de un recibo interpretado, para el detalle en pantalla."""
    from sqlalchemy import text

    from app.database.connection import engine

    with engine.connect() as conn:
        cabecera = conn.execute(text("""
            SELECT e.*, r.texto_ocr, r.fila_sheet
            FROM entregas_locales e
            JOIN entregas_locales_raw r ON r.id = e.raw_id
            WHERE e.id = :id
        """), {"id": entrega_id}).mappings().first()
        if not cabecera:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")
        lineas = conn.execute(text("""
            SELECT * FROM entregas_locales_detalle WHERE entrega_id = :id ORDER BY id
        """), {"id": entrega_id}).mappings().all()

    return {"cabecera": dict(cabecera), "lineas": [dict(l) for l in lineas]}


@router.patch("/raw/{fila_sheet}")
def actualizar_raw(fila_sheet: int, cambios: RawUpdate):
    """Corrige un dato crudo del Sheet (ej. un numero de guia mal tipeado) y
    lo escribe de vuelta en el Sheet real -- unico endpoint de BLIS que
    escribe sobre ese Sheet, acotado a las columnas A-O (nunca la foto ni el
    texto OCR). `fila_sheet` es el numero de fila real del Sheet (el mismo
    `_fila` que trae el proxy del bot). Si la escritura al Sheet falla, el
    cambio en Supabase queda guardado igual (ver `sheet_actualizado`).
    """
    campos = cambios.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="No se envio ningun campo para actualizar.")
    try:
        return sheet.actualizar_raw(fila_sheet, campos)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sincronizar-sheet")
def sincronizar_sheet():
    """Paso 1: trae el Google Sheet a `entregas_locales_raw` (sin LLM, rapido).

    No toca el Apps Script ni el bot: lee la hoja con una cuenta de servicio
    de solo lectura.
    """
    try:
        return sheet.sincronizar()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo leer el Sheet: {e}")


@router.post("/interpretar")
def interpretar(limite: int = Query(25, ge=1, le=100)):
    """Paso 2: reinterpreta con Claude los recibos que aun no tienen lectura.

    Se llama repetidamente hasta que `pendientes` llega a 0. El limite por
    llamada es bajo a proposito (~3 s por recibo contra la API del modelo).
    """
    try:
        return llm.interpretar_pendientes(limite=limite)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/cruzar")
def cruzar(desde: str | None = Query(None, description="YYYY-MM-DD; solo recalcula pedidos desde esa fecha")):
    """Paso 3: recalcula el cruce de los pedidos de Dartis.

    `desde` acota el recalculo mientras la interpretacion de recibos
    todavia no cubre todo el Sheet: recalcular pedidos viejos que ni
    siquiera tienen su recibo interpretado no suma nada. Sin `desde`,
    recalcula todo el historial. Conserva `verificado_manual`: un recalculo
    no borra lo que alguien ya reviso a mano.
    """
    return cruce.recalcular(desde=desde)

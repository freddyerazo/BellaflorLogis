"""
API para la pestana "Documentacion" de BLIS: respaldos que se entregan al
departamento financiero.

POST /api/finance-documents/logiztik/rellenar
  - Recibe el PDF original del reporte de flete de Logiztik-Group Ecuador
    (DETAIL/ORDER NUMBER vacios), cruza el AWB contra dartis_ventas y
    devuelve el mismo PDF con esos dos campos completados.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.logiztik_invoice_filler import procesar_factura_logiztik

router = APIRouter(prefix="/finance-documents", tags=["Documentacion"])
logger = logging.getLogger(__name__)


@router.post("/logiztik/rellenar")
async def rellenar_factura_logiztik(file: UploadFile = File(...)):
    contenido = await file.read()
    try:
        resultado = procesar_factura_logiztik(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("Error rellenando factura Logiztik (%s)", file.filename)
        raise HTTPException(status_code=500, detail="No se pudo procesar el PDF.") from None

    nombre_salida = f"{resultado['invoice_number']}_completada.pdf"
    return Response(
        content=resultado["pdf_bytes"],
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_salida}"',
            # Solo valores garantizados ASCII (numeros) -- nombres de
            # cliente pueden traer tildes y romperian el header HTTP.
            "X-Invoice-Number": resultado["invoice_number"],
            "X-Awb-Number": resultado["awb_number"],
            "X-Clientes-Encontrados": str(resultado["clientes_encontrados"]),
        },
    )

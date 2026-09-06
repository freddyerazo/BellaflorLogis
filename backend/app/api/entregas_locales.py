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

from app.services import entregas_locales_cruce as cruce
from app.services import entregas_locales_llm as llm
from app.services import entregas_locales_sheet as sheet

router = APIRouter(prefix="/entregas-locales", tags=["Entregas Locales"])


@router.get("/resumen")
def resumen():
    """Contadores de la pantalla: universo de Dartis, estados del cruce y
    cuantos recibos quedan por interpretar."""
    return {**cruce.resumen(), "sheet_configurado": sheet.configurado()}


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
def cruzar():
    """Paso 3: recalcula el cruce de TODOS los pedidos de Dartis.

    Conserva `verificado_manual`: un recalculo no borra lo que alguien ya
    reviso a mano.
    """
    return cruce.recalcular()

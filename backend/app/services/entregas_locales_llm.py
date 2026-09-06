"""Reinterpretacion de recibos OCR del modulo Entregas Locales.

Toma el texto OCR crudo de un recibo (columna "Texto Completo (OCR)" del
Sheet del bot "EntregasLocales" / IngresosLocales) y lo estructura en el
contrato que consumen `entregas_locales` + `entregas_locales_detalle`
(ver database/migrations/038_entregas_locales.sql).

Deliberadamente NO reutiliza el JSON que ya arma el bot original
(deepseek-chat, funcion estructurarConGemini en codigo.js): ese JSON aplasta
varias fincas/clientes en un solo string separado por " | ", que es
justamente lo que este modulo existe para dejar de hacer.

El prompt esta calibrado con estadisticas reales sobre las 3.515 filas del
Sheet (medido 2026-09-06), no con suposiciones -- cada regla de abajo
responde a un patron real encontrado:

  - 17,2% de los recibos traen 2 o mas fincas en el mismo documento -> el
    esquema es SIEMPRE una lista de items, nunca un campo plano, aunque el
    caso comun sea 1 sola finca.
  - ~27% mencionan "Prom" y 13% usan el formato "Max-9.0 Min-9.0" con guion
    -- verificado que DeepSeek y Claude confunden ese guion con un signo
    negativo en al menos 1 de cada 3 recibos con esa forma. Y Claude, al
    encontrar varios valores, a veces devuelve texto ("Max-7.0 Min-6.0
    Prom-6.86") en vez de un numero, rompiendo el esquema -- paso en 4 de
    10 recibos de la primera prueba real.
  - 3 formatos de fecha conviven (dd/mm/aaaa 73,5%, aaaa-mm-dd 12,4%,
    dd-Mon-aa 11,0%) -- hay que normalizar los tres a uno solo.
  - Solo 54% usan la palabra "INGRESO" para el numero de guia; el resto usa
    otras etiquetas segun el formato de cada agencia (ver los 8 formatos
    documentados abajo).
  - "N Guia / Ingreso" y "Total Fulls / PCS" del Sheet original en realidad
    mezclan DOS campos distintos cada uno. Verificado: 877 de 3.515 recibos
    traen a la vez un numero de INGRESO (interno de la bodega, uno por todo
    el documento) Y un AWB/HAWB (guia aerea, uno POR FINCA dentro del mismo
    recibo -- ejemplo real: un solo "INGRESO: ING-00150881" con tres AWB
    distintos, uno por cada "EXP:"). Por eso numero_ingreso va a nivel de
    cabecera y numero_guia a nivel de cada item. Lo mismo con fulls/piezas:
    "TOTAL: 1.75 / 7" son dos numeros (1,75 fulls, 7 piezas), no uno.
  - 0,03% del OCR no es un recibo en absoluto (se encontro un caso real:
    una captura de conversacion de WhatsApp). Rarisimo, pero silencioso si
    no se detecta -- devuelve `es_recibo_valido: false` en vez de inventar.
  - Se encontro un caso real donde un modelo copio el nombre de la finca
    dentro del campo "cliente" cuando el recibo no traia cliente -- de ahi
    la regla explicita de nunca inventar ese campo.
"""

import json
import re

PROMPT_EXTRACCION = """Eres un asistente de logistica de flores de exportacion en Ecuador. Vas a
recibir el texto OCR crudo de un recibo de ingreso a bodega de carga aerea o
terrestre, emitido por una agencia logistica (no por Bellaflor).

El recibo puede venir en cualquiera de estos formatos, y el OCR puede traer
errores, texto cortado o repetido:
- Fresh Logistics Carga (Centro Logistico Alpachaca): multi-finca, tabla de
  clientes por finca, "INGRESO A CUARTOS FRIOS"
- FloralTech / Floral Tech: "Comprobante de Recepcion", TOMIN/TOMAX/TOPRD,
  "PERSONA RECIBE/ENTREGA"
- LogiztikAlliance Group: multiples exportadores con AWBL/HAWBL, chofer al
  final
- UPS/Saftec: "Ingreso a Cuartos Frios", columna EXS, AWB+FINCA+CLIENTE
- Kuehne+Nagel: "Remision de Cultivo", tabla TIPO CAJA/CANTIDAD, CONDUCTOR,
  temperatura como lista de valores separados por "/" (ej "7C/7C/6C/7C")
- Green Logistics / LDSEXPORT: tabla DIMENSION con CANT/TIPO/LARGO/ANCHO/
  ALTO/PESO
- Panatworld / Panatlantic: "INGRESO# FISICO", MAWB/BL, HAWB/HBL, RESP-FINC
- ONE Teamcargo / Value Cargo / Pacific Air Cargo / EBF Cargo / 3FCargo/
  BFCargo (variantes del mismo formato "INGRESO A CUARTOS FRIOS"): BODEGUERO,
  CHOFER, PLACAS, TEMP, EXP:<finca> AWB CLIENTE BXS<cantidad>, TOTAL EXP -- se
  repite el bloque "EXP:...TOTAL EXP:" una vez POR CADA finca en el mismo
  recibo

REGLA CRITICA — UN ITEM POR CADA LINEA DE CLIENTE, no por cada finca. Esta es
la regla que mas se rompe: antes de responder, hacé una lista mental de CADA
linea que tenga un nombre de cliente/comprador (aunque varias compartan la
misma finca) y generá un item por cada una de esas lineas -- NUNCA un item
por finca que junte varios clientes adentro. Ejemplo real: un recibo con
finca "SARITA ROSES" y tres lineas de cliente distintas (MF-AKULA KZ,
MF DEVYATN KZ, MF FLORENTINA) son TRES items con finca="SARITA ROSES" cada
uno, NO un item solo con el total sumado. Contá los items que vas a devolver
y volvé a contar cuantas lineas de cliente hay en el texto: si no coinciden,
te faltaron lineas. El 17% de los recibos reales tienen 2 o mas fincas, y
dentro de cada finca puede haber a su vez varios clientes -- NUNCA combines
nada en un solo texto separado por "|".

REGLA CRITICA — AGENCIA, FINCA y CLIENTE son TRES entidades que NUNCA se
repiten entre si:
- agencia_logistica es la empresa que EMITE el recibo (aparece una sola vez,
  arriba del todo, junto con su direccion/telefono/RUC) -- va SOLO en el
  campo agencia_logistica, jamas como valor de "finca" de un item.
- finca es la EXPORTADORA/FLORICOLA de Ecuador que embarca la carga (suele
  coincidir con nombres como EXPOFLOR, OASISFLOWER, AMAZINGROSES, o
  cualquier otro exportador mencionado tras "EXP:"/"FINCA:"/"FLORICOLA").
- cliente es el COMPRADOR final, casi siempre en EEUU/extranjero (nombres
  con LLC, INC, CORP, FLOWER MARKET, o un codigo tipo "KZ"/"HB"/"QB" al
  lado). Si un item no tiene un comprador identificable, cliente: null --
  pero NUNCA copies ahi el valor de finca ni el de agencia_logistica.
Antes de responder, verificá que ningun item tenga finca == agencia_logistica
ni cliente == finca.

REGLA CRITICA — TEMPERATURA, siempre UN SOLO NUMERO, nunca texto:
- "Max-9.0 Min-9.0 Prom-9.0": el guion es separador ("Max: 9.0"), NO es un
  signo negativo. Nunca devuelvas un numero negativo por esto.
- Si hay "Prom" (promedio), usa ese valor.
- Si no hay "Prom" pero hay Max y Min, calcula el promedio de los dos.
- Si hay una lista tipo "7C/7C/6C/7C/7C" (Kuehne+Nagel), calcula el promedio
  de todos los valores.
- Si no hay ningun dato de temperatura, usa null. Jamas inventes un valor.
- El campo final es SIEMPRE un numero (o null) — nunca un string con varios
  valores o palabras como "Max"/"Min"/"Prom" dentro.

REGLA CRITICA — FULLS y PIEZAS son DOS campos separados, no los combines:
- "TOTAL: 1.75 / 7" significa 1,75 fulls / 7 piezas — el primer numero
  (con decimales) es total_fulls, el segundo (entero) es total_piezas.
- "BXS/PCS: 1.750 / 7" es el mismo patron: total_fulls=1.75, total_piezas=7
  (aunque el primer numero tenga un punto de miles aparente, es un decimal:
  1.750 = "1 full con 750 milesimas", no "mil setecientos cincuenta").
- Si el recibo trae el total por finca (varias lineas "TOTAL EXP:"), los
  totales de cada item son los de SU PROPIA linea, no el total general del
  documento.
- Si solo aparece un numero y no queda claro si es fulls o piezas, ponelo en
  total_fulls, dejá total_piezas en null, y anotalo en observaciones.

REGLA CRITICA — NUMERO DE INGRESO vs AWB vs HAWB, son 3 campos distintos,
no los mezcles:
- "numero_ingreso" (cabecera, uno por todo el recibo): el numero interno de
  la bodega para ese ingreso completo -- suele venir como "INGRESO N#",
  "INGRESO:", "INGRESO# FISICO", "N RECEPCION", "Remision de Cultivo".
- "awb" (por CADA item/finca, nunca en la cabecera): el numero maestro de
  la guia aerea de esa finca especifica -- AWB y MAWB son el MISMO concepto
  (MAWB es solo el nombre completo de AWB), asi que cualquiera de las dos
  etiquetas va en este campo.
- "hawb" (por CADA item/finca): la guia house, que emite el consolidador/
  forwarder para ese embarque puntual dentro del AWB maestro -- es un
  numero DISTINTO del AWB, no una repeticion. Verificado: 1.212 de 3.515
  recibos traen AWB y HAWB a la vez, y 232 con valores CLARAMENTE distintos
  entre si (ej. AWB 14511884596 / HAWB 1096850) -- nunca asumas que son el
  mismo numero repetido. Un recibo con varias fincas casi siempre trae una
  guia distinta por finca.
- OJO con el formato del AWB: es UN solo numero de 11 digitos que se escribe
  con un guion y un espacio, "NNN-NNNN NNNN" (los 3 primeros identifican a la
  aerolinea). Ejemplo: "230-6591 9346" es UN awb completo, NO un awb
  "230-6591" mas un hawb "9346". Solo llena "hawb" si el recibo trae DOS
  numeros claramente separados y etiquetados como cosas distintas.
- Si el recibo solo trae un numero de guia sin etiqueta clara de cual es,
  ponelo en "awb" (es el mas comun cuando no se distingue) y dejá "hawb" en
  null. Un encabezado combinado tipo "AWB/HAWB" o "AWB HAWB" seguido de un
  unico numero significa que ese numero es el awb, no que haya dos.
- Si el recibo no distingue ningun numero de guia del numero de ingreso,
  ponelo en numero_ingreso (cabecera) y dejá awb/hawb en null.

REGLA CRITICA — nombre_chofer, cedula y placa son TRES datos distintos, y en
el OCR casi siempre aparecen SIN etiqueta, en lineas seguidas (ej. "EDWIN
CACHAGO" / "1717050981" / "PCY2612", una debajo de otra, sin las palabras
"CHOFER:"/"CEDULA:"/"PLACA:" delante). Distinguilos por su forma, no por si
tienen etiqueta:
- nombre_chofer: texto con letras, normalmente 2-4 palabras (nombre y apellido)
- cedula: solo digitos, normalmente 10 (cedula ecuatoriana)
- placa: combinacion corta de letras y numeros (ej. PCY2612, PAB4983, IAA2070)
Nunca los combines en un solo campo ni asumas que la primera linea despues
del bloque de carga es el chofer sin verificar que tenga forma de nombre.

FECHA: normaliza siempre a dd/MM/yyyy sin importar el formato de origen
(dd/mm/yyyy, yyyy-mm-dd, o dd-Mon-yy como "19-Aug-26").

VALIDEZ: si el texto no corresponde en absoluto a un recibo de bodega (por
ejemplo, una captura de una conversacion de chat, o texto sin ninguna
relacion con logistica), responde "es_recibo_valido": false y deja el resto
de los campos en null / lista vacia. No lo interpretes igual "por si acaso".

CALIDAD: evalua "alta" si el texto es claro y los campos se leen sin
ambiguedad, "media" si hay partes dudosas pero se pudo interpretar, "baja"
si el OCR esta muy cortado o ilegible (frecuente en recibos con OCR de
menos de 80 caracteres).

Responde UNICAMENTE con este JSON, sin markdown ni texto adicional:
{
  "es_recibo_valido": true,
  "fecha_documento": "dd/MM/yyyy o null",
  "hora_documento": "HH:mm o null",
  "agencia_logistica": "nombre de la empresa emisora del recibo (la agencia de carga/bodega), o null",
  "nombre_chofer": "string o null",
  "cedula": "string o null",
  "placa": "string o null",
  "numero_ingreso": "el numero interno de bodega de TODO el recibo, o null",
  "temperatura_c": 0.0,
  "observaciones": "string, vacio si no hay nada relevante",
  "calidad_ocr": "alta|media|baja",
  "items": [
    {
      "finca": "nombre de la finca/exportadora tal como aparece",
      "cliente": "nombre del cliente final, o null si no aparece",
      "awb": "AWB/MAWB (numero maestro) de ESTA finca especifica, o null",
      "hawb": "HAWB (numero house) de ESTA finca especifica, o null",
      "cajas_detalle": "texto tipo 'FB:0 HB:0 QB:7' o el detalle que traiga el recibo",
      "total_fulls": 0.0,
      "total_piezas": 0
    }
  ]
}"""


def limpiar_respuesta_json(texto: str) -> dict:
    """Los tres proveedores probados (DeepSeek, Gemini, Claude) a veces
    envuelven el JSON en un bloque ```json ... ``` pese a pedirse lo
    contrario en el prompt. Se limpia antes de parsear."""
    t = texto.strip()
    t = re.sub(r"^```(json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    return json.loads(t)


# Columnas de destino, para referencia rapida al conectar esto con
# entregas_locales / entregas_locales_detalle (migracion 038):
#
#   Sheet (Fecha/Hora Registro)  -> entregas_locales_raw, tal cual (NO pasa
#                                    por el LLM: son timestamps del propio
#                                    bot, ya confiables)
#   es_recibo_valido             -> decide si se crea entregas_locales o se
#                                    descarta la fila (se guarda igual en
#                                    entregas_locales_raw para trazabilidad)
#   fecha_documento               -> entregas_locales.fecha_documento (DATE)
#   hora_documento                -> entregas_locales.hora_documento
#   agencia_logistica              -> entregas_locales.agencia_raw (agencia_id
#                                    se resuelve despues contra cargo_agencies)
#   nombre_chofer/cedula/placa    -> entregas_locales, tal cual
#   numero_ingreso                 -> entregas_locales.numero_ingreso (numero
#                                    interno de bodega, UNO por todo el recibo)
#   temperatura_c                  -> entregas_locales.temperatura_c (NUMERIC)
#   observaciones                  -> entregas_locales.observaciones
#   calidad_ocr                    -> entregas_locales.calidad_ocr
#   items[].finca                  -> entregas_locales_detalle.finca_raw
#                                    (finca_id se resuelve despues contra farms)
#   items[].cliente                 -> entregas_locales_detalle.cliente
#   items[].awb                      -> entregas_locales_detalle.awb (= MAWB,
#                                    UNO por cada finca del recibo)
#   items[].hawb                     -> entregas_locales_detalle.hawb (house,
#                                    puede diferir del awb -- no es el mismo dato)
#   items[].cajas_detalle            -> entregas_locales_detalle.cajas_detalle
#   items[].total_fulls              -> entregas_locales_detalle.total_fulls
#   items[].total_piezas             -> entregas_locales_detalle.total_piezas


# ============================================================
#  Llamada al modelo + persistencia
# ============================================================
# Proveedor elegido: Claude (2026-09-06). La decision se tomo con datos, no
# por preferencia: sobre 20 recibos reales evaluados con este mismo prompt,
# DeepSeek cometio 11 errores objetivos contra 3 de Claude. Y sobre todo, los
# errores son de distinta gravedad -- el de Claude (repetir el nombre de la
# finca en el campo cliente, fila 328) se ve a simple vista; el de DeepSeek
# (devolver total_fulls = 0.0 en las 11 lineas de la fila 1105, teniendo el
# numero disponible dentro de cajas_detalle) es silencioso y se colaria a un
# reporte de fulls despachados sin que nadie lo note.

import logging
import os
from datetime import datetime, timezone

from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine

logger = logging.getLogger(__name__)
UTC = timezone.utc

MODELO = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 2000


def _cliente_anthropic():
    import anthropic

    clave = os.getenv("ANTHROPIC_API_KEY", "")
    if not clave:
        raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno.")
    return anthropic.Anthropic(api_key=clave)


def interpretar(texto_ocr: str) -> dict:
    """Una llamada al modelo por recibo. Devuelve el dict ya parseado."""
    cliente = _cliente_anthropic()
    r = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        system=PROMPT_EXTRACCION,
        messages=[{"role": "user", "content": texto_ocr}],
    )
    return limpiar_respuesta_json(r.content[0].text)


def _a_numero(v):
    """El modelo puede devolver '1.75', 1.75 o None. Nunca revienta por esto."""
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _a_fecha(v):
    """dd/MM/yyyy -> date. El prompt exige ese formato, pero si el modelo
    devuelve otra cosa se guarda NULL en vez de romper la carga entera."""
    if not v:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _resolver_catalogos(conn):
    """Mapa {variante en mayusculas -> id} para agencias y fincas.

    Se resuelve contra `ocr_variants` y el nombre oficial de cargo_agencies /
    farms -- las mismas tablas que ya existian para esto desde las migraciones
    002/003 y que la pestaña vieja nunca uso.
    """
    agencias = {}
    for fila in conn.execute(text(
        "SELECT id, name, dartis_name, ocr_variants FROM cargo_agencies WHERE active"
    )).mappings():
        for texto in [fila["name"], fila["dartis_name"], *(fila["ocr_variants"] or [])]:
            if texto:
                agencias[texto.strip().upper()] = fila["id"]

    fincas = {}
    for fila in conn.execute(text(
        "SELECT id, name, code, ocr_variants FROM farms WHERE active"
    )).mappings():
        for texto in [fila["name"], fila["code"], *(fila["ocr_variants"] or [])]:
            if texto:
                fincas[texto.strip().upper()] = fila["id"]
    return agencias, fincas


def _normalizar(texto: str) -> str:
    """Aplana el texto para comparar catalogos: mayusculas, sin acentos, sin
    espacios ni puntuacion.

    Sin esto el match falla en casos obvios y frecuentes: "ONE TEAM CARGO SA"
    no coincide con "ONETEAMCARGO S.A." ni "LDSEXPORT IMPORT CIA.LTDA." con
    "LDS EXPORT", solo por donde cayeron los espacios y los puntos. Medido
    sobre datos reales: 3 de las primeras 5 agencias quedaban sin resolver
    antes de normalizar asi.
    """
    import unicodedata

    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", t.upper())


def _buscar_id(catalogo: dict, valor: str):
    """Match exacto normalizado primero; si no, por contencion.

    El OCR deforma los nombres constantemente (191 variantes distintas para
    ~36 agencias reales), asi que el match exacto solo no alcanza. Lo que NO
    se hace es adivinar con similitud difusa: si no hay contencion clara se
    deja NULL, y el texto crudo queda igual guardado en agencia_raw/finca_raw
    para poder resolverlo despues sin perder el dato.
    """
    if not valor:
        return None
    v = _normalizar(valor)
    if not v:
        return None
    normalizado = {_normalizar(k): id_ for k, id_ in catalogo.items()}
    if v in normalizado:
        return normalizado[v]
    # Contencion en cualquier direccion, exigiendo un largo minimo para no
    # cruzar por coincidencias cortas ("LDS" dentro de cualquier palabra).
    for clave, id_ in normalizado.items():
        if len(clave) >= 6 and (clave in v or v in clave):
            return id_
    return None


def interpretar_pendientes(limite: int = 25, recientes_primero: bool = True) -> dict:
    """Procesa filas de `entregas_locales_raw` que aun no tienen interpretacion.

    Va de a lotes chicos a proposito: son ~3.500 recibos, cada llamada al
    modelo tarda ~3 s, y hacerlo todo de una vez seria una peticion HTTP de
    horas que ningun timeout de Render sobrevive. La pantalla llama a este
    endpoint repetidamente hasta que `pendientes` llega a 0.

    Arranca por los recibos MAS RECIENTES por defecto: el Sheet tiene
    historia desde febrero 2026, pero `dartis_ventas` solo desde junio, asi
    que procesar de viejo a nuevo gasta llamadas al modelo en recibos que
    todavia no tienen contra que cruzarse. Al reves, cada lote empieza a
    aportar cruces reales desde el primero.
    """
    orden = "DESC" if recientes_primero else "ASC"
    with engine.connect() as conn:
        pendientes = conn.execute(text(f"""
            SELECT r.id, r.fila_sheet, r.texto_ocr, r.ver_foto_url
            FROM entregas_locales_raw r
            LEFT JOIN entregas_locales e ON e.raw_id = r.id
            WHERE e.id IS NULL
              AND r.texto_ocr IS NOT NULL
              AND length(r.texto_ocr) > 30
            ORDER BY r.fila_sheet {orden}
            LIMIT :limite
        """), {"limite": limite}).mappings().all()

    procesadas = 0
    invalidas = 0
    errores = []

    for fila in pendientes:
        try:
            datos = interpretar(fila["texto_ocr"])
        except Exception as e:  # una fila mala no puede frenar el lote entero
            logger.warning("Fila %s: fallo la interpretacion: %s", fila["fila_sheet"], e)
            errores.append({"fila_sheet": fila["fila_sheet"], "error": str(e)[:200]})
            continue

        es_valido = bool(datos.get("es_recibo_valido", True))
        calidad = datos.get("calidad_ocr")

        with engine.begin() as conn:
            agencias, fincas = _resolver_catalogos(conn)
            agencia_raw = (datos.get("agencia_logistica") or "").strip() or "(sin identificar)"

            entrega_id = conn.execute(text("""
                INSERT INTO entregas_locales (
                    raw_id, fecha_documento, hora_documento, numero_ingreso,
                    agencia_id, agencia_raw, nombre_chofer, cedula, placa,
                    temperatura_c, observaciones, foto_url, calidad_ocr,
                    modelo_interpretacion, interpretado_at
                ) VALUES (
                    :raw_id, :fecha_documento, :hora_documento, :numero_ingreso,
                    :agencia_id, :agencia_raw, :nombre_chofer, :cedula, :placa,
                    :temperatura_c, :observaciones, :foto_url, :calidad_ocr,
                    :modelo, now()
                ) RETURNING id
            """), {
                "raw_id": fila["id"],
                "fecha_documento": _a_fecha(datos.get("fecha_documento")),
                "hora_documento": datos.get("hora_documento"),
                "numero_ingreso": datos.get("numero_ingreso"),
                "agencia_id": _buscar_id(agencias, agencia_raw),
                "agencia_raw": agencia_raw,
                "nombre_chofer": datos.get("nombre_chofer"),
                "cedula": datos.get("cedula"),
                "placa": datos.get("placa"),
                "temperatura_c": _a_numero(datos.get("temperatura_c")),
                "observaciones": datos.get("observaciones"),
                "foto_url": fila["ver_foto_url"],
                "calidad_ocr": calidad if calidad in ("alta", "media", "baja") else None,
                "modelo": MODELO,
            }).scalar()

            items = datos.get("items") or []
            if not es_valido:
                invalidas += 1
                items = []

            tuplas = []
            for it in items:
                finca_raw = (it.get("finca") or "").strip()
                if not finca_raw:
                    continue
                tuplas.append((
                    entrega_id, _buscar_id(fincas, finca_raw), finca_raw,
                    it.get("cliente"), it.get("awb"), it.get("hawb"),
                    it.get("cajas_detalle"),
                    _a_numero(it.get("total_fulls")), _a_numero(it.get("total_piezas")),
                ))
            if tuplas:
                cursor = conn.connection.cursor()
                execute_values(cursor, """
                    INSERT INTO entregas_locales_detalle (
                        entrega_id, finca_id, finca_raw, cliente, awb, hawb,
                        cajas_detalle, total_fulls, total_piezas
                    ) VALUES %s
                """, tuplas)

        procesadas += 1

    with engine.connect() as conn:
        restantes = conn.execute(text("""
            SELECT count(*) FROM entregas_locales_raw r
            LEFT JOIN entregas_locales e ON e.raw_id = r.id
            WHERE e.id IS NULL AND r.texto_ocr IS NOT NULL AND length(r.texto_ocr) > 30
        """)).scalar()

    return {
        "procesadas": procesadas,
        "invalidas": invalidas,
        "errores": errores,
        "pendientes": restantes,
        "modelo": MODELO,
    }

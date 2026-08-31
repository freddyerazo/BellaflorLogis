"""Cliente de la API movil de Agrocalidad (backend de la app AGRO Movil).

Reemplaza al scraping con Playwright que corria en GitHub Actions: expone los
mismos datos como REST/JSON, sin captcha ni bloqueo anti-bot. La cadena cruda
tarda ~1,7 s (las dos llamadas van en paralelo) contra los 30-90 s del worker.

    https://guia.agrocalidad.gob.ec/agrodb/aplicaciones/mvc/AplicacionMovilExternos/

Cadena de consulta:
    obtenerProductosPorSubtipoProducto/<subtipo>          -> catalogo de productos
    obtenerDatosProductos/<id_producto>                   -> ficha (cientifico, partida)
    obtenerPaisProducto/<id_producto>/<movimiento>        -> paises con requisitos
    obtenerRequisitosPorPais/<id_producto>/<movimiento>/<id_localizacion>

CUIDADO con el movimiento: va como la palabra completa y CON TILDE
("Exportación"). Sin tilde el servicio responde 200 con lista vacia, no un
error — es decir, falla en silencio.

Nota: esta API es publica pero es el backend interno de una app oficial, no una
API publicada como abierta. Para uso formal corresponde convenio con Agrocalidad.
"""

import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE = ("https://guia.agrocalidad.gob.ec/agrodb/aplicaciones/mvc/"
        "AplicacionMovilExternos")

TIMEOUT = 30
USER_AGENT = "BLIS/1.0 (Bellaflor Group)"

# Movimientos tal como los espera el servicio. La tilde es obligatoria.
MOVIMIENTOS = ("Exportación", "Importación", "Tránsito", "Nacional")

# Subtipos del area vegetal que le interesan a Bellaflor.
SUBTIPO_FLORES = 21
SUBTIPO_FOLLAJES = 23
SUBTIPOS_BELLAFLOR = (SUBTIPO_FLORES, SUBTIPO_FOLLAJES)

# El catalogo son ~2.300 productos que casi no cambian: se cachea en memoria.
_CACHE_TTL = 60 * 60 * 12
_cache_catalogo: dict = {"datos": None, "ts": 0.0}
_lock = threading.Lock()


class AgrocalidadError(RuntimeError):
    """Fallo al consultar la API de Agrocalidad."""


def normalizar(texto: str) -> str:
    """Mayusculas sin tildes, para comparar nombres de producto y pais."""
    t = str(texto or "").strip().upper()
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _pedir(ruta: str) -> list:
    """POST a la API. Devuelve siempre una lista (vacia si no hay datos).

    Reintenta una vez ante fallo de red o error 5xx: el servicio es de un
    organismo publico y ocasionalmente corta la conexion. No se reintenta un
    4xx, que siempre indica una ruta mal armada de nuestro lado.
    """
    url = f"{BASE}/{ruta.lstrip('/')}"
    resp = None
    ultimo_error: Exception | None = None

    for intento in range(2):
        try:
            with httpx.Client(timeout=TIMEOUT) as cliente:
                resp = cliente.post(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code < 500:
                break
            ultimo_error = AgrocalidadError(
                f"Agrocalidad respondio {resp.status_code} en {ruta}")
        except httpx.HTTPError as e:
            ultimo_error = e
            resp = None
        if intento == 0:
            time.sleep(0.5)

    if resp is None:
        raise AgrocalidadError(
            f"No se pudo contactar a Agrocalidad: {ultimo_error}") from ultimo_error

    if resp.status_code == 400:
        # El servicio responde 400 con cuerpo vacio cuando falta un segmento
        # de la ruta; es un error de programacion, no del usuario.
        raise AgrocalidadError(f"Agrocalidad rechazo la ruta {ruta} (400)")
    if resp.status_code >= 400:
        raise AgrocalidadError(f"Agrocalidad respondio {resp.status_code} en {ruta}")

    try:
        datos = resp.json()
    except ValueError as e:
        raise AgrocalidadError(f"Agrocalidad no devolvio JSON en {ruta}") from e

    return datos if isinstance(datos, list) else []


def _validar_movimiento(movimiento: str) -> str:
    if movimiento not in MOVIMIENTOS:
        raise AgrocalidadError(
            f"Movimiento invalido: {movimiento!r}. Debe ser uno de {MOVIMIENTOS} "
            "(con tilde; sin ella el servicio devuelve vacio sin avisar)."
        )
    return movimiento


# ---------------------------------------------------------------------------
# Catalogo de productos
# ---------------------------------------------------------------------------
def catalogo_productos(forzar: bool = False) -> list[dict]:
    """Flores (subtipo 21) + follajes (subtipo 23), cacheado en memoria.

    Cada elemento: {id_producto, nombre_comun, id_subtipo_producto}.
    """
    with _lock:
        vigente = (
            _cache_catalogo["datos"] is not None
            and (time.time() - _cache_catalogo["ts"]) < _CACHE_TTL
        )
        if vigente and not forzar:
            return _cache_catalogo["datos"]

    productos = []
    for subtipo in SUBTIPOS_BELLAFLOR:
        for p in _pedir(f"RestWsRequisitos/obtenerProductosPorSubtipoProducto/{subtipo}"):
            productos.append({
                "id_producto": p["id_producto"],
                "nombre_comun": (p.get("nombre_comun") or "").strip(),
                "id_subtipo_producto": subtipo,
            })

    with _lock:
        _cache_catalogo["datos"] = productos
        _cache_catalogo["ts"] = time.time()
    return productos


def buscar_productos(termino: str, limite: int = 50) -> list[dict]:
    """Busca por coincidencia en el nombre. Los exactos y los que empiezan
    por el termino van primero, que es lo que el usuario espera al tipear."""
    t = normalizar(termino)
    if len(t) < 2:
        return []

    exactos, prefijos, contienen = [], [], []
    for p in catalogo_productos():
        n = normalizar(p["nombre_comun"])
        if n == t:
            exactos.append(p)
        elif n.startswith(t):
            prefijos.append(p)
        elif t in n:
            contienen.append(p)

    orden = lambda p: len(p["nombre_comun"])  # noqa: E731
    return (sorted(exactos, key=orden) + sorted(prefijos, key=orden)
            + sorted(contienen, key=orden))[:limite]


def ficha_producto(id_producto: int) -> dict | None:
    """Ficha del producto: nombre cientifico, partida arancelaria, area, codigo.

    OJO: `codigo_producto` NO identifica un producto — el 0001 lo comparten
    rosa, clavel, crisantemo, aster y otros. Para cruzar usar id_producto.
    """
    filas = _pedir(f"RestWsRequisitos/obtenerDatosProductos/{int(id_producto)}")
    return filas[0] if filas else None


def paises_producto(id_producto: int, movimiento: str = "Exportación") -> list[dict]:
    """Destinos con requisitos publicados para ese producto y movimiento.

    Cada elemento: {id_localizacion, nombre_pais}. La lista es propia de cada
    producto: rosa tiene 157 destinos, Ammi majus 66 y Asparagus 3.

    No son solo paises: tambien aparecen bloques como "Unión Europea" (2062) y
    "Comunidad económica Euroasiática - CEEA" (2064).

    Se descartan las entradas sin `id_localizacion`: Agrocalidad devuelve algunas
    (San Bartolome y San Martin en el caso de rosa) y sin ese id la consulta de
    requisitos no se puede armar, asi que ofrecerlas solo llevaria a un error.
    """
    _validar_movimiento(movimiento)
    filas = _pedir(
        f"RestWsRequisitos/obtenerPaisProducto/{int(id_producto)}/{movimiento}")
    return [p for p in filas if p.get("id_localizacion") is not None]


def requisitos(id_producto: int, id_localizacion: int,
               movimiento: str = "Exportación") -> list[dict]:
    """Requisitos para la combinacion producto/movimiento/pais.

    Cada elemento: {id_requisito, nombre, requisito, detalle_impreso}.
    Lista vacia = Agrocalidad no tiene requisitos registrados para ese destino;
    no es un error (pasa, por ejemplo, con varias especies hacia Chile).
    """
    _validar_movimiento(movimiento)
    return _pedir(
        f"RestWsRequisitos/obtenerRequisitosPorPais/{int(id_producto)}"
        f"/{movimiento}/{int(id_localizacion)}")


def codigo_con_letra(codigo_producto: str | None) -> str | None:
    """La web muestra "A0007" donde la API devuelve "0007".

    Se antepone la letra para que el codigo guardado sea el mismo que ve el
    usuario en guia.agrocalidad.gob.ec. Verificado contra la web y contra las
    157 filas historicas del scraping, todas de area SV con prefijo 'A'.
    """
    if not codigo_producto:
        return None
    codigo = str(codigo_producto).strip()
    return codigo if codigo[:1].isalpha() else f"A{codigo}"


def consultar(id_producto: int, id_localizacion: int,
              movimiento: str = "Exportación") -> dict:
    """Cadena completa: ficha + requisitos.

    Las dos llamadas son independientes entre si, asi que van en paralelo:
    secuenciales suman ~1,6 s y concurrentes cuestan lo que la mas lenta.
    """
    _validar_movimiento(movimiento)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_ficha = pool.submit(ficha_producto, id_producto)
        f_reqs = pool.submit(requisitos, id_producto, id_localizacion, movimiento)
        ficha = f_ficha.result()
        reqs = f_reqs.result()

    if ficha is None:
        raise AgrocalidadError(
            f"Agrocalidad no tiene ficha para el producto {id_producto}")

    return {
        "ficha": ficha,
        "requisitos": reqs,
        "status": "CON_REQUISITOS" if reqs else "SIN_REQUISITOS_REGISTRADOS",
    }

"""Pre-alerta por correo de un despacho de Armellini.

Replica el formato que Bellaflor ya venia enviando a mano: en ingles, con
una tabla de PO, fechas y conteo de cajas desglosado por finca y por tipo
de caja, mas el tamano de cada tipo. No lleva adjunto.

    POs and piece counts for Heinen's

    Good afternoon,
    I hope you are doing well.
    Please find below the pre-alert for the Heinen's shipment for your review.

    | PO           | 2631008034498          |
    | Miami Date   | Aug - 16               |
    | DD Heinens   | Aug - 19               |
    |              | BOXES                  |
    |              | QB      | EB           |
    | EXPOFLOR ... |         | 20           |
    | OASISFLOWER  |         |              |
    | AMAZINGROSES |         |              |
    | Total        |         | 20           |
    | EB SIZE      | 41.0 X 6.0 X 5.0 INCHES|

Las fincas se listan siempre las tres del catalogo, aunque vayan en cero:
asi es como se venia enviando.

"Miami Date" es la salida del camion (caja_fecha_transportador). "DD" es
la entrega en destino, que no esta en ninguna fuente: se calcula sumando
armellini_consignees.dias_entrega.
"""

from datetime import datetime, timedelta
from html import escape

from sqlalchemy import text

from app.database.connection import engine
from app.services import mailer

# Columnas de tipo de caja que siempre se muestran, en este orden, aunque
# el envio no lleve ninguna de ese tipo. Cualquier otro tipo presente se
# agrega despues.
TIPOS_FIJOS = ("QB", "EB")

# Orden en que se listan las fincas, igual que en los correos enviados a
# mano. Cualquier finca que no este aqui va al final, alfabeticamente.
ORDEN_FINCAS = ("EXPOFLOR", "OASISFLOWER", "AMAZINGROSES")

_EXPORT = """
    SELECT id, filename, shipdate, total_cajas, awbs, pos, barcodes,
           correo_enviado_at, correo_destinatarios
    FROM armellini_exports WHERE id = :id
"""

_DESTINOS = """
    SELECT o.nombre_cliente,
           count(*)                            AS cajas,
           max(ac.consignee_code)              AS consignee_code,
           coalesce(max(ac.emails), '{}')      AS emails,
           coalesce(max(ac.dias_entrega), 3)   AS dias_entrega
    FROM expoflor_operaciones_cajas o
    LEFT JOIN armellini_consignees ac ON ac.destinatario = o.nombre_cliente
    WHERE o.codigo_pieza = ANY(:barcodes)
    GROUP BY o.nombre_cliente
    ORDER BY o.nombre_cliente
"""

# Conteo por finca y tipo de caja, con las medidas de cada tipo.
_DESGLOSE = """
    SELECT o.nombre_cultivo, o.empaque, count(*) AS cajas,
           max(o.largo_inch) AS largo, max(o.ancho_inch) AS ancho, max(o.alto_inch) AS alto
    FROM expoflor_operaciones_cajas o
    WHERE o.codigo_pieza = ANY(:barcodes)
    GROUP BY o.nombre_cultivo, o.empaque
"""

_FECHA_SALIDA = """
    SELECT max(fecha_carrier) AS salida
    FROM expoflor_operaciones_cajas WHERE codigo_pieza = ANY(:barcodes)
"""

_FINCAS = "SELECT code, name FROM farms WHERE active"


def _ordenar_fincas(fincas: list[dict]) -> list[str]:
    """Las conocidas en el orden de siempre; el resto al final, alfabetico."""
    def clave(f):
        code = (f["code"] or "").upper()
        return (ORDEN_FINCAS.index(code) if code in ORDEN_FINCAS else len(ORDEN_FINCAS),
                f["name"] or "")
    return [f["name"] for f in sorted(fincas, key=clave)]


def _fecha(d) -> str:
    """'Aug - 16', como en los correos enviados a mano."""
    return f"{d.strftime('%b')} - {d.day}" if d else "—"


def datos(export_id: int) -> dict | None:
    with engine.connect() as conn:
        export = conn.execute(text(_EXPORT), {"id": export_id}).mappings().first()
        if export is None:
            return None

        barcodes = list(export["barcodes"] or [])
        p = {"barcodes": barcodes}
        destinos = [dict(d) for d in conn.execute(text(_DESTINOS), p).mappings()]
        desglose = [dict(d) for d in conn.execute(text(_DESGLOSE), p).mappings()]
        salida = conn.execute(text(_FECHA_SALIDA), p).scalar()
        fincas = [dict(f) for f in conn.execute(text(_FINCAS)).mappings()]

    correos = mailer.normalizar([c for d in destinos for c in (d["emails"] or [])])
    sin_correo = sorted({d["nombre_cliente"] for d in destinos if not (d["emails"] or [])})

    # Tipos de caja: los fijos primero, luego cualquier otro que aparezca.
    presentes = {d["empaque"] for d in desglose if d["empaque"]}
    tipos = list(TIPOS_FIJOS) + sorted(presentes - set(TIPOS_FIJOS))

    conteo = {(d["nombre_cultivo"], d["empaque"]): d["cajas"] for d in desglose}
    medidas = {
        d["empaque"]: f"{d['largo']}.0 X {d['ancho']}.0 X {d['alto']}.0 INCHES"
        for d in desglose if d["empaque"]
    }

    dias = max((d["dias_entrega"] for d in destinos), default=3)
    return {
        "export": dict(export),
        "destinos": destinos,
        "destinatarios": correos,
        "destinos_sin_correo": sin_correo,
        "fincas": _ordenar_fincas(fincas),
        "tipos": tipos,
        "conteo": conteo,
        "medidas": medidas,
        "fecha_salida": salida,
        "fecha_entrega": salida + timedelta(days=dias) if salida else None,
        "dias_entrega": dias,
    }


def _nombres(destinos: list[dict]) -> str:
    return ", ".join(d["nombre_cliente"] for d in destinos) or "Armellini"


def _asunto(d: dict) -> str:
    return f"POs and piece counts for {_nombres(d['destinos'])}"


def _filas_tabla(d: dict):
    """(etiqueta, [valor por tipo]) para las filas de fincas y el total."""
    filas = []
    for finca in d["fincas"]:
        filas.append((finca, [d["conteo"].get((finca, t)) for t in d["tipos"]]))
    total = [
        sum(v for (f, tt), v in d["conteo"].items() if tt == t) or None
        for t in d["tipos"]
    ]
    return filas, total


def _cuerpos(d: dict) -> tuple[str, str]:
    destino = _nombres(d["destinos"])
    po = ", ".join(d["export"]["pos"] or []) or "—"
    miami = _fecha(d["fecha_salida"])
    entrega = _fecha(d["fecha_entrega"])
    tipos = d["tipos"]
    filas, total = _filas_tabla(d)

    # --- texto plano ---------------------------------------------------
    ancho = max([len(f) for f, _ in filas] + [12])
    def linea(et, vals):
        return "  " + et.ljust(ancho) + "".join(("" if v is None else str(v)).rjust(8) for v in vals)

    t = [
        "Good afternoon,",
        "",
        "I hope you are doing well.",
        "",
        f"Please find below the pre-alert for the {destino} shipment for your review.",
        "",
        "  " + "PO".ljust(ancho) + po,
        "  " + "Miami Date".ljust(ancho) + miami,
        "  " + f"DD {destino}".ljust(ancho) + entrega,
        "",
        "  " + "BOXES".rjust(ancho + 8 * len(tipos)),
        "  " + "".ljust(ancho) + "".join(x.rjust(8) for x in tipos),
    ]
    t += [linea(f, v) for f, v in filas]
    t += [linea("Total", total), ""]
    t += [f"  {tipo} SIZE: {d['medidas'][tipo]}" for tipo in tipos if tipo in d["medidas"]]
    t += [
        "",
        "Kindly let me know if you need any additional information or documentation.",
        "",
        "Thank you in advance for your support.",
        "",
        "Best regards,",
    ]
    texto = "\n".join(t)

    # --- html ------------------------------------------------------------
    borde = "border:1px solid #999;padding:6px 10px"
    def celda(v, extra=""):
        return f'<td style="{borde};text-align:right;{extra}">{"" if v is None else v}</td>'

    encabezado = "".join(
        f'<td style="{borde};text-align:center;font-weight:600">{escape(x)}</td>' for x in tipos)
    cuerpo = "".join(
        f'<tr><td style="{borde}">{escape(f)}</td>' + "".join(celda(v) for v in vals) + "</tr>"
        for f, vals in filas)
    fila_total = ('<tr><td style="%s;font-weight:700">Total</td>' % borde
                  + "".join(celda(v, "font-weight:700") for v in total) + "</tr>")
    tamanos = "".join(
        f'<tr><td style="{borde};font-weight:700">{escape(t_)} SIZE</td>'
        f'<td style="{borde};text-align:center" colspan="{len(tipos)}">{escape(d["medidas"][t_])}</td></tr>'
        for t_ in tipos if t_ in d["medidas"])
    n = len(tipos)

    html = f"""<div style="font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#1a1a1a;line-height:1.6;font-size:15px">
  <p>Good afternoon,</p>
  <p>I hope you are doing well.</p>
  <p>Please find below the <strong>pre-alert</strong> for the <strong>{escape(destino)}</strong> shipment for your review.</p>
  <table style="border-collapse:collapse;margin:18px 0">
    <tr><td style="{borde};font-weight:700">PO</td>
        <td style="{borde};text-align:center" colspan="{n}">{escape(po)}</td></tr>
    <tr><td style="{borde};font-weight:700">Miami Date</td>
        <td style="{borde};text-align:right" colspan="{n}">{escape(miami)}</td></tr>
    <tr><td style="{borde};font-weight:700">DD {escape(destino)}</td>
        <td style="{borde};text-align:right" colspan="{n}">{escape(entrega)}</td></tr>
    <tr><td style="{borde}"></td>
        <td style="{borde};text-align:center;font-weight:700;background:#e8e8e8" colspan="{n}">BOXES</td></tr>
    <tr><td style="{borde}"></td>{encabezado}</tr>
    {cuerpo}
    {fila_total}
  </table>
  <table style="border-collapse:collapse;margin-bottom:18px">{tamanos}</table>
  <p>Kindly let me know if you need any additional information or documentation.</p>
  <p>Thank you in advance for your support.</p>
  <p>Best regards,</p>
</div>"""
    return texto, html


def vista_previa(export_id: int) -> dict | None:
    d = datos(export_id)
    if d is None:
        return None
    texto, html = _cuerpos(d)
    return {
        **d,
        "asunto": _asunto(d),
        "texto": texto,
        "html": html,
        "configurado": mailer.configurado(),
        "remitente": mailer.usuario() or None,
    }


def enviar(export_id: int, destinatarios: list[str] | None = None) -> dict:
    """Manda la pre-alerta y la registra. El registro se escribe DESPUES
    del envio: si el correo falla, no queda marcado como enviado."""
    previa = vista_previa(export_id)
    if previa is None:
        raise LookupError(f"El export {export_id} no existe.")

    destinos = mailer.normalizar(destinatarios) if destinatarios else previa["destinatarios"]
    if not destinos:
        faltan = ", ".join(previa["destinos_sin_correo"]) or "el destino de la carga"
        raise ValueError(
            f"No hay correos configurados para {faltan}. "
            "Agreguelos en la pestana Consignees antes de enviar."
        )

    enviados = mailer.enviar(destinos, previa["asunto"], previa["texto"], previa["html"])

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE armellini_exports
            SET correo_enviado_at = now(), correo_destinatarios = :dest, correo_asunto = :asunto
            WHERE id = :id
        """), {"dest": enviados, "asunto": previa["asunto"], "id": export_id})

    return {
        "export_id": export_id,
        "asunto": previa["asunto"],
        "destinatarios": enviados,
        "enviado_at": datetime.now(),
    }

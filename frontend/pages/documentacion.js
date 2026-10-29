const $ = (sel) => document.querySelector(sel);

function mostrarError(destino, mensaje) {
  const div = $(destino);
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = "msg-error";
  p.textContent = mensaje;
  div.appendChild(p);
}

function mostrarMensaje(destino, mensaje, clase = "msg-ok") {
  const div = $(destino);
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = clase;
  p.textContent = mensaje;
  div.appendChild(p);
}

// ---------- Facturas Logiztik: completar DETAIL / ORDER NUMBER ----------
$("#btn-logiztik-rellenar").addEventListener("click", async (e) => {
  const input = $("#logiztik-file");
  const archivo = input.files[0];
  if (!archivo) {
    mostrarError("#res-logiztik", "Elegí el PDF original de Logiztik antes de continuar.");
    return;
  }

  const boton = e.target;
  boton.disabled = true;
  mostrarMensaje("#res-logiztik", "Leyendo el PDF y cruzando contra Dartis...", "msg-info");

  const form = new FormData();
  form.append("file", archivo);

  try {
    const r = await fetch("/api/finance-documents/logiztik/rellenar", { method: "POST", body: form });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Error del servidor");
    }

    const invoiceNumber = r.headers.get("X-Invoice-Number");
    const awbNumber = r.headers.get("X-Awb-Number");
    const clientesEncontrados = r.headers.get("X-Clientes-Encontrados");

    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `${invoiceNumber || "factura"}_completada.pdf`;
    enlace.click();
    URL.revokeObjectURL(url);

    const detalleCruce =
      clientesEncontrados === "0"
        ? "sin cruce en Dartis para ese AWB -- se completó con \"SIN CRUCE EN DARTIS\""
        : `${clientesEncontrados} cliente(s) encontrado(s) en Dartis`;
    mostrarMensaje(
      "#res-logiztik",
      `Factura ${invoiceNumber} (AWB ${awbNumber}) completada y descargada -- ${detalleCruce}.`
    );
  } catch (err) {
    mostrarError("#res-logiztik", err.message);
  } finally {
    boton.disabled = false;
  }
});

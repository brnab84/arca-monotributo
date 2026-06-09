"""Servidor web: módulos de Parametrizaciones y Emisión de facturas.

Reutiliza el backend existente (wsaa, wsfev1, factura_pdf) sin modificarlo.
Ejecutar:  python app.py   ->  http://localhost:5000
"""
import json
import os
import traceback

from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file,
    abort,
)
from werkzeug.utils import secure_filename

import config
from wsfev1 import emitir_factura_c, ultimo_comprobante
from factura_pdf import generar_pdf

app = Flask(__name__)
# La clave de sesión se toma del entorno; sólo cae a un valor aleatorio en dev.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)

FACTURAS_DIR = "facturas"
os.makedirs(FACTURAS_DIR, exist_ok=True)


# ---------- Parametrizaciones ----------
@app.route("/parametrizaciones", methods=["GET", "POST"])
def parametrizaciones():
    if request.method == "POST":
        try:
            settings = {
                "homologacion": request.form.get("ambiente") == "homologacion",
                "cuit": int(request.form["cuit"]),
                "pto_vta": int(request.form["pto_vta"]),
                "cert_path": config.CERT_PATH,
                "key_path": config.KEY_PATH,
            }

            # Guardar certificado y clave si se pegaron
            cert_txt = request.form.get("cert", "").strip()
            key_txt = request.form.get("key", "").strip()
            if cert_txt:
                with open(config.CERT_PATH, "w") as f:
                    f.write(cert_txt + "\n")
            if key_txt:
                with open(config.KEY_PATH, "w") as f:
                    f.write(key_txt + "\n")

            with open(config.SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)

            # Recargar config y limpiar token (cambió CUIT o ambiente)
            config.reload()
            if os.path.exists(config.TOKEN_CACHE):
                os.remove(config.TOKEN_CACHE)

            flash("Configuración guardada correctamente.", "ok")
        except Exception as e:
            flash(f"Error al guardar: {e}", "error")
        return redirect(url_for("parametrizaciones"))

    cert_existe = os.path.exists(config.CERT_PATH)
    key_existe = os.path.exists(config.KEY_PATH)
    return render_template(
        "parametrizaciones.html",
        cfg=config,
        cert_existe=cert_existe,
        key_existe=key_existe,
    )


# ---------- Emisión ----------
@app.route("/", methods=["GET", "POST"])
def emitir():
    listo = os.path.exists(config.CERT_PATH) and os.path.exists(config.KEY_PATH)

    if request.method == "POST":
        try:
            importe = float(request.form["importe"])
            descripcion = request.form.get("descripcion", "").strip() or "Venta"
            concepto = int(request.form.get("concepto", 1))
            doc_tipo = int(request.form.get("doc_tipo", 99))
            doc_nro = int(request.form.get("doc_nro") or 0)
            cond_iva = int(request.form.get("cond_iva", 5))
            cliente = request.form.get("cliente", "").strip() or "Consumidor Final"

            cae, vto, numero = emitir_factura_c(
                importe_total=importe,
                doc_tipo=doc_tipo,
                doc_nro=doc_nro,
                cond_iva_receptor=cond_iva,
                concepto=concepto,
            )

            nombre_pdf = f"factura_C_{config.PTO_VTA:04d}_{numero:08d}.pdf"
            ruta = os.path.join(FACTURAS_DIR, nombre_pdf)
            generar_pdf(
                nro_cmp=numero,
                importe_total=importe,
                cae=cae,
                cae_vto=vto,
                descripcion=descripcion,
                receptor_nombre=cliente,
                tipo_doc_rec=doc_tipo,
                nro_doc_rec=doc_nro,
                salida=ruta,
            )

            return render_template(
                "emitir.html", cfg=config, listo=listo,
                resultado={"numero": numero, "cae": cae, "vto": vto,
                           "pdf": nombre_pdf, "importe": importe},
            )
        except Exception as e:
            flash(f"No se pudo emitir: {e}", "error")
            traceback.print_exc()
            # Re-renderizamos el form (no redirect) para no perder lo cargado.
            return render_template(
                "emitir.html", cfg=config, listo=listo, resultado=None,
                form=request.form,
            )

    return render_template("emitir.html", cfg=config, listo=listo, resultado=None)


@app.route("/factura/<nombre>")
def descargar(nombre):
    # Evitar path traversal: normalizamos y verificamos que quede dentro de FACTURAS_DIR.
    nombre = secure_filename(nombre)
    base = os.path.abspath(FACTURAS_DIR)
    ruta = os.path.abspath(os.path.join(base, nombre))
    if os.path.commonpath([base, ruta]) != base or not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, as_attachment=True)


if __name__ == "__main__":
    # debug y host configurables por entorno; por defecto, sólo localhost sin debug.
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    app.run(host=host, port=5000, debug=debug)

"""Servidor web: módulos de Parametrizaciones y Emisión de facturas.

Reutiliza el backend existente (wsaa, wsfev1, factura_pdf) sin modificarlo.
Ejecutar:  python app.py   ->  http://localhost:5000
"""
import hmac
import json
import os
import secrets
import traceback

from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file,
    abort, session,
)
from werkzeug.utils import secure_filename

import config
from wsfev1 import emitir_factura_c, ultimo_comprobante
from factura_pdf import generar_pdf

app = Flask(__name__)
# La clave de sesión se toma del entorno; sólo cae a un valor aleatorio en dev.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)
# Cookie de sesión endurecida.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_COOKIE_SECURE", "").lower()
    in ("1", "true", "yes"),
)

FACTURAS_DIR = "facturas"
os.makedirs(FACTURAS_DIR, exist_ok=True)

# Contraseña de acceso. Si no se define, la app corre sin login (modo dev local).
APP_PASSWORD = os.environ.get("APP_PASSWORD")

# Endpoints que no requieren sesión iniciada.
PUBLIC_ENDPOINTS = {"login", "static"}


# ---------- CSRF ----------
def _csrf_token():
    tok = session.get("_csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["_csrf"] = tok
    return tok


@app.context_processor
def _inject_csrf():
    # Disponible como csrf_token() en todas las plantillas.
    return {"csrf_token": _csrf_token}


# ---------- Guard: CSRF + autenticación ----------
@app.before_request
def _guard():
    # 1) CSRF: validar token en cualquier POST.
    if request.method == "POST":
        enviado = request.form.get("_csrf", "")
        esperado = session.get("_csrf", "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            abort(400, "Token CSRF inválido o ausente.")

    # 2) Autenticación: si hay contraseña configurada, exigir login.
    if not APP_PASSWORD:
        return
    if request.endpoint in PUBLIC_ENDPOINTS:
        return
    if not session.get("auth"):
        return redirect(url_for("login", next=request.path))


def _safe_next(destino):
    """Evita open-redirect: sólo aceptamos rutas internas."""
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("emitir")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not APP_PASSWORD:
        return redirect(url_for("emitir"))
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), APP_PASSWORD):
            session["auth"] = True
            return redirect(_safe_next(request.args.get("next")))
        flash("Contraseña incorrecta.", "error")
    return render_template("login.html", cfg=config)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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

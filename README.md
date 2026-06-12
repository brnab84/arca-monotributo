# Facturación ARCA — Monotributo (Factura C)

Backend en Python para emitir **Factura C** de monotributistas vía los web services de ARCA (ex-AFIP): autenticación con **WSAA** y obtención de **CAE** con **WSFEv1**.

## Requisitos

- Python 3.9+
- CUIT + Clave Fiscal nivel 3
- Certificado digital X.509 asociado al web service `wsfe` en ARCA
- Punto de venta tipo "Factura Electrónica – Monotributo – Web Services"

## Instalación

```bash
pip install -r requirements.txt
cp config.example.py config.py   # completá CUIT y punto de venta
```

Colocá tus credenciales en la raíz: `cert.pem` y `private.key` (no se versionan).

## Uso

```bash
python main.py
```

```python
from wsfev1 import emitir_factura_c

cae, vto, numero = emitir_factura_c(importe_total=1000.0)
```

## Ambientes

- `HOMOLOGACION = True` → entorno de pruebas (sin validez legal).
- `HOMOLOGACION = False` → producción. Mismo código, distinto certificado y URL.

## Estructura

| Archivo | Función |
|---|---|
| `config.py` | CUIT, punto de venta, URLs |
| `wsaa.py` | Autenticación, firma CMS, cache del token |
| `wsfev1.py` | Último comprobante y solicitud de CAE |
| `main.py` | Ejemplo de uso |

## Servidor web

```bash
python app.py   # -> http://127.0.0.1:5000
```

### GitHub Codespaces

El repo incluye `.devcontainer/`: al crear el Codespace se instalan las
dependencias solas y se reenvía el puerto `5000`. Como las credenciales **no**
están versionadas, cargá tu `cert.pem` y `private.key` desde la pantalla de
**Parametrizaciones** (o subiéndolos a la raíz) antes de emitir. Arrancá con:

```bash
APP_PASSWORD=tu-clave FLASK_COOKIE_SECURE=1 python app.py
```

Abrí el puerto `5000` desde la pestaña **PORTS** (dejalo en visibilidad *Private*).


Variables de entorno (todas opcionales para uso local):

| Variable | Para qué | Default |
|---|---|---|
| `APP_PASSWORD` | Si se define, exige login con esa contraseña. Sin ella, la app corre sin login (sólo recomendable en localhost). | — (sin login) |
| `FLASK_SECRET_KEY` | Clave para firmar la cookie de sesión. Si no se define, se genera una aleatoria al arrancar (las sesiones se invalidan en cada reinicio). | aleatoria |
| `FLASK_HOST` | Interfaz de escucha. | `127.0.0.1` |
| `FLASK_DEBUG` | `1`/`true` para modo debug (**sólo en desarrollo**). | apagado |
| `FLASK_COOKIE_SECURE` | `1`/`true` para marcar la cookie como `Secure` (usar detrás de HTTPS). | apagado |

Los formularios POST están protegidos con tokens CSRF.

## Seguridad

Los certificados (`*.pem`, `*.key`), el `token.json`, `settings.json` y `config.py`
están en `.gitignore`. **Nunca los subas al repositorio.** Si alguna vez se filtró una
clave privada, **revocá y regenerá el certificado en ARCA** además de purgarla del
historial de git.

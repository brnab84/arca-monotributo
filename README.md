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

## Seguridad

Los certificados (`*.pem`, `*.key`) y el `token.json` están en `.gitignore`. **Nunca los subas al repositorio.**

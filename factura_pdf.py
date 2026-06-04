"""Genera el PDF de una Factura C con el código QR exigido por ARCA (RG 4892).

Usa solo reportlab (incluye su propio generador de QR), sin dependencias extra.
"""
import base64
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

import config

TIPO_CMP = 11  # Factura C


def _qr_arca(cuit, pto_vta, nro_cmp, importe, cae, fecha, tipo_doc_rec=99, nro_doc_rec=0):
    """Arma el QR en el formato oficial: URL de ARCA con el JSON en base64."""
    data = {
        "ver": 1,
        "fecha": fecha,                 # AAAA-MM-DD
        "cuit": int(cuit),
        "ptoVta": int(pto_vta),
        "tipoCmp": TIPO_CMP,
        "nroCmp": int(nro_cmp),
        "importe": round(float(importe), 2),
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": int(tipo_doc_rec),
        "nroDocRec": int(nro_doc_rec),
        "tipoCodAut": "E",              # E = CAE
        "codAut": int(cae),
    }
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    return f"https://www.afip.gob.ar/fe/qr/?p={payload}"


def generar_pdf(
    nro_cmp,
    importe_total,
    cae,
    cae_vto,
    descripcion="Servicios profesionales",
    receptor_nombre="Consumidor Final",
    receptor_doc="",
    tipo_doc_rec=99,
    nro_doc_rec=0,
    salida=None,
):
    """Crea el PDF de la factura. Devuelve la ruta del archivo generado."""
    fecha_emision = datetime.now().strftime("%d/%m/%Y")
    fecha_qr = datetime.now().strftime("%Y-%m-%d")
    vto = datetime.strptime(str(cae_vto), "%Y%m%d").strftime("%d/%m/%Y")
    salida = salida or f"factura_C_{config.PTO_VTA:04d}_{int(nro_cmp):08d}.pdf"

    c = canvas.Canvas(salida, pagesize=A4)
    w, h = A4

    # Recuadro con el tipo de comprobante (C)
    c.rect(95 * mm, h - 35 * mm, 14 * mm, 18 * mm)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(102 * mm, h - 28 * mm, "C")
    c.setFont("Helvetica", 7)
    c.drawCentredString(102 * mm, h - 33 * mm, "COD. 11")

    # Encabezado emisor
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, h - 22 * mm, "FACTURA")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 28 * mm, f"CUIT: {config.CUIT}")
    c.drawString(20 * mm, h - 33 * mm, "Responsable Monotributo")

    # Datos del comprobante
    c.setFont("Helvetica-Bold", 11)
    c.drawString(120 * mm, h - 22 * mm,
                 f"N° {config.PTO_VTA:04d}-{int(nro_cmp):08d}")
    c.setFont("Helvetica", 9)
    c.drawString(120 * mm, h - 28 * mm, f"Fecha de emisión: {fecha_emision}")

    # Línea separadora
    c.line(20 * mm, h - 40 * mm, 190 * mm, h - 40 * mm)

    # Receptor
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 48 * mm, f"Cliente: {receptor_nombre}")
    if receptor_doc:
        c.drawString(20 * mm, h - 53 * mm, f"Documento: {receptor_doc}")

    # Detalle
    c.line(20 * mm, h - 60 * mm, 190 * mm, h - 60 * mm)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(22 * mm, h - 66 * mm, "Descripción")
    c.drawRightString(188 * mm, h - 66 * mm, "Importe")
    c.line(20 * mm, h - 68 * mm, 190 * mm, h - 68 * mm)
    c.setFont("Helvetica", 9)
    c.drawString(22 * mm, h - 75 * mm, descripcion)
    c.drawRightString(188 * mm, h - 75 * mm, f"$ {importe_total:,.2f}")

    # Total
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(188 * mm, h - 95 * mm, f"TOTAL: $ {importe_total:,.2f}")

    # QR + CAE (parte inferior)
    url = _qr_arca(config.CUIT, config.PTO_VTA, nro_cmp, importe_total, cae,
                   fecha_qr, tipo_doc_rec, nro_doc_rec)
    qr = QrCodeWidget(url)
    b = qr.getBounds()
    size = 35 * mm
    d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0,
                                       size / (b[3] - b[1]), 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, 20 * mm, 20 * mm)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(60 * mm, 45 * mm, f"CAE N°: {cae}")
    c.drawString(60 * mm, 40 * mm, f"Fecha de vto. de CAE: {vto}")
    c.setFont("Helvetica", 7)
    c.drawString(60 * mm, 33 * mm, "Comprobante autorizado por ARCA")

    c.showPage()
    c.save()
    return salida

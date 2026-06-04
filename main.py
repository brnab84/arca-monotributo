"""Ejemplo: emitir una Factura C y generar su PDF con QR."""
from wsfev1 import emitir_factura_c, ultimo_comprobante
from factura_pdf import generar_pdf

if __name__ == "__main__":
    print("Último comprobante:", ultimo_comprobante())

    cae, vto, numero = emitir_factura_c(importe_total=1000.0)
    print(f"Factura C N° {numero}")
    print(f"CAE: {cae}")
    print(f"Vence: {vto}")

    pdf = generar_pdf(
        nro_cmp=numero,
        importe_total=1000.0,
        cae=cae,
        cae_vto=vto,
        descripcion="Servicios profesionales",
    )
    print(f"PDF generado: {pdf}")

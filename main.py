"""Ejemplo: emitir una Factura C a consumidor final por $1000."""
from wsfev1 import emitir_factura_c, ultimo_comprobante

if __name__ == "__main__":
    print("Último comprobante:", ultimo_comprobante())

    cae, vto, numero = emitir_factura_c(importe_total=1000.0)
    print(f"Factura C N° {numero}")
    print(f"CAE: {cae}")
    print(f"Vence: {vto}")

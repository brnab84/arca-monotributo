"""WSFEv1: emisión de Factura C (monotributo) y obtención del CAE."""
from datetime import datetime

from zeep import Client

import config
from wsaa import get_auth

# Tipos de comprobante (monotributo)
FACTURA_C = 11
NOTA_DEBITO_C = 12
NOTA_CREDITO_C = 13

# Concepto
PRODUCTOS = 1
SERVICIOS = 2
PRODUCTOS_Y_SERVICIOS = 3

# Tipo de documento del receptor
CUIT = 80
DNI = 96
CONSUMIDOR_FINAL = 99

# Condición IVA del receptor (obligatorio desde 2024)
CI_RESPONSABLE_INSCRIPTO = 1
CI_EXENTO = 4
CI_CONSUMIDOR_FINAL = 5
CI_MONOTRIBUTO = 6


def _auth_dict():
    token, sign = get_auth()
    return {"Token": token, "Sign": sign, "Cuit": config.CUIT}


def _client():
    return Client(config.WSFE_WSDL)


def ultimo_comprobante(cbte_tipo=FACTURA_C):
    """Devuelve el número del último comprobante autorizado."""
    c = _client()
    r = c.service.FECompUltimoAutorizado(
        Auth=_auth_dict(), PtoVta=config.PTO_VTA, CbteTipo=cbte_tipo
    )
    return r.CbteNro


def emitir_factura_c(
    importe_total,
    doc_tipo=CONSUMIDOR_FINAL,
    doc_nro=0,
    cond_iva_receptor=CI_CONSUMIDOR_FINAL,
    concepto=PRODUCTOS,
):
    """Emite una Factura C y devuelve (cae, vencimiento_cae, numero)."""
    c = _client()
    numero = ultimo_comprobante(FACTURA_C) + 1
    hoy = datetime.now().strftime("%Y%m%d")

    det = {
        "Concepto": concepto,
        "DocTipo": doc_tipo,
        "DocNro": doc_nro,
        "CbteDesde": numero,
        "CbteHasta": numero,
        "CbteFch": hoy,
        "ImpTotal": importe_total,
        "ImpTotConc": 0,          # no gravado
        "ImpNeto": importe_total, # en Factura C el neto = total
        "ImpOpEx": 0,
        "ImpTrib": 0,
        "ImpIVA": 0,              # monotributo no discrimina IVA
        "MonId": "PES",
        "MonCotiz": 1,
        "CondicionIVAReceptorId": cond_iva_receptor,
    }
    # Concepto servicios/ambos requiere fechas de servicio
    if concepto in (SERVICIOS, PRODUCTOS_Y_SERVICIOS):
        det.update({"FchServDesde": hoy, "FchServHasta": hoy, "FchVtoPago": hoy})

    req = {
        "FeCabReq": {"CantReg": 1, "PtoVta": config.PTO_VTA, "CbteTipo": FACTURA_C},
        "FeDetReq": {"FECAEDetRequest": [det]},
    }

    r = c.service.FECAESolicitar(Auth=_auth_dict(), FeCAEReq=req)
    detresp = r.FeDetResp.FECAEDetResponse[0]

    if detresp.Resultado != "A":
        obs = detresp.Observaciones
        raise RuntimeError(f"Rechazada: {obs}")

    return detresp.CAE, detresp.CAEFchVto, numero

"""Copiá este archivo como config.py y completá tus datos."""

HOMOLOGACION = True

CUIT = 20111111112
PTO_VTA = 1
CERT_PATH = "cert.pem"
KEY_PATH = "private.key"

if HOMOLOGACION:
    WSAA_WSDL = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
    WSFE_WSDL = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
else:
    WSAA_WSDL = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
    WSFE_WSDL = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"

SERVICE = "wsfe"
TOKEN_CACHE = "token.json"

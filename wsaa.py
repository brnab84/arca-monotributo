"""WSAA: autenticación contra ARCA. Devuelve token + sign (válidos 12 hs)."""
import base64
import json
import os
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, pkcs7, Encoding
from zeep import Client

import config

ARG_TZ = timezone(timedelta(hours=-3))


def _build_tra():
    now = datetime.now(ARG_TZ)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
  <header>
    <uniqueId>{int(now.timestamp())}</uniqueId>
    <generationTime>{(now - timedelta(minutes=10)).isoformat()}</generationTime>
    <expirationTime>{(now + timedelta(minutes=10)).isoformat()}</expirationTime>
  </header>
  <service>{config.SERVICE}</service>
</loginTicketRequest>""".encode("utf-8")


def _sign_tra(tra: bytes) -> str:
    with open(config.CERT_PATH, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())
    with open(config.KEY_PATH, "rb") as f:
        key = load_pem_private_key(f.read(), password=None)
    cms = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(tra)
        .add_signer(cert, key, hashes.SHA256())
        .sign(Encoding.DER, [pkcs7.PKCS7Options.Binary])
    )
    return base64.b64encode(cms).decode()


def _cache_valid():
    if not os.path.exists(config.TOKEN_CACHE):
        return None
    with open(config.TOKEN_CACHE) as f:
        data = json.load(f)
    if datetime.fromisoformat(data["expira"]) > datetime.now(ARG_TZ) + timedelta(minutes=5):
        return data["token"], data["sign"]
    return None


def get_auth():
    """Devuelve (token, sign). Reusa el cache si sigue vigente."""
    cached = _cache_valid()
    if cached:
        return cached

    cms = _sign_tra(_build_tra())
    client = Client(config.WSAA_WSDL)
    resp = client.service.loginCms(in0=cms)

    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp)
    token = root.findtext(".//token")
    sign = root.findtext(".//sign")
    expira = root.findtext(".//expirationTime")

    with open(config.TOKEN_CACHE, "w") as f:
        json.dump({"token": token, "sign": sign, "expira": expira}, f)
    return token, sign

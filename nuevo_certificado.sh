#!/usr/bin/env bash
# Genera una clave privada y un CSR nuevos para solicitar o ROTAR el
# certificado en ARCA. No toca ARCA: sólo prepara los archivos locales.
#
# Uso:  ./nuevo_certificado.sh <CUIT> [nombre_simbolico]
set -euo pipefail

CUIT="${1:-}"
NOMBRE="${2:-facturador}"

if [[ -z "$CUIT" ]]; then
  read -rp "Ingresá tu CUIT (sin guiones): " CUIT
fi

if ! [[ "$CUIT" =~ ^[0-9]{11}$ ]]; then
  echo "Error: el CUIT debe tener 11 dígitos, sin guiones." >&2
  exit 1
fi

# No pisar una clave existente sin confirmar (rotar = clave nueva).
if [[ -f private.key ]]; then
  read -rp "Ya existe private.key. ¿Sobrescribir con una nueva? (s/N) " R
  [[ "$R" =~ ^[sS]$ ]] || { echo "Cancelado."; exit 1; }
fi

echo "→ Generando clave privada (private.key)…"
openssl genrsa -out private.key 2048

echo "→ Generando pedido de certificado (pedido.csr)…"
openssl req -new -key private.key \
  -subj "/C=AR/O=${NOMBRE}/CN=${NOMBRE}/serialNumber=CUIT ${CUIT}" \
  -out pedido.csr

cat <<EOF

Listo. Próximos pasos en ARCA:
  1. Copiá el contenido del CSR de abajo (de BEGIN a END).
  2. Entrá a ARCA → WSASS (homologación) o "Administración de Certificados
     Digitales" (producción).
  3. Creá un DN nuevo, pegá el CSR y descargá el certificado como cert.pem.
  4. REVOCÁ el certificado viejo y autorizá el nuevo DN al servicio wsfe.
  5. Borrá el token cacheado:  rm -f token.json

----- pedido.csr -----
EOF
cat pedido.csr

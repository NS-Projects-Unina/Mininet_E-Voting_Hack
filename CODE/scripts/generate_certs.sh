#!/bin/bash
# ====================================================================
#  Generate self-signed SSL certificate for the voting server
#  Run this ONCE before using HTTPS mode.
# ====================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$SCRIPT_DIR/../server/certs"

mkdir -p "$CERT_DIR"

echo "[*] Generating self-signed SSL certificate …"
echo "    Output: $CERT_DIR/"

openssl req -x509 -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out    "$CERT_DIR/server.crt" \
    -days 365 -nodes \
    -subj "/C=IT/ST=Lab/L=Lab/O=E-Voting/CN=10.0.0.1"

echo ""
echo "[+] Certificate generated:"
echo "    $CERT_DIR/server.crt"
echo "    $CERT_DIR/server.key"
echo ""
echo "    Start the server in HTTPS mode with:"
echo "    python3 server/voting_server.py --https"

#!/usr/bin/env python3
"""Write the PEM certificates and SAML metadata used by the lab inventory.

Private keys are generated in memory and discarded. Re-run this if you change
the not-after dates, then keep inventory/lab.yaml in step with those dates.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parent
CERT_DIR = ROOT / "fixtures" / "certs"

CERTS = {
    "saml-signing.pem": datetime(2028, 6, 15, tzinfo=UTC),
    "ssl-lab.pem": datetime(2028, 4, 25, tzinfo=UTC),
    "wifi-dot1x.pem": datetime(2028, 3, 1, tzinfo=UTC),
}
METADATA_NOT_AFTER = datetime(2028, 5, 20, tzinfo=UTC)
NOT_BEFORE = datetime(2026, 1, 1, tzinfo=UTC)


def build_cert(common_name: str, not_after: datetime, key: rsa.RSAPrivateKey) -> x509.Certificate:
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(not_after)
        .sign(key, hashes.SHA256())
    )


def pem_bytes(certificate: x509.Certificate) -> bytes:
    return certificate.public_bytes(serialization.Encoding.PEM)


def metadata_xml(certificate: x509.Certificate) -> str:
    der = certificate.public_bytes(serialization.Encoding.DER)
    body = base64.encodebytes(der).decode("ascii").strip()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" '
        'entityID="https://lab.example.test/saml">\n'
        "  <SPSSODescriptor protocolSupportEnumeration="
        '"urn:oasis:names:tc:SAML:2.0:protocol">\n'
        '    <KeyDescriptor use="signing">\n'
        '      <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">\n'
        "        <X509Data>\n"
        f"          <X509Certificate>{body}</X509Certificate>\n"
        "        </X509Data>\n"
        "      </KeyInfo>\n"
        "    </KeyDescriptor>\n"
        "  </SPSSODescriptor>\n"
        "</EntityDescriptor>\n"
    )


def main() -> None:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for filename, not_after in CERTS.items():
        common_name = filename.removesuffix(".pem") + ".lab.example.test"
        certificate = build_cert(common_name, not_after, key)
        (CERT_DIR / filename).write_bytes(pem_bytes(certificate))
    metadata_cert = build_cert("metadata.lab.example.test", METADATA_NOT_AFTER, key)
    (CERT_DIR / "idp-metadata.xml").write_text(metadata_xml(metadata_cert), encoding="utf-8")
    print(f"wrote fixtures in {CERT_DIR}")


if __name__ == "__main__":
    main()

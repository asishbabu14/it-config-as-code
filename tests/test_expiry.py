import socket
import ssl
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from helpers import ROOT, expiry

LAB = ROOT / "tools" / "expiry-monitor" / "inventory" / "lab.yaml"
NOW = datetime(2028, 4, 1, tzinfo=UTC)
HEALTHY = datetime(2026, 11, 25, tzinfo=UTC)


def _key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_cert(
    common_name: str, not_after: datetime, key: rsa.RSAPrivateKey | None = None
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    signing_key = key or _key()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(signing_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime(2026, 1, 1, tzinfo=UTC))
        .not_valid_after(not_after)
        .sign(signing_key, hashes.SHA256())
    )
    return certificate, signing_key


def write_pem(directory: Path, certificate: x509.Certificate, filename: str = "cert.pem") -> Path:
    path = directory / filename
    path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return path


@pytest.mark.parametrize(
    ("days", "status"),
    [
        (61, "ok"),
        (60, "notice"),
        (31, "notice"),
        (30, "warning"),
        (8, "warning"),
        (7, "critical"),
        (0, "critical"),
        (-1, "expired"),
    ],
)
def test_thresholds(days: int, status: str):
    assert expiry.classify(days) == status


def test_days_until_uses_whole_days():
    now = datetime(2028, 4, 1, tzinfo=UTC)
    assert expiry.days_until(now + timedelta(days=5), now) == 5
    assert expiry.days_until(now + timedelta(days=5, hours=3), now) == 5
    assert expiry.days_until(now - timedelta(hours=1), now) == -1


def test_pem_and_metadata_round_trip(tmp_path: Path):
    not_after = datetime(2028, 5, 20, tzinfo=UTC)
    certificate, _key_material = make_cert("lab.example.test", not_after)
    pem_path = write_pem(tmp_path, certificate)
    assert expiry.load_pem_expiry(pem_path) == not_after

    earlier, _ = make_cert("earlier.lab.example.test", datetime(2028, 4, 2, tzinfo=UTC))
    later_body = certificate.public_bytes(serialization.Encoding.DER)
    early_body = earlier.public_bytes(serialization.Encoding.DER)
    import base64

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://lab.example.test">
  <SPSSODescriptor>
    <KeyDescriptor use="signing">
      <X509Data>
        <X509Certificate>{base64.b64encode(later_body).decode()}</X509Certificate>
        <X509Certificate>{base64.b64encode(early_body).decode()}</X509Certificate>
      </X509Data>
    </KeyDescriptor>
  </SPSSODescriptor>
</EntityDescriptor>
"""
    metadata = tmp_path / "metadata.xml"
    metadata.write_text(xml, encoding="utf-8")
    assert expiry.load_metadata_expiry(metadata) == datetime(2028, 4, 2, tzinfo=UTC)


def test_inventory_file_reports_each_source(tmp_path: Path):
    certificate, _ = make_cert("from-file.lab.example.test", datetime(2028, 4, 8, tzinfo=UTC))
    pem_path = write_pem(tmp_path, certificate)
    inventory = tmp_path / "inventory.yaml"
    inventory.write_text(
        f"""
certificates:
  - name: from-pem
    kind: saml_signing
    pem: {pem_path.name}
  - name: from-date
    kind: apple_push
    not_after: "2028-04-03T00:00:00Z"
domains:
  - name: lab.example.test
    expires_on: "2028-05-20"
""",
        encoding="utf-8",
    )
    items = {item.name: item for item in expiry.evaluate(inventory, NOW)}
    assert items["from-pem"].status == "critical"
    assert items["from-pem"].source == "pem"
    assert items["from-date"].status == "critical"
    assert items["from-date"].days_left == 2
    assert items["lab.example.test"].status == "notice"


def test_lab_inventory_demo_clock_and_healthy_clock():
    demo = {item.name: item.status for item in expiry.evaluate(LAB, NOW)}
    assert demo == {
        "lab-wifi-dot1x": "expired",
        "lab-mdm-apple-push": "critical",
        "files.lab.example.test": "warning",
        "lab-portal-ssl": "warning",
        "lab-portal-metadata": "notice",
        "lab-portal-saml": "ok",
        "lab.example.test": "ok",
    }
    healthy = expiry.evaluate(LAB, HEALTHY)
    assert all(item.status == "ok" for item in healthy)
    assert expiry.run(["--inventory", str(LAB), "--now", "2026-11-25T00:00:00Z", "--quiet"]) == 0
    assert expiry.run(["--inventory", str(LAB), "--now", "2028-04-01T00:00:00Z", "--quiet"]) == 1


def test_reports_and_exit_zero(tmp_path: Path):
    markdown = tmp_path / "expiry.md"
    payload = tmp_path / "expiry.json"
    code = expiry.run(
        [
            "--inventory",
            str(LAB),
            "--now",
            "2028-04-01T00:00:00Z",
            "--markdown",
            str(markdown),
            "--json",
            str(payload),
            "--exit-zero",
            "--quiet",
        ]
    )
    assert code == 0
    text = markdown.read_text(encoding="utf-8")
    assert "lab-wifi-dot1x" in text
    assert "Action needed: 2" in text
    assert '"action_needed": 2' in payload.read_text(encoding="utf-8")


def test_bad_inventory_exits_2(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("certificates:\n  - name: missing\n    kind: ssl\n", encoding="utf-8")
    assert expiry.run(["--inventory", str(path), "--quiet"]) == 2


def test_live_tls_check(tmp_path: Path):
    not_after = datetime(2028, 4, 4, tzinfo=UTC)
    certificate, key = make_cert("localhost", not_after)
    cert_path = write_pem(tmp_path, certificate)
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(certfile=cert_path, keyfile=key_path)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def serve() -> None:
        try:
            connection, _address = listener.accept()
        except OSError:
            return
        try:
            with server.wrap_socket(connection, server_side=True):
                pass
        except OSError:
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        found = expiry.read_tls_expiry("127.0.0.1", port, timeout=5)
        assert found == not_after
    finally:
        listener.close()
        thread.join(timeout=2)

    inventory = tmp_path / "live.yaml"
    inventory.write_text(
        """
certificates:
  - name: live-ssl
    kind: ssl
    host: 127.0.0.1
    port: 1
    live_check: true
""",
        encoding="utf-8",
    )
    items = expiry.evaluate(inventory, NOW, timeout=0.2)
    assert items[0].status == "error"
    assert items[0].source == "tls"

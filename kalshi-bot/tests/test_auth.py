import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kalshi_bot.client.auth import RsaRequestSigner


def _generate_key_pem() -> tuple[bytes, rsa.RSAPublicKey]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem, key.public_key()


def test_signature_verifies_against_expected_message():
    pem, public_key = _generate_key_pem()
    signer = RsaRequestSigner(api_key_id="key-id", private_key_pem=pem)
    ts = 1234567890000
    path = "/trade-api/v2/portfolio/events/orders"

    signature = signer.sign(method="post", path=path, timestamp_ms=ts)

    public_key.verify(
        base64.b64decode(signature),
        f"{ts}POST{path}".encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )


def test_headers_contain_required_fields():
    pem, _ = _generate_key_pem()
    signer = RsaRequestSigner(api_key_id="key-id", private_key_pem=pem)

    headers = signer.headers(method="GET", path="/trade-api/v2/portfolio/balance")

    assert headers["KALSHI-ACCESS-KEY"] == "key-id"
    assert headers["KALSHI-ACCESS-TIMESTAMP"].isdigit()
    assert headers["KALSHI-ACCESS-SIGNATURE"]

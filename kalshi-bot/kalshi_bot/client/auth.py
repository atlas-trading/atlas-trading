import base64
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class RsaRequestSigner:
    """Kalshi API 요청 서명: RSA-PSS(SHA256)로 '{timestamp_ms}{METHOD}{path}'를 서명.

    path는 쿼리스트링을 제외한 전체 경로 (예: /trade-api/v2/portfolio/events/orders).
    """

    def __init__(self, *, api_key_id: str, private_key_pem: bytes) -> None:
        self._api_key_id = api_key_id
        key = serialization.load_pem_private_key(private_key_pem, password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Kalshi API key must be an RSA private key")
        self._private_key = key

    @classmethod
    def from_file(cls, *, api_key_id: str, private_key_path: Path) -> "RsaRequestSigner":
        return cls(api_key_id=api_key_id, private_key_pem=private_key_path.read_bytes())

    def sign(self, *, method: str, path: str, timestamp_ms: int) -> str:
        message = f"{timestamp_ms}{method.upper()}{path}".encode()
        signature = self._private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode()

    def headers(self, *, method: str, path: str, timestamp_ms: int | None = None) -> dict[str, str]:
        ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
        return {
            "KALSHI-ACCESS-KEY": self._api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": str(ts),
            "KALSHI-ACCESS-SIGNATURE": self.sign(method=method, path=path, timestamp_ms=ts),
        }

"""Kubernetes Secret management endpoints"""
import base64
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

NAMESPACE = "atlas-trading"
MANAGED_PREFIX = "exchange-"


def _get_v1():
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        return client.CoreV1Api()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Kubernetes unavailable: {e}")


class SecretUpsert(BaseModel):
    data: Dict[str, str]  # key -> plaintext value (encoded server-side)


@router.get("/k8s-secrets")
async def list_secrets() -> List[Dict[str, Any]]:
    """Secret 이름 목록만 반환 (값 노출 없음)"""
    v1 = _get_v1()
    try:
        secrets = v1.list_namespaced_secret(NAMESPACE)
        return [
            {
                "name": s.metadata.name,
                "key_count": len(s.data) if s.data else 0,
                "created_at": s.metadata.creation_timestamp.isoformat()
                if s.metadata.creation_timestamp
                else None,
            }
            for s in secrets.items
            if s.metadata.name.startswith(MANAGED_PREFIX)
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/k8s-secrets/{name}/keys")
async def get_secret_keys(name: str) -> Dict[str, Any]:
    """특정 Secret의 키 이름만 반환 (값 제외)"""
    v1 = _get_v1()
    try:
        secret = v1.read_namespaced_secret(name, NAMESPACE)
        return {
            "name": name,
            "keys": list(secret.data.keys()) if secret.data else [],
        }
    except HTTPException:
        raise
    except Exception as e:
        status = 404 if "Not Found" in str(e) else 500
        raise HTTPException(status_code=status, detail=str(e))


@router.put("/k8s-secrets/{name}")
async def upsert_secret(name: str, body: SecretUpsert) -> Dict[str, Any]:
    """Secret KV 업로드 (없으면 생성, 있으면 병합)"""
    if not name.startswith(MANAGED_PREFIX):
        raise HTTPException(
            status_code=400,
            detail=f"Secret 이름은 '{MANAGED_PREFIX}'로 시작해야 합니다",
        )

    v1 = _get_v1()
    from kubernetes import client as k8s

    encoded = {k: base64.b64encode(v.encode()).decode() for k, v in body.data.items()}

    try:
        existing = v1.read_namespaced_secret(name, NAMESPACE)
        merged = dict(existing.data or {})
        merged.update(encoded)
        patch = k8s.V1Secret(
            metadata=k8s.V1ObjectMeta(name=name, namespace=NAMESPACE),
            data=merged,
        )
        v1.patch_namespaced_secret(name, NAMESPACE, patch)
        return {"action": "updated", "name": name, "keys": list(body.data.keys())}
    except HTTPException:
        raise
    except Exception as e:
        if "Not Found" in str(e):
            secret = k8s.V1Secret(
                metadata=k8s.V1ObjectMeta(name=name, namespace=NAMESPACE),
                data=encoded,
            )
            v1.create_namespaced_secret(NAMESPACE, secret)
            return {"action": "created", "name": name, "keys": list(body.data.keys())}
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/k8s-secrets/{name}/keys/{key}")
async def delete_secret_key(name: str, key: str) -> Dict[str, Any]:
    """Secret에서 특정 키 삭제"""
    v1 = _get_v1()
    from kubernetes import client as k8s

    try:
        existing = v1.read_namespaced_secret(name, NAMESPACE)
        data = dict(existing.data or {})
        if key not in data:
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
        del data[key]
        patch = k8s.V1Secret(
            metadata=k8s.V1ObjectMeta(name=name, namespace=NAMESPACE),
            data=data,
        )
        v1.patch_namespaced_secret(name, NAMESPACE, patch)
        return {"action": "deleted", "name": name, "key": key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

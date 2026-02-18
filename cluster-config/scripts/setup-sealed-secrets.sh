#!/bin/bash
# =============================================================================
# Sealed Secrets 설정 스크립트
# AWS Secrets Manager처럼 k8s Secret을 git에 안전하게 저장할 수 있게 해줍니다.
#
# 원리:
#   1. 클러스터에 Sealed Secrets Controller 설치 (비공개 키 보유)
#   2. kubeseal CLI로 Secret을 암호화 → SealedSecret 생성
#   3. SealedSecret은 git에 커밋 가능 (클러스터 키 없이는 복호화 불가)
#   4. ArgoCD가 SealedSecret을 배포하면 컨트롤러가 자동으로 복호화
# =============================================================================
set -e

echo "=== Sealed Secrets 설치 ==="

# 1. Controller 설치 (kube-system 네임스페이스)
echo "[1/3] Sealed Secrets Controller 설치 중..."
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.26.0/controller.yaml

# kubeseal CLI 설치 (macOS)
if ! command -v kubeseal &> /dev/null; then
  echo "[2/3] kubeseal CLI 설치 중..."
  brew install kubeseal
else
  echo "[2/3] kubeseal CLI 이미 설치됨: $(kubeseal --version)"
fi

# Controller가 준비될 때까지 대기
echo "[3/3] Controller 준비 대기 중..."
kubectl rollout status deployment/sealed-secrets-controller -n kube-system --timeout=60s

echo ""
echo "=== 설치 완료 ==="
echo ""
echo "=== API 키 등 Secret 추가하는 방법 ==="
echo ""
echo "1. 일반 Secret YAML 작성 (git에 올리지 말 것!):"
cat << 'SECRET_EXAMPLE'
# /tmp/my-secret.yaml (절대 git에 올리지 말 것)
apiVersion: v1
kind: Secret
metadata:
  name: atlas-secrets
  namespace: atlas-trading
type: Opaque
stringData:
  BINANCE_API_KEY: "your-actual-api-key-here"
  BINANCE_SECRET_KEY: "your-actual-secret-key-here"
  DB_PASSWORD: "your-db-password"
SECRET_EXAMPLE

echo ""
echo "2. kubeseal로 암호화 (SealedSecret 생성):"
echo "   kubeseal --format yaml < /tmp/my-secret.yaml > cluster-config/base/sealed-secret.yaml"
echo ""
echo "3. 암호화된 파일은 git에 커밋 가능:"
echo "   git add cluster-config/base/sealed-secret.yaml"
echo "   git commit -m 'Add sealed secrets'"
echo ""
echo "4. ArgoCD가 자동 sync → 컨트롤러가 복호화 → 실제 Secret 생성"
echo ""
echo "=== 공개 키 백업 (선택사항) ==="
echo "kubeseal --fetch-cert > cluster-config/scripts/sealed-secrets-public-key.pem"
echo "# 비공개 키는 절대 노출 금지! 클러스터 내 kube-system에만 존재"

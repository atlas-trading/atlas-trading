# Cluster Config - K8s 클러스터 설정

이 디렉토리는 k3s 클러스터 설정 및 K8s 매니페스트를 포함합니다.

## 디렉토리 구조

```
cluster-config/
├── k3s/
│   ├── server-config.yaml      # k3s 서버 설정
│   └── agent-config.yaml       # k3s 에이전트 설정
├── manifests/
│   ├── namespace.yaml          # trading 네임스페이스
│   ├── deployment.yaml         # core-platform Deployment
│   ├── service.yaml            # ClusterIP Service
│   ├── configmap.yaml          # 비밀이 아닌 설정
│   ├── sealed-secret.yaml      # 암호화된 API 키
│   └── network-policy.yaml     # Pod 간 통신 제한
└── scripts/
    ├── setup-cluster.sh        # 클러스터 초기 설정
    └── backup-db.sh            # PostgreSQL 백업
```

## k3s 클러스터 구성

### 옵션 A: 맥미니 포함 (4노드)

**맥미니 (서버):**
- k3s server (컨트롤 플레인)
- PostgreSQL (K8s 외부)
- Redis (K8s 외부)

**라즈베리파이 × 3 (에이전트):**
- k3s agent (워커 노드)

### 옵션 B: 라즈베리파이만 (3노드) - 추천

**맥미니:**
- DB 전용 (K8s 외부)
- PostgreSQL
- Redis

**라즈베리파이 × 3:**
- k3s server (Pi #1)
- k3s agent (Pi #2, #3)

## 설치 가이드

### 1. 맥미니 설정 (옵션 B)

```bash
# PostgreSQL 설치
brew install postgresql@14 timescaledb

# PostgreSQL 시작
brew services start postgresql@14

# TimescaleDB 확장 설치
psql postgres -c "CREATE EXTENSION timescaledb;"

# Redis 설치 및 시작
brew install redis
brew services start redis
```

### 2. 라즈베리파이 준비

```bash
# 모든 Pi에서 실행
sudo apt update && sudo apt upgrade -y

# 고정 IP 설정 (예시)
# Pi #1: 192.168.10.11
# Pi #2: 192.168.10.12
# Pi #3: 192.168.10.13
```

### 3. k3s 서버 설치 (Pi #1)

```bash
curl -sfL https://get.k3s.io | sh -s - \
  --disable traefik \
  --write-kubeconfig-mode 644

# 노드 토큰 저장
sudo cat /var/lib/rancher/k3s/server/node-token
```

### 4. k3s 에이전트 설치 (Pi #2, #3)

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.10.11:6443 \
  K3S_TOKEN=<노드토큰> sh -
```

### 5. kubectl 설정

```bash
# 로컬 머신에서
scp pi@192.168.10.11:~/.kube/config ~/.kube/config-atlas

# KUBECONFIG 설정
export KUBECONFIG=~/.kube/config-atlas

# 클러스터 확인
kubectl get nodes
```

## Sealed Secrets 설치

```bash
# Sealed Secrets 컨트롤러 설치
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# kubeseal CLI 설치 (로컬)
brew install kubeseal
```

## API 키 설정

### 1. Secret 생성 (로컬에서만, 절대 커밋 금지)

```bash
kubectl create secret generic exchange-api-keys \
  --from-literal=binance-api-key=YOUR_KEY \
  --from-literal=binance-api-secret=YOUR_SECRET \
  --dry-run=client -o yaml > /tmp/secret.yaml
```

### 2. Sealed Secret 생성

```bash
kubeseal -o yaml < /tmp/secret.yaml > manifests/exchange-api-sealed-secret.yaml

# 원본 삭제
rm /tmp/secret.yaml

# Git에 커밋 (암호화됨)
git add manifests/exchange-api-sealed-secret.yaml
```

## 배포

```bash
# 네임스페이스 생성
kubectl apply -f manifests/namespace.yaml

# Sealed Secret 배포
kubectl apply -f manifests/exchange-api-sealed-secret.yaml

# 나머지 리소스 배포
kubectl apply -f manifests/
```

## 문제 해결

### 노드가 Ready 상태가 안 됨

```bash
# 노드 상태 확인
kubectl describe node <node-name>

# k3s 로그 확인 (해당 노드에서)
sudo journalctl -u k3s -f
```

### Pod가 Pending 상태

```bash
# Pod 이벤트 확인
kubectl describe pod <pod-name> -n trading

# 일반적 원인: 리소스 부족, 이미지 pull 실패
```

### 이미지 pull 실패

```bash
# 이미지 레지스트리 인증 설정
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  -n trading
```

## 다음 단계

1. [Dockerfile 작성](../core-platform/Dockerfile)
2. [매니페스트 작성](manifests/)
3. [CI/CD 파이프라인 설정](../.github/workflows/)

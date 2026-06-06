# 운영 가이드 (Runbook)

## 로컬 개발 실행

### 사전 요구사항

- Python 3.12+, uv 설치
- Docker Desktop 실행 중

### 인프라 시작

```bash
cd infrastructure
docker compose up -d
# PostgreSQL(5432) 시작
```

### 트레이딩 엔진 실행

```bash
cd core-platform

# 패키지 설치 (최초 1회)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Binance Testnet 실행
BINANCE_TESTNET_API_KEY=<key> \
BINANCE_TESTNET_API_SECRET=<secret> \
DATABASE_URL=postgresql+asyncpg://atlas:atlas@localhost:5432/atlas \
uv run python run_local.py
```

### 테스트 / 린트

```bash
cd core-platform
uv run pytest          # 전체 테스트 (132개)
uv run pytest -x       # 첫 실패 시 중단
uv run ruff check .    # 린트
```

### Kill Switch (즉시 거래 중단)

코드에서 직접 호출하거나 향후 API endpoint를 통해 조작합니다:

```python
risk_manager.set_kill_switch(True)   # 전체 신호 거부
risk_manager.set_connected(False)    # 연결 끊김 처리
```

---

## 프로덕션 운영 (K8s 클러스터)

### 일상 운영

#### 일일 체크리스트
- [ ] 클러스터 상태 확인: `kubectl get nodes`
- [ ] Pod 상태 확인: `kubectl get pods -n trading`
- [ ] Discord 알림 확인
- [ ] 일일 PnL 리포트 확인

#### 주간 체크리스트
- [ ] 백업 복원 테스트
- [ ] 거래소 로그인 이력 확인
- [ ] 로그 분석 (에러, 경고)
- [ ] 성능 메트릭 리뷰

### 장애 대응

#### Pod 재시작 반복

**증상:**
```bash
kubectl get pods -n trading
# CrashLoopBackOff 상태
```

**진단:**
```bash
kubectl logs -n trading <pod-name> --previous
kubectl describe pod -n trading <pod-name>
```

**일반적 원인:**
- 환경변수 누락 (API 키)
- DB 연결 실패
- 메모리 부족 (OOMKilled)

**해결:**
```bash
kubectl get secrets -n trading
kubectl get configmap -n trading
kubectl describe pod -n trading <pod-name> | grep -A 5 "Limits"
```

#### 데이터베이스 연결 실패

**증상:**
- "Connection refused" 에러
- 모든 전략 Pod 실패

**진단:**
```bash
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h <맥미니-IP> -U atlas -d atlas
```

**해결:**
- PostgreSQL 재시작: `brew services restart postgresql`
- Docker Compose 재시작: `docker compose restart timescaledb`

### 비상 상황

#### 긴급 거래 중단

```bash
# 1. 모든 전략 Pod 중단
kubectl scale deployment -n trading strategy-runner --replicas=0

# 2. 거래소에서 수동으로 포지션 확인 및 청산
```

#### API 키 유출 의심

1. 거래소 웹사이트에서 API 키 즉시 비활성화
2. Pod 즉시 중단 (위 참조)
3. 오픈 포지션 수동 확인 및 청산
4. 새 API 키 발급 후 Sealed Secret 재생성 및 재배포

### 백업 및 복구

#### 데이터베이스 백업

```bash
pg_dump -U atlas atlas > /tmp/atlas_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 데이터베이스 복구

```bash
dropdb -U atlas atlas
createdb -U atlas atlas
psql -U atlas atlas < /path/to/backup.sql
```

### 업데이트 및 배포

```bash
# 이미지 빌드 및 배포
docker buildx build --platform linux/arm64 \
  -t ghcr.io/your-org/atlas-trading:v1.x.x --push .

kubectl set image deployment/strategy-runner \
  -n trading strategy-runner=ghcr.io/your-org/atlas-trading:v1.x.x

kubectl rollout status deployment/strategy-runner -n trading
```

#### 롤백

```bash
kubectl rollout undo deployment/strategy-runner -n trading
```

### 모니터링 (K8s)

**Grafana**: `http://100.110.86.86:31177` (Tailscale)

**주요 메트릭:**
- CPU 사용률 < 70%
- 메모리 사용률 < 80%
- 주문 레이턴시 < 2초

**Discord Webhook 테스트:**
```bash
curl -X POST <DISCORD_WEBHOOK_URL> \
  -H "Content-Type: application/json" \
  -d '{"content": "테스트 알림입니다."}'
```

## 연락처

- **긴급 상황**: Discord #alerts 채널
- **일반 문의**: README.md 참조

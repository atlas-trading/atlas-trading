# 운영 가이드 (Runbook)

## 일상 운영

### 일일 체크리스트
- [ ] 클러스터 상태 확인: `kubectl get nodes`
- [ ] Pod 상태 확인: `kubectl get pods -n trading`
- [ ] Discord 알림 확인
- [ ] 일일 PnL 리포트 확인

### 주간 체크리스트
- [ ] 백업 복원 테스트
- [ ] 거래소 로그인 이력 확인
- [ ] 로그 분석 (에러, 경고)
- [ ] 성능 메트릭 리뷰

## 장애 대응

### Pod 재시작 반복

**증상:**
```bash
kubectl get pods -n trading
# CrashLoopBackOff 상태
```

**진단:**
```bash
# 로그 확인
kubectl logs -n trading <pod-name> --previous

# 이벤트 확인
kubectl describe pod -n trading <pod-name>
```

**일반적 원인:**
- 환경변수 누락 (API 키)
- DB 연결 실패
- 메모리 부족 (OOMKilled)

**해결:**
```bash
# Secret 확인
kubectl get secrets -n trading

# ConfigMap 확인
kubectl get configmap -n trading

# 리소스 제한 확인
kubectl describe pod -n trading <pod-name> | grep -A 5 "Limits"
```

### 데이터베이스 연결 실패

**증상:**
- "Connection refused" 에러
- 모든 전략 Pod 실패

**진단:**
```bash
# 맥미니에서 PostgreSQL 상태 확인
systemctl status postgresql
# 또는
brew services list | grep postgresql

# 네트워크 연결 테스트
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql -h <맥미니-IP> -U atlas -d trading
```

**해결:**
- PostgreSQL 재시작: `systemctl restart postgresql`
- 방화벽 확인: `ufw status`
- pg_hba.conf에 클러스터 IP 대역 추가

### Kill Switch 오작동

**증상:**
- 정상 상황에서도 모든 주문 차단

**진단:**
```bash
# Redis 연결
kubectl run -it --rm redis-cli --image=redis:7 --restart=Never -- \
  redis-cli -h <맥미니-IP>

# Kill Switch 플래그 확인
GET kill_switch
```

**해결:**
```bash
# Kill Switch 비활성화
SET kill_switch false
```

### 라즈베리파이 노드 다운

**증상:**
```bash
kubectl get nodes
# NotReady 상태
```

**자동 복구:**
- K8s가 자동으로 Pod를 다른 노드로 재스케줄링

**수동 개입:**
```bash
# 노드 상태 확인
kubectl describe node <node-name>

# 라즈베리파이 재부팅
ssh pi@<node-ip>
sudo reboot

# 노드 복구 후 확인
kubectl get nodes
```

## 비상 상황

### 긴급 거래 중단

**시나리오:**
- 시스템 버그 발견
- 예상치 못한 대량 손실
- 보안 침해 의심

**즉시 조치:**
```bash
# 1. Kill Switch 활성화
kubectl run -it --rm redis-cli --image=redis:7 --restart=Never -- \
  redis-cli -h <맥미니-IP> SET kill_switch true

# 2. 모든 전략 Pod 중단
kubectl scale deployment -n trading strategy-runner --replicas=0

# 3. 거래소에서 수동으로 포지션 확인 및 청산
```

### API 키 유출 의심

**즉시 조치:**
1. 거래소 웹사이트에서 API 키 즉시 비활성화
2. Kill Switch 활성화 (위 참조)
3. 오픈 포지션 수동 확인
4. 거래소 로그인 이력, API 호출 로그 확인

**복구:**
1. 새 API 키 발급
2. Sealed Secret 재생성
3. Pod 재배포
4. 테스트 후 Kill Switch 해제

## 백업 및 복구

### 데이터베이스 백업

**자동 백업 확인:**
```bash
# 맥미니에서
ls -lh /var/backups/postgres/
```

**수동 백업:**
```bash
pg_dump -U atlas trading > /tmp/trading_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 데이터베이스 복구

**전체 복구:**
```bash
# 1. 기존 DB 삭제 (주의!)
dropdb -U atlas trading

# 2. 새 DB 생성
createdb -U atlas trading

# 3. TimescaleDB 확장 설치
psql -U atlas -d trading -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# 4. 백업 복원
psql -U atlas trading < /var/backups/postgres/trading_backup_YYYYMMDD.sql
```

## 성능 최적화

### Pod 리소스 튜닝

**현재 사용량 확인:**
```bash
kubectl top pods -n trading
```

**리소스 조정:**
```yaml
# cluster-config/manifests/deployment.yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 데이터베이스 최적화

**인덱스 추가:**
```sql
-- 주문 조회 최적화
CREATE INDEX idx_orders_timestamp ON orders(created_at DESC);

-- OHLCV 조회 최적화
CREATE INDEX idx_ohlcv_symbol_time ON ohlcv(symbol, timestamp DESC);
```

**Vacuum 실행:**
```bash
psql -U atlas -d trading -c "VACUUM ANALYZE;"
```

## 모니터링

### 주요 메트릭

**시스템 메트릭:**
- CPU 사용률: < 70%
- 메모리 사용률: < 80%
- 디스크 사용률: < 85%

**애플리케이션 메트릭:**
- 주문 레이턴시: < 2초
- API 에러율: < 1%
- Pod 재시작 횟수: 0 (일주일 기준)

**비즈니스 메트릭:**
- 일일 PnL
- 승률
- 최대 손실 (Drawdown)

### 알림 설정

**Discord Webhook 테스트:**
```bash
curl -X POST <DISCORD_WEBHOOK_URL> \
  -H "Content-Type: application/json" \
  -d '{"content": "🧪 테스트 알림입니다."}'
```

## 업데이트 및 배포

### 코드 업데이트

```bash
# 1. 코드 변경 후 이미지 빌드
docker buildx build --platform linux/arm64,linux/arm/v7 \
  -t ghcr.io/your-org/atlas-trading:v1.2.3 \
  --push .

# 2. 이미지 업데이트
kubectl set image deployment/strategy-runner \
  -n trading \
  strategy-runner=ghcr.io/your-org/atlas-trading:v1.2.3

# 3. 롤아웃 상태 확인
kubectl rollout status deployment/strategy-runner -n trading
```

### 롤백

```bash
# 이전 버전으로 롤백
kubectl rollout undo deployment/strategy-runner -n trading

# 특정 리비전으로 롤백
kubectl rollout undo deployment/strategy-runner -n trading --to-revision=2
```

## 유지보수

### 로그 정리

```bash
# 30일 이상 된 로그 삭제
find /var/log/atlas-trading -name "*.log" -mtime +30 -delete
```

### 디스크 공간 정리

```bash
# 사용되지 않는 Docker 이미지 정리
docker image prune -a -f

# 오래된 백업 삭제 (90일 이상)
find /var/backups/postgres -name "*.sql" -mtime +90 -delete
```

## 연락처

- **긴급 상황**: Discord #alerts 채널
- **일반 문의**: README.md 참조

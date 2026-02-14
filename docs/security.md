# 보안 정책

## 핵심 원칙

1. **출금 권한 절대 금지**: 거래소 API 키에 출금 권한을 절대 부여하지 않습니다
2. **평문 금지**: API 키, 비밀번호 등 민감 정보는 평문으로 저장 금지
3. **최소 권한**: 필요한 최소한의 권한만 부여
4. **감사 로그**: 모든 주요 작업은 로그 기록

## API 키 관리

### 거래소 API 키 설정

**필수 설정:**
- ✅ 거래 권한 (Trading)
- ✅ 조회 권한 (Read)
- ❌ 출금 권한 (Withdrawal) - **절대 활성화 금지**

**추가 보안:**
- IP 화이트리스트: 홈 네트워크 IP만 허용
- 2FA 필수 활성화

### Kubernetes Secrets 관리

**Sealed Secrets 사용:**
```bash
# 1. SealedSecret 생성
kubectl create secret generic exchange-api-keys \
  --from-literal=binance-api-key=YOUR_KEY \
  --from-literal=binance-api-secret=YOUR_SECRET \
  --dry-run=client -o yaml \
  | kubeseal -o yaml > cluster-config/manifests/exchange-api-sealed-secret.yaml

# 2. Git에 커밋 (암호화되어 안전)
git add cluster-config/manifests/exchange-api-sealed-secret.yaml
git commit -m "Add sealed exchange API keys"

# 3. 클러스터에 배포
kubectl apply -f cluster-config/manifests/exchange-api-sealed-secret.yaml
```

**평문 Secret 절대 금지:**
```yaml
# ❌ 이렇게 하지 마세요
apiVersion: v1
kind: Secret
metadata:
  name: exchange-api-keys
stringData:
  binance-api-key: "actual_key_here"  # 평문 노출!
```

## 네트워크 보안

### VLAN 분리

```
홈 네트워크 (일반)
  192.168.1.0/24

트레이딩 VLAN (격리)
  192.168.10.0/24
  ↓
  맥미니, 라즈베리파이만 연결
```

### K8s Network Policy

```yaml
# Pod 간 통신 제한
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: strategy-runner-policy
spec:
  podSelector:
    matchLabels:
      app: strategy-runner
  policyTypes:
  - Egress
  egress:
  # PostgreSQL 접근 허용
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  # 거래소 API 접근 허용
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

### 방화벽 규칙

**인바운드:**
- ❌ 모든 외부 트래픽 차단
- ✅ SSH만 특정 IP에서 허용 (관리용)

**아웃바운드:**
- ✅ 거래소 API (HTTPS 443)
- ✅ NTP (시간 동기화)
- ✅ DNS (53)
- ❌ 나머지 차단

## 코드 보안

### 환경변수 관리

**올바른 방법:**
```python
# app/core/config.py
import os

# K8s Secret에서 주입된 환경변수
BINANCE_API_KEY = os.environ["BINANCE_API_KEY"]
BINANCE_API_SECRET = os.environ["BINANCE_API_SECRET"]
```

**잘못된 방법:**
```python
# ❌ 절대 이렇게 하지 마세요
BINANCE_API_KEY = "actual_key_hardcoded"  # 코드에 평문!
```

### .gitignore 필수 항목

```gitignore
# 환경변수 파일
.env
.env.*
!.env.template

# K8s Secret (평문)
*-secret.yaml
!*-sealed-secret.yaml

# 로그 (API 키 포함 가능)
*.log
nohup.out
```

## 모니터링 및 알림

### 보안 이벤트 알림

**즉시 알림 대상:**
- 예상치 못한 주문 체결
- API 키 인증 실패
- Kill Switch 발동
- 비정상적 네트워크 트래픽

**Discord Webhook 설정:**
```python
import requests

def send_security_alert(message: str):
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    requests.post(webhook_url, json={
        "content": f"🚨 **보안 알림** 🚨\n{message}"
    })
```

## 침해 대응

### 의심 시나리오

**API 키 유출 의심:**
1. 즉시 거래소에서 API 키 비활성화
2. Kill Switch 활성화
3. 모든 오픈 포지션 수동 확인
4. 거래소 로그인 이력 확인
5. 새 API 키 발급 후 Sealed Secret 재생성

**비정상 거래 발견:**
1. Kill Switch 즉시 활성화
2. 거래소에서 수동으로 포지션 청산
3. 로그 분석 (누가, 언제, 무엇을)
4. 시스템 무결성 검사

### 정기 점검

**주 1회:**
- 거래소 로그인 이력 확인
- API 키 활성 상태 확인
- 백업 복원 테스트

**월 1회:**
- K8s 클러스터 보안 업데이트
- 의존성 취약점 스캔
- 침투 테스트 (펜테스팅)

## 규정 준수

### 로그 보존
- 모든 주문 로그: 최소 1년
- 에러 로그: 최소 3개월
- 시스템 로그: 최소 1개월

### 감사 추적
- 누가 (User/Pod)
- 언제 (Timestamp)
- 무엇을 (Action)
- 결과 (Success/Failure)

## 체크리스트

### 초기 설정 시
- [ ] 거래소 API 키 출금 권한 비활성화 확인
- [ ] IP 화이트리스트 설정
- [ ] 2FA 활성화
- [ ] Sealed Secrets 설치
- [ ] Network Policy 적용
- [ ] Discord Webhook 설정

### 정기 점검
- [ ] API 키 권한 재확인 (월 1회)
- [ ] 거래소 로그인 이력 확인 (주 1회)
- [ ] 백업 복원 테스트 (주 1회)
- [ ] 보안 업데이트 적용 (월 1회)

---

**⚠️ 중요**: 보안은 한 번에 끝나는 작업이 아닙니다. 지속적인 모니터링과 개선이 필요합니다.

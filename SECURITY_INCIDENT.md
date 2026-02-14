# 보안 사고 대응 체크리스트

**발생일**: 2024-10-08 23:53 (nohup.out 수정 시간 기준)
**발견일**: 2026-02-15
**상태**: 악성코드 실행 흔적 확인, 현재 활성 위협 없음

## 🔍 사고 분석

### 발견된 악성 파일
- `/Users/jang-yeonghwan/atlas-trading/core-platform/nohup.out`
- 크기: 36KB
- macOS 인포스틸러 (AppleScript 난독화)

### 악성 행위
1. ✅ 암호화폐 지갑 탈취 시도 (200+ 확장 프로그램)
2. ✅ Keychain 탈취 시도
3. ✅ 브라우저 쿠키/로그인 정보 탈취 시도
4. ✅ Apple Notes 탈취 시도
5. ✅ 데이터 유출 시도 (185.93.89.62)

### 현재 상태
- ✅ 프로세스 종료됨 (Terminated: 15)
- ✅ 악성 IP 연결 없음
- ✅ LaunchDaemon 정상
- ⚠️ 일부 데이터 유출 가능성

---

## 📋 즉시 조치 체크리스트

### Priority 1: 계정 보안 (즉시)

#### 거래소 계정
- [ ] **Binance API 키 폐기 및 재발급**
  - 로그인: https://www.binance.com
  - API Management > 기존 키 삭제
  - 새 API 키 생성 (거래 권한만, 출금 금지, IP 화이트리스트)

- [ ] **Bybit API 키 폐기 및 재발급**
  - 로그인: https://www.bybit.com
  - API Management > 기존 키 삭제
  - 새 API 키 생성 (거래 권한만, 출금 금지, IP 화이트리스트)

- [ ] **거래소 로그인 이력 확인**
  - 의심스러운 로그인 있는지 확인
  - 2FA 활성화 재확인

#### 암호화폐 지갑
- [ ] **하드웨어 지갑 (Ledger/Trezor) 확인**
  - PIN 변경
  - 시드구문 노출 여부 확인
  - 의심스러운 거래 내역 확인

- [ ] **소프트웨어 지갑 자산 이동**
  - MetaMask, Exodus 등 사용 중인 지갑
  - 새 지갑 생성 후 자산 즉시 이동
  - 기존 지갑 시드구문 폐기

#### 비밀번호 변경
- [ ] **거래소 비밀번호 변경** (Binance, Bybit)
- [ ] **이메일 비밀번호 변경** (거래소 연동 이메일)
- [ ] **브라우저 저장 비밀번호 전체 변경**
- [ ] **macOS 로그인 비밀번호 변경**

---

### Priority 2: 시스템 정리 (1시간 이내)

#### 악성 파일 제거
```bash
# nohup.out 삭제
rm /Users/jang-yeonghwan/atlas-trading/core-platform/nohup.out

# /tmp/ 의심 파일 확인 및 삭제
ls -la /tmp/ | grep -E "[0-9]{5}"
rm -rf /tmp/[의심스러운숫자]/

# .username, .chost, .pwd 파일 확인
ls -la ~/. | grep -E "username|chost|pwd|botid"
rm ~/.username ~/.chost ~/.pwd ~/.botid 2>/dev/null
```

#### 시스템 점검
```bash
# LaunchDaemon 재확인
sudo ls -la /Library/LaunchDaemons/ | grep -v "com.apple"

# 실행 중인 프로세스 확인
ps aux | grep -i "osascript\|curl.*185"

# 네트워크 연결 확인
lsof -i | grep -v "LISTEN"
```

---

### Priority 3: 예방 조치 (24시간 이내)

#### 보안 강화
- [ ] **FileVault 암호화 활성화**
  ```bash
  # System Preferences > Security & Privacy > FileVault
  ```

- [ ] **방화벽 활성화**
  ```bash
  sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
  ```

- [ ] **Gatekeeper 확인**
  ```bash
  spctl --status
  ```

#### 환경 정리
- [ ] **core-platform/.env 파일 삭제**
  ```bash
  rm /Users/jang-yeonghwan/atlas-trading/core-platform/.env
  ```

- [ ] **API 키를 환경변수에서 제거**
  ```bash
  # .zshrc, .bashrc 등에서 BINANCE_API_KEY 등 제거
  ```

---

### Priority 4: 모니터링 (지속)

#### 일일 점검 (1주일)
- [ ] 거래소 로그인 이력
- [ ] 지갑 거래 내역
- [ ] 이메일 로그인 알림
- [ ] 시스템 로그 (`Console.app`)

#### 주간 점검 (1개월)
- [ ] 거래소 API 키 활성 상태
- [ ] 지갑 잔액 변동
- [ ] 신용카드 청구 내역

---

## 🔐 새 API 키 설정 (재발급 후)

### 1. 환경변수 파일 생성 (임시, 테스트용만)
```bash
# core-platform/.env.example 복사
cp .env.example .env.local

# 새 API 키 입력 (.env.local은 .gitignore에 포함)
BINANCE_API_KEY=<새키>
BINANCE_API_SECRET=<새시크릿>
```

### 2. K8s Sealed Secret으로 이전 (실전 배포 시)
```bash
# Sealed Secret 생성 (새 atlas-trading 레포에서)
kubectl create secret generic exchange-api-keys \
  --from-literal=binance-api-key=<새키> \
  --from-literal=binance-api-secret=<새시크릿> \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > cluster-config/manifests/exchange-api-sealed-secret.yaml

# Git 커밋 (암호화되어 안전)
git add cluster-config/manifests/exchange-api-sealed-secret.yaml
git commit -m "Update sealed API keys after security incident"
```

---

## 📊 사고 타임라인

| 시간 | 이벤트 | 상태 |
|------|--------|------|
| 2024-10-08 23:53 | 악성코드 실행 (nohup.out 생성) | ⚠️ |
| 2024-10-08 23:53 | 프로세스 종료 (Terminated: 15) | ✅ |
| 2026-02-15 03:xx | Opus 에이전트가 분석 중 발견 | ✅ |
| 2026-02-15 03:xx | 즉시 조치 시작 | 🔄 |

---

## ⚠️ 권장 사항

### 단기 (1주일)
- 모든 암호화폐 자산을 새 지갑으로 이동
- 거래소 API 키 일일 점검
- 시스템 로그 모니터링

### 중기 (1개월)
- macOS 클린 재설치 고려
- 하드웨어 지갑 사용 권장
- 정기 보안 점검 루틴 확립

### 장기
- API 키 정기 로테이션 (3개월)
- 보안 교육 및 인식 강화
- 백업 시스템 구축

---

**⚠️ 중요**: 이 문서는 `.gitignore`에 추가하지 마세요. 사고 기록으로 보관합니다.

# Atlas Trading - 암호화폐 퀀트 트레이딩 플랫폼

홈서버 K8s 클러스터 기반 암호화폐 자동매매 시스템 (Monorepo)

## 🏗️ 아키텍처

- **하드웨어**: M1 맥미니 1대 + 라즈베리파이 3대
- **K8s**: k3s (ARM 최적화)
- **언어**: Python 3.12
- **거래소**: CCXT API (Binance, Bybit)
- **데이터베이스**: PostgreSQL + TimescaleDB (맥미니 외부)
- **보안**: Kubernetes Secrets + Sealed Secrets

## 📁 Monorepo 구조

```
atlas-trading/
├── cluster-config/         # K8s 클러스터 설정
│   ├── k3s/               # k3s 서버/에이전트 설정
│   ├── manifests/         # K8s 매니페스트 (Deployment, Service 등)
│   └── scripts/           # 클러스터 관리 스크립트
│
├── core-platform/         # 메인 트레이딩 플랫폼
│   ├── app/
│   │   ├── ccxt/         # 거래소 API 래퍼
│   │   ├── risk/         # 리스크 관리
│   │   ├── notifications/ # 알림 (Discord)
│   │   └── strategies/   # 트레이딩 전략
│   ├── Dockerfile
│   └── pyproject.toml
│
├── infrastructure/        # 인프라 설정
│   ├── postgres/         # PostgreSQL/TimescaleDB
│   ├── monitoring/       # Prometheus, Grafana
│   └── redis/            # Kill Switch, Celery
│
└── docs/                 # 문서
    ├── architecture.md
    ├── security.md
    └── runbook.md
```

## 🚀 Quick Start

### 1. 로컬 개발 환경

```bash
# Core Platform 개발
cd core-platform
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. K8s 클러스터 구성 (홈서버)

```bash
# 클러스터 설정 및 배포
cd cluster-config
./scripts/setup-cluster.sh
```

## 📊 개발 로드맵

### ✅ Phase 0: 프로젝트 초기화 (Week 0)
- [x] Monorepo 구조 생성
- [x] Git 초기화
- [ ] 기존 core-platform 코드 마이그레이션

### 🔨 Phase 1: 인프라 구축 (Week 1-4)
- [ ] k3s 클러스터 구성 (맥미니 + 라즈베리파이 3대)
- [ ] PostgreSQL/TimescaleDB 설정 (맥미니 외부)
- [ ] Dockerfile 작성 (multi-arch)
- [ ] Sealed Secrets 설정

### 🛡️ Phase 2: 리스크 관리 (Week 5-6)
- [ ] Pre-trade 검증 시스템
- [ ] Kill Switch (Redis 기반)
- [ ] Discord 알림

### 🧪 Phase 3: 테스트넷 (Week 7-12)
- [ ] Binance Testnet 장기 운용 (최소 4주)
- [ ] 모니터링 & 로깅
- [ ] 백업 자동화

### 💰 Phase 4: 실전 (Week 13+)
- [ ] 소액 실전 ($100-500)
- [ ] 성능 최적화

## ⚠️ 핵심 원칙

1. **Fail-Closed**: 불확실하면 거래 중단
2. **Infrastructure-First**: 인프라 먼저, 전략은 나중
3. **Zero Withdrawal**: API 키에 출금 권한 절대 금지
4. **Observability-First**: 모든 것을 측정하고 기록
5. **Single Variable Change**: 한 번에 하나씩만 변경

## 📚 문서

- [아키텍처 설계](docs/architecture.md) - 시스템 구조 및 데이터 흐름
- [보안 정책](docs/security.md) - API 키 관리, 네트워크 보안
- [운영 가이드](docs/runbook.md) - 장애 대응 절차

## 🔐 보안

- API 키는 **Sealed Secrets**로 관리 (평문 금지)
- 거래소 API 키에 **출금 권한 절대 부여 금지**
- 홈 네트워크 IP만 화이트리스트
- 2FA 필수

## 📈 성능 목표

- **가동률**: 99.9% (연 8.76시간 다운타임)
- **레이턴시**: < 2초 (주문 생성 → 거래소)
- **테스트넷 기간**: 최소 4주
- **소액 실전 기간**: 최소 2주

---

**⚠️ 주의**: 이 시스템은 실제 자금을 다룹니다. 테스트넷 충분한 검증 없이 실전 운용을 절대 금지합니다.

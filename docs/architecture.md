# 아키텍처 설계

## 시스템 개요

Atlas Trading은 홈서버 K8s 클러스터에서 운영되는 암호화폐 자동매매 시스템입니다.

## 하드웨어 구성

```
┌─────────────────────────────────────────────────────┐
│                  홈 라우터 (VLAN 분리)                │
└────┬──────────┬──────────┬──────────┬─────────────┘
     │          │          │          │
     │          │          │          │
┌────▼────┐ ┌──▼─────┐ ┌──▼─────┐ ┌──▼─────┐
│ M1      │ │ RPi #1 │ │ RPi #2 │ │ RPi #3 │
│ 맥미니   │ │        │ │        │ │        │
│         │ │ k3s    │ │ k3s    │ │ k3s    │
│ k3s     │ │ agent  │ │ agent  │ │ agent  │
│ server? │ │        │ │        │ │        │
│ or      │ │ [Pod]  │ │ [Pod]  │ │ [Pod]  │
│ DB only │ │ Strategy│ │ Strategy│ │ Data   │
│         │ │ Runner │ │ Runner │ │Collector│
│ [PostgreSQL] │ │        │ │        │
│ [Redis]     │ │        │ │        │
└─────────┘ └────────┘ └────────┘ └────────┘
```

### 노드 역할

**M1 맥미니**
- 옵션 A: k3s server (컨트롤 플레인) + DB
- 옵션 B: DB 전용 (K8s 외부)
- PostgreSQL + TimescaleDB
- Redis (Kill Switch + Celery)
- 자동 백업

**라즈베리파이 × 3**
- k3s agent (워커 노드)
- 트레이딩 Pod 실행
- 데이터 수집 Pod

## 소프트웨어 스택

### 컨테이너 오케스트레이션
- **k3s**: 라즈베리파이 최적화, 경량 K8s
- **containerd**: 컨테이너 런타임

### 애플리케이션
- **언어**: Python 3.12
- **프레임워크**: FastAPI
- **거래소 API**: CCXT
- **태스크 큐**: Celery

### 데이터베이스
- **PostgreSQL 14+**: 주문 이력, 전략 상태
- **TimescaleDB**: OHLCV 시계열 데이터
- **Redis**: Kill Switch 플래그, Celery 브로커

### 보안
- **Sealed Secrets**: API 키 암호화 관리
- **Network Policy**: Pod 간 통신 제한

### 모니터링
- **Prometheus**: 메트릭 수집
- **node_exporter**: 노드 모니터링
- **Discord Webhook**: 실시간 알림

## 데이터 흐름

### 1. 데이터 수집
```
거래소 API
    ↓
Data Collector Pod (CCXT)
    ↓
PostgreSQL/TimescaleDB
```

### 2. 매매 시그널 생성
```
PostgreSQL (최신 OHLCV)
    ↓
Strategy Runner Pod
    ↓
매매 시그널 생성
```

### 3. 주문 실행
```
Strategy Runner
    ↓
Pre-Trade Risk Check
    ↓ (통과)
Kill Switch Check (Redis)
    ↓ (비활성)
주문 실행 (CCXT)
    ↓
거래소 API
    ↓
주문 결과 기록 (PostgreSQL)
    ↓
Discord 알림
```

## 리스크 관리 시스템

### Pre-Trade 검증
- 최대 주문 금액 체크
- 최대 포지션 크기 체크
- 잔고 충분성 검증

### Kill Switch
- Redis 기반 글로벌 플래그
- 활성화 시 모든 신규 주문 차단
- 오픈 포지션 시장가 청산

### 알림 시스템
- 모든 주문 체결 알림
- 에러 발생 시 즉시 알림
- Kill Switch 발동 알림
- 일일 리스크 리포트

## 네트워크 구성

### 보안 계층
1. **물리적 분리**: 트레이딩 전용 VLAN
2. **K8s Network Policy**: Pod 간 통신 제한
3. **Sealed Secrets**: API 키 암호화
4. **IP 화이트리스트**: 거래소 API 접근 제한

### 통신 흐름
- **Pod → PostgreSQL**: 5432 (맥미니)
- **Pod → Redis**: 6379 (맥미니)
- **Pod → 거래소 API**: HTTPS (443)
- **외부 → 없음**: 인바운드 트래픽 차단

## 배포 전략

### 컨테이너 이미지
- Multi-arch 빌드: `linux/arm64`, `linux/arm/v7`
- 로컬 레지스트리 또는 GitHub Container Registry

### 롤링 업데이트
- K8s Deployment `strategy: RollingUpdate`
- `maxUnavailable: 1`, `maxSurge: 1`

### 백업 전략
- PostgreSQL: 일일 자동 `pg_dump`
- 외부 저장소 (NAS 또는 클라우드)
- 복원 테스트 주 1회

## 확장성 설계

### 수평 확장
- Strategy Runner Pod: 여러 전략 병렬 실행
- Data Collector Pod: 거래소별 분리

### 수직 확장 제한
- 라즈베리파이: 메모리 2-4GB (모델에 따라)
- 가벼운 워크로드에 집중

## 장애 대응

### 노드 장애
- K8s 자동 Pod 재스케줄링
- 다른 노드로 자동 이동

### 네트워크 장애
- Fail-Closed: 거래소 연결 불가 시 모든 신규 주문 중단
- 외부 헬스체크 (UptimeRobot 등)

### 데이터베이스 장애
- PostgreSQL 연결 실패 시 모든 거래 중단
- 자동 백업으로부터 복원

## 성능 목표

- **레이턴시**: < 2초 (주문 생성 → 거래소 전송)
- **가동률**: 99.9% (연 8.76시간 다운타임)
- **RTO**: < 30분 (복구 목표 시간)
- **RPO**: < 1시간 (데이터 손실 허용)

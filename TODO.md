# Atlas Trading - TODO List

## 🎯 High Priority

### 1. 백테스트 결과 저장 방식 개선 (Hybrid Approach)

**현재 상태:**
- PostgreSQL DB에만 저장
- 웹 대시보드에서 조회 가능
- 재현성/버전 관리 없음

**목표:**
DB(빠른 조회) + 파일(재현성/Git 관리) 하이브리드 방식

**구현 사항:**

#### Phase 1: 파일 Export 기능 (30분~1시간)
- [ ] 백테스트 결과를 JSON으로 export
  - `results/{date}_{strategy}_{symbol}_{timeframe}.json`
  - 포함: 전체 결과, trades, equity_curve, parameters
- [ ] CSV export (거래 내역만)
  - `results/{date}_{strategy}_{symbol}_trades.csv`
- [ ] Summary 파일 자동 업데이트
  - `results/summary.json` - 모든 백테스트 메타데이터

**파일 구조:**
```
results/
├── 2024-02-15_RSI_BTC_1d.json           # 전체 결과
├── 2024-02-15_RSI_BTC_1d_trades.csv     # 거래 내역
├── 2024-02-15_MACD_ETH_4h.json
├── summary.json                          # 전체 요약
└── .gitignore                            # 큰 파일 제외
```

#### Phase 2: Auto-Archive & Cleanup (1~2시간)
- [ ] 백테스트 실행 시 자동으로 파일 저장
  - `BacktestEngine.run()` 또는 API 엔드포인트에서 호출
- [ ] DB 자동 정리 스크립트
  - 30일 이상 된 데이터 → 파일로 export 후 DB에서 삭제
  - 또는 Archive 테이블로 이동
- [ ] API 엔드포인트 추가
  - `GET /api/v1/backtests/{id}/export` - JSON/CSV 다운로드
  - `POST /api/v1/backtests/import` - 파일에서 DB로 복원

#### Phase 3: Git Integration (선택, 30분)
- [ ] 중요한 결과만 Git 커밋
  - 플래그: `is_milestone=True`인 백테스트만
  - 예: 최종 전략, 논문/보고서용 결과
- [ ] `.gitignore` 설정
  - 일반 백테스트 결과는 제외
  - `results/*.json` 제외
  - `results/milestones/*.json` 포함

**파일 포맷 예시:**
```json
{
  "metadata": {
    "id": 14,
    "strategy_name": "RSI_Mean_Reversion_14_30_70",
    "symbol": "BTC/USDT",
    "timeframe": "1d",
    "start_date": "2024-01-01",
    "end_date": "2026-02-14",
    "executed_at": "2024-02-15T10:30:00Z"
  },
  "parameters": {
    "initial_capital": 10000,
    "commission": 0.001,
    "use_kelly_sizing": true,
    "kelly_fraction": 0.5
  },
  "results": {
    "final_capital": 10389.45,
    "total_return": 3.89,
    "max_drawdown": -13.67,
    "sharpe_ratio": 0.234,
    "total_trades": 11,
    "win_rate": 63.64
  },
  "trades": [...],
  "equity_curve": [...]
}
```

**구현 위치:**
- `core-platform/app/backtesting/exporter.py` - Export 로직
- `core-platform/app/backtesting/importer.py` - Import 로직
- `api-server/app/api/v1/export.py` - Export API
- `core-platform/scripts/archive_old_backtests.py` - 자동 정리

---

## 🔬 Strategy Development

### 2. 전략 5~10개 추가 (우선순위 높음)

**현재:** RSI, Golden Cross (2개)

**추가할 전략:**
- [ ] Bollinger Bands Mean Reversion ⭐ (쉬움, 2~3시간)
- [ ] MACD Crossover ⭐ (쉬움, 2~3시간)
- [ ] EMA Ribbon ⭐⭐ (중간, 3~4시간)
- [ ] Breakout (Donchian Channel) ⭐⭐ (중간, 3~4시간)
- [ ] Volume-Price Trend (VPT) ⭐⭐ (중간, 3~4시간)
- [ ] Ichimoku Cloud ⭐⭐⭐ (복잡, 5~6시간)
- [ ] Multi-timeframe Trend Following ⭐⭐⭐ (복잡, 6~8시간)

**구현 위치:**
- `core-platform/app/strategies/bollinger_bands.py`
- `core-platform/app/strategies/macd.py`
- ...

**테스트:**
- 각 전략마다 백테스트 실행
- Monte Carlo 시뮬레이션으로 검증
- 결과 파일 저장 (`results/`)

---

## 📊 Portfolio Management

### 3. 전략 상관관계 분석 (4~6시간)

**목표:** 여러 전략을 어떻게 조합할지 결정

**구현 사항:**
- [ ] Correlation Matrix 계산
  - 전략 간 수익률 상관계수
  - 시각화: Heatmap
- [ ] Drawdown 동시성 분석
  - 같은 시기에 손실이 나는지 확인
- [ ] Diversification Score
  - 포트폴리오 분산 정도 측정
- [ ] Sharpe Ratio 비교

**구현 위치:**
- `core-platform/app/analytics/correlation.py`
- `api-server/app/api/v1/correlation.py`
- `web-dashboard/src/pages/StrategyCorrelation.tsx`

**API 엔드포인트:**
- `GET /api/v1/analytics/correlation` - 전략 간 상관관계
- `GET /api/v1/analytics/diversification` - 분산 점수

---

### 4. 포트폴리오 최적화 & 리밸런싱 (1~2일)

**Kelly Criterion 확장:**
- [ ] Multi-strategy Kelly
  - 여러 전략에 자본을 어떻게 배분할지
  - Mean-Variance Optimization과 결합
- [ ] Fractional Kelly
  - Full Kelly는 너무 공격적 → 1/2 Kelly, 1/4 Kelly

**리밸런싱 알고리즘:**
- [ ] Time-based (매주/매월 고정)
- [ ] Threshold-based (비중 5% 이상 변동 시)
- [ ] Kelly-adjusted (성과에 따라 동적)

**구현 위치:**
- `core-platform/app/portfolio/optimizer.py`
- `core-platform/app/portfolio/rebalancer.py`
- `web-dashboard/src/pages/Portfolio.tsx`

**API 엔드포인트:**
- `POST /api/v1/portfolio/optimize` - 최적 자본 배분 계산
- `POST /api/v1/portfolio/rebalance` - 리밸런싱 시뮬레이션

---

## 💰 Live Trading

### 5. 실거래 API 연동 (3~4일)

**단계별 접근:**
1. **Read-only API** (1일)
   - [ ] 바이낸스 API 클라이언트
   - [ ] 바이비트 API 클라이언트
   - [ ] 잔고 조회
   - [ ] 포지션 조회
   - [ ] Balance & Portfolio 페이지 실제 데이터 표시

2. **Paper Trading** (1~2일)
   - [ ] 모의 주문 실행 (실제 돈 안 씀)
   - [ ] 포지션 추적
   - [ ] PnL 계산
   - [ ] 주문 히스토리

3. **Live Trading** (1일)
   - [ ] 실제 주문 실행
   - [ ] Risk Management
     - 최대 손실 제한
     - 일일 거래 횟수 제한
     - 긴급 정지 (Kill Switch)
   - [ ] 알림 (Telegram/Discord)

**구현 위치:**
- `core-platform/app/exchange/binance.py`
- `core-platform/app/exchange/bybit.py`
- `core-platform/app/trading/executor.py`
- `core-platform/app/trading/monitor.py`
- `web-dashboard/src/pages/Trading/Balance.tsx`

**Safety First:**
- [ ] 환경 변수로 API 키 관리 (.env)
- [ ] Read-only API 키로 테스트
- [ ] Paper Trading으로 충분히 검증
- [ ] 소액으로 시작 (초기 $100~$500)

---

## 🖥️ Infrastructure

### 6. 홈서버 구축 (1~2일)

**목표:** 24/7 자동 실행 환경

**구성:**
- [x] ArgoCD GitOps 파이프라인 (Task #86 완료)
  - k3d 클러스터에 ArgoCD 설치 완료
  - LoadBalancer 서비스 구성 (Tailscale 네트워크 접근)
  - Application 매니페스트 생성 (main 브랜치 auto-sync)
  - 문서화: docs/ARGOCD.md
- [ ] Docker Compose
  - PostgreSQL
  - Redis (캐싱/작업큐)
  - API Server
  - Web Dashboard
  - Nginx (리버스 프록시)
- [ ] Systemd 설정 (자동 재시작)
- [ ] 로그 관리 (Logrotate)
- [x] 모니터링 (Grafana + Prometheus) - 완료 (Task #85, 2026-02-18)
  - k3d 클러스터에 kube-prometheus-stack 설치
  - Tailscale 네트워크로 접근: http://100.110.86.86:31177
  - Kubernetes 클러스터/Node Exporter 메트릭 수집
  - 사전 구성된 대시보드 포함
  - 문서: docs/MONITORING.md
- [ ] 백업 자동화 (DB + 파일)

**구현 위치:**
- `docker-compose.yml`
- `nginx.conf`
- `systemd/atlas-trading.service`

---

## 📈 Analysis & Monitoring

### 7. 고급 분석 기능 (선택)

- [ ] Regime Analysis (시장 상황별 성과)
- [ ] Walk-Forward Analysis (시간에 따른 안정성)
- [ ] Parameter Sensitivity (파라미터 민감도)
- [ ] Market Analysis (BTC/ETH 가격, 변동성)
- [ ] Risk Monitoring (VaR, CVaR, 집중도)

---

## 🎨 UI/UX Improvements

### 8. 어드민 대시보드 개선

- [ ] Balance & Portfolio 페이지 구현
- [ ] Strategy Management 페이지
  - 전략 목록
  - 파라미터 편집 UI
  - 활성화/비활성화 토글
- [ ] Live Performance 대시보드
- [ ] Market Analysis 차트
- [ ] 모바일 반응형 최적화

---

## 📝 Documentation

### 9. 문서화

- [ ] README.md 작성
  - 프로젝트 소개
  - 설치 방법
  - 사용 방법
- [ ] API 문서 (Swagger/OpenAPI)
- [ ] 전략 설명서
  - 각 전략의 로직
  - 파라미터 설명
  - 백테스트 결과
- [ ] 아키텍처 문서
  - 시스템 구조
  - 데이터 흐름
  - 배포 가이드

---

## ✅ Completed

- [x] Kelly Criterion position sizing
- [x] Monte Carlo simulation with dynamic Kelly
- [x] Multi-exchange support (Binance, Bybit, OKX, etc.)
- [x] Admin dashboard with sidebar navigation
- [x] Dark/light mode toggle
- [x] Basic backtest infrastructure
- [x] Cost stress test
- [x] Profit concentration analysis
- [x] Rolling Sharpe ratio
- [x] Holding time vs PnL analysis
- [x] Slight Edge visualization

---

## 📅 Suggested Timeline

**Week 1-2:** 전략 5~7개 추가
**Week 3:** 백테스트 결과 export/import + 상관관계 분석
**Week 4:** 포트폴리오 최적화 & 리밸런싱
**Week 5-6:** Paper Trading 구축
**Week 7:** 홈서버 구축 & 배포
**Week 8+:** Live Trading 시작 (소액)

---

## 💡 Notes

- 전략 개발과 백테스트가 가장 중요 (먼저 해야 다른 기능이 의미 있음)
- Paper Trading으로 충분히 검증 후 Live Trading
- 리스크 관리 철저히 (최대 손실, 일일 한도 등)
- 정기적으로 백테스트 재실행 (시장 변화 반영)

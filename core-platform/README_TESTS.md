# Atlas Trading - 테스트 가이드

## 📋 테스트 구조

```
tests/
├── test_strategy_base.py      # Strategy 인터페이스 및 지표 테스트 (20 tests)
├── test_backtest_engine.py    # 백테스팅 엔진 테스트 (13 tests)
└── test_risk_manager.py       # Risk Manager 테스트 (20 tests)
```

**총 53개 테스트**

---

## 🚀 테스트 실행

### 전체 테스트 실행
```bash
pytest tests/ -v
```

### 특정 파일 테스트
```bash
pytest tests/test_strategy_base.py -v
pytest tests/test_backtest_engine.py -v
pytest tests/test_risk_manager.py -v
```

### 커버리지 포함
```bash
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
```

### 빠른 실행 (경고 숨김)
```bash
pytest tests/ -q
```

---

## 📊 테스트 커버리지

현재 커버리지:
- **Strategy Base**: ~80%
- **Backtest Engine**: ~80%
- **Risk Manager**: ~95%

### 커버리지 리포트 보기
```bash
# HTML 리포트 생성
pytest tests/ --cov=app --cov-report=html

# 브라우저에서 열기
open htmlcov/index.html
```

---

## ✅ 테스트 체크리스트

### Strategy Base (test_strategy_base.py)
- [x] 전략 초기화 및 파라미터 설정
- [x] 파라미터 검증 (범위, 타입, 필수 여부)
- [x] 파라미터 업데이트 및 리셋
- [x] 포지션 진입/청산 콜백
- [x] 데이터 전처리 및 지표 추가
- [x] 시그널 생성 및 검증
- [x] 지표 계산 (SMA, EMA, RSI, BB, MACD, ATR, ADX)

### Backtest Engine (test_backtest_engine.py)
- [x] 엔진 초기화
- [x] 롱/숏 포지션 진입 및 청산
- [x] 자산 계산 (Equity, Position Value)
- [x] 수수료 차감
- [x] Kelly Criterion 계산
- [x] 전략 실행 및 결과 계산
- [x] 성과 지표 계산 (Return, MDD, Sharpe)
- [x] Equity Curve 기록
- [x] 여러 거래 실행

### Risk Manager (test_risk_manager.py)
- [x] Risk Manager 초기화
- [x] 메트릭 업데이트 (자산, PnL, Drawdown)
- [x] 시그널 검증
- [x] 일일 손실 제한
- [x] 최대 낙폭 제한
- [x] 포지션 크기 제한
- [x] 거래 빈도 제한
- [x] 연속 손실 제한 및 일시정지
- [x] Kill Switch 활성화/해제
- [x] 거래 후 메트릭 업데이트
- [x] 청산 시그널은 항상 허용

---

## 🧪 테스트 작성 가이드

### 1. 새 전략 테스트

```python
from app.strategies.base import Strategy, Signal
import pytest

class TestMyStrategy:
    def test_strategy_initialization(self):
        strategy = MyStrategy(param1=10)
        assert strategy.param1 == 10

    def test_signal_generation(self):
        strategy = MyStrategy()
        df = create_sample_data()
        df = strategy.prepare_data(df)

        signal = strategy.on_bar(df.iloc[-1])
        assert signal.action in ['long', 'short', 'close', 'hold']
```

### 2. 백테스트 시나리오 테스트

```python
def test_profitable_strategy(sample_data):
    engine = BacktestEngine(initial_capital=10000)
    strategy = ProfitableStrategy()

    result = engine.run(sample_data, strategy)

    assert result['total_return'] > 0
    assert result['win_rate'] > 50
```

### 3. Risk Manager 테스트

```python
def test_custom_risk_limit():
    limits = RiskLimits(max_daily_loss_pct=3.0)
    manager = RiskManager(initial_capital=10000, limits=limits)

    # 3% 손실 발생
    manager.metrics.daily_pnl_pct = -3.1

    signal = {'action': 'long', 'size': 0.5}
    assert manager.validate_signal(signal, 50000) == False
```

---

## 🔧 CI/CD 통합

### GitHub Actions 예시

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.14

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest tests/ --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## 📝 테스트 베스트 프랙티스

1. **독립성**: 각 테스트는 독립적으로 실행 가능해야 함
2. **재현성**: 랜덤 시드 사용 시 고정값 설정
3. **명확성**: 테스트 이름으로 목적을 명확히 표현
4. **빠름**: 단위 테스트는 1초 이내 실행
5. **커버리지**: 핵심 로직은 80% 이상 커버

---

## 🐛 테스트 실패 시 디버깅

### 상세 로그 보기
```bash
pytest tests/test_strategy_base.py -v --tb=long
```

### 특정 테스트만 실행
```bash
pytest tests/test_strategy_base.py::TestStrategyBase::test_strategy_initialization -v
```

### 디버거 사용
```bash
pytest tests/test_strategy_base.py --pdb
```

---

## 📚 추가 테스트 계획

### 향후 추가할 테스트
- [ ] Monte Carlo 시뮬레이션 테스트
- [ ] Walk-Forward Analysis 테스트
- [ ] Parameter Optimization 테스트
- [ ] 실시간 데이터 스트리밍 테스트
- [ ] API 엔드포인트 통합 테스트
- [ ] Paper Trading 엔진 테스트
- [ ] Go 실행 엔진 테스트 (향후)

---

## 💡 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [pytest-cov 가이드](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

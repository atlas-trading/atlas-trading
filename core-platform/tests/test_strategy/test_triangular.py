from decimal import Decimal

from atlas.core.exchange import Exchange
from atlas.core.quote import Quote
from atlas.core.ticker import Ticker
from atlas.core.trading_pair import TradingPair
from atlas.strategy.arbitrage.triangular import _TRIANGLES, TriangularArbitrageStrategy

_EXCHANGE = Exchange.BINANCE
_QTY = Decimal("0.01")


def _strategy(min_profit: Decimal = Decimal("0.002")) -> TriangularArbitrageStrategy:
    return TriangularArbitrageStrategy(
        exchange=_EXCHANGE, order_quantity=_QTY, min_profit=min_profit
    )


# --- BTC-ETH-USDT 삼각형: arb 발생 가격 (spread 없음, 3.2% 오차) ---
_ARB_TICKERS = {
    "BTC/USDT": {"bid": 50000, "ask": 50000},
    "ETH/BTC": {"bid": 0.06, "ask": 0.06},
    "ETH/USDT": {"bid": 3200, "ask": 3200},  # fair value = 50000*0.06 = 3000 → 6.7% overpriced
}

# --- BTC-ETH-USDT 삼각형: 공정 가격 (spread 있음, arb 없음) ---
_FAIR_TICKERS = {
    "BTC/USDT": {"bid": 49999, "ask": 50001},
    "ETH/BTC": {"bid": 0.05999, "ask": 0.06001},
    "ETH/USDT": {"bid": 2999, "ask": 3001},
}


def test_all_pairs_count():
    strategy = _strategy()
    pairs = strategy.all_pairs()
    assert len(pairs) == 9


def test_all_pairs_no_duplicates():
    strategy = _strategy()
    pairs = strategy.all_pairs()
    assert len(set(pairs)) == len(pairs)


def test_all_pairs_covers_all_triangles():
    strategy = _strategy()
    pair_set = set(strategy.all_pairs())
    for triangle in _TRIANGLES:
        assert triangle <= pair_set


def test_on_tickers_empty_returns_no_signals():
    strategy = _strategy()
    assert strategy.on_tickers({}) == []


def test_on_tickers_partial_prices_skips_triangle():
    # BTC-ETH-USDT 삼각형에서 ETH/BTC만 빠진 경우
    strategy = _strategy()
    tickers = {
        "BTC/USDT": {"bid": 50000, "ask": 50001},
        "ETH/USDT": {"bid": 3000, "ask": 3001},
    }
    assert strategy.on_tickers(tickers) == []


def test_on_tickers_fair_prices_no_signal():
    strategy = _strategy()
    assert strategy.on_tickers(_FAIR_TICKERS) == []


def test_on_tickers_arb_returns_signal():
    strategy = _strategy()
    signals = strategy.on_tickers(_ARB_TICKERS)
    assert len(signals) == 1


def test_signal_exchange():
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    assert signal.exchange == _EXCHANGE


def test_signal_quantities():
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    assert signal.leg1_quantity == _QTY
    assert signal.leg2_quantity == _QTY
    assert signal.leg3_quantity == _QTY


def test_signal_expected_profit_positive():
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    assert signal.expected_profit > 0


def test_signal_pairs_belong_to_btc_eth_usdt_triangle():
    strategy = _strategy()
    [signal] = strategy.on_tickers(_ARB_TICKERS)
    btc_eth_usdt = frozenset(
        {
            TradingPair(ticker=Ticker.BTC, quote=Quote.USDT),
            TradingPair(ticker=Ticker.ETH, quote=Quote.BTC),
            TradingPair(ticker=Ticker.ETH, quote=Quote.USDT),
        }
    )
    signal_pairs = {signal.leg1_pair, signal.leg2_pair, signal.leg3_pair}
    assert signal_pairs == btc_eth_usdt


def test_min_profit_threshold_filters_signal():
    # 아주 높은 min_profit 설정 → 신호 차단
    strategy = _strategy(min_profit=Decimal("0.5"))
    assert strategy.on_tickers(_ARB_TICKERS) == []


def test_price_cache_persists_across_calls():
    strategy = _strategy()
    # 첫 번째 호출: BTC/USDT, ETH/USDT만
    strategy.on_tickers(
        {
            "BTC/USDT": {"bid": 50000, "ask": 50000},
            "ETH/USDT": {"bid": 3200, "ask": 3200},
        }
    )
    # 두 번째 호출: ETH/BTC 추가 → 캐시와 합쳐 삼각형 완성
    signals = strategy.on_tickers(
        {
            "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        }
    )
    assert len(signals) == 1


def test_invalid_symbol_ignored():
    strategy = _strategy()
    tickers = {
        "BTC/USDT": {"bid": 50000, "ask": 50000},
        "INVALID_SYMBOL": {"bid": 1, "ask": 1},
        "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        "ETH/USDT": {"bid": 3200, "ask": 3200},
    }
    signals = strategy.on_tickers(tickers)
    assert len(signals) == 1


def test_zero_bid_or_ask_ignored():
    strategy = _strategy()
    tickers = {
        "BTC/USDT": {"bid": 0, "ask": 50000},  # bid=0 → 무시
        "ETH/BTC": {"bid": 0.06, "ask": 0.06},
        "ETH/USDT": {"bid": 3200, "ask": 3200},
    }
    assert strategy.on_tickers(tickers) == []

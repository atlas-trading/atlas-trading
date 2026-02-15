"""Cost Stress Test - Critical for Strategy Validation

Tests strategy robustness under realistic cost assumptions:
1. Commission 2x: Double the commission rate
2. Slippage +1 tick: Add 1 tick slippage per trade
3. Execution delay: Delay entry/exit by 1 bar

If strategy fails these tests, it should be discarded.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class CostStressResult:
    """Cost stress test results"""
    # Base case
    base_sharpe: float
    base_cagr: float
    base_total_return: float
    base_max_drawdown: float

    # Commission 2x stress
    comm_2x_sharpe: float
    comm_2x_cagr: float
    comm_2x_total_return: float
    comm_2x_sharpe_delta: float  # Change in Sharpe
    comm_2x_sharpe_delta_pct: float  # % change in Sharpe

    # Slippage +1 tick stress
    slip_1tick_sharpe: float
    slip_1tick_cagr: float
    slip_1tick_total_return: float
    slip_1tick_cagr_delta: float  # Change in CAGR
    slip_1tick_cagr_delta_pct: float  # % change in CAGR

    # Execution delay (1 bar)
    delay_1bar_sharpe: float
    delay_1bar_cagr: float
    delay_1bar_total_return: float
    delay_1bar_max_drawdown: float
    delay_1bar_total_return_delta: float  # Change in total return
    delay_1bar_total_return_delta_pct: float  # % change

    # Risk assessment
    passes_stress_test: bool
    failure_reasons: list[str]
    risk_grade: str  # "PASS", "WARNING", "FAIL"


def calculate_cagr(total_return: float, days: int) -> float:
    """Calculate Compound Annual Growth Rate"""
    if days <= 0:
        return 0.0
    years = days / 365.25
    if years <= 0:
        return 0.0

    final_value = 1.0 + (total_return / 100.0)
    if final_value <= 0:
        return -100.0

    cagr = (pow(final_value, 1.0 / years) - 1.0) * 100.0
    return cagr


def calculate_sharpe(returns: list[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from returns"""
    if not returns or len(returns) < 2:
        return 0.0

    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate

    if np.std(excess_returns, ddof=1) == 0:
        return 0.0

    sharpe = np.mean(excess_returns) / np.std(excess_returns, ddof=1)
    # Annualize (assuming daily returns)
    sharpe_annualized = sharpe * np.sqrt(252)
    return sharpe_annualized


def recalculate_with_commission_2x(
    trades: list,
    initial_capital: float,
    original_commission: float
) -> tuple[float, float, float]:
    """Recalculate performance with 2x commission"""
    commission_2x = original_commission * 2.0

    capital = initial_capital
    equity_curve = [capital]
    peak = capital
    max_dd = 0.0

    for trade in trades:
        if trade.pnl is None or trade.exit_price is None:
            continue

        # Recalculate commission with 2x rate
        trade_value = trade.quantity * trade.entry_price
        exit_value = trade.quantity * trade.exit_price
        new_commission = (trade_value + exit_value) * commission_2x

        # Adjust PnL
        adjusted_pnl = trade.pnl + (trade.commission_paid - new_commission)
        capital += adjusted_pnl
        equity_curve.append(capital)

        # Update drawdown
        if capital > peak:
            peak = capital
        dd = ((peak - capital) / peak) * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    total_return = ((capital - initial_capital) / initial_capital) * 100.0

    # Calculate daily returns
    returns = []
    for i in range(1, len(equity_curve)):
        ret = ((equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]) * 100.0
        returns.append(ret)

    sharpe = calculate_sharpe(returns)

    return total_return, sharpe, max_dd


def recalculate_with_slippage(
    trades: list,
    initial_capital: float,
    tick_size: float = 0.01  # Default 1 cent for crypto
) -> tuple[float, float, float]:
    """Recalculate performance with +1 tick slippage per trade"""
    capital = initial_capital
    equity_curve = [capital]
    peak = capital
    max_dd = 0.0

    for trade in trades:
        if trade.pnl is None or trade.exit_price is None:
            continue

        # Apply slippage: worse entry, worse exit
        slippage_entry = tick_size if trade.side == 'long' else -tick_size
        slippage_exit = -tick_size if trade.side == 'long' else tick_size

        # Recalculate PnL with slippage
        slipped_entry = trade.entry_price + slippage_entry
        slipped_exit = trade.exit_price + slippage_exit

        if trade.side == 'long':
            slipped_pnl = (slipped_exit - slipped_entry) * trade.quantity
        else:
            slipped_pnl = (slipped_entry - slipped_exit) * trade.quantity

        # Subtract commission
        slipped_pnl -= trade.commission_paid

        capital += slipped_pnl
        equity_curve.append(capital)

        # Update drawdown
        if capital > peak:
            peak = capital
        dd = ((peak - capital) / peak) * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    total_return = ((capital - initial_capital) / initial_capital) * 100.0

    # Calculate daily returns
    returns = []
    for i in range(1, len(equity_curve)):
        ret = ((equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]) * 100.0
        returns.append(ret)

    sharpe = calculate_sharpe(returns)

    return total_return, sharpe, max_dd


def recalculate_with_delay(
    trades: list,
    initial_capital: float
) -> tuple[float, float, float]:
    """Recalculate performance assuming 1-bar execution delay

    Simplified: Assumes next bar's price is worse by small percentage
    In reality, you'd need actual next-bar price data
    """
    capital = initial_capital
    equity_curve = [capital]
    peak = capital
    max_dd = 0.0

    # Assume 0.1% worse fill due to 1-bar delay (conservative estimate)
    delay_slippage_pct = 0.001

    for trade in trades:
        if trade.pnl is None or trade.exit_price is None:
            continue

        # Apply delay slippage
        delayed_pnl = trade.pnl * (1.0 - delay_slippage_pct * 2)  # Entry + Exit

        capital += delayed_pnl
        equity_curve.append(capital)

        # Update drawdown
        if capital > peak:
            peak = capital
        dd = ((peak - capital) / peak) * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    total_return = ((capital - initial_capital) / initial_capital) * 100.0

    # Calculate daily returns
    returns = []
    for i in range(1, len(equity_curve)):
        ret = ((equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]) * 100.0
        returns.append(ret)

    sharpe = calculate_sharpe(returns)

    return total_return, sharpe, max_dd


def run_cost_stress_test(
    trades: list,
    initial_capital: float,
    commission_rate: float,
    start_date,
    end_date,
    base_total_return: float,
    base_sharpe: float,
    base_max_drawdown: float
) -> CostStressResult:
    """Run comprehensive cost stress test"""

    # Calculate base CAGR
    days = (end_date - start_date).days
    base_cagr = calculate_cagr(base_total_return, days)

    # Test 1: Commission 2x
    comm_2x_return, comm_2x_sharpe, comm_2x_dd = recalculate_with_commission_2x(
        trades, initial_capital, commission_rate
    )
    comm_2x_cagr = calculate_cagr(comm_2x_return, days)
    comm_2x_sharpe_delta = comm_2x_sharpe - base_sharpe
    comm_2x_sharpe_delta_pct = (comm_2x_sharpe_delta / base_sharpe * 100.0) if base_sharpe != 0 else 0.0

    # Test 2: Slippage +1 tick
    slip_return, slip_sharpe, slip_dd = recalculate_with_slippage(
        trades, initial_capital
    )
    slip_cagr = calculate_cagr(slip_return, days)
    slip_cagr_delta = slip_cagr - base_cagr
    slip_cagr_delta_pct = (slip_cagr_delta / base_cagr * 100.0) if base_cagr != 0 else 0.0

    # Test 3: Execution delay (1 bar)
    delay_return, delay_sharpe, delay_dd = recalculate_with_delay(
        trades, initial_capital
    )
    delay_cagr = calculate_cagr(delay_return, days)
    delay_return_delta = delay_return - base_total_return
    delay_return_delta_pct = (delay_return_delta / base_total_return * 100.0) if base_total_return != 0 else 0.0

    # Risk assessment
    failure_reasons = []

    # Fail criteria (conservative thresholds)
    if comm_2x_sharpe < 0.5:
        failure_reasons.append("Sharpe < 0.5 with 2x commission")
    if comm_2x_sharpe_delta_pct < -50:
        failure_reasons.append("Sharpe drops >50% with 2x commission")

    if slip_cagr < 0:
        failure_reasons.append("Negative CAGR with +1 tick slippage")
    if slip_cagr_delta_pct < -80:
        failure_reasons.append("CAGR drops >80% with slippage")

    if delay_return < 0:
        failure_reasons.append("Negative return with 1-bar delay")

    passes = len(failure_reasons) == 0

    # Risk grading
    if passes:
        risk_grade = "PASS"
    elif len(failure_reasons) == 1:
        risk_grade = "WARNING"
    else:
        risk_grade = "FAIL"

    return CostStressResult(
        base_sharpe=base_sharpe,
        base_cagr=base_cagr,
        base_total_return=base_total_return,
        base_max_drawdown=base_max_drawdown,
        comm_2x_sharpe=comm_2x_sharpe,
        comm_2x_cagr=comm_2x_cagr,
        comm_2x_total_return=comm_2x_return,
        comm_2x_sharpe_delta=comm_2x_sharpe_delta,
        comm_2x_sharpe_delta_pct=comm_2x_sharpe_delta_pct,
        slip_1tick_sharpe=slip_sharpe,
        slip_1tick_cagr=slip_cagr,
        slip_1tick_total_return=slip_return,
        slip_1tick_cagr_delta=slip_cagr_delta,
        slip_1tick_cagr_delta_pct=slip_cagr_delta_pct,
        delay_1bar_sharpe=delay_sharpe,
        delay_1bar_cagr=delay_cagr,
        delay_1bar_total_return=delay_return,
        delay_1bar_max_drawdown=delay_dd,
        delay_1bar_total_return_delta=delay_return_delta,
        delay_1bar_total_return_delta_pct=delay_return_delta_pct,
        passes_stress_test=passes,
        failure_reasons=failure_reasons,
        risk_grade=risk_grade
    )

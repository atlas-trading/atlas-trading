import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../api';

// Mock axios at the module level
vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => ({
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        interceptors: {
          request: { use: vi.fn(), eject: vi.fn() },
          response: { use: vi.fn(), eject: vi.fn() },
        },
      })),
    },
  };
});

describe('Backtest API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listBacktests', () => {
    it('should fetch backtest list successfully', async () => {
      const mockData = [
        {
          id: 1,
          strategy_name: 'Golden Cross',
          symbol: 'BTCUSDT',
          total_return: 15.5,
        },
      ];

      // Spy on the actual API function
      const spy = vi.spyOn(api.backtestAPI, 'listBacktests').mockResolvedValue(mockData as any);

      const result = await api.backtestAPI.listBacktests();
      expect(result).toEqual(mockData);
      expect(spy).toHaveBeenCalled();

      spy.mockRestore();
    });
  });

  describe('runMonteCarlo', () => {
    it('should run Monte Carlo simulation successfully', async () => {
      const mockResult = {
        n_simulations: 1000,
        initial_capital: 10000,
        risk_grade: 'LOW',
        final_capital_mean: 11500,
        final_capital_median: 11400,
        final_capital_std: 500,
        final_capital_5th: 10800,
        final_capital_95th: 12200,
        final_capital_min: 10500,
        final_capital_max: 12800,
        total_return_mean: 15.0,
        total_return_median: 14.0,
        total_return_std: 5.0,
        total_return_5th: 8.0,
        total_return_95th: 22.0,
        max_drawdown_mean: -8.5,
        max_drawdown_median: -8.0,
        max_drawdown_worst: -12.0,
        max_drawdown_best: -5.0,
        sharpe_ratio_mean: 1.5,
        sharpe_ratio_median: 1.4,
        probability_of_loss: 5.0,
        value_at_risk_5: -500,
        conditional_var_5: -800,
        confidence_interval_95: [10800, 12200],
        volatility_ratio: 0.33,
        sample_equity_curves: [],
        all_final_capitals: [],
      };

      const spy = vi.spyOn(api.backtestAPI, 'runMonteCarlo').mockResolvedValue(mockResult as any);

      const result = await api.backtestAPI.runMonteCarlo(1, 1000);
      expect(result.n_simulations).toBe(1000);
      expect(result.risk_grade).toBe('LOW');
      expect(spy).toHaveBeenCalledWith(1, 1000);

      spy.mockRestore();
    });
  });

  describe('runCostStressTest', () => {
    it('should run cost stress test successfully', async () => {
      const mockResult = {
        base_sharpe: 1.5,
        base_cagr: 20.5,
        base_total_return: 15.5,
        base_max_drawdown: -10.2,
        comm_2x_sharpe: 1.2,
        comm_2x_cagr: 18.0,
        comm_2x_total_return: 12.0,
        comm_2x_sharpe_delta: -0.3,
        comm_2x_sharpe_delta_pct: -20.0,
        slip_1tick_sharpe: 1.3,
        slip_1tick_cagr: 19.0,
        slip_1tick_total_return: 14.0,
        slip_1tick_cagr_delta: -1.5,
        slip_1tick_cagr_delta_pct: -7.3,
        delay_1bar_sharpe: 1.4,
        delay_1bar_cagr: 19.5,
        delay_1bar_total_return: 14.5,
        delay_1bar_max_drawdown: -11.0,
        delay_1bar_total_return_delta: -1.0,
        delay_1bar_total_return_delta_pct: -6.5,
        passes_stress_test: true,
        failure_reasons: [],
        risk_grade: 'PASS',
      };

      const spy = vi.spyOn(api.backtestAPI, 'runCostStressTest').mockResolvedValue(mockResult as any);

      const result = await api.backtestAPI.runCostStressTest(1);
      expect(result.passes_stress_test).toBe(true);
      expect(result.risk_grade).toBe('PASS');
      expect(spy).toHaveBeenCalledWith(1);

      spy.mockRestore();
    });

    it('should handle failed stress test', async () => {
      const mockResult = {
        base_sharpe: 1.5,
        base_cagr: 20.5,
        base_total_return: 15.5,
        base_max_drawdown: -10.2,
        comm_2x_sharpe: 0.3,
        comm_2x_cagr: 2.0,
        comm_2x_total_return: 1.5,
        comm_2x_sharpe_delta: -1.2,
        comm_2x_sharpe_delta_pct: -80.0,
        slip_1tick_sharpe: 0.4,
        slip_1tick_cagr: 3.0,
        slip_1tick_total_return: 2.0,
        slip_1tick_cagr_delta: -17.5,
        slip_1tick_cagr_delta_pct: -85.4,
        delay_1bar_sharpe: 0.5,
        delay_1bar_cagr: 4.0,
        delay_1bar_total_return: 3.0,
        delay_1bar_max_drawdown: -15.0,
        delay_1bar_total_return_delta: -12.5,
        delay_1bar_total_return_delta_pct: -80.6,
        passes_stress_test: false,
        failure_reasons: ['Sharpe < 0.5 with 2x commission'],
        risk_grade: 'FAIL',
      };

      const spy = vi.spyOn(api.backtestAPI, 'runCostStressTest').mockResolvedValue(mockResult as any);

      const result = await api.backtestAPI.runCostStressTest(1);
      expect(result.passes_stress_test).toBe(false);
      expect(result.failure_reasons).toHaveLength(1);
      expect(spy).toHaveBeenCalledWith(1);

      spy.mockRestore();
    });
  });
});

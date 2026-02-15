import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MonteCarloPanel from '../MonteCarloPanel';
import { backtestAPI } from '../../../services/api';

vi.mock('../../../services/api');

describe('MonteCarloPanel', () => {
  it('should render initial state with simulation controls', () => {
    render(<MonteCarloPanel backtestId={1} initialCapital={10000} />);

    expect(screen.getByRole('heading', { name: /Monte Carlo Simulation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Simulation/i })).toBeInTheDocument();
    expect(screen.getByText(/Simulation Count:/i)).toBeInTheDocument();
  });

  it('should allow changing simulation count', () => {
    render(<MonteCarloPanel backtestId={1} initialCapital={10000} />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: '5000' } });

    expect(select).toHaveValue('5000');
  });

  it('should display LOW risk result correctly', async () => {
    const mockResult = {
      n_simulations: 1000,
      initial_capital: 10000,
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
      risk_grade: 'LOW',
      sample_equity_curves: [],
      all_final_capitals: [10500, 10800, 11000, 11200, 11400, 11600, 11800, 12000, 12200, 12500],
    };

    vi.mocked(backtestAPI.runMonteCarlo).mockResolvedValue(mockResult);

    render(<MonteCarloPanel backtestId={1} initialCapital={10000} />);

    const runButton = screen.getByRole('button', { name: /Run Simulation/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText('LOW')).toBeInTheDocument();
      expect(screen.getByText(/5.0%/)).toBeInTheDocument(); // Probability of loss
    });
  });

  it('should display HIGH risk warning', async () => {
    const mockResult = {
      n_simulations: 1000,
      initial_capital: 10000,
      final_capital_mean: 9500,
      final_capital_median: 9400,
      final_capital_std: 1500,
      final_capital_5th: 7500,
      final_capital_95th: 11500,
      final_capital_min: 6000,
      final_capital_max: 13000,
      total_return_mean: -5.0,
      total_return_median: -6.0,
      total_return_std: 15.0,
      total_return_5th: -25.0,
      total_return_95th: 15.0,
      max_drawdown_mean: -25.0,
      max_drawdown_median: -24.0,
      max_drawdown_worst: -40.0,
      max_drawdown_best: -15.0,
      sharpe_ratio_mean: 0.5,
      sharpe_ratio_median: 0.4,
      probability_of_loss: 45.0,
      value_at_risk_5: -2500,
      conditional_var_5: -3500,
      confidence_interval_95: [7500, 11500],
      volatility_ratio: 3.0,
      risk_grade: 'HIGH',
      sample_equity_curves: [],
      all_final_capitals: [6000, 7000, 8000, 9000, 9400, 9800, 10500, 11000, 11500, 13000],
    };

    vi.mocked(backtestAPI.runMonteCarlo).mockResolvedValue(mockResult);

    render(<MonteCarloPanel backtestId={1} initialCapital={10000} />);

    const runButton = screen.getByRole('button', { name: /Run Simulation/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText('HIGH')).toBeInTheDocument();
      expect(screen.getByText(/45.0%/)).toBeInTheDocument(); // High probability of loss
    });
  });
});

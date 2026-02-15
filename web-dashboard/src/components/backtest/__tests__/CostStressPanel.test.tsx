import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CostStressPanel from '../CostStressPanel';
import { backtestAPI } from '../../../services/api';

vi.mock('../../../services/api');

describe('CostStressPanel', () => {
  it('should render initial state with run button', () => {
    render(<CostStressPanel backtestId={1} />);

    expect(screen.getByRole('heading', { name: /Cost Stress Test/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Cost Stress Test/i })).toBeInTheDocument();
    expect(screen.getByText(/Commission 2x/i)).toBeInTheDocument();
  });

  it('should show loading state when running test', async () => {
    vi.mocked(backtestAPI.runCostStressTest).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    render(<CostStressPanel backtestId={1} />);

    const runButton = screen.getByRole('button', { name: /Run Cost Stress Test/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText(/Running Test.../i)).toBeInTheDocument();
    });
  });

  it('should display PASS result correctly', async () => {
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

    vi.mocked(backtestAPI.runCostStressTest).mockResolvedValue(mockResult);

    render(<CostStressPanel backtestId={1} />);

    const runButton = screen.getByRole('button', { name: /Run Cost Stress Test/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText('PASS')).toBeInTheDocument();
      expect(screen.getByText(/✓ PASSED/i)).toBeInTheDocument();
    });
  });

  it('should display FAIL result with reasons', async () => {
    const mockResult = {
      base_sharpe: 1.0,
      base_cagr: 10.0,
      base_total_return: 8.0,
      base_max_drawdown: -15.0,
      comm_2x_sharpe: 0.3,
      comm_2x_cagr: 2.0,
      comm_2x_total_return: 1.5,
      comm_2x_sharpe_delta: -0.7,
      comm_2x_sharpe_delta_pct: -70.0,
      slip_1tick_sharpe: 0.5,
      slip_1tick_cagr: -2.0,
      slip_1tick_total_return: -1.5,
      slip_1tick_cagr_delta: -12.0,
      slip_1tick_cagr_delta_pct: -120.0,
      delay_1bar_sharpe: 0.4,
      delay_1bar_cagr: 3.0,
      delay_1bar_total_return: 2.5,
      delay_1bar_max_drawdown: -18.0,
      delay_1bar_total_return_delta: -5.5,
      delay_1bar_total_return_delta_pct: -68.75,
      passes_stress_test: false,
      failure_reasons: [
        'Sharpe < 0.5 with 2x commission',
        'Negative CAGR with +1 tick slippage',
      ],
      risk_grade: 'FAIL',
    };

    vi.mocked(backtestAPI.runCostStressTest).mockResolvedValue(mockResult);

    render(<CostStressPanel backtestId={1} />);

    const runButton = screen.getByRole('button', { name: /Run Cost Stress Test/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText('FAIL')).toBeInTheDocument();
      expect(screen.getByText(/✗ FAILED/i)).toBeInTheDocument();
      expect(screen.getByText(/Sharpe < 0.5 with 2x commission/i)).toBeInTheDocument();
      expect(screen.getByText(/Negative CAGR with \+1 tick slippage/i)).toBeInTheDocument();
    });
  });

  it('should handle errors gracefully', async () => {
    vi.mocked(backtestAPI.runCostStressTest).mockRejectedValue(
      new Error('Network error')
    );

    render(<CostStressPanel backtestId={1} />);

    const runButton = screen.getByRole('button', { name: /Run Cost Stress Test/i });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    });
  });
});

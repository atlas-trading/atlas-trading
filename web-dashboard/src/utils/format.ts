// Formatting utilities

/**
 * Format symbol with slash (BTCUSDT → BTC/USDT)
 */
export function formatSymbol(symbol: string): string {
  if (symbol.endsWith('USDT')) {
    const base = symbol.slice(0, -4);
    return `${base}/USDT`;
  }
  if (symbol.endsWith('BUSD')) {
    const base = symbol.slice(0, -4);
    return `${base}/BUSD`;
  }
  if (symbol.endsWith('BTC')) {
    const base = symbol.slice(0, -3);
    return `${base}/BTC`;
  }
  if (symbol.endsWith('ETH')) {
    const base = symbol.slice(0, -3);
    return `${base}/ETH`;
  }
  return symbol;
}

/**
 * Format percentage with color
 */
export function formatPercent(value: number | null, decimals: number = 2): string {
  if (value === null || value === undefined) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

/**
 * Format date
 */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US');
}

/**
 * Format datetime
 */
export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US');
}

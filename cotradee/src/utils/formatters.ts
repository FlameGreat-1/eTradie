const DECIMAL_PLACES = { PRICE: 5, VOLUME: 2, PERCENTAGE: 2, CURRENCY: 2 } as const;
const CURRENCY_SYMBOLS: Record<string, string> = { USD: '$', EUR: '€', GBP: '£', JPY: '¥' };

export function formatCurrency(
  value: number,
  currency: string = 'USD',
  decimals: number = DECIMAL_PLACES.CURRENCY,
): string {
  const symbol = CURRENCY_SYMBOLS[currency] || '$';
  const isNeg = value < 0;
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(value));
  return isNeg ? `-${symbol}${formatted}` : `${symbol}${formatted}`;
}

export function formatProfitLoss(value: number) {
  const formatted = formatCurrency(value);
  if (value > 0) return { text: `+${formatted}`, color: 'text-success', trend: 'up' as const };
  if (value < 0) return { text: formatted, color: 'text-danger', trend: 'down' as const };
  return { text: formatted, color: 'text-content-muted', trend: 'neutral' as const };
}

export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPrice(value: number): string {
  return formatNumber(value, DECIMAL_PLACES.PRICE);
}

export function formatVolume(value: number): string {
  return formatNumber(value, DECIMAL_PLACES.VOLUME);
}

export function formatPercentage(value: number, decimals = 2, showSign = false): string {
  const sign = showSign && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  }).format(new Date(date));
}

export function formatRelativeTime(date: string | Date): string {
  const diff = Date.now() - new Date(date).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function formatSymbol(symbol: string): string {
  if (symbol.includes('/')) return symbol;
  if (symbol.length === 6) return `${symbol.slice(0, 3)}/${symbol.slice(3)}`;
  return symbol;
}

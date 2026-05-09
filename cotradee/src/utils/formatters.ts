/**
 * Number / currency formatters used across the dashboard.
 *
 * Every formatter defends against non-finite values so the UI never
 * shows `$NaN` or `$Infinity` while data is loading or after a
 * transient broker error.
 */

const DECIMAL_PLACES = {
  PRICE: 5,
  VOLUME: 2,
  PERCENTAGE: 2,
  CURRENCY: 2,
} as const;

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
};

const PLACEHOLDER = '—';

function safeNumber(value: number | string | null | undefined): number | null {
  if (value == null) return null;
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

export function formatCurrency(
  value: number | string | null | undefined,
  currency: string = 'USD',
  decimals: number = DECIMAL_PLACES.CURRENCY,
): string {
  const n = safeNumber(value);
  if (n === null) return PLACEHOLDER;
  const symbol = CURRENCY_SYMBOLS[currency] || '$';
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(n));
  return n < 0 ? `-${symbol}${formatted}` : `${symbol}${formatted}`;
}

export function formatProfitLoss(value: number | string | null | undefined) {
  const n = safeNumber(value);
  if (n === null) return { text: PLACEHOLDER, color: 'text-content-muted', trend: 'neutral' as const };
  const formatted = formatCurrency(n);
  if (n > 0) return { text: `+${formatted}`, color: 'text-success', trend: 'up' as const };
  if (n < 0) return { text: formatted, color: 'text-danger', trend: 'down' as const };
  return { text: formatted, color: 'text-content-muted', trend: 'neutral' as const };
}

export function formatNumber(
  value: number | string | null | undefined,
  decimals = 0,
): string {
  const n = safeNumber(value);
  if (n === null) return PLACEHOLDER;
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

export function formatPrice(value: number | string | null | undefined): string {
  return formatNumber(value, DECIMAL_PLACES.PRICE);
}

export function formatVolume(value: number | string | null | undefined): string {
  return formatNumber(value, DECIMAL_PLACES.VOLUME);
}

export function formatAssetPrice(symbol: string, value: number | string | null | undefined): string {
  const n = safeNumber(value);
  if (n === null) return PLACEHOLDER;
  
  // Forex pairs like EURUSD typically need 5 decimal places.
  // Indices and Gold typically need 2.
  const decimals = n < 100 ? 5 : 2;
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

export function formatPercentage(
  value: number | string | null | undefined,
  decimals = 2,
  showSign = false,
): string {
  const n = safeNumber(value);
  if (n === null) return PLACEHOLDER;
  const sign = showSign && n > 0 ? '+' : '';
  return `${sign}${n.toFixed(decimals)}%`;
}

export function formatCompact(value: number | string | null | undefined): string {
  const n = safeNumber(value);
  if (n === null) return PLACEHOLDER;
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(n);
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return PLACEHOLDER;
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return PLACEHOLDER;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(d);
}

export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return PLACEHOLDER;
  const t = new Date(date).getTime();
  if (Number.isNaN(t)) return PLACEHOLDER;
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function formatSymbol(symbol: string | null | undefined): string {
  if (!symbol) return PLACEHOLDER;
  if (symbol.includes('/')) return symbol;
  if (symbol.length === 6) return `${symbol.slice(0, 3)}/${symbol.slice(3)}`;
  return symbol;
}

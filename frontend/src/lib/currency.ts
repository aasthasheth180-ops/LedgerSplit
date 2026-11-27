import type { GroupCurrency } from './groups';

export function currencyDigits(currency: GroupCurrency): number {
  return currency === 'JPY' ? 0 : 2;
}

// Integer minor units; accepts API decimal strings and user input.
export function parseMinor(value: string, currency: GroupCurrency): number {
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!match) throw new Error('Enter a valid monetary amount.');
  const digits = currencyDigits(currency);
  const fraction = match[3] ?? '';
  if (fraction.slice(digits).replace(/0/g, '')) throw new Error('Invalid currency precision.');
  const units = Number(match[2]) * 10 ** digits + Number(fraction.slice(0, digits).padEnd(digits, '0'));
  if (!Number.isSafeInteger(units)) throw new Error('Amount is too large.');
  return match[1] ? -units : units;
}

export function minorToDecimal(units: number, currency: GroupCurrency): string {
  if (!Number.isSafeInteger(units)) throw new Error('Invalid minor units.');
  const digits = currencyDigits(currency);
  const absolute = Math.abs(units).toString().padStart(digits + 1, '0');
  return (units < 0 ? '-' : '') + (digits ? absolute.slice(0, -digits) + '.' + absolute.slice(-digits) : absolute);
}

export function formatMoney(value: string, currency: GroupCurrency): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(parseMinor(value, currency) / 10 ** currencyDigits(currency));
}

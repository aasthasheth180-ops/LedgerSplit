import type { GroupCurrency, GroupSplitMethod } from './groups';
import type { ExpenseSplitCreate } from './expenses';
import { parseMinor, minorToDecimal } from './currency';

export interface SplitParticipant { userId: number; value?: string }

export function calculateSplits(amount: string, currency: GroupCurrency, method: GroupSplitMethod, participants: SplitParticipant[]): ExpenseSplitCreate[] {
  const total = parseMinor(amount, currency);
  if (total <= 0 || total > (currency === 'JPY' ? 9999999999 : 999999999999)) throw new Error('Amount must be positive and within the supported limit.');
  if (!participants.length || participants.some(p => !Number.isSafeInteger(p.userId) || p.userId <= 0) || new Set(participants.map(p => p.userId)).size !== participants.length) throw new Error('Select unique participants.');
  let shares: number[];
  if (method === 'Equal') {
    const base = Math.floor(total / participants.length);
    shares = participants.map((_, i) => base + (i < total % participants.length ? 1 : 0));
  } else if (method === 'Exact') {
    shares = participants.map(p => parseMinor(p.value ?? '', currency));
  } else if (method === 'Percent') {
    const weights = participants.map(p => parseMinor(p.value ?? '', 'USD'));
    if (weights.some(w => w < 0 || w > 10000) || weights.reduce((a,b) => a+b,0) !== 10000) throw new Error('Percentages must total 100%.');
    // Largest remainder allocation, with stable participant-order tie breaking.
    const parts = weights.map((w,i) => { const product = BigInt(total) * BigInt(w); return { i, units: Number(product / 10000n), remainder: Number(product % 10000n) }; });
    shares = parts.map(p => p.units);
    const left = total - shares.reduce((a,b) => a+b,0);
    parts.sort((a,b) => b.remainder-a.remainder || a.i-b.i).slice(0,left).forEach(p => { shares[p.i] += 1; });
  } else { throw new Error('Invalid split method.'); }
  if (shares.some(s => s < 0) || shares.reduce((a,b) => a+b,0) !== total) throw new Error('Shares must be nonnegative and total the expense amount.');
  return participants.map((p,i) => ({user_id:p.userId, amount_owed:minorToDecimal(shares[i],currency)}));
}

import { useEffect, useState, useCallback } from 'react';
import { useApi } from './useApi';
import { useGroups, type GroupWithMembers } from './useGroups';
import type { ExpenseResponse } from '../lib/expenses';
import type { PaymentResponse, PaymentRequestResponse } from '../lib/payments';
import type { BalanceResponse, SettlementResponse } from '../lib/balances';

export interface GroupFinances extends GroupWithMembers {
  expenses: ExpenseResponse[];
  payments: PaymentResponse[];
  paymentRequests: PaymentRequestResponse[];
  balances: BalanceResponse['balances'];
  settlements: SettlementResponse['settlements'];
}

export function useGroupFinances() {
  const { request } = useApi();
  const { groups, currentUserId, isLoading: groupsLoading, error: groupsError, reload: reloadGroups } = useGroups();
  type Result = { source: typeof groups; request: typeof request; revision: number; userId: typeof currentUserId; data: GroupFinances[]; error: string };
  const [result, setResult] = useState<Result | null>(null);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(r => r + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    if (groupsLoading || groupsError) return () => controller.abort();
    async function load() {
      try {
        const result = await Promise.all(groups.map(async group => {
          const base = `/groups/${group.id}`;
          const [expenses, payments, paymentRequests, balances, settlements] = await Promise.all([
            request<ExpenseResponse[]>(`${base}/expenses`, {signal}),
            request<PaymentResponse[]>(`${base}/payments`, {signal}),
            request<PaymentRequestResponse[]>(`${base}/payment-requests`, {signal}),
            request<BalanceResponse>(`${base}/balances`, {signal}),
            request<SettlementResponse>(`${base}/settlements`, {signal}),
          ]);
          return {...group, expenses, payments, paymentRequests, balances: balances.balances, settlements: settlements.settlements};
        }));
        if (!signal.aborted) setResult({source: groups, request, revision, userId: currentUserId, data: result, error: ""});
      } catch (err) {
        if (!signal.aborted) setResult({source: groups, request, revision, userId: currentUserId, data: [], error: err instanceof Error ? err.message : 'Unable to load financial data.'});
      }
    }
    void load();
    return () => controller.abort();
  }, [groups, groupsLoading, groupsError, request, revision, currentUserId]);
  const current = !groupsLoading && !groupsError && result && result.source === groups && result.request === request && result.revision === revision && result.userId === currentUserId ? result : null;
  return { groups: current?.data ?? [], currentUserId, isLoading: groupsLoading || (!groupsError && !current), error: groupsError || current?.error || '', reload, reloadGroups };
}

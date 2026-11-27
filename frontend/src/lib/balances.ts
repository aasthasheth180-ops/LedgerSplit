export interface BalanceResponse {
  group_id: number;
  balances: { user_id: number; net_balance: string }[];
}
export interface Settlement {
  from_user_id: number;
  to_user_id: number;
  amount: string;
}
export interface SettlementResponse {
  group_id: number;
  settlements: Settlement[];
}

// Types derived from the current LedgerSplit OpenAPI contract.
export interface PaymentCreate {
  to_user_id: number;
  amount: number | string;
}

export interface PaymentResponse {
  id: number;
  group_id: number;
  from_user_id: number;
  to_user_id: number;
  amount: string;
  status: "pending" | "confirmed" | "rejected";
  created_at: string;
  confirmed_at: string | null;
}

export interface PaymentRequestCreate {
  due_date?: string | null;
  debtor_id: number;
  amount: number | string;
  description?: string | null;
}

export interface PaymentRequestResponse {
  fulfilled_amount: string;
  due_date: string | null;
  id: number;
  group_id: number;
  requester_id: number;
  debtor_id: number;
  amount: string;
  description: string | null;
  status: "pending" | "fulfilled" | "cancelled";
  created_at: string;
  resolved_at: string | null;
}

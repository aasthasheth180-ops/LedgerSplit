// Types derived from the current LedgerSplit OpenAPI contract.
export interface ExpenseSplitCreate {
  user_id: number;
  amount_owed: number | string;
}

export interface ExpenseSplitResponse {
  id: number;
  expense_id: number;
  user_id: number;
  amount_owed: string;
}

export interface ExpenseCreate {
  description: string;
  amount: number | string;
  category?: "Groceries" | "Dining" | "Home" | "Utilities" | "Travel" | "Rent" | "Other";
  expense_date?: string | null;
  reference?: string | null;
  split_method?: "Equal" | "Exact" | "Percent";
  splits: ExpenseSplitCreate[];
}

export interface ExpenseResponse {
  id: number;
  group_id: number;
  paid_by: number;
  description: string;
  amount: string;
  category: "Groceries" | "Dining" | "Home" | "Utilities" | "Travel" | "Rent" | "Other";
  expense_date: string | null;
  reference: string | null;
  split_method: "Equal" | "Exact" | "Percent";
  created_at: string;
  splits: ExpenseSplitResponse[];
}

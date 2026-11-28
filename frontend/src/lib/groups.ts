export type GroupCategory =
  | "Home"
  | "Trip"
  | "Friends"
  | "Work"
  | "Other";

export type GroupCurrency =
  | "USD"
  | "EUR"
  | "GBP"
  | "CAD"
  | "JPY"
  | "INR";

export type GroupSplitMethod =
  | "Equal"
  | "Exact"
  | "Percent";

export type GroupRole = "owner" | "member";

export interface GroupCreateRequest {
  name: string;
  description: string | null;
  category: GroupCategory;
  custom_category: string | null;
  currency: GroupCurrency;
  default_split: GroupSplitMethod;
  color: string;
  member_emails: string[];
}

export interface GroupResponse {
  archived_at?: string | null;
  id: number;
  name: string;
  description: string | null;
  category: GroupCategory;
  custom_category: string | null;
  currency: GroupCurrency;
  default_split: GroupSplitMethod;
  color: string;
  created_by: number;
  created_at: string;
}

export interface GroupMemberResponse {
  id: number;
  group_id: number;
  user_id: number;
  role: GroupRole;
  joined_at: string;
  full_name: string | null;
}

export type GroupMemberAddRequest =
  | {
      email: string;
      user_id?: never;
    }
  | {
      user_id: number;
      email?: never;
    };

export function getGroupCategoryLabel(
  group: GroupResponse
): string {
  return group.category === "Other"
    ? group.custom_category || "Other"
    : group.category;
}

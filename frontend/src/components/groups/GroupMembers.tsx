import { useState, type FormEvent } from "react";
import { useApi } from "../../hooks/useApi";
import { useAuthSubmission } from "../../hooks/useAuthSubmission";
import type { GroupMemberResponse } from "../../lib/groups";

type Props = {
  groupId: number;
  members: GroupMemberResponse[];
  isOwner: boolean;
  onChanged: () => void;
};

export default function GroupMembers({
  groupId,
  members,
  isOwner,
  onChanged,
}: Props) {
  const { request } = useApi();

  const {
    isLoading,
    beginSubmission,
    endSubmission,
  } = useAuthSubmission();

  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isOwner || !beginSubmission()) return;

    setError("");

    try {
      const normalizedEmail = email.trim().toLowerCase();

      if (!normalizedEmail) {
        setError("Please enter a member email.");
        return;
      }

      await request<GroupMemberResponse>(
        `/groups/${groupId}/members`,
        {
          method: "POST",
          body: JSON.stringify({
            email: normalizedEmail,
          }),
        }
      );

      setEmail("");
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to add member."
      );
    } finally {
      endSubmission();
    }
  }

  async function removeMember(member: GroupMemberResponse) {
    if (!isOwner || member.role === "owner") return;

    if (!beginSubmission()) return;

    setError("");

    try {
      if (
        !window.confirm(
          `Remove ${member.full_name || "this member"} from the group?`
        )
      ) {
        return;
      }

      await request<void>(
        `/groups/${groupId}/members/${member.user_id}`,
        { method: "DELETE" }
      );

      onChanged();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to remove member."
      );
    } finally {
      endSubmission();
    }
  }

  return (
    <section className="mt-5 rounded-xl bg-[#eef4ef] p-4 dark:bg-[#232b25]">
      <h3 className="text-sm font-bold text-[#325f3f] dark:text-[#f3f5f2]">
        Group Members ({members.length})
      </h3>

      <div className="mt-3 space-y-2">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white p-3 dark:bg-[#1b201d]"
          >
            <div>
              <p className="text-sm font-semibold text-[#325f3f] dark:text-[#e4eee6]">
                {member.full_name || `User ${member.user_id}`}
              </p>

              <p className="text-xs capitalize text-[#717971] dark:text-[#b9cbbd]">
                {member.role}
              </p>
            </div>

            {isOwner && member.role !== "owner" && (
              <button
                type="button"
                disabled={isLoading}
                onClick={() => void removeMember(member)}
                className="rounded-lg px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50 dark:text-red-300 dark:hover:bg-red-950"
              >
                Remove
              </button>
            )}
          </div>
        ))}
      </div>

      {isOwner && (
        <form onSubmit={addMember} className="mt-4">
          <label className="text-xs font-semibold text-[#325f3f] dark:text-[#d4efda]">
            Add registered member

            <input
              type="email"
              required
              value={email}
              disabled={isLoading}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="member@example.com"
              className="mt-2 w-full rounded-lg border border-[#d9e1da] bg-white px-3 py-2 text-sm text-[#325f3f] dark:text-[#e4eee6] dark:border-[#35483b] dark:bg-[#1b201d]"
            />
          </label>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-2 rounded-lg bg-[#4a7856] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {isLoading ? "Please wait..." : "Add Member"}
          </button>
        </form>
      )}

      {error && (
        <p
          role="alert"
          className="mt-3 text-sm text-red-700 dark:text-red-300"
        >
          {error}
        </p>
      )}
    </section>
  );
}

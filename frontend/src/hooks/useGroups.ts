import { useEffect, useState } from "react";
import { useApi } from "./useApi";
import type {
  GroupResponse,
  GroupMemberResponse,
} from "../lib/groups";

export type GroupWithMembers = GroupResponse & {
  members: GroupMemberResponse[];
};

export function useGroups() {
  const { request } = useApi();

  const [groups, setGroups] = useState<GroupWithMembers[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    async function loadGroups() {
      setIsLoading(true);
      setError("");

      try {
        const [user, records] = await Promise.all([
          request<{ id: number }>("/users/me", { signal }),
          request<GroupResponse[]>("/groups", { signal }),
        ]);

        const result = await Promise.all(
          records.map(async (group) => ({
            ...group,
            members: await request<GroupMemberResponse[]>(
              `/groups/${group.id}/members`,
              { signal }
            ),
          }))
        );

        if (!signal.aborted) {
          setCurrentUserId(user.id);
          setGroups(result);
        }
      } catch (err) {
        if (!signal.aborted) {
          setGroups([]);
          setCurrentUserId(null);
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load groups."
          );
        }
      } finally {
        if (!signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadGroups();

    return () => controller.abort();
  }, [request, revision]);

  function reload() {
    setRevision((previous) => previous + 1);
  }

  return {
    groups,
    currentUserId,
    isLoading,
    error,
    reload,
  };
}

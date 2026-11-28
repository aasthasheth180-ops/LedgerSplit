import { useState } from "react";
import { useApi } from "../hooks/useApi";
import { useAuthSubmission } from "../hooks/useAuthSubmission";

type Props = {
  path: string;
  method: "DELETE" | "POST";
  label: string;
  confirmation: string;
  onChanged: () => void;
  destructive?: boolean;
};

export default function LifecycleAction({
  path,
  method,
  label,
  confirmation,
  onChanged,
  destructive = false,
}: Props) {
  const { request } = useApi();
  const submission = useAuthSubmission();
  const [error, setError] = useState("");

  async function handleAction() {
    if (!window.confirm(confirmation)) return;
    if (!submission.beginSubmission()) return;

    setError("");

    try {
      await request(path, { method });
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to complete this action."
      );
    } finally {
      submission.endSubmission();
    }
  }

  return (
    <div>
      <button
        type="button"
        disabled={submission.isLoading}
        onClick={() => void handleAction()}
        className={`rounded-lg border px-3 py-2 text-xs font-semibold transition disabled:opacity-50 ${
          destructive
            ? "border-red-200 text-red-700 hover:bg-red-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950"
            : "border-[#b8d2be] text-[#325f3f] hover:bg-[#e3efe5] dark:border-[#405a47] dark:text-[#c4e4ca] dark:hover:bg-[#304236]"
        }`}
      >
        {submission.isLoading ? "Processing..." : label}
      </button>

      {error && (
        <p
          role="alert"
          className="mt-2 text-xs text-red-700 dark:text-red-300"
        >
          {error}
        </p>
      )}
    </div>
  );
}
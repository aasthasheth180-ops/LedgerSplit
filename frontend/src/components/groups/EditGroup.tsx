import { useState, type FormEvent } from "react";
import { useApi } from "../../hooks/useApi";
import { useAuthSubmission } from "../../hooks/useAuthSubmission";

type Category = "Home" | "Trip" | "Friends" | "Work" | "Other";

type Props = {
  group: {
    id: number;
    name: string;
    category: Category;
    custom_category: string | null;
  };
  onChanged: () => void;
};

export default function EditGroup({
  group,
  onChanged,
}: Props) {
  const { request } = useApi();

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(group.name);
  const [category, setCategory] = useState<Category>(
    group.category
  );
  const [customCategory, setCustomCategory] = useState(
    group.custom_category ?? ""
  );
  const [error, setError] = useState("");

  const {
    isLoading,
    beginSubmission,
    endSubmission,
  } = useAuthSubmission();

  const inputStyle =
    "w-full rounded-xl border border-[#dce5dc] bg-white px-4 py-3 text-sm outline-none focus:border-[#4a7856] dark:border-[#35483b] dark:bg-[#242e27] dark:text-[#edf3ed]";

  function openEditor() {
    setName(group.name);
    setCategory(group.category);
    setCustomCategory(group.custom_category ?? "");
    setError("");
    setEditing(true);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Group name cannot be blank.");
      return;
    }

    if (category === "Other" && !customCategory.trim()) {
      setError("Please enter a custom category.");
      return;
    }

    if (!beginSubmission()) return;

    try {
      await request(`/groups/${group.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: name.trim(),
          category,
          custom_category:
            category === "Other"
              ? customCategory.trim()
              : null,
        }),
      });

      setEditing(false);
      onChanged();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update group."
      );
    } finally {
      endSubmission();
    }
  }

  if (!editing) {
    return (
      <button
        type="button"
        onClick={openEditor}
        className="mt-3 self-start rounded-xl bg-[#e3efe5] px-4 py-2 text-sm font-semibold text-[#325f3f] transition hover:bg-[#d1e5d5] dark:bg-[#304236] dark:text-[#d4efda]"
      >
        Edit Group
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSave}
      className="mt-4 space-y-4 rounded-xl border border-[#dce5dc] p-4 dark:border-[#35483b]"
    >
      <h3 className="text-sm font-bold text-[#325f3f] dark:text-[#edf3ed]">
        Edit Group
      </h3>

      <label className="block space-y-2">
        <span className="text-xs font-semibold">
          Group name
        </span>

        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={100}
          required
          disabled={isLoading}
          className={inputStyle}
        />
      </label>

      <label className="block space-y-2">
        <span className="text-xs font-semibold">
          Category
        </span>

        <select
          value={category}
          onChange={(event) =>
            setCategory(event.target.value as Category)
          }
          disabled={isLoading}
          className={inputStyle}
        >
          {["Home", "Trip", "Friends", "Work", "Other"].map(
            (value) => (
              <option key={value} value={value}>
                {value}
              </option>
            )
          )}
        </select>
      </label>

      {category === "Other" && (
        <label className="block space-y-2">
          <span className="text-xs font-semibold">
            Custom category
          </span>

          <input
            value={customCategory}
            onChange={(event) =>
              setCustomCategory(event.target.value)
            }
            maxLength={50}
            required
            disabled={isLoading}
            className={inputStyle}
          />
        </label>
      )}

      <p className="text-xs text-[#717971] dark:text-[#b9cbbd]">
        Currency, members, expenses and balances will
        remain unchanged.
      </p>

      {error && (
        <p
          role="alert"
          className="text-sm text-red-700 dark:text-red-300"
        >
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-xl bg-[#4a7856] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {isLoading ? "Saving..." : "Save Changes"}
        </button>

        <button
          type="button"
          disabled={isLoading}
          onClick={() => setEditing(false)}
          className="rounded-xl border border-[#dce5dc] px-4 py-2 text-sm font-semibold dark:border-[#35483b]"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
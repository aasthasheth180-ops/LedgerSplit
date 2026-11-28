
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import LifecycleAction from "./LifecycleAction";
import EditLedgerMetadata from "./EditLedgerMetadata";
import EditGroup from "./groups/EditGroup";

const { request } = vi.hoisted(() => ({
  request: vi.fn(),
}));

vi.mock("../hooks/useApi", () => ({
  useApi: () => ({ request }),
}));

const onChanged = vi.fn();

beforeEach(() => {
  request.mockReset();
  request.mockResolvedValue({});
  onChanged.mockReset();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), {
    target: { value },
  });
}

function setupGroup() {
  render(
    <EditGroup
      group={{
        id: 7,
        name: "ResearchMates",
        category: "Other",
        custom_category: "Research",
      }}
      onChanged={onChanged}
    />
  );

  fireEvent.click(
    screen.getByRole("button", { name: "Edit Group" })
  );
}

function setupExpense() {
  render(
    <EditLedgerMetadata
      endpoint="/groups/7/expenses/10"
      description="Weekly groceries"
      category="Groceries"
      date="2026-11-26"
      reference={null}
      onChanged={onChanged}
    />
  );

  fireEvent.click(
    screen.getByRole("button", { name: "Edit expense" })
  );
}

function setupRequest() {
  render(
    <EditLedgerMetadata
      endpoint="/groups/7/payment-requests/30"
      description="Groceries repayment"
      date={null}
      onChanged={onChanged}
    />
  );

  fireEvent.click(
    screen.getByRole("button", { name: "Edit request" })
  );
}

describe("Group metadata editing", () => {
  it("updates only editable group metadata", async () => {
    setupGroup();

    change("Group name", "  Research Team  ");
    change("Custom category", "Academic");

    fireEvent.click(
      screen.getByRole("button", { name: "Save Changes" })
    );

    await waitFor(() =>
      expect(onChanged).toHaveBeenCalledTimes(1)
    );

    expect(request).toHaveBeenCalledTimes(1);

    expect(request).toHaveBeenCalledWith("/groups/7", {
      method: "PATCH",
      body: JSON.stringify({
        name: "Research Team",
        category: "Other",
        custom_category: "Academic",
      }),
    });
  });

  it("rejects a whitespace-only group name", async () => {
    setupGroup();
    change("Group name", "   ");

    fireEvent.click(
      screen.getByRole("button", { name: "Save Changes" })
    );

    expect(
      await screen.findByText("Group name cannot be blank.")
    ).toBeTruthy();

    expect(request).not.toHaveBeenCalled();
  });

  it("clears custom category when changing category", async () => {
    setupGroup();
    change("Category", "Home");

    fireEvent.click(
      screen.getByRole("button", { name: "Save Changes" })
    );

    await waitFor(() =>
      expect(onChanged).toHaveBeenCalledTimes(1)
    );

    expect(request).toHaveBeenCalledWith("/groups/7", {
      method: "PATCH",
      body: JSON.stringify({
        name: "ResearchMates",
        category: "Home",
        custom_category: null,
      }),
    });
  });

  it("retains editor and displays backend errors", async () => {
    request.mockRejectedValueOnce(
      new Error("Group update denied")
    );

    setupGroup();

    fireEvent.click(
      screen.getByRole("button", { name: "Save Changes" })
    );

    expect(
      await screen.findByRole("alert")
    ).toHaveProperty("textContent", "Group update denied");

    expect(screen.getByLabelText("Group name")).toBeTruthy();
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("Financial metadata editing", () => {
  it("updates expense metadata without modifying amounts", async () => {
    setupExpense();

    change("Description", "Updated groceries");
    change("Category", "Dining");
    change("Expense date", "2026-11-27");
    change("Reference", "Receipt 123");

    fireEvent.click(
      screen.getByRole("button", { name: "Save changes" })
    );

    await waitFor(() =>
      expect(onChanged).toHaveBeenCalledTimes(1)
    );

    expect(request).toHaveBeenCalledTimes(1);

    expect(request).toHaveBeenCalledWith(
      "/groups/7/expenses/10",
      {
        method: "PATCH",
        body: JSON.stringify({
          description: "Updated groceries",
          category: "Dining",
          expense_date: "2026-11-27",
          reference: "Receipt 123",
        }),
      }
    );

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("rejects a whitespace-only expense description", async () => {
    setupExpense();
    change("Description", "   ");

    fireEvent.click(
      screen.getByRole("button", { name: "Save changes" })
    );

    expect(
      await screen.findByText("Description is required.")
    ).toBeTruthy();

    expect(request).not.toHaveBeenCalled();
  });

  it("updates payment request description and due date only", async () => {
    setupRequest();

    change("Description", "Updated repayment");
    change("Due date", "2026-12-05");

    fireEvent.click(
      screen.getByRole("button", { name: "Save changes" })
    );

    await waitFor(() =>
      expect(onChanged).toHaveBeenCalledTimes(1)
    );

    expect(request).toHaveBeenCalledTimes(1);

    expect(request).toHaveBeenCalledWith(
      "/groups/7/payment-requests/30",
      {
        method: "PATCH",
        body: JSON.stringify({
          description: "Updated repayment",
          due_date: "2026-12-05",
        }),
      }
    );
  });

  it("retains financial editor when the backend rejects an update", async () => {
    request.mockRejectedValueOnce(
      new Error("Expense update denied")
    );

    setupExpense();

    fireEvent.click(
      screen.getByRole("button", { name: "Save changes" })
    );

    expect(
      await screen.findByRole("alert")
    ).toHaveProperty("textContent", "Expense update denied");

    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("cancels editing without submitting changes", () => {
    setupExpense();
    change("Description", "Unsaved description");

    fireEvent.click(
      screen.getByRole("button", { name: "Cancel" })
    );

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(request).not.toHaveBeenCalled();
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("Lifecycle actions", () => {
  it.each([
    ["/groups/7/archive", "POST", "Archive Group"],
    ["/groups/7", "DELETE", "Delete Group"],
    ["/groups/7/expenses/10", "DELETE", "Delete"],
  ] as const)(
    "submits %s using %s",
    async (path, method, label) => {
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(
        <LifecycleAction
          path={path}
          method={method}
          label={label}
          confirmation="Confirm action?"
          onChanged={onChanged}
        />
      );

      fireEvent.click(
        screen.getByRole("button", { name: label })
      );

      await waitFor(() =>
        expect(onChanged).toHaveBeenCalledTimes(1)
      );

      expect(request).toHaveBeenCalledTimes(1);
      expect(request).toHaveBeenCalledWith(path, { method });
    }
  );

  it("does not submit when confirmation is cancelled", () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(
      <LifecycleAction
        path="/groups/7"
        method="DELETE"
        label="Delete Group"
        confirmation="Delete group?"
        onChanged={onChanged}
      />
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Delete Group" })
    );

    expect(request).not.toHaveBeenCalled();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("displays backend rejection without reporting success", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);

    request.mockRejectedValueOnce(
      new Error("Group has outstanding balances")
    );

    render(
      <LifecycleAction
        path="/groups/7/archive"
        method="POST"
        label="Archive Group"
        confirmation="Archive group?"
        onChanged={onChanged}
      />
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Archive Group" })
    );

    expect(
      await screen.findByRole("alert")
    ).toHaveProperty(
      "textContent",
      "Group has outstanding balances"
    );

    expect(onChanged).not.toHaveBeenCalled();
  });

  it("prevents rapid duplicate lifecycle submissions", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);

    let resolveRequest!: (value: unknown) => void;

    request.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        })
    );

    render(
      <LifecycleAction
        path="/groups/7/archive"
        method="POST"
        label="Archive Group"
        confirmation="Archive group?"
        onChanged={onChanged}
      />
    );

    const button = screen.getByRole("button", {
      name: "Archive Group",
    });

    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });

    expect(request).toHaveBeenCalledTimes(1);
    expect((button as HTMLButtonElement).disabled).toBe(true);

    await act(async () => {
      resolveRequest({});
    });

    expect(onChanged).toHaveBeenCalledTimes(1);
  });
});

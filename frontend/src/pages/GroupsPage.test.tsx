import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GroupsPage from "./GroupsPage";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../hooks/useApi", () => ({ useApi: () => ({ request }) }));
vi.mock("../components/background/WavyBackground", () => ({ default: () => null }));
vi.mock("../components/layout/AppSidebar", () => ({ default: () => null }));
vi.mock("../components/layout/AppHeader", () => ({ default: ({ search, onSearchChange }: { search: string; onSearchChange: (s: string) => void }) => <input aria-label="Search groups" value={search} onChange={e => onSearchChange(e.target.value)} /> }));

const group = { id: 7, name: "ResearchMates", category: "Other", custom_category: "Research", currency: "USD", default_split: "Equal", color: "#4a7856", created_by: 1, created_at: "2026-11-26T00:00:00Z", description: null };
const owner = { id: 1, group_id: 7, user_id: 1, full_name: "Owner Example", role: "owner", joined_at: group.created_at };
const member = { ...owner, id: 2, user_id: 2, full_name: "Member Example", role: "member" };
function setup(userId = 1) {
  let members = [owner, member];
  request.mockReset();
  request.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/users/me") return { id: userId };
    if (path === "/groups") return [group];
    if (path === "/groups/7/members" && options?.method === "POST") throw new Error("User is already a group member");
    if (path === "/groups/7/members/2" && options?.method === "DELETE") { members = [owner]; return; }
    if (path === "/groups/7/members") return members;
    if (["/groups/7/expenses", "/groups/7/payments", "/groups/7/payment-requests"].includes(path)) return [];
    if (path === "/groups/7/balances") return { group_id: 7, balances: members.map(m => ({ user_id: m.user_id, net_balance: "0.00" })) };
    if (path === "/groups/7/settlements") return { group_id: 7, settlements: [] };
    throw new Error(`Unexpected request ${path}`);
  });
  render(<MemoryRouter><GroupsPage /></MemoryRouter>);
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Groups integration", () => {
  it("renders real groups and custom categories, and searches", async () => {
    setup();
    await screen.findByRole("heading", { name: "ResearchMates" });
    expect(screen.getByText("Research")).toBeTruthy();
    expect(screen.queryByText("Show sample groups")).toBeNull();
    fireEvent.change(screen.getByLabelText("Search groups"), { target: { value: "missing" } });
    expect(screen.getByText("No groups found")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Search groups"), { target: { value: "Research" } });
    expect(screen.getByRole("heading", { name: "ResearchMates" })).toBeTruthy();
  });
  it("hides mutation controls from regular members", async () => {
    setup(2);
    fireEvent.click(await screen.findByRole("button", { name: "View Members" }));
    expect(screen.getByText("Owner Example")).toBeTruthy();
    expect(screen.getByText("Member Example")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Add Member" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
  });
  it("shows backend duplicate error and retains members", async () => {
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "View Members" }));
    fireEvent.change(screen.getByPlaceholderText("member@example.com"), { target: { value: "member@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Member" }));
    expect((await screen.findByRole("alert")).textContent).toContain("User is already a group member");
    expect(screen.getByText("Group Members (2)")).toBeTruthy();
  });
  it("removes a member and reloads real membership", async () => {
    setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    fireEvent.click(await screen.findByRole("button", { name: "View Members" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    await screen.findByText("Group Members (1)");
    expect(screen.queryByText("Member Example")).toBeNull();
    expect(request).toHaveBeenCalledWith("/groups/7/members/2", { method: "DELETE" });
  });
  it("reports load failures", async () => {
    setup();
    // Initial effect already started; reject a subsequent refresh instead.
    await screen.findByRole("heading", { name: "ResearchMates" });
    request.mockRejectedValue(new Error("Network unavailable"));
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Network unavailable"));
  });
});



describe("Group lifecycle integration", () => {
  it("filters active, archived and all groups", async () => {
    setup();

    const archivedGroup = {
      ...group,
      id: 8,
      name: "Archived Research",
      archived_at: group.created_at,
    };

    await screen.findByRole("heading", {
      name: "ResearchMates",
    });

    const base = request.getMockImplementation()!;

    request.mockImplementation(
      async (path: string, options?: RequestInit) => {
        if (path === "/groups") {
          return [group, archivedGroup];
        }

        return base(
          path.replace(/^\/groups\/8\//, "/groups/7/"),
          options
        );
      }
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Refresh" })
    );

    await screen.findByRole("button", {
      name: "Archived (1)",
    });

    expect(
      screen.queryByRole("heading", {
        name: "Archived Research",
      })
    ).toBeNull();

    fireEvent.click(
      screen.getByRole("button", { name: "Archived (1)" })
    );

    expect(
      await screen.findByRole("heading", {
        name: "Archived Research",
      })
    ).toBeTruthy();

    expect(
      screen.queryByRole("heading", {
        name: "ResearchMates",
      })
    ).toBeNull();

    expect(
      screen.getByText("Archived · Read-only history")
    ).toBeTruthy();

    expect(
      screen.queryByRole("button", { name: "Archive Group" })
    ).toBeNull();

    expect(
      screen.queryByRole("button", { name: "Delete Group" })
    ).toBeNull();

    fireEvent.click(
      screen.getByRole("button", { name: "View Members" })
    );

    expect(
      screen.queryByRole("button", { name: "Add Member" })
    ).toBeNull();

    fireEvent.click(
      screen.getByRole("button", { name: "All Groups (2)" })
    );

    expect(
      screen.getByRole("heading", { name: "ResearchMates" })
    ).toBeTruthy();

    expect(
      screen.getByRole("heading", { name: "Archived Research" })
    ).toBeTruthy();
  });

  it("shows lifecycle controls to the owner", async () => {
    setup();

    await screen.findByRole("heading", {
      name: "ResearchMates",
    });

    expect(
      screen.getByRole("button", { name: "Archive Group" })
    ).toBeTruthy();

    expect(
      screen.getByRole("button", { name: "Delete Group" })
    ).toBeTruthy();
  });

  it("hides lifecycle controls from regular members", async () => {
    setup(2);

    await screen.findByRole("heading", {
      name: "ResearchMates",
    });

    expect(
      screen.queryByRole("button", { name: "Archive Group" })
    ).toBeNull();

    expect(
      screen.queryByRole("button", { name: "Delete Group" })
    ).toBeNull();
  });

  it("shows an empty archived group view", async () => {
    setup();

    await screen.findByRole("heading", {
      name: "ResearchMates",
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Archived (0)" })
    );

    expect(
      screen.getByRole("heading", {
        name: "No archived groups",
      })
    ).toBeTruthy();
  });
});

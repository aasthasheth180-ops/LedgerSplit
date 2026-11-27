import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
} from "vitest";

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import {
  MemoryRouter,
  Routes,
  Route,
} from "react-router-dom";

import type { ReactNode } from "react";

import LoginPage from "./LoginPage";
import RegisterPage from "./RegisterPage";

import { apiRequest, ApiError } from "../lib/api";

type GoogleCallbacks = {
  nonce?: string;
  onSuccess: (response: { credential?: string }) => void;
  onError: () => void;
};

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  googleCallbacks: null as GoogleCallbacks | null,
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    login: mocks.login,
  }),
}));

vi.mock("../components/auth/AuthLayout", () => ({
  default: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
}));

vi.mock("../lib/authSession", () => ({
  withAuthLock: async (
    operation: () => Promise<unknown>
  ) => operation(),
}));

vi.mock("../lib/api", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../lib/api")>();

  return {
    ...actual,
    apiRequest: vi.fn(),
  };
});

vi.mock("@react-oauth/google", () => ({
  GoogleLogin: (props: GoogleCallbacks) => {
    mocks.googleCallbacks = props;

    return (
      <button
        type="button"
        onClick={() =>
          props.onSuccess({
            credential: "mock-google-credential",
          })
        }
      >
        Mock Google Login
      </button>
    );
  },
}));

const mockApi = vi.mocked(apiRequest);

let challengeNumber = 0;

function defaultApiResponse(endpoint: string) {
  if (endpoint === "/auth/google/challenge") {
    challengeNumber += 1;

    return Promise.resolve({
      nonce: `nonce-${challengeNumber}`,
      expires_in: 300,
    });
  }

  if (
    endpoint === "/auth/google" ||
    endpoint === "/auth/login"
  ) {
    return Promise.resolve({
      access_token: "mock-access-token",
      token_type: "bearer",
    });
  }

  if (endpoint === "/auth/register") {
    return Promise.resolve({
      id: 1,
      email: "test@example.com",
    });
  }

  return Promise.reject(
    new Error(`Unexpected endpoint: ${endpoint}`)
  );
}

function renderPage(path = "/login") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/register"
          element={<RegisterPage />}
        />

        <Route
          path="/expenses"
          element={<div>Expenses Dashboard</div>}
        />
      </Routes>
    </MemoryRouter>
  );
}

function countRequests(endpoint: string) {
  return mockApi.mock.calls.filter(
    ([url]) => url === endpoint
  ).length;
}

async function getGoogleCallbacks() {
  await screen.findByRole("button", {
    name: "Mock Google Login",
  });

  if (!mocks.googleCallbacks) {
    throw new Error("Google callbacks are unavailable.");
  }

  return mocks.googleCallbacks;
}

function fillLoginForm() {
  fireEvent.change(
    screen.getByLabelText("Email address"),
    {
      target: { value: "test@example.com" },
    }
  );

  fireEvent.change(
    screen.getByLabelText("Password"),
    {
      target: { value: "SecurePassword123!" },
    }
  );
}

function fillRegisterForm(
  confirmPassword = "SecurePassword123!"
) {
  fireEvent.change(
    screen.getByLabelText("Full name"),
    {
      target: { value: "Test User" },
    }
  );

  fireEvent.change(
    screen.getByLabelText("Email address"),
    {
      target: { value: "test@example.com" },
    }
  );

  fireEvent.change(
    screen.getByLabelText("Password", {
      exact: true,
    }),
    {
      target: { value: "SecurePassword123!" },
    }
  );

  fireEvent.change(
    screen.getByLabelText("Confirm password"),
    {
      target: { value: confirmPassword },
    }
  );

  fireEvent.click(
    screen.getByRole("checkbox")
  );
}

function getLoginForm() {
  const form = screen
    .getByLabelText("Email address")
    .closest("form");

  if (!form) {
    throw new Error("Login form not found.");
  }

  return form;
}

describe("Authentication page integration", () => {
  beforeEach(() => {
    challengeNumber = 0;

    mocks.googleCallbacks = null;
    mocks.login.mockReset();

    mockApi.mockReset();
    mockApi.mockImplementation(defaultApiResponse);

    vi.stubEnv(
      "VITE_GOOGLE_CLIENT_ID",
      "test-client.apps.googleusercontent.com"
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
  });

  it("successfully signs in with Google", async () => {
    renderPage();

    const google = await getGoogleCallbacks();

    await act(async () => {
      google.onSuccess({
        credential: "google-token",
      });
    });

    expect(countRequests("/auth/google")).toBe(1);

    expect(mocks.login).toHaveBeenCalledWith(
      "mock-access-token"
    );

    expect(
      await screen.findByText("Expenses Dashboard")
    ).toBeTruthy();
  });

  it("rejects duplicate Google callbacks", async () => {
    renderPage();

    const google = await getGoogleCallbacks();

    await act(async () => {
      google.onSuccess({
        credential: "google-token",
      });

      google.onSuccess({
        credential: "google-token",
      });
    });

    expect(countRequests("/auth/google")).toBe(1);
    expect(mocks.login).toHaveBeenCalledTimes(1);
  });

  it("rejects duplicate email submissions", async () => {
    renderPage();

    await getGoogleCallbacks();
    fillLoginForm();

    const form = getLoginForm();

    await act(async () => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });

    expect(countRequests("/auth/login")).toBe(1);
    expect(mocks.login).toHaveBeenCalledTimes(1);
  });

  it("blocks Google when email login starts first", async () => {
    renderPage();

    const google = await getGoogleCallbacks();

    fillLoginForm();

    const form = getLoginForm();

    await act(async () => {
      fireEvent.submit(form);

      google.onSuccess({
        credential: "google-token",
      });
    });

    expect(countRequests("/auth/login")).toBe(1);
    expect(countRequests("/auth/google")).toBe(0);
  });

  it("blocks email when Google login starts first", async () => {
    renderPage();

    const google = await getGoogleCallbacks();

    fillLoginForm();

    const form = getLoginForm();

    await act(async () => {
      google.onSuccess({
        credential: "google-token",
      });

      fireEvent.submit(form);
    });

    expect(countRequests("/auth/google")).toBe(1);
    expect(countRequests("/auth/login")).toBe(0);
  });

  it("rejects stale Google callbacks and allows retry", async () => {
    let failGoogle = true;

    mockApi.mockImplementation((endpoint) => {
      if (
        endpoint === "/auth/google" &&
        failGoogle
      ) {
        failGoogle = false;

        return Promise.reject(
          new ApiError(401, "Invalid Google credential")
        );
      }

      return defaultApiResponse(endpoint);
    });

    renderPage();

    const oldGoogle = await getGoogleCallbacks();

    await act(async () => {
      oldGoogle.onSuccess({
        credential: "invalid-token",
      });
    });

    expect(
      await screen.findByRole("alert")
    ).toBeTruthy();

    await waitFor(() => {
      expect(
        mocks.googleCallbacks?.nonce
      ).not.toBe(oldGoogle.nonce);
    });

    const newGoogle = await getGoogleCallbacks();

    await act(async () => {
      oldGoogle.onSuccess({
        credential: "stale-token",
      });
    });

    expect(countRequests("/auth/google")).toBe(1);

    await act(async () => {
      newGoogle.onSuccess({
        credential: "new-token",
      });
    });

    expect(countRequests("/auth/google")).toBe(2);

    expect(
      await screen.findByText("Expenses Dashboard")
    ).toBeTruthy();
  });

  it("allows email retry after failed authentication", async () => {
    let failLogin = true;

    mockApi.mockImplementation((endpoint) => {
      if (
        endpoint === "/auth/login" &&
        failLogin
      ) {
        failLogin = false;

        return Promise.reject(
          new ApiError(401, "Invalid credentials")
        );
      }

      return defaultApiResponse(endpoint);
    });

    renderPage();

    await getGoogleCallbacks();

    fillLoginForm();

    fireEvent.submit(getLoginForm());

    await screen.findByText("Invalid credentials");

    fireEvent.submit(getLoginForm());

    expect(
      await screen.findByText("Expenses Dashboard")
    ).toBeTruthy();

    expect(countRequests("/auth/login")).toBe(2);
  });

  it("blocks Google registration until terms are accepted", async () => {
    renderPage("/register");

    expect(
      screen.queryByRole("button", {
        name: "Mock Google Login",
      })
    ).toBeNull();

    expect(
      countRequests("/auth/google/challenge")
    ).toBe(0);

    fireEvent.click(
      screen.getByRole("checkbox")
    );

    await getGoogleCallbacks();

    expect(
      countRequests("/auth/google/challenge")
    ).toBe(1);
  });

  it("registers successfully after correcting validation errors", async () => {
    renderPage("/register");

    fillRegisterForm("IncorrectPassword");

    fireEvent.submit(getLoginForm());

    expect(
      await screen.findByText("Passwords do not match.")
    ).toBeTruthy();

    expect(countRequests("/auth/register")).toBe(0);

    fireEvent.change(
      screen.getByLabelText("Confirm password"),
      {
        target: {
          value: "SecurePassword123!",
        },
      }
    );

    fireEvent.submit(getLoginForm());

    expect(
      await screen.findByText(
        "Welcome back to LedgerSplit"
      )
    ).toBeTruthy();

    expect(countRequests("/auth/register")).toBe(1);
  });

  it("sends accepted terms during Google registration", async () => {
    renderPage("/register");

    fireEvent.click(
      screen.getByRole("checkbox")
    );

    const google = await getGoogleCallbacks();

    await act(async () => {
      google.onSuccess({
        credential: "registration-token",
      });
    });

    expect(mockApi).toHaveBeenCalledWith(
      "/auth/google",
      {
        method: "POST",
        body: JSON.stringify({
          credential: "registration-token",
          remember_me: false,
          accepted_terms: true,
        }),
      }
    );

    expect(
      await screen.findByText("Expenses Dashboard")
    ).toBeTruthy();
  });

  it("directs unregistered Google users to registration", async () => {
  mockApi.mockImplementation((endpoint) => {
    if (endpoint === "/auth/google") {
      return Promise.reject(
        new ApiError(
          400,
          "Please accept the terms and privacy policy to create an account"
        )
      );
    }

    return defaultApiResponse(endpoint);
  });

  renderPage();

  const google = await getGoogleCallbacks();

  await act(async () => {
    google.onSuccess({
      credential: "new-google-user-token",
    });
  });

  const registrationLink = await screen.findByRole(
    "link",
    { name: "Create your account →" }
  );

  expect(
    registrationLink.getAttribute("href")
  ).toBe("/register");

  expect(mocks.login).not.toHaveBeenCalled();

  fireEvent.click(registrationLink);

  expect(
    await screen.findByText("Create your account", {
      selector: "h1",
    })
  ).toBeTruthy();
});
});

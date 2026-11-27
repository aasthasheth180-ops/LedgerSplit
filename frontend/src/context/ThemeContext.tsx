
import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import type { ReactNode } from "react";

type Theme = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

type ThemeContextType = {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
};

const ThemeContext = createContext<ThemeContextType | undefined>(
  undefined
);

const STORAGE_KEY = "ledgersplit-theme";

function getInitialTheme(): Theme {
  const savedTheme = localStorage.getItem(STORAGE_KEY);

  if (
    savedTheme === "light" ||
    savedTheme === "dark" ||
    savedTheme === "system"
  ) {
    return savedTheme;
  }

  return "light";
}

export function ThemeProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  const [systemIsDark, setSystemIsDark] = useState(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );

  const resolvedTheme: ResolvedTheme =
    theme === "system"
      ? systemIsDark
        ? "dark"
        : "light"
      : theme;

  useEffect(() => {
    const mediaQuery = window.matchMedia(
      "(prefers-color-scheme: dark)"
    );

    function handleSystemChange(event: MediaQueryListEvent) {
      setSystemIsDark(event.matches);
    }

    mediaQuery.addEventListener("change", handleSystemChange);

    return () => {
      mediaQuery.removeEventListener(
        "change",
        handleSystemChange
      );
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;

    root.classList.toggle(
      "dark",
      resolvedTheme === "dark"
    );

    root.style.colorScheme = resolvedTheme;

    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme, resolvedTheme]);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        resolvedTheme,
        setTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error(
      "useTheme must be used inside ThemeProvider"
    );
  }

  return context;
}

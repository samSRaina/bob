import { useEffect, useState } from "react";

const STORAGE_KEY = "bob-engine-theme";

function getInitialTheme(): "light" | "dark" {
  if (typeof document !== "undefined" && document.documentElement.classList.contains("dark")) {
    return "dark";
  }
  return "light";
}

/** Dark/light theme toggle. The initial class is set synchronously in index.html
 * (before React mounts) to avoid a flash of the wrong theme; this hook just keeps
 * React state in sync with that class and persists changes. */
export function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(getInitialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore — private browsing / storage disabled
    }
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  return { theme, toggleTheme };
}

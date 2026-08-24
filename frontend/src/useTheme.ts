import { useEffect, useState } from "react";

type ThemePreference = "light" | "dark" | "auto";

const STORAGE_KEY = "goodhvac-theme";

function applyTheme(preference: ThemePreference) {
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  if (preference !== "auto") {
    root.classList.add(preference);
  }
}

/**
 * Tracks the user's theme preference (light/dark/auto), persisting it to
 * localStorage and applying a .light/.dark class to <html>. "auto" removes
 * both classes so the CSS's prefers-color-scheme media query takes over.
 */
export function useTheme(): [ThemePreference, (next: ThemePreference) => void] {
  const [preference, setPreference] = useState<ThemePreference>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" || stored === "auto" ? stored : "auto";
  });

  useEffect(() => {
    applyTheme(preference);
    localStorage.setItem(STORAGE_KEY, preference);
  }, [preference]);

  return [preference, setPreference];
}

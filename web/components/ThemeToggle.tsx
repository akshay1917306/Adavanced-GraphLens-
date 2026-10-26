"use client";

import { useEffect, useState } from "react";

type Theme = "system" | "light" | "dark";
const ORDER: Theme[] = ["system", "light", "dark"];

// Only a per-viewer convenience: if storage is blocked, the page still works.
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("graphlens-theme");
      if (saved === "light" || saved === "dark") setTheme(saved);
    } catch {
      /* storage blocked: keep the system theme */
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
  }, [theme]);

  function next() {
    const value = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    setTheme(value);
    try {
      if (value === "system") localStorage.removeItem("graphlens-theme");
      else localStorage.setItem("graphlens-theme", value);
    } catch {
      /* ignore */
    }
  }

  return (
    <button type="button" onClick={next} className="theme" aria-label={`Theme: ${theme}. Click to change.`}>
      Theme: {theme}
    </button>
  );
}

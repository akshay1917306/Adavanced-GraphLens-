"use client";

import { useEffect, useSyncExternalStore } from "react";
import { readTheme, subscribeTheme, writeTheme, type Theme } from "@/lib/theme";

const ORDER: Theme[] = ["system", "light", "dark"];

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, () => "system" as Theme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
  }, [theme]);

  function next() {
    writeTheme(ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]);
  }

  return (
    <button type="button" onClick={next} className="theme" aria-label={`Theme: ${theme}. Click to change.`}>
      Theme: {theme}
    </button>
  );
}

// The chosen theme. It is a per-viewer convenience kept in localStorage (and, when signed in as a
// visitor, also in the saved preferences). If storage is blocked the page still works.

export type Theme = "system" | "light" | "dark";

const KEY = "graphlens-theme";
const listeners = new Set<() => void>();

export function readTheme(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

export function writeTheme(value: Theme) {
  try {
    if (value === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, value);
  } catch {
    /* ignore: the choice then lasts only until the page is closed */
  }
  listeners.forEach((notify) => notify());
}

export function subscribeTheme(notify: () => void) {
  listeners.add(notify);
  return () => {
    listeners.delete(notify);
  };
}

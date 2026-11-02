import { useEffect, useState } from "react";

import AppearanceContext from "./appearanceContext";

const THEME_KEY = "sams-theme";
const SIDEBAR_KEY = "sams-sidebar";

function getInitialTheme() {
  const savedTheme = localStorage.getItem(THEME_KEY);

  if (
    savedTheme === "light" ||
    savedTheme === "dark" ||
    savedTheme === "system"
  ) {
    return savedTheme;
  }

  return "light";
}

function getInitialSidebar() {
  const savedSidebar = localStorage.getItem(SIDEBAR_KEY);

  if (savedSidebar === "expanded" || savedSidebar === "compact") {
    return savedSidebar;
  }

  return "expanded";
}

export function AppearanceProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme);
  const [sidebarMode, setSidebarMode] = useState(getInitialSidebar);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(SIDEBAR_KEY, sidebarMode);
  }, [sidebarMode]);

  useEffect(() => {
    const root = document.documentElement;

    if (theme === "dark") {
      root.dataset.theme = "dark";
      return;
    }

    if (theme === "light") {
      root.dataset.theme = "light";
      return;
    }

    const mediaQuery = window.matchMedia(
      "(prefers-color-scheme: dark)",
    );

    const applySystemTheme = () => {
      root.dataset.theme = mediaQuery.matches ? "dark" : "light";
    };

    applySystemTheme();

    mediaQuery.addEventListener("change", applySystemTheme);

    return () => {
      mediaQuery.removeEventListener("change", applySystemTheme);
    };
  }, [theme]);

  const value = {
    theme,
    setTheme,
    sidebarMode,
    setSidebarMode,
  };

  return (
    <AppearanceContext.Provider value={value}>
      {children}
    </AppearanceContext.Provider>
  );
}
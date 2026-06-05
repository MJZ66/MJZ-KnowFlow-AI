export type Theme = 'light' | 'dark';

const THEME_KEY = 'knowflow_theme';

export function getSavedTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  return stored === 'light' ? 'light' : 'dark';
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  root.setAttribute('data-theme', theme);
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
  window.dispatchEvent(new CustomEvent('knowflow-theme-change', { detail: theme }));
}

export function initTheme(): void {
  applyTheme(getSavedTheme());
}

export function toggleTheme(): Theme {
  const next: Theme = getSavedTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}

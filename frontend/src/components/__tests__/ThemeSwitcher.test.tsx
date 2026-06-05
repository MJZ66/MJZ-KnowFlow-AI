import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import ThemeSwitcher from '../ThemeSwitcher';
import { getSavedTheme, setTheme } from '../../theme';

function renderSwitcher() {
  return render(
    <I18nextProvider i18n={i18n}>
      <ThemeSwitcher />
    </I18nextProvider>,
  );
}

describe('ThemeSwitcher', () => {
  beforeEach(() => {
    setTheme('dark');
  });

  it('renders and toggles theme', () => {
    renderSwitcher();
    const btn = screen.getByTestId('theme-switcher');
    expect(btn).toBeInTheDocument();
    expect(getSavedTheme()).toBe('dark');
    fireEvent.click(btn);
    expect(getSavedTheme()).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    fireEvent.click(btn);
    expect(getSavedTheme()).toBe('dark');
  });
});

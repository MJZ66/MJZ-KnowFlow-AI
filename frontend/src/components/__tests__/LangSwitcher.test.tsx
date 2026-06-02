import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import LangSwitcher from '../LangSwitcher';

describe('LangSwitcher', () => {
  beforeEach(() => {
    localStorage.clear();
    i18n.changeLanguage('zh-CN');
  });

  it('toggles language label on click', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <LangSwitcher />
      </I18nextProvider>,
    );
    expect(screen.getByText('EN')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('中文')).toBeInTheDocument();
  });

  it('persists language to localStorage', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <LangSwitcher />
      </I18nextProvider>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(localStorage.getItem('knowflow_lang')).toBe('en-US');
  });
});

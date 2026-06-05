import type { ReactNode } from 'react';

interface TabPanelProps {
  panelKey: string;
  children: ReactNode;
  className?: string;
}

/** Cross-fade tab content without layout jump. */
export default function TabPanel({ panelKey, children, className = '' }: TabPanelProps) {
  return (
    <div key={panelKey} className={`tab-panel ${className}`.trim()}>
      {children}
    </div>
  );
}

import { useCallback, useState } from 'react';

/** Wrap an async handler with a single pending flag (prevents double-submit). */
export function usePendingAction<T extends unknown[]>(
  action: (...args: T) => Promise<void>,
) {
  const [pending, setPending] = useState(false);

  const run = useCallback(
    async (...args: T) => {
      if (pending) return;
      setPending(true);
      try {
        await action(...args);
      } finally {
        setPending(false);
      }
    },
    [action, pending],
  );

  return { pending, run };
}

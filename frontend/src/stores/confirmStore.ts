import { create } from 'zustand';

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
}

interface ConfirmState extends ConfirmOptions {
  open: boolean;
  resolve: ((value: boolean) => void) | null;
}

interface ConfirmStore extends ConfirmState {
  request: (options: ConfirmOptions) => Promise<boolean>;
  close: (result: boolean) => void;
}

export const useConfirmStore = create<ConfirmStore>((set, get) => ({
  open: false,
  title: '',
  message: '',
  confirmLabel: undefined,
  cancelLabel: undefined,
  variant: 'default',
  resolve: null,

  request: (options) =>
    new Promise<boolean>((resolve) => {
      set({
        open: true,
        resolve,
        ...options,
      });
    }),

  close: (result) => {
    const { resolve } = get();
    resolve?.(result);
    set({
      open: false,
      resolve: null,
      title: '',
      message: '',
      confirmLabel: undefined,
      cancelLabel: undefined,
      variant: 'default',
    });
  },
}));

export function confirmAction(options: ConfirmOptions): Promise<boolean> {
  return useConfirmStore.getState().request(options);
}

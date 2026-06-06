import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { router } from './routes';
import LogoutOverlay from './components/LogoutOverlay';
import ToastContainer from './components/ToastContainer';
import ConfirmModal from './components/ConfirmModal';
import { useUserStore } from './stores/userStore';

export default function App() {
  const fetchMe = useUserStore((s) => s.fetchMe);
  const isAuthenticated = useUserStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      fetchMe();
    }
  }, [isAuthenticated, fetchMe]);

  // Ensure i18n is initialized
  useTranslation();

  return (
    <>
      <RouterProvider router={router} />
      <LogoutOverlay />
      <ToastContainer />
      <ConfirmModal />
    </>
  );
}

import { createBrowserRouter, Navigate, useParams } from 'react-router-dom';
import PageTransitionOutlet from '../components/PageTransitionOutlet';
import { useUserStore } from '../stores/userStore';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import DashboardPage from '../pages/DashboardPage';
import KBDetailPage from '../pages/KBDetailPage';
import AdminPage from '../pages/AdminPage';
import AccountPage from '../pages/AccountPage';
import SetupPage from '../pages/SetupPage';

function ChatRedirect() {
  const { kbId } = useParams<{ kbId: string }>();
  return <Navigate to={`/kbs/${kbId}`} replace />;
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useUserStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RedirectIfAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useUserStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    element: <PageTransitionOutlet />,
    children: [
      {
        path: '/login',
        element: (
          <RedirectIfAuth>
            <LoginPage />
          </RedirectIfAuth>
        ),
      },
      {
        path: '/register',
        element: (
          <RedirectIfAuth>
            <RegisterPage />
          </RedirectIfAuth>
        ),
      },
      {
        path: '/dashboard',
        element: (
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        ),
      },
      {
        path: '/kbs/:kbId',
        element: (
          <RequireAuth>
            <KBDetailPage />
          </RequireAuth>
        ),
      },
      {
        path: '/kbs/:kbId/chat',
        element: (
          <RequireAuth>
            <ChatRedirect />
          </RequireAuth>
        ),
      },
      {
        path: '/admin',
        element: (
          <RequireAuth>
            <AdminPage />
          </RequireAuth>
        ),
      },
      {
        path: '/setup',
        element: (
          <RequireAuth>
            <SetupPage />
          </RequireAuth>
        ),
      },
      {
        path: '/account',
        element: (
          <RequireAuth>
            <AccountPage />
          </RequireAuth>
        ),
      },
      {
        path: '/',
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: '*',
        element: <Navigate to="/dashboard" replace />,
      },
    ],
  },
]);

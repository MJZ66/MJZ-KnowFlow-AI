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
  const isLoading = useUserStore((s) => s.isLoading);
  const authChecked = useUserStore((s) => s.authChecked);
  if (!authChecked || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const user = useUserStore((s) => s.user);
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  if (!isAdmin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function RedirectIfAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useUserStore((s) => s.isAuthenticated);
  const authChecked = useUserStore((s) => s.authChecked);
  const isLoading = useUserStore((s) => s.isLoading);
  if (!authChecked || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }
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
            <RequireAdmin>
              <AdminPage />
            </RequireAdmin>
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

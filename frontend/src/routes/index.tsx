import { createBrowserRouter, Navigate } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import DashboardPage from '../pages/DashboardPage';
import KBDetailPage from '../pages/KBDetailPage';
import ChatPage from '../pages/ChatPage';
import AdminPage from '../pages/AdminPage';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RedirectIfAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (token) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <RedirectIfAuth><LoginPage /></RedirectIfAuth>,
  },
  {
    path: '/register',
    element: <RedirectIfAuth><RegisterPage /></RedirectIfAuth>,
  },
  {
    path: '/dashboard',
    element: <RequireAuth><DashboardPage /></RequireAuth>,
  },
  {
    path: '/kbs/:kbId',
    element: <RequireAuth><KBDetailPage /></RequireAuth>,
  },
  {
    path: '/kbs/:kbId/chat',
    element: <RequireAuth><ChatPage /></RequireAuth>,
  },
  {
    path: '/admin',
    element: <RequireAuth><AdminPage /></RequireAuth>,
  },
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
]);

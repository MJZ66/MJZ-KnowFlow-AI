import { useLocation, Outlet } from 'react-router-dom';

/**
 * Route-level enter animation — keyed by pathname for smooth page changes.
 */
export default function PageTransitionOutlet() {
  const location = useLocation();
  return (
    <div key={location.pathname} className="route-view">
      <Outlet />
    </div>
  );
}

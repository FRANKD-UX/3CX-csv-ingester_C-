import React, { useEffect, useRef } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import { useRole } from '@/contexts/RoleContext';

/** Routes that require admin or manager role */
const SETTINGS_ROUTES = ['/upload', '/history'];

interface SettingsGuardProps {
  children: React.ReactNode;
}

/**
 * Wraps a route and redirects agents to "/" with a toast notification
 * when they attempt to access Settings-only pages (Admin role required).
 */
const SettingsGuard: React.FC<SettingsGuardProps> = ({ children }) => {
  const { canAccessSettings } = useRole();
  const location = useLocation();
  const toastedRef = useRef(false);

  const isRestricted = SETTINGS_ROUTES.some((r) => location.pathname.startsWith(r));

  useEffect(() => {
    if (isRestricted && !canAccessSettings && !toastedRef.current) {
      toastedRef.current = true;
      toast.error('Access denied — this page requires Admin role.', {
        duration: 4000,
      });
    }
    if (!isRestricted || canAccessSettings) {
      toastedRef.current = false;
    }
  }, [isRestricted, canAccessSettings]);

  if (isRestricted && !canAccessSettings) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default SettingsGuard;

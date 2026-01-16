import { tokenManager } from '@/api';
import { useAuthStore } from '@/stores';
import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';

interface RoleProtectedRouteProps {
    allowedRoles: string[];
}

/**
 * Role-based protected route that checks user's role in current account
 * @param allowedRoles - Array of roles that can access this route (e.g., ['owner', 'admin'])
 */
export function RoleProtectedRoute({ allowedRoles }: RoleProtectedRouteProps) {
    const { isAuthenticated, currentAccount, isInitialized, initialize } = useAuthStore();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const init = async () => {
            if (!isInitialized) {
                await initialize();
            }
            setIsLoading(false);
        };

        init();
    }, [isInitialized, initialize]);

    // Show loading state while initializing
    if (isLoading || !isInitialized) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading...</p>
                </div>
            </div>
        );
    }

    const token = tokenManager.getAccessToken();
    const payload = token ? tokenManager.decodeToken(token) : null;

    if (!isAuthenticated || !token) {
        return <Navigate to="/login" replace />;
    }

    // Super admins bypass role checks
    if (payload?.is_super_admin) {
        return <Outlet />;
    }

    // Check if user's role is in allowed roles
    const userRole = currentAccount?.role || payload?.account_role;
    const hasAccess = userRole && allowedRoles.includes(userRole);

    if (!hasAccess) {
        // Redirect to dashboard with insufficient permissions
        return <Navigate to="/dashboard" replace />;
    }

    return <Outlet />;
}

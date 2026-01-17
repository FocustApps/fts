import { tokenManager } from '@/api';
import { useAuthStore } from '@/stores';
import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';

/**
 * Super admin route wrapper that requires super admin privileges
 */
export function SuperAdminRoute() {
    const { isAuthenticated, isInitialized, initialize } = useAuthStore();
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

    // Decode token to check super admin status
    const token = tokenManager.getAccessToken();
    const payload = token ? tokenManager.decodeToken(token) : null;
    const isSuperAdmin = payload?.is_super_admin === true;

    if (!isAuthenticated || !token) {
        return <Navigate to="/login" replace />;
    }

    if (!isSuperAdmin) {
        // Redirect to dashboard if not super admin
        return <Navigate to="/dashboard" replace />;
    }

    return <Outlet />;
}

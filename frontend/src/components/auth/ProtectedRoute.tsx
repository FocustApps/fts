import { tokenManager } from '@/api';
import { useAuthStore } from '@/stores';
import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

/**
 * Protected route wrapper that requires authentication
 */
export function ProtectedRoute() {
    const location = useLocation();
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

    // Check if token exists and is valid
    const token = tokenManager.getAccessToken();
    const hasValidToken = token && !tokenManager.isTokenExpired(token);

    if (!isAuthenticated || !hasValidToken) {
        // Redirect to login, preserving the attempted location
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <Outlet />;
}

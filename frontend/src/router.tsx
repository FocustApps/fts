import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ProtectedRoute, RoleProtectedRoute, SuperAdminRoute } from './components/auth';
import { MainLayout } from './components/layout';
import { AccountDetail, AccountForm, AccountList, AccountUserManager } from './features/admin';
import { NotificationCenter, NotificationPreferences } from './features/notifications';
import { PlanDetail, PlanForm, PlanList } from './features/plans';
import { SystemDetail, SystemForm, SystemList } from './features/systems';
import { TestCaseDetail, TestCaseForm, TestCaseList } from './features/test-cases';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';

/**
 * Main application router with role-based protection
 */
export const router = createBrowserRouter([
    {
        path: '/',
        element: <Navigate to="/dashboard" replace />,
    },
    {
        path: '/login',
        element: <LoginPage />,
    },
    {
        path: '/register',
        element: <RegisterPage />,
    },
    // Protected routes - require authentication and use MainLayout
    {
        element: <ProtectedRoute />,
        children: [
            {
                element: <MainLayout />,
                children: [
                    {
                        path: '/dashboard',
                        element: <DashboardPage />,
                    },
                    {
                        path: '/plans',
                        element: <PlanList />,
                    },
                    {
                        path: '/plans/new',
                        element: <PlanForm />,
                    },
                    {
                        path: '/plans/:id',
                        element: <PlanDetail />,
                    },
                    {
                        path: '/plans/:id/edit',
                        element: <PlanForm />,
                    },
                    {
                        path: '/test-cases',
                        element: <TestCaseList />,
                    },
                    {
                        path: '/test-cases/new',
                        element: <TestCaseForm />,
                    },
                    {
                        path: '/test-cases/:id',
                        element: <TestCaseDetail />,
                    },
                    {
                        path: '/test-cases/:id/edit',
                        element: <TestCaseForm />,
                    },
                    {
                        path: '/systems',
                        element: <SystemList />,
                    },
                    {
                        path: '/systems/new',
                        element: <SystemForm />,
                    },
                    {
                        path: '/systems/:id',
                        element: <SystemDetail />,
                    },
                    {
                        path: '/systems/:id/edit',
                        element: <SystemForm />,
                    },
                    {
                        path: '/notifications',
                        element: <NotificationCenter />,
                    },
                    {
                        path: '/settings',
                        element: <div className="p-6">Settings (Coming Soon)</div>,
                    },
                    {
                        path: '/settings/notifications',
                        element: <NotificationPreferences />,
                    },
                ],
            },
        ],
    },
    // Role-protected routes - require specific roles and use MainLayout
    {
        element: <RoleProtectedRoute allowedRoles={['owner', 'admin']} />,
        children: [
            {
                element: <MainLayout />,
                children: [
                    {
                        path: '/accounts/:accountId/settings',
                        element: <div className="p-6">Account Settings (Owner/Admin Only)</div>,
                    },
                    {
                        path: '/accounts/:accountId/users',
                        element: <div className="p-6">Manage Users (Owner/Admin Only)</div>,
                    },
                ],
            },
        ],
    },
    // Super admin routes - require super admin privileges and use MainLayout
    {
        path: '/admin',
        element: <SuperAdminRoute />,
        children: [
            {
                element: <MainLayout />,
                children: [
                    {
                        index: true,
                        element: <Navigate to="/admin/accounts" replace />,
                    },
                    {
                        path: 'accounts',
                        element: <AccountList />,
                    },
                    {
                        path: 'accounts/new',
                        element: <AccountForm />,
                    },
                    {
                        path: 'accounts/:id',
                        element: <AccountDetail />,
                    },
                    {
                        path: 'accounts/:id/edit',
                        element: <AccountForm />,
                    },
                    {
                        path: 'accounts/:id/users',
                        element: <AccountUserManager />,
                    },
                    {
                        path: 'users',
                        element: <div className="p-6">All Users Management</div>,
                    },
                    {
                        path: 'impersonate',
                        element: <div className="p-6">User Impersonation</div>,
                    },
                ],
            },
        ],
    },
    // 404 catch-all
    {
        path: '*',
        element: (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-6xl font-bold text-gray-900">404</h1>
                    <p className="mt-2 text-xl text-gray-600">Page not found</p>
                    <a
                        href="/dashboard"
                        className="mt-4 inline-block text-blue-600 hover:text-blue-500"
                    >
                        Go back to dashboard
                    </a>
                </div>
            </div>
        ),
    },
]);

import { usersApi } from '@/api';
import { toast, useAuthStore, useNotificationStore } from '@/stores';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export function Header() {
    const navigate = useNavigate();
    const { user, currentAccount, isImpersonating, impersonatedBy, logout } = useAuthStore();
    const { unreadCount, startPolling, stopPolling } = useNotificationStore();
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Start notification polling when component mounts
        startPolling();

        return () => {
            // Stop polling when component unmounts
            stopPolling();
        };
    }, [startPolling, stopPolling]);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsDropdownOpen(false);
            }
        }

        if (isDropdownOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            return () => {
                document.removeEventListener('mousedown', handleClickOutside);
            };
        }
    }, [isDropdownOpen]);

    const handleLogout = async () => {
        try {
            await logout();
            navigate('/login');
        } catch {
            toast.error('Logout failed', 'Please try again');
        }
        setIsDropdownOpen(false);
    };

    const handleSwitchAccount = async (accountId: string) => {
        try {
            await useAuthStore.getState().switchAccount(accountId);
            toast.success('Account switched successfully');
            navigate('/dashboard');
        } catch {
            toast.error('Failed to switch account', 'Please try again');
        }
        setIsDropdownOpen(false);
    };

    const getRoleBadgeColor = (role: string) => {
        const colors = {
            owner: 'bg-purple-100 text-purple-800',
            admin: 'bg-blue-100 text-blue-800',
            member: 'bg-green-100 text-green-800',
            viewer: 'bg-gray-100 text-gray-800',
        };
        return colors[role as keyof typeof colors] || colors.viewer;
    };

    if (!user || !currentAccount) {
        return null;
    }

    return (
        <>
            {/* Impersonation Banner */}
            {isImpersonating && (
                <div className="bg-yellow-50 border-b border-yellow-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                                <svg
                                    className="h-5 w-5 text-yellow-600"
                                    fill="none"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                <span className="text-sm font-medium text-yellow-800">
                                    Impersonating {user.email}
                                </span>
                                {impersonatedBy && (
                                    <span className="text-sm text-yellow-600">
                                        (by admin: {impersonatedBy})
                                    </span>
                                )}
                            </div>
                            <button
                                onClick={() => {
                                    /* TODO: End impersonation */
                                }}
                                className="text-sm text-yellow-800 hover:text-yellow-900 underline"
                            >
                                End Impersonation
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Header */}
            <header className="bg-white border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        {/* Logo */}
                        <div className="flex items-center">
                            <Link to="/dashboard" className="flex items-center">
                                <span className="text-2xl font-bold text-blue-600">Fenrir</span>
                            </Link>
                        </div>

                        {/* Navigation */}
                        <nav className="hidden md:flex space-x-8">
                            <Link
                                to="/dashboard"
                                className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                            >
                                Dashboard
                            </Link>
                            <Link
                                to="/plans"
                                className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                            >
                                Plans
                            </Link>
                            <Link
                                to="/test-cases"
                                className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                            >
                                Test Cases
                            </Link>
                            <Link
                                to="/systems"
                                className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                            >
                                Systems
                            </Link>
                        </nav>

                        {/* Right side */}
                        <div className="flex items-center space-x-4">
                            {/* Notifications */}
                            <button
                                onClick={() => navigate('/notifications')}
                                className="relative p-2 text-gray-600 hover:text-gray-900"
                            >
                                <svg
                                    className="h-6 w-6"
                                    fill="none"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                </svg>
                                {unreadCount > 0 && (
                                    <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
                                        {unreadCount > 99 ? '99+' : unreadCount}
                                    </span>
                                )}
                            </button>

                            {/* Account Switcher Dropdown */}
                            <div className="relative" ref={dropdownRef}>
                                <button
                                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                    className="flex items-center space-x-3 p-2 rounded-md hover:bg-gray-100"
                                >
                                    <div className="text-right">
                                        <div className="text-sm font-medium text-gray-900">
                                            {currentAccount.account_name}
                                        </div>
                                        <div className="flex items-center justify-end space-x-1">
                                            <span
                                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getRoleBadgeColor(currentAccount.role)}`}
                                            >
                                                {currentAccount.role}
                                            </span>
                                        </div>
                                    </div>
                                    <svg
                                        className="h-5 w-5 text-gray-400"
                                        fill="none"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="2"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                    >
                                        <path d="M19 9l-7 7-7-7" />
                                    </svg>
                                </button>

                                {/* Dropdown Menu */}
                                {isDropdownOpen && (
                                    <div className="absolute right-0 mt-2 w-64 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
                                        <div className="py-1">
                                            <div className="px-4 py-2 border-b border-gray-200">
                                                <p className="text-sm font-medium text-gray-900">
                                                    {user.email}
                                                </p>
                                                <p className="text-xs text-gray-500">@{user.username}</p>
                                            </div>

                                            <AccountList onSwitchAccount={handleSwitchAccount} />

                                            <div className="border-t border-gray-200">
                                                <Link
                                                    to="/settings"
                                                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                                    onClick={() => setIsDropdownOpen(false)}
                                                >
                                                    Settings
                                                </Link>
                                                <button
                                                    onClick={handleLogout}
                                                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                                >
                                                    Sign out
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </header>
        </>
    );
}

function AccountList({ onSwitchAccount }: { onSwitchAccount: (accountId: string) => void }) {
    const currentAccount = useAuthStore((state) => state.currentAccount);
    const getCachedRole = useAuthStore((state) => state.getCachedRole);

    // Fetch user's accounts
    const { data: accounts = [], isLoading } = useQuery({
        queryKey: ['user-accounts'],
        queryFn: usersApi.getMyAccounts,
        staleTime: 5 * 60 * 1000, // 5 minutes
    });

    if (isLoading) {
        return (
            <div className="border-t border-gray-200 px-4 py-4">
                <p className="text-sm text-gray-500">Loading accounts...</p>
            </div>
        );
    }

    if (accounts.length === 0) {
        return null;
    }

    const getRoleBadgeColor = (role: string) => {
        const colors = {
            owner: 'bg-purple-100 text-purple-800',
            admin: 'bg-blue-100 text-blue-800',
            member: 'bg-green-100 text-green-800',
            viewer: 'bg-gray-100 text-gray-800',
        };
        return colors[role as keyof typeof colors] || colors.viewer;
    };

    return (
        <div className="border-t border-gray-200">
            <div className="px-4 py-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Switch Account
                </p>
            </div>
            {accounts.map((account) => {
                const cachedRole = getCachedRole(account.account_id);
                const displayRole = cachedRole || account.role;
                const isCurrent = account.account_id === currentAccount?.account_id;

                return (
                    <button
                        key={account.account_id}
                        onClick={() => !isCurrent && onSwitchAccount(account.account_id)}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 ${isCurrent ? 'bg-gray-50' : ''
                            }`}
                        disabled={isCurrent}
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium text-gray-900">{account.account_name}</p>
                                {isCurrent && (
                                    <p className="text-xs text-gray-500">Current account</p>
                                )}
                            </div>
                            <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getRoleBadgeColor(displayRole)}`}
                            >
                                {displayRole}
                            </span>
                        </div>
                    </button>
                );
            })}
        </div>
    );
}

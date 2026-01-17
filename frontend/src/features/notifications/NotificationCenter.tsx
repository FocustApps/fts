import { useNotificationStore } from '@/stores';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Link } from 'react-router-dom';

export function NotificationCenter() {
    const {
        notifications,
        fetchNotifications,
        markAsRead,
        markAllAsRead,
        fetchUnreadCount,
    } = useNotificationStore();

    // Fetch notifications on mount and set up polling
    const { isLoading, error, refetch } = useQuery({
        queryKey: ['notifications'],
        queryFn: fetchNotifications,
        refetchInterval: 30000, // Poll every 30 seconds
        refetchIntervalInBackground: false,
    });

    // Update unread count periodically
    useEffect(() => {
        const interval = setInterval(fetchUnreadCount, 30000);
        return () => clearInterval(interval);
    }, [fetchUnreadCount]);

    const handleMarkAsRead = async (notificationId: string) => {
        try {
            await markAsRead(notificationId);
        } catch (error) {
            console.error('Failed to mark as read:', error);
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await markAllAsRead();
            await refetch();
        } catch (error) {
            console.error('Failed to mark all as read:', error);
        }
    };

    const getNotificationIcon = (type: string) => {
        const icons = {
            success: (
                <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
            error: (
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
            warning: (
                <svg className="h-5 w-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
            ),
            info: (
                <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
        };
        return icons[type as keyof typeof icons] || icons.info;
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        return date.toLocaleDateString();
    };

    if (isLoading && notifications.length === 0) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="bg-white rounded-lg p-4 mb-3 border border-gray-200">
                            <div className="flex items-start space-x-3">
                                <div className="h-5 w-5 bg-gray-200 rounded-full"></div>
                                <div className="flex-1 space-y-2">
                                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                                    <div className="h-3 bg-gray-200 rounded w-full"></div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex">
                        <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-red-800">Failed to load notifications</h3>
                            <p className="text-sm text-red-700 mt-1">Please try refreshing the page.</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
                <div className="flex items-center space-x-3">
                    <Link
                        to="/settings/notifications"
                        className="text-sm text-blue-600 hover:text-blue-500"
                    >
                        Settings
                    </Link>
                    {notifications.some((n) => !n.is_read) && (
                        <button
                            onClick={handleMarkAllAsRead}
                            className="text-sm text-blue-600 hover:text-blue-500"
                        >
                            Mark all as read
                        </button>
                    )}
                </div>
            </div>

            {/* Notifications List */}
            {notifications.length === 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                    <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                        />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No notifications</h3>
                    <p className="mt-1 text-sm text-gray-500">You're all caught up!</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {notifications.map((notification) => (
                        <div
                            key={notification.notification_id}
                            className={`bg-white rounded-lg border p-4 transition-all ${notification.is_read
                                    ? 'border-gray-200 hover:border-gray-300'
                                    : 'border-blue-200 bg-blue-50 hover:bg-blue-100'
                                }`}
                        >
                            <div className="flex items-start space-x-3">
                                {/* Icon */}
                                <div className="flex-shrink-0 mt-1">
                                    {getNotificationIcon(notification.notification_type)}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <p className="text-sm font-medium text-gray-900">
                                                {notification.title}
                                            </p>
                                            {notification.message && (
                                                <p className="mt-1 text-sm text-gray-600">
                                                    {notification.message}
                                                </p>
                                            )}
                                            <p className="mt-1 text-xs text-gray-500">
                                                {formatDate(notification.created_at)}
                                            </p>
                                        </div>

                                        {/* Actions */}
                                        <div className="flex items-center space-x-2 ml-4">
                                            {!notification.is_read && (
                                                <button
                                                    onClick={() =>
                                                        handleMarkAsRead(notification.notification_id)
                                                    }
                                                    className="text-xs text-blue-600 hover:text-blue-500"
                                                >
                                                    Mark as read
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Action URL */}
                                    {notification.action_url && (
                                        <Link
                                            to={notification.action_url}
                                            className="inline-flex items-center mt-2 text-sm text-blue-600 hover:text-blue-500"
                                        >
                                            View details
                                            <svg
                                                className="ml-1 h-4 w-4"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={2}
                                                    d="M9 5l7 7-7 7"
                                                />
                                            </svg>
                                        </Link>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

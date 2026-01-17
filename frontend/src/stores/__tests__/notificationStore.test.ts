import { notificationsApi } from '@/api';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotificationStore } from '../notificationStore';

// Mock the notificationsApi
vi.mock('@/api', () => ({
    notificationsApi: {
        list: vi.fn(),
        getUnreadCount: vi.fn(),
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        getPreferences: vi.fn(),
        updatePreferences: vi.fn(),
    },
}));

const mockNotifications = [
    {
        notification_id: '1',
        user_id: 'user1',
        notification_type: 'info' as const,
        title: 'Test Notification 1',
        message: 'Message 1',
        is_read: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    },
    {
        notification_id: '2',
        user_id: 'user1',
        notification_type: 'warning' as const,
        title: 'Test Notification 2',
        message: 'Message 2',
        is_read: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    },
];

const mockPreferences = {
    preference_id: 'pref1',
    user_id: 'user1',
    email_enabled: true,
    in_app_enabled: true,
    test_completion_enabled: true,
    test_failure_enabled: true,
    daily_summary_enabled: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
};

describe('notificationStore', () => {
    beforeEach(() => {
        // Reset store
        useNotificationStore.getState().reset();

        // Reset mocks
        vi.clearAllMocks();
    });

    describe('fetchNotifications', () => {
        it('should fetch notifications successfully', async () => {
            vi.mocked(notificationsApi.list).mockResolvedValue(mockNotifications);

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.fetchNotifications();
            });

            await waitFor(() => {
                expect(result.current.notifications).toHaveLength(2);
                expect(result.current.notifications[0].title).toBe('Test Notification 1');
                expect(result.current.lastFetchedAt).toBeDefined();
            });

            expect(notificationsApi.list).toHaveBeenCalledWith({ limit: 50 });
        });

        it('should handle fetch error', async () => {
            const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
            vi.mocked(notificationsApi.list).mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useNotificationStore());

            await expect(
                act(async () => {
                    await result.current.fetchNotifications();
                })
            ).rejects.toThrow('Network error');

            expect(consoleErrorSpy).toHaveBeenCalled();
            consoleErrorSpy.mockRestore();
        });
    });

    describe('fetchUnreadCount', () => {
        it('should fetch unread count successfully', async () => {
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 5 });

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.fetchUnreadCount();
            });

            await waitFor(() => {
                expect(result.current.unreadCount).toBe(5);
            });
        });

        it('should handle fetch error', async () => {
            const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
            vi.mocked(notificationsApi.getUnreadCount).mockRejectedValue(new Error('API error'));

            const { result } = renderHook(() => useNotificationStore());

            await expect(
                act(async () => {
                    await result.current.fetchUnreadCount();
                })
            ).rejects.toThrow('API error');

            consoleErrorSpy.mockRestore();
        });
    });

    describe('markAsRead', () => {
        it('should mark notification as read and update state', async () => {
            vi.mocked(notificationsApi.list).mockResolvedValue(mockNotifications);
            vi.mocked(notificationsApi.markAsRead).mockResolvedValue(undefined);

            const { result } = renderHook(() => useNotificationStore());

            // First fetch notifications
            await act(async () => {
                await result.current.fetchNotifications();
            });

            // Set initial unread count
            act(() => {
                useNotificationStore.setState({ unreadCount: 2 });
            });

            // Mark one as read
            await act(async () => {
                await result.current.markAsRead('1');
            });

            await waitFor(() => {
                const notification = result.current.notifications.find((n) => n.notification_id === '1');
                expect(notification?.is_read).toBe(true);
                expect(result.current.unreadCount).toBe(1);
            });

            expect(notificationsApi.markAsRead).toHaveBeenCalledWith('1');
        });

        it('should not allow unread count to go below zero', async () => {
            vi.mocked(notificationsApi.list).mockResolvedValue(mockNotifications);
            vi.mocked(notificationsApi.markAsRead).mockResolvedValue(undefined);

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.fetchNotifications();
            });

            // Set unread count to 0
            act(() => {
                useNotificationStore.setState({ unreadCount: 0 });
            });

            await act(async () => {
                await result.current.markAsRead('1');
            });

            await waitFor(() => {
                expect(result.current.unreadCount).toBe(0);
            });
        });
    });

    describe('markAllAsRead', () => {
        it('should mark all notifications as read', async () => {
            vi.mocked(notificationsApi.list).mockResolvedValue(mockNotifications);
            vi.mocked(notificationsApi.markAllAsRead).mockResolvedValue(undefined);

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.fetchNotifications();
            });

            act(() => {
                useNotificationStore.setState({ unreadCount: 2 });
            });

            await act(async () => {
                await result.current.markAllAsRead();
            });

            await waitFor(() => {
                expect(result.current.notifications.every((n) => n.is_read)).toBe(true);
                expect(result.current.unreadCount).toBe(0);
            });

            expect(notificationsApi.markAllAsRead).toHaveBeenCalled();
        });
    });

    describe('fetchPreferences', () => {
        it('should fetch notification preferences', async () => {
            vi.mocked(notificationsApi.getPreferences).mockResolvedValue(mockPreferences);

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.fetchPreferences();
            });

            await waitFor(() => {
                expect(result.current.preferences).toEqual(mockPreferences);
            });
        });
    });

    describe('updatePreferences', () => {
        it('should update notification preferences', async () => {
            const updatedPrefs = { ...mockPreferences, email_enabled: false };
            vi.mocked(notificationsApi.updatePreferences).mockResolvedValue(updatedPrefs);

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.updatePreferences({ email_enabled: false });
            });

            await waitFor(() => {
                expect(result.current.preferences?.email_enabled).toBe(false);
            });

            expect(notificationsApi.updatePreferences).toHaveBeenCalledWith({ email_enabled: false });
        });
    });

    describe('Polling', () => {
        it('should start polling and set state correctly', () => {
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 3 });

            const { result } = renderHook(() => useNotificationStore());

            expect(result.current.isPolling).toBe(false);

            act(() => {
                result.current.startPolling(1000);
            });

            expect(result.current.isPolling).toBe(true);
            expect(result.current.pollInterval).not.toBeNull();
        });

        it('should call fetchUnreadCount on polling start', async () => {
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 3 });

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                result.current.startPolling(1000);
                // Wait for the initial fetch
                await new Promise((resolve) => setTimeout(resolve, 0));
            });

            expect(notificationsApi.getUnreadCount).toHaveBeenCalled();
        });

        it('should not start polling if already polling', () => {
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 3 });

            const { result } = renderHook(() => useNotificationStore());

            act(() => {
                result.current.startPolling(1000);
            });

            const pollInterval = result.current.pollInterval;

            // Try to start again
            act(() => {
                result.current.startPolling(1000);
            });

            // Should have the same interval reference
            expect(result.current.pollInterval).toBe(pollInterval);
        });

        it('should stop polling', () => {
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 3 });

            const { result } = renderHook(() => useNotificationStore());

            act(() => {
                result.current.startPolling(1000);
            });

            expect(result.current.isPolling).toBe(true);

            act(() => {
                result.current.stopPolling();
            });

            expect(result.current.isPolling).toBe(false);
            expect(result.current.pollInterval).toBeNull();
        });

        it('should use default interval if not specified', () => {
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 3 });

            const { result } = renderHook(() => useNotificationStore());

            act(() => {
                result.current.startPolling(); // No interval specified
            });

            expect(result.current.isPolling).toBe(true);
        });

        it('should handle errors during polling gracefully', async () => {
            const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
            vi.mocked(notificationsApi.getUnreadCount).mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                result.current.startPolling(1000);
                // Wait for the initial fetch
                await new Promise((resolve) => setTimeout(resolve, 0));
            });

            // Should still be polling despite error
            expect(result.current.isPolling).toBe(true);
            expect(consoleErrorSpy).toHaveBeenCalled();

            // Clean up
            act(() => {
                result.current.stopPolling();
            });

            consoleErrorSpy.mockRestore();
        });
    });

    describe('reset', () => {
        it('should reset store to initial state', async () => {
            vi.mocked(notificationsApi.list).mockResolvedValue(mockNotifications);
            vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue({ unread_count: 5 });

            const { result } = renderHook(() => useNotificationStore());

            await act(async () => {
                await result.current.fetchNotifications();
                await result.current.fetchUnreadCount();
            });

            expect(result.current.notifications).toHaveLength(2);
            expect(result.current.unreadCount).toBe(5);

            act(() => {
                result.current.reset();
            });

            expect(result.current.notifications).toHaveLength(0);
            expect(result.current.unreadCount).toBe(0);
            expect(result.current.isPolling).toBe(false);
            expect(result.current.pollInterval).toBeNull();
            expect(result.current.lastFetchedAt).toBeNull();
            expect(result.current.preferences).toBeNull();
        });
    });
});

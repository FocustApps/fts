import { notificationsApi } from '@/api';
import type { components } from '@/types/api';
import { create } from 'zustand';

type Notification = components['schemas']['NotificationResponse'];
type NotificationPreferences = components['schemas']['NotificationPreferenceResponse'];

interface NotificationState {
    // Notifications
    notifications: Notification[];
    unreadCount: number;
    preferences: NotificationPreferences | null;

    // Polling state
    isPolling: boolean;
    pollInterval: NodeJS.Timeout | null;
    lastFetchedAt: Date | null;

    // Actions
    fetchNotifications: () => Promise<Notification[]>;
    fetchUnreadCount: () => Promise<void>;
    markAsRead: (notificationId: string) => Promise<void>;
    markAllAsRead: () => Promise<void>;

    // Preferences
    fetchPreferences: () => Promise<void>;
    updatePreferences: (preferences: Partial<NotificationPreferences>) => Promise<void>;

    // Polling control
    startPolling: (intervalMs?: number) => void;
    stopPolling: () => void;

    // Reset
    reset: () => void;
}

const DEFAULT_POLL_INTERVAL = 30000; // 30 seconds

const initialState = {
    notifications: [],
    unreadCount: 0,
    preferences: null,
    isPolling: false,
    pollInterval: null,
    lastFetchedAt: null,
};

export const useNotificationStore = create<NotificationState>((set, get) => ({
    ...initialState,

    fetchNotifications: async () => {
        try {
            const notifications = await notificationsApi.list({ limit: 50 });
            set({
                notifications,
                lastFetchedAt: new Date(),
            });
            return notifications; // Return data for TanStack Query
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
            throw error;
        }
    },

    fetchUnreadCount: async () => {
        try {
            const response = await notificationsApi.getUnreadCount();
            set({ unreadCount: typeof response === 'number' ? response : response.unread_count });
        } catch (error) {
            console.error('Failed to fetch unread count:', error);
            throw error;
        }
    },

    markAsRead: async (notificationId: string) => {
        try {
            await notificationsApi.markAsRead(notificationId);

            // Update local state
            set((state) => ({
                notifications: state.notifications.map((n) =>
                    n.notification_id === notificationId ? { ...n, is_read: true } : n
                ),
                unreadCount: Math.max(0, state.unreadCount - 1),
            }));
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
            throw error;
        }
    },

    markAllAsRead: async () => {
        try {
            await notificationsApi.markAllAsRead();

            // Update local state
            set((state) => ({
                notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
                unreadCount: 0,
            }));
        } catch (error) {
            console.error('Failed to mark all as read:', error);
            throw error;
        }
    },

    fetchPreferences: async () => {
        try {
            const preferences = await notificationsApi.getPreferences();
            set({ preferences });
        } catch (error) {
            console.error('Failed to fetch notification preferences:', error);
            throw error;
        }
    },

    updatePreferences: async (updates: Partial<NotificationPreferences>) => {
        try {
            const preferences = await notificationsApi.updatePreferences(updates);
            set({ preferences });
        } catch (error) {
            console.error('Failed to update notification preferences:', error);
            throw error;
        }
    },

    startPolling: (intervalMs = DEFAULT_POLL_INTERVAL) => {
        const state = get();

        // Don't start if already polling
        if (state.isPolling) {
            return;
        }

        // Initial fetch
        state.fetchUnreadCount().catch(console.error);

        // Set up polling interval
        const pollInterval = setInterval(() => {
            get().fetchUnreadCount().catch(console.error);
        }, intervalMs);

        set({
            isPolling: true,
            pollInterval,
        });
    },

    stopPolling: () => {
        const { pollInterval } = get();

        if (pollInterval) {
            clearInterval(pollInterval);
        }

        set({
            isPolling: false,
            pollInterval: null,
        });
    },

    reset: () => {
        get().stopPolling();
        set(initialState);
    },
}));

// Cleanup on window unload
if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
        useNotificationStore.getState().stopPolling();
    });
}

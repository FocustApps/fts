import apiClient from '@/lib/axios';
import type { components } from '@/types/api';

/**
 * Type aliases from generated OpenAPI types
 */
type NotificationResponse = components['schemas']['NotificationResponse'];
type UnreadCountResponse = components['schemas']['UnreadCountResponse'];
type NotificationPreferencesResponse = components['schemas']['NotificationPreferencesResponse'];
type UpdatePreferencesRequest = components['schemas']['UpdatePreferencesRequest'];

/**
 * Notifications API
 */
export const notificationsApi = {
    /**
     * List user's notifications
     */
    async list(params?: {
        include_read?: boolean;
        limit?: number;
        offset?: number;
    }): Promise<NotificationResponse[]> {
        const response = await apiClient.get<NotificationResponse[]>(
            '/v1/api/users/me/notifications',
            { params }
        );
        return response.data;
    },

    /**
     * Get unread notification count
     */
    async getUnreadCount(): Promise<number> {
        const response = await apiClient.get<UnreadCountResponse>(
            '/v1/api/users/me/notifications/unread-count'
        );
        return response.data.unread_count;
    },

    /**
     * Mark notification as read
     */
    async markAsRead(notificationId: string): Promise<void> {
        await apiClient.put(`/v1/api/users/me/notifications/${notificationId}/read`);
    },

    /**
     * Mark all notifications as read
     */
    async markAllAsRead(): Promise<{ marked_count: number }> {
        const response = await apiClient.put('/v1/api/users/me/notifications/read-all');
        return response.data;
    },

    /**
     * Delete notification
     */
    async delete(notificationId: string): Promise<void> {
        await apiClient.delete(`/v1/api/users/me/notifications/${notificationId}`);
    },

    /**
     * Get notification preferences
     */
    async getPreferences(): Promise<NotificationPreferencesResponse> {
        const response = await apiClient.get<NotificationPreferencesResponse>(
            '/v1/api/users/me/notification-preferences'
        );
        return response.data;
    },

    /**
     * Update notification preferences
     */
    async updatePreferences(
        data: UpdatePreferencesRequest
    ): Promise<NotificationPreferencesResponse> {
        const response = await apiClient.put<NotificationPreferencesResponse>(
            '/v1/api/users/me/notification-preferences',
            data
        );
        return response.data;
    },
};

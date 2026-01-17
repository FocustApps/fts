import { notificationsApi } from '@/api';
import { useNotificationStore } from '@/stores';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationCenter } from '../NotificationCenter';

vi.mock('@/api', () => ({
    notificationsApi: {
        list: vi.fn(),
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        getUnreadCount: vi.fn(),
    },
}));

const mockNotifications = [
    {
        notification_id: '1',
        auth_user_id: 'user1',
        notification_type: 'success',
        title: 'Test Completed',
        message: 'Your test run completed successfully',
        action_url: '/test-runs/123',
        is_read: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    },
    {
        notification_id: '2',
        auth_user_id: 'user1',
        notification_type: 'error',
        title: 'Test Failed',
        message: 'Your test run failed with 3 errors',
        action_url: null,
        is_read: true,
        created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
        updated_at: new Date(Date.now() - 3600000).toISOString(),
    },
];

describe('NotificationCenter', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useNotificationStore.getState().reset();
        vi.mocked(notificationsApi.list).mockResolvedValue(mockNotifications);
        vi.mocked(notificationsApi.getUnreadCount).mockResolvedValue(1);
    });

    it('should render loading state initially', async () => {
        // Delay the mock response to keep it in loading state briefly
        vi.mocked(notificationsApi.list).mockImplementation(
            () => new Promise(resolve => setTimeout(() => resolve(mockNotifications), 100))
        );

        renderWithProviders(<NotificationCenter />);

        // Should show skeleton loaders while loading
        const skeletons = document.querySelectorAll('.animate-pulse');
        expect(skeletons.length).toBeGreaterThan(0);

        // Wait for data to load
        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });
    });

    it('should fetch and display notifications', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
            expect(screen.getByText('Test Failed')).toBeInTheDocument();
        });

        expect(notificationsApi.list).toHaveBeenCalled();
    });

    it('should display notification details correctly', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        expect(screen.getByText('Your test run completed successfully')).toBeInTheDocument();
        expect(screen.getByText('Your test run failed with 3 errors')).toBeInTheDocument();
    });

    it('should show "Mark as read" button for unread notifications', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        const markAsReadButtons = screen.getAllByText('Mark as read');
        expect(markAsReadButtons).toHaveLength(1); // Only one unread notification
    });

    it('should mark notification as read when clicked', async () => {
        const user = userEvent.setup();
        vi.mocked(notificationsApi.markAsRead).mockResolvedValue(undefined);

        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        const markAsReadButton = screen.getByText('Mark as read');
        await user.click(markAsReadButton);

        await waitFor(() => {
            expect(notificationsApi.markAsRead).toHaveBeenCalledWith('1');
        });
    });

    it('should show "Mark all as read" button when unread notifications exist', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Mark all as read')).toBeInTheDocument();
        });
    });

    it('should mark all notifications as read', async () => {
        const user = userEvent.setup();
        vi.mocked(notificationsApi.markAllAsRead).mockResolvedValue({ marked_count: 1 });

        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Mark all as read')).toBeInTheDocument();
        });

        const markAllButton = screen.getByText('Mark all as read');
        await user.click(markAllButton);

        await waitFor(() => {
            expect(notificationsApi.markAllAsRead).toHaveBeenCalled();
        });
    });

    it('should display "View details" link for notifications with action_url', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        const viewDetailsLinks = screen.getAllByText('View details');
        expect(viewDetailsLinks).toHaveLength(1); // Only one notification has action_url
    });

    it('should show empty state when no notifications', async () => {
        vi.mocked(notificationsApi.list).mockResolvedValue([]);

        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('No notifications')).toBeInTheDocument();
            expect(screen.getByText("You're all caught up!")).toBeInTheDocument();
        });
    });

    it('should show error state when fetch fails', async () => {
        vi.mocked(notificationsApi.list).mockRejectedValue(new Error('Network error'));

        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Failed to load notifications')).toBeInTheDocument();
        });
    });

    it('should display correct notification icons', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        // Both notifications should have SVG icons
        const svgIcons = document.querySelectorAll('svg');
        expect(svgIcons.length).toBeGreaterThan(0);
    });

    it('should format dates correctly', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        // Should show "Just now" for recent notification
        expect(screen.getByText('Just now')).toBeInTheDocument();

        // Should show "1h ago" for older notification
        expect(screen.getByText('1h ago')).toBeInTheDocument();
    });

    it('should have link to notification settings', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Settings')).toBeInTheDocument();
        });

        const settingsLink = screen.getByText('Settings').closest('a');
        expect(settingsLink).toHaveAttribute('href', '/settings/notifications');
    });

    it('should apply different styles to read and unread notifications', async () => {
        renderWithProviders(<NotificationCenter />);

        await waitFor(() => {
            expect(screen.getByText('Test Completed')).toBeInTheDocument();
        });

        const notifications = document.querySelectorAll('.bg-white');
        expect(notifications.length).toBeGreaterThan(0);

        // Unread notification should have blue styling
        const unreadNotification = screen.getByText('Test Completed').closest('div.bg-blue-50');
        expect(unreadNotification).toBeInTheDocument();
    });
});

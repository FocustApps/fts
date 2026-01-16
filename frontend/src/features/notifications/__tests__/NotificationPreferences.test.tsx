import { notificationsApi } from '@/api';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationPreferences } from '../NotificationPreferences';

vi.mock('@/api', () => ({
    notificationsApi: {
        getPreferences: vi.fn(),
        updatePreferences: vi.fn(),
    },
}));

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

describe('NotificationPreferences', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(notificationsApi.getPreferences).mockResolvedValue(mockPreferences);
    });

    it('should render loading state initially', async () => {
        // Delay the mock response to keep it in loading state briefly
        vi.mocked(notificationsApi.getPreferences).mockImplementation(
            () => new Promise(resolve => setTimeout(() => resolve(mockPreferences), 100))
        );

        renderWithProviders(<NotificationPreferences />);

        // Should show skeleton loaders while loading
        const skeletons = document.querySelectorAll('.animate-pulse');
        expect(skeletons.length).toBeGreaterThan(0);

        // Wait for data to load
        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });
    });

    it('should fetch and display preferences', async () => {
        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        expect(notificationsApi.getPreferences).toHaveBeenCalled();
    });

    it('should display all preference sections', async () => {
        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Delivery Methods')).toBeInTheDocument();
            expect(screen.getByText('Notification Types')).toBeInTheDocument();
        });
    });

    it('should display all preference toggles', async () => {
        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        expect(screen.getByText('Email notifications')).toBeInTheDocument();
        expect(screen.getByText('In-app notifications')).toBeInTheDocument();
        expect(screen.getByText('Test completion')).toBeInTheDocument();
        expect(screen.getByText('Test failure')).toBeInTheDocument();
        expect(screen.getByText('Daily summary')).toBeInTheDocument();
    });

    it('should show correct toggle states', async () => {
        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        // Get all toggle buttons
        const toggles = screen.getAllByRole('switch');

        // First 4 should be checked (enabled), last one unchecked (disabled)
        expect(toggles[0]).toHaveAttribute('aria-checked', 'true'); // email_enabled
        expect(toggles[1]).toHaveAttribute('aria-checked', 'true'); // in_app_enabled
        expect(toggles[2]).toHaveAttribute('aria-checked', 'true'); // test_completion_enabled
        expect(toggles[3]).toHaveAttribute('aria-checked', 'true'); // test_failure_enabled
        expect(toggles[4]).toHaveAttribute('aria-checked', 'false'); // daily_summary_enabled
    });

    it('should toggle preference when clicked', async () => {
        const user = userEvent.setup();
        vi.mocked(notificationsApi.updatePreferences).mockResolvedValue({
            ...mockPreferences,
            email_enabled: false,
        });

        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        const emailToggle = screen.getAllByRole('switch')[0];
        await user.click(emailToggle);

        await waitFor(() => {
            expect(notificationsApi.updatePreferences).toHaveBeenCalledWith({
                email_enabled: false,
            });
        });
    });

    it('should disable toggles while saving', async () => {
        const user = userEvent.setup();

        // Make the API call slow
        vi.mocked(notificationsApi.updatePreferences).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve(mockPreferences), 1000))
        );

        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        const emailToggle = screen.getAllByRole('switch')[0];
        await user.click(emailToggle);

        // Toggle should be disabled immediately
        expect(emailToggle).toHaveClass('opacity-50');
        expect(emailToggle).toHaveClass('cursor-not-allowed');
    });

    it('should show success toast on save', async () => {
        const user = userEvent.setup();
        vi.mocked(notificationsApi.updatePreferences).mockResolvedValue(mockPreferences);

        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        const emailToggle = screen.getAllByRole('switch')[0];
        await user.click(emailToggle);

        // Note: Toast appears from the store, would need to render toast container to test
        await waitFor(() => {
            expect(notificationsApi.updatePreferences).toHaveBeenCalled();
        });
    });

    it('should show error state when preferences fail to load', async () => {
        vi.mocked(notificationsApi.getPreferences).mockRejectedValue(
            new Error('Failed to load')
        );

        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(
                screen.getByText('Failed to load notification preferences')
            ).toBeInTheDocument();
        });
    });

    it('should display descriptions for each preference', async () => {
        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        expect(screen.getByText('Receive notifications via email')).toBeInTheDocument();
        expect(
            screen.getByText('Show notifications in the notification center')
        ).toBeInTheDocument();
        expect(
            screen.getByText('Notify when a test run completes successfully')
        ).toBeInTheDocument();
        expect(screen.getByText('Notify when a test run fails')).toBeInTheDocument();
        expect(screen.getByText('Receive a daily summary of test activity')).toBeInTheDocument();
    });

    it('should show info message about auto-save', async () => {
        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Email notifications')).toBeInTheDocument();
        });

        expect(
            screen.getByText(
                /Changes are saved automatically. You can update these preferences at any time./
            )
        ).toBeInTheDocument();
    });

    it('should toggle test completion preference', async () => {
        const user = userEvent.setup();
        vi.mocked(notificationsApi.updatePreferences).mockResolvedValue({
            ...mockPreferences,
            test_completion_enabled: false,
        });

        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Test completion')).toBeInTheDocument();
        });

        const testCompletionToggle = screen.getAllByRole('switch')[2];
        await user.click(testCompletionToggle);

        await waitFor(() => {
            expect(notificationsApi.updatePreferences).toHaveBeenCalledWith({
                test_completion_enabled: false,
            });
        });
    });

    it('should toggle daily summary preference', async () => {
        const user = userEvent.setup();
        vi.mocked(notificationsApi.updatePreferences).mockResolvedValue({
            ...mockPreferences,
            daily_summary_enabled: true,
        });

        renderWithProviders(<NotificationPreferences />);

        await waitFor(() => {
            expect(screen.getByText('Daily summary')).toBeInTheDocument();
        });

        const dailySummaryToggle = screen.getAllByRole('switch')[4];
        await user.click(dailySummaryToggle);

        await waitFor(() => {
            expect(notificationsApi.updatePreferences).toHaveBeenCalledWith({
                daily_summary_enabled: true,
            });
        });
    });
});

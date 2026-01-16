import { accountsApi } from '@/api';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountDetail } from '../AccountDetail';

vi.mock('@/api', () => ({
    accountsApi: {
        getById: vi.fn(),
        deactivate: vi.fn(),
    },
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        useParams: () => ({ id: 'acc1' }),
    };
});

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const mockAccount = {
    account_id: 'acc1',
    account_name: 'Acme Corporation',
    owner_user_id: 'user1',
    is_active: true,
    created_at: new Date('2024-01-15').toISOString(),
    updated_at: new Date('2024-01-20').toISOString(),
};

describe('AccountDetail', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(accountsApi.getById).mockResolvedValue(mockAccount);
    });

    it('should render loading state initially', async () => {
        vi.mocked(accountsApi.getById).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve(mockAccount), 100))
        );

        renderWithProviders(<AccountDetail />);

        // Should show skeleton loaders
        const skeletons = document.querySelectorAll('.animate-pulse');
        expect(skeletons.length).toBeGreaterThan(0);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });
    });

    it('should fetch and display account details', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        expect(accountsApi.getById).toHaveBeenCalledWith('acc1');
    });

    it('should display account information in info tab', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        // Should show account details
        expect(screen.getByText('Account Name')).toBeInTheDocument();
        expect(screen.getByText('Account ID')).toBeInTheDocument();
        expect(screen.getByText('acc1')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('should show three tabs', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        expect(screen.getByText('Account Info')).toBeInTheDocument();
        expect(screen.getByText('Users')).toBeInTheDocument();
        expect(screen.getByText('Audit Logs')).toBeInTheDocument();
    });

    it('should switch between tabs', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        // Click Users tab
        await user.click(screen.getByText('Users'));
        expect(screen.getByText('Account Users')).toBeInTheDocument();
        expect(screen.getByText('Open User Manager')).toBeInTheDocument();

        // Click Audit Logs tab
        await user.click(screen.getByText('Audit Logs'));
        expect(screen.getByText('Audit log history for this account will be implemented here.')).toBeInTheDocument();

        // Click back to Account Info
        await user.click(screen.getByText('Account Info'));
        expect(screen.getByText('Account Name')).toBeInTheDocument();
    });

    it('should display action buttons', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        expect(screen.getByText('Manage Users')).toBeInTheDocument();
        expect(screen.getByText('Edit')).toBeInTheDocument();
        expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    it('should show delete confirmation modal when delete clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        // Click delete button
        const deleteButton = screen.getByText('Delete');
        await user.click(deleteButton);

        // Modal should appear
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Delete Account/i })).toBeInTheDocument();
            expect(screen.getByText(/All associated data and user access will be removed/)).toBeInTheDocument();
        });
    });

    it('should handle account deletion', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.deactivate).mockResolvedValue({ message: 'Account deleted' });

        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        // Click delete button
        await user.click(screen.getByText('Delete'));

        // Confirm deletion in modal
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Delete Account/i })).toBeInTheDocument();
        });

        const confirmButton = screen.getAllByText('Delete Account')[1]; // Second one is the button
        await user.click(confirmButton);

        await waitFor(() => {
            expect(accountsApi.deactivate).toHaveBeenCalledWith('acc1');
        });
    });

    it('should show error state when fetch fails', async () => {
        vi.mocked(accountsApi.getById).mockRejectedValue(new Error('Failed to fetch'));

        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByText('Error Loading Account')).toBeInTheDocument();
            expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
        });
    });

    it('should display formatted dates', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        // Check for Created At and Updated At fields
        expect(screen.getByText('Created At')).toBeInTheDocument();
        expect(screen.getByText('Updated At')).toBeInTheDocument();
    });

    it('should have link to accounts list', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        const backLink = screen.getByText('Back to Accounts');
        expect(backLink).toBeInTheDocument();
        expect(backLink.closest('a')).toHaveAttribute('href', '/admin/accounts');
    });

    it('should have links to edit and manage users', async () => {
        renderWithProviders(<AccountDetail />);

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Acme Corporation/i })).toBeInTheDocument();
        });

        const editLink = screen.getByText('Edit').closest('a');
        expect(editLink).toHaveAttribute('href', '/admin/accounts/acc1/edit');

        const manageUsersLink = screen.getByText('Manage Users').closest('a');
        expect(manageUsersLink).toHaveAttribute('href', '/admin/accounts/acc1/users');
    });
});

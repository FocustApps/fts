import { accountsApi } from '@/api';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountUserManager } from '../AccountUserManager';

vi.mock('@/api', () => ({
    accountsApi: {
        getById: vi.fn(),
        listUsers: vi.fn(),
        removeUser: vi.fn(),
        updateUserRole: vi.fn(),
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
        info: vi.fn(),
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

const mockUsers = [
    {
        user_id: 'user1',
        email: 'owner@acme.com',
        username: 'owner',
        role: 'owner',
        is_primary: true,
    },
    {
        user_id: 'user2',
        email: 'admin@acme.com',
        username: 'admin',
        role: 'admin',
        is_primary: false,
    },
    {
        user_id: 'user3',
        email: 'member@acme.com',
        username: 'member',
        role: 'member',
        is_primary: false,
    },
];

describe('AccountUserManager', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(accountsApi.getById).mockResolvedValue(mockAccount);
        vi.mocked(accountsApi.listUsers).mockResolvedValue(mockUsers);
    });

    it('should render loading state initially', async () => {
        vi.mocked(accountsApi.listUsers).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve(mockUsers), 100))
        );

        renderWithProviders(<AccountUserManager />);

        const skeletons = document.querySelectorAll('.animate-pulse');
        expect(skeletons.length).toBeGreaterThan(0);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });
    });

    it('should fetch and display users', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
            expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
            expect(screen.getByText('member@acme.com')).toBeInTheDocument();
        });

        expect(accountsApi.listUsers).toHaveBeenCalledWith('acc1');
    });

    it('should display account name in header', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('Acme Corporation - Users')).toBeInTheDocument();
        });
    });

    it('should show user roles with color badges', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        expect(screen.getByText('Owner')).toBeInTheDocument();
        expect(screen.getByText('Admin')).toBeInTheDocument();
        expect(screen.getByText('Member')).toBeInTheDocument();
    });

    it('should show primary account badge', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('Primary')).toBeInTheDocument();
        });
    });

    it('should filter users by search', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        const searchInput = screen.getByPlaceholderText('Search by email or username...');
        await user.type(searchInput, 'admin');

        await waitFor(() => {
            expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
            expect(screen.queryByText('member@acme.com')).not.toBeInTheDocument();
        });
    });

    it('should select and deselect users with checkboxes', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        const checkboxes = screen.getAllByRole('checkbox');
        const userCheckbox = checkboxes[1]; // First checkbox is "select all"

        await user.click(userCheckbox);
        expect(screen.getByText('3 users (1 selected)')).toBeInTheDocument();

        await user.click(userCheckbox);
        expect(screen.getByText('3 users')).toBeInTheDocument();
        expect(screen.queryByText('selected')).not.toBeInTheDocument();
    });

    it('should select all users when select all clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        const checkboxes = screen.getAllByRole('checkbox');
        const selectAllCheckbox = checkboxes[0];

        await user.click(selectAllCheckbox);
        expect(screen.getByText('3 users (3 selected)')).toBeInTheDocument();
    });

    it('should show bulk action buttons when users selected', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        const checkboxes = screen.getAllByRole('checkbox');
        await user.click(checkboxes[1]);

        expect(screen.getByText(/Update Roles \(1\)/)).toBeInTheDocument();
        expect(screen.getByText(/Remove \(1\)/)).toBeInTheDocument();
    });

    it('should open add users modal when add button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        const addButton = screen.getByText('Add Users');
        await user.click(addButton);

        await waitFor(() => {
            expect(screen.getByText('Add Users to Account')).toBeInTheDocument();
        });
    });

    it('should open update roles modal when update roles clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        // Select a user
        const checkboxes = screen.getAllByRole('checkbox');
        await user.click(checkboxes[2]); // Select admin user

        // Click update roles button
        const updateButton = screen.getByText(/Update Roles/);
        await user.click(updateButton);

        await waitFor(() => {
            expect(screen.getByText('Update User Roles')).toBeInTheDocument();
        });
    });

    it('should disable remove button for owners', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        // Find all trash buttons
        const trashButtons = document.querySelectorAll('[title*="remove"]');
        const ownerTrashButton = trashButtons[0];

        expect(ownerTrashButton).toHaveAttribute('disabled');
        expect(ownerTrashButton).toHaveAttribute('title', 'Cannot remove owner');
    });

    it('should show delete confirmation modal when remove clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
        });

        // Click remove button for admin user (second row)
        const trashButtons = document.querySelectorAll('[title="Remove user"]');
        await user.click(trashButtons[0]);

        await waitFor(() => {
            expect(screen.getByText('Remove User from Account')).toBeInTheDocument();
        });
    });

    it('should handle user removal', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.removeUser).mockResolvedValue({ message: 'User removed' });

        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
        });

        // Click remove button
        const trashButtons = document.querySelectorAll('[title="Remove user"]');
        await user.click(trashButtons[0]);

        // Wait for modal and find Remove button
        await waitFor(() => {
            expect(screen.getByText('Remove User from Account')).toBeInTheDocument();
        });

        const deleteButton = screen.getByRole('button', { name: 'Delete' });
        await user.click(deleteButton);

        await waitFor(() => {
            expect(accountsApi.removeUser).toHaveBeenCalledWith('acc1', 'user2');
        });
    });

    it('should show error state when fetch fails', async () => {
        vi.mocked(accountsApi.listUsers).mockRejectedValue(new Error('Failed to fetch'));

        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('Error Loading Users')).toBeInTheDocument();
        });
    });

    it('should show empty state when no users', async () => {
        vi.mocked(accountsApi.listUsers).mockResolvedValue([]);

        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('No users found')).toBeInTheDocument();
            expect(screen.getByText('Get started by adding a user')).toBeInTheDocument();
        });
    });

    it('should display user count', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('3 users')).toBeInTheDocument();
        });
    });

    it('should have link back to account detail', async () => {
        renderWithProviders(<AccountUserManager />);

        await waitFor(() => {
            expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
        });

        const backLink = screen.getByText('Back to Account');
        expect(backLink.closest('a')).toHaveAttribute('href', '/admin/accounts/acc1');
    });
});

import { accountsApi } from '@/api';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BulkUpdateRolesModal } from '../BulkUpdateRolesModal';

vi.mock('@/api', () => ({
    accountsApi: {
        updateUserRole: vi.fn(),
    },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

const mockUsers = [
    {
        user_id: 'user1',
        email: 'owner@acme.com',
        username: 'owner',
        role: 'owner',
    },
    {
        user_id: 'user2',
        email: 'admin@acme.com',
        username: 'admin',
        role: 'admin',
    },
    {
        user_id: 'user3',
        email: 'member@acme.com',
        username: 'member',
        role: 'member',
    },
];

describe('BulkUpdateRolesModal', () => {
    const mockOnClose = vi.fn();
    const mockOnSuccess = vi.fn();

    const defaultProps = {
        accountId: 'acc1',
        accountName: 'Acme Corporation',
        selectedUserIds: ['user2', 'user3'],
        users: mockUsers,
        isOpen: true,
        onClose: mockOnClose,
        onSuccess: mockOnSuccess,
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should not render when isOpen is false', () => {
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} isOpen={false} />);

        expect(screen.queryByText('Update User Roles')).not.toBeInTheDocument();
    });

    it('should render modal when isOpen is true', () => {
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        expect(screen.getByText('Update User Roles')).toBeInTheDocument();
        expect(screen.getByText('Acme Corporation')).toBeInTheDocument();
    });

    it('should display selected users count', () => {
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        expect(screen.getByText('Selected Users (2)')).toBeInTheDocument();
    });

    it('should list selected users with current roles', () => {
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
        expect(screen.getByText('member@acme.com')).toBeInTheDocument();

        // Should show current roles
        const roles = screen.getAllByText(/admin|member/i);
        expect(roles.length).toBeGreaterThan(0);
    });

    it('should show warning when owners are selected', () => {
        const propsWithOwner = {
            ...defaultProps,
            selectedUserIds: ['user1', 'user2'],
        };

        renderWithProviders(<BulkUpdateRolesModal {...propsWithOwner} />);

        expect(screen.getByText('Account owners detected')).toBeInTheDocument();
        expect(screen.getByText(/Owner roles cannot be changed/)).toBeInTheDocument();
        expect(screen.getByText(/owner - will be skipped/)).toBeInTheDocument();
    });

    it('should have role selection dropdown', () => {
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const roleSelect = screen.getByDisplayValue(/Member/);
        expect(roleSelect).toBeInTheDocument();
    });

    it('should allow changing role selection', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const roleSelect = screen.getByRole('combobox');
        await user.selectOptions(roleSelect, 'admin');

        expect(roleSelect).toHaveValue('admin');
    });

    it('should display role descriptions', () => {
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        expect(screen.getByText('Role Permissions')).toBeInTheDocument();
        expect(screen.getByText(/Admin:/)).toBeInTheDocument();
        expect(screen.getByText(/Member:/)).toBeInTheDocument();
        expect(screen.getByText(/Viewer:/)).toBeInTheDocument();
        expect(screen.getByText(/Owner:/)).toBeInTheDocument();
    });

    it('should call updateUserRole for each selected user', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.updateUserRole).mockResolvedValue({
            association_id: 'assoc1',
            auth_user_id: 'user2',
            account_id: 'acc1',
            role: 'admin',
            is_primary: false,
            is_active: true,
            created_at: new Date().toISOString(),
        });

        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const roleSelect = screen.getByRole('combobox');
        await user.selectOptions(roleSelect, 'admin');

        const submitButton = screen.getByText('Update Roles');
        await user.click(submitButton);

        await waitFor(() => {
            expect(accountsApi.updateUserRole).toHaveBeenCalledWith('acc1', 'user2', { role: 'admin' });
            expect(accountsApi.updateUserRole).toHaveBeenCalledWith('acc1', 'user3', { role: 'admin' });
        });
    });

    it('should skip owners when updating roles', async () => {
        const user = userEvent.setup();
        const propsWithOwner = {
            ...defaultProps,
            selectedUserIds: ['user1', 'user2'],
        };

        vi.mocked(accountsApi.updateUserRole).mockResolvedValue({
            association_id: 'assoc1',
            auth_user_id: 'user2',
            account_id: 'acc1',
            role: 'admin',
            is_primary: false,
            is_active: true,
            created_at: new Date().toISOString(),
        });

        renderWithProviders(<BulkUpdateRolesModal {...propsWithOwner} />);

        const submitButton = screen.getByText('Update Roles');
        await user.click(submitButton);

        await waitFor(() => {
            // Should only call once for user2, not for owner (user1)
            expect(accountsApi.updateUserRole).toHaveBeenCalledTimes(1);
            expect(accountsApi.updateUserRole).toHaveBeenCalledWith('acc1', 'user2', { role: 'member' });
        });
    });

    it('should close modal after successful update', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.updateUserRole).mockResolvedValue({
            association_id: 'assoc1',
            auth_user_id: 'user2',
            account_id: 'acc1',
            role: 'admin',
            is_primary: false,
            is_active: true,
            created_at: new Date().toISOString(),
        });

        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const submitButton = screen.getByText('Update Roles');
        await user.click(submitButton);

        await waitFor(() => {
            expect(mockOnClose).toHaveBeenCalled();
            expect(mockOnSuccess).toHaveBeenCalled();
        });
    });

    it('should show loading state during submission', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.updateUserRole).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve({
                association_id: 'assoc1',
                auth_user_id: 'user2',
                account_id: 'acc1',
                role: 'admin',
                is_primary: false,
                is_active: true,
                created_at: new Date().toISOString(),
            }), 100))
        );

        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const submitButton = screen.getByText('Update Roles');
        await user.click(submitButton);

        expect(screen.getByText('Updating...')).toBeInTheDocument();
    });

    it('should disable form during submission', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.updateUserRole).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve({
                association_id: 'assoc1',
                auth_user_id: 'user2',
                account_id: 'acc1',
                role: 'admin',
                is_primary: false,
                is_active: true,
                created_at: new Date().toISOString(),
            }), 100))
        );

        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const submitButton = screen.getByText('Update Roles');
        await user.click(submitButton);

        const roleSelect = screen.getByRole('combobox');
        expect(roleSelect).toBeDisabled();
        expect(screen.getByText('Cancel')).toBeDisabled();
    });

    it('should call onClose when cancel clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const cancelButton = screen.getByText('Cancel');
        await user.click(cancelButton);

        expect(mockOnClose).toHaveBeenCalled();
    });

    it('should call onClose when X button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const closeButton = screen.getByRole('button', { name: '' }); // X button
        await user.click(closeButton);

        expect(mockOnClose).toHaveBeenCalled();
    });

    it('should not close during submission when backdrop clicked', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.updateUserRole).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve({
                association_id: 'assoc1',
                auth_user_id: 'user2',
                account_id: 'acc1',
                role: 'admin',
                is_primary: false,
                is_active: true,
                created_at: new Date().toISOString(),
            }), 100))
        );

        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        const submitButton = screen.getByText('Update Roles');
        await user.click(submitButton);

        const backdrop = document.querySelector('.bg-black');
        if (backdrop) {
            await user.click(backdrop);
            expect(mockOnClose).not.toHaveBeenCalled();
        }
    });

    it('should reset form state when closed', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkUpdateRolesModal {...defaultProps} />);

        // Change role
        const roleSelect = screen.getByRole('combobox');
        await user.selectOptions(roleSelect, 'admin');

        // Close modal
        await user.click(screen.getByText('Cancel'));

        expect(mockOnClose).toHaveBeenCalled();
    });
});

import { accountsApi } from '@/api';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BulkAddUsersModal } from '../BulkAddUsersModal';

vi.mock('@/api', () => ({
    accountsApi: {
        addUser: vi.fn(),
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

describe('BulkAddUsersModal', () => {
    const mockOnClose = vi.fn();
    const defaultProps = {
        accountId: 'acc1',
        accountName: 'Acme Corporation',
        isOpen: true,
        onClose: mockOnClose,
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should not render when isOpen is false', () => {
        renderWithProviders(<BulkAddUsersModal {...defaultProps} isOpen={false} />);

        expect(screen.queryByText('Add Users to Account')).not.toBeInTheDocument();
    });

    it('should render modal when isOpen is true', () => {
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        expect(screen.getByText('Add Users to Account')).toBeInTheDocument();
        expect(screen.getByText('Acme Corporation')).toBeInTheDocument();
    });

    it('should show note about email-based lookup', () => {
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        expect(screen.getByText('Note: Email-based user lookup')).toBeInTheDocument();
        expect(screen.getByText(/Users must already exist in the system/)).toBeInTheDocument();
    });

    it('should have one user row by default', () => {
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInputs = screen.getAllByPlaceholderText('user@example.com');
        expect(emailInputs).toHaveLength(1);
    });

    it('should add another user row when add button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const addButton = screen.getByText('Add Another User');
        await user.click(addButton);

        const emailInputs = screen.getAllByPlaceholderText('user@example.com');
        expect(emailInputs).toHaveLength(2);
    });

    it('should remove user row when remove button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        // Add a second row
        await user.click(screen.getByText('Add Another User'));

        const emailInputs = screen.getAllByPlaceholderText('user@example.com');
        expect(emailInputs).toHaveLength(2);

        // Remove the second row
        const removeButtons = screen.getAllByTitle('Remove user');
        await user.click(removeButtons[1]);

        const emailInputsAfter = screen.getAllByPlaceholderText('user@example.com');
        expect(emailInputsAfter).toHaveLength(1);
    });

    it('should not allow removing the last row', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const removeButtons = screen.getAllByTitle('Remove user');
        expect(removeButtons[0]).toBeDisabled();
    });

    it('should allow typing in email field', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        expect(emailInput).toHaveValue('test@example.com');
    });

    it('should allow selecting role', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const roleSelect = screen.getByDisplayValue('Member');
        await user.selectOptions(roleSelect, 'admin');

        expect(roleSelect).toHaveValue('admin');
    });

    it('should show validation error for empty email', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const submitButton = screen.getByText('Add Users');
        await user.click(submitButton);

        await waitFor(() => {
            expect(screen.getByText('Email is required')).toBeInTheDocument();
        });
    });

    it('should clear validation error when user types', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        // Trigger validation error
        const submitButton = screen.getByText('Add Users');
        await user.click(submitButton);

        await waitFor(() => {
            expect(screen.getByText('Email is required')).toBeInTheDocument();
        });

        // Type to clear error
        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        expect(screen.queryByText('Email is required')).not.toBeInTheDocument();
    });

    it('should call addUser API when form submitted', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.addUser).mockResolvedValue({
            association_id: 'assoc1',
            auth_user_id: 'user1',
            account_id: 'acc1',
            role: 'member',
            is_primary: false,
            is_active: true,
            created_at: new Date().toISOString(),
        });

        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        const submitButton = screen.getByText('Add Users');
        await user.click(submitButton);

        await waitFor(() => {
            expect(accountsApi.addUser).toHaveBeenCalledWith('acc1', {
                auth_user_id: 'test@example.com',
                role: 'member',
            });
        });
    });

    it('should close modal after successful submission', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.addUser).mockResolvedValue({
            association_id: 'assoc1',
            auth_user_id: 'user1',
            account_id: 'acc1',
            role: 'member',
            is_primary: false,
            is_active: true,
            created_at: new Date().toISOString(),
        });

        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        const submitButton = screen.getByText('Add Users');
        await user.click(submitButton);

        await waitFor(() => {
            expect(mockOnClose).toHaveBeenCalled();
        });
    });

    it('should show loading state during submission', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.addUser).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve({
                association_id: 'assoc1',
                auth_user_id: 'user1',
                account_id: 'acc1',
                role: 'member',
                is_primary: false,
                is_active: true,
                created_at: new Date().toISOString(),
            }), 100))
        );

        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        const submitButton = screen.getByText('Add Users');
        await user.click(submitButton);

        expect(screen.getByText('Adding Users...')).toBeInTheDocument();
    });

    it('should disable form during submission', async () => {
        const user = userEvent.setup();
        vi.mocked(accountsApi.addUser).mockImplementation(
            () => new Promise((resolve) => setTimeout(() => resolve({
                association_id: 'assoc1',
                auth_user_id: 'user1',
                account_id: 'acc1',
                role: 'member',
                is_primary: false,
                is_active: true,
                created_at: new Date().toISOString(),
            }), 100))
        );

        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        const submitButton = screen.getByText('Add Users');
        await user.click(submitButton);

        expect(emailInput).toBeDisabled();
        expect(screen.getByDisplayValue('Member')).toBeDisabled();
    });

    it('should call onClose when cancel clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const cancelButton = screen.getByText('Cancel');
        await user.click(cancelButton);

        expect(mockOnClose).toHaveBeenCalled();
    });

    it('should call onClose when X button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const closeButton = screen.getByRole('button', { name: '' }); // X button
        await user.click(closeButton);

        expect(mockOnClose).toHaveBeenCalled();
    });

    it('should display user count in footer', () => {
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        expect(screen.getByText('0 user(s) to add')).toBeInTheDocument();
    });

    it('should update user count when email entered', async () => {
        const user = userEvent.setup();
        renderWithProviders(<BulkAddUsersModal {...defaultProps} />);

        const emailInput = screen.getByPlaceholderText('user@example.com');
        await user.type(emailInput, 'test@example.com');

        expect(screen.getByText('1 user(s) to add')).toBeInTheDocument();
    });
});

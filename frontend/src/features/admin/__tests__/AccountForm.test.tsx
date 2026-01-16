import { accountsApi, usersApi } from '@/api';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountForm } from '../AccountForm';

const mockNavigate = vi.fn();
const mockUseParams = vi.fn();

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        useParams: () => mockUseParams(),
    };
});

vi.mock('@/api', () => ({
    accountsApi: {
        listAll: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
    },
    usersApi: {
        list: vi.fn(),
    },
}));

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
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
};

const mockUsers = [
    {
        user_id: 'user1',
        email: 'owner@acme.com',
        username: 'owner',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
    },
    {
        user_id: 'user2',
        email: 'admin@acme.com',
        username: 'admin',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
    },
];

describe('AccountForm', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(usersApi.list).mockResolvedValue(mockUsers);
    });

    describe('Create Mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should render create form with empty fields', async () => {
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('heading', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            expect(nameInput).toHaveValue('');
        });

        it('should have owner field enabled in create mode', async () => {
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const ownerSelect = screen.getByLabelText(/Account Owner/i);
                expect(ownerSelect).not.toBeDisabled();
            });
        });

        it('should load users for owner dropdown', async () => {
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(usersApi.list).toHaveBeenCalled();
                expect(screen.getByText('owner@acme.com')).toBeInTheDocument();
                expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
            });
        });

        it('should validate required account name', async () => {
            const user = userEvent.setup();
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('heading', { name: /Create Account/i })).toBeInTheDocument();
            });

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            expect(screen.getByText('Account name is required')).toBeInTheDocument();
        });

        it('should validate required owner selection', async () => {
            const user = userEvent.setup();
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.type(nameInput, 'New Account');

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            expect(screen.getByText('Owner is required')).toBeInTheDocument();
        });

        it('should submit create form with valid data', async () => {
            const user = userEvent.setup();
            vi.mocked(accountsApi.create).mockResolvedValue({
                ...mockAccount,
                account_name: 'New Account',
            });

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.type(nameInput, 'New Account');

            const ownerSelect = screen.getByLabelText(/Account Owner/i);
            await user.selectOptions(ownerSelect, 'user1');

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(accountsApi.create).toHaveBeenCalledWith({
                    account_name: 'New Account',
                    owner_user_id: 'user1',
                });
                expect(mockNavigate).toHaveBeenCalledWith('/admin/accounts/acc1');
            });
        });

        it('should show loading state during submission', async () => {
            const user = userEvent.setup();
            vi.mocked(accountsApi.create).mockImplementation(
                () => new Promise((resolve) => setTimeout(() => resolve(mockAccount), 100))
            );

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.type(nameInput, 'New Account');

            const ownerSelect = screen.getByLabelText(/Account Owner/i);
            await user.selectOptions(ownerSelect, 'user1');

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            expect(screen.getByText('Saving...')).toBeInTheDocument();
        });

        it('should disable form during submission', async () => {
            const user = userEvent.setup();
            vi.mocked(accountsApi.create).mockImplementation(
                () => new Promise((resolve) => setTimeout(() => resolve(mockAccount), 100))
            );

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.type(nameInput, 'New Account');

            const ownerSelect = screen.getByLabelText(/Account Owner/i);
            await user.selectOptions(ownerSelect, 'user1');

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            expect(nameInput).toBeDisabled();
            expect(ownerSelect).toBeDisabled();
            expect(screen.getByText('Cancel')).toBeDisabled();
        });
    });

    describe('Edit Mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({ id: 'acc1' });
            vi.mocked(accountsApi.listAll).mockResolvedValue([mockAccount]);
        });

        it('should render loading state initially', async () => {
            renderWithProviders(<AccountForm />);

            expect(screen.getByRole('heading', { name: /Edit Account/i })).toBeInTheDocument();

            // Wait for data to load
            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });
        });

        it('should load and display account data', async () => {
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });

            expect(accountsApi.listAll).toHaveBeenCalled();
        });

        it('should have owner field disabled in edit mode', async () => {
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const ownerSelect = screen.getByLabelText(/Account Owner/i);
                expect(ownerSelect).toBeDisabled();
            });
        });

        it('should show help text for disabled owner field', async () => {
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByText('Owner cannot be changed after account creation')).toBeInTheDocument();
            });
        });

        it('should submit update form with valid data', async () => {
            const user = userEvent.setup();
            vi.mocked(accountsApi.update).mockResolvedValue({
                ...mockAccount,
                account_name: 'Updated Account',
            });

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.clear(nameInput);
            await user.type(nameInput, 'Updated Account');

            const submitButton = screen.getByText('Update Account');
            await user.click(submitButton);

            await waitFor(() => {
                expect(accountsApi.update).toHaveBeenCalledWith('acc1', {
                    account_name: 'Updated Account',
                    owner_user_id: 'user1',
                });
                expect(mockNavigate).toHaveBeenCalledWith('/admin/accounts/acc1');
            });
        });

        it('should validate required account name on update', async () => {
            const user = userEvent.setup();
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.clear(nameInput);

            const submitButton = screen.getByText('Update Account');
            await user.click(submitButton);

            expect(screen.getByText('Account name is required')).toBeInTheDocument();
        });

        it('should show loading state during update', async () => {
            const user = userEvent.setup();
            vi.mocked(accountsApi.update).mockImplementation(
                () => new Promise((resolve) => setTimeout(() => resolve(mockAccount), 100))
            );

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.clear(nameInput);
            await user.type(nameInput, 'Updated Account');

            const submitButton = screen.getByText('Update Account');
            await user.click(submitButton);

            expect(screen.getByText('Saving...')).toBeInTheDocument();
        });
    });

    describe('Navigation', () => {
        it('should navigate back when cancel clicked', async () => {
            mockUseParams.mockReturnValue({});
            const user = userEvent.setup();
            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const cancelButton = screen.getByText('Cancel');
            await user.click(cancelButton);

            expect(mockNavigate).toHaveBeenCalledWith('/admin/accounts');
        });

        it('should navigate to account detail after successful update', async () => {
            const user = userEvent.setup();
            mockUseParams.mockReturnValue({ id: 'acc1' });
            vi.mocked(accountsApi.listAll).mockResolvedValue([mockAccount]);
            vi.mocked(accountsApi.update).mockResolvedValue(mockAccount);

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });

            const submitButton = screen.getByText('Update Account');
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/admin/accounts/acc1');
            });
        });

        it('should navigate to accounts list after successful create', async () => {
            const user = userEvent.setup();
            mockUseParams.mockReturnValue({});
            vi.mocked(accountsApi.create).mockResolvedValue(mockAccount);

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.type(nameInput, 'New Account');

            const ownerSelect = screen.getByLabelText(/Account Owner/i);
            await user.selectOptions(ownerSelect, 'user1');

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/admin/accounts/acc1');
            });
        });
    });

    describe('Error Handling', () => {
        it('should show error toast on create failure', async () => {
            mockUseParams.mockReturnValue({});
            const user = userEvent.setup();
            const { toast } = await import('sonner');
            vi.mocked(accountsApi.create).mockRejectedValue(new Error('Failed to create'));

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Account Name/i);
            await user.type(nameInput, 'New Account');

            const ownerSelect = screen.getByLabelText(/Account Owner/i);
            await user.selectOptions(ownerSelect, 'user1');

            const submitButton = screen.getByRole('button', { name: /Create Account/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalled();
            });
        });

        it('should show error toast on update failure', async () => {
            const user = userEvent.setup();
            const { toast } = await import('sonner');
            mockUseParams.mockReturnValue({ id: 'acc1' });
            vi.mocked(accountsApi.listAll).mockResolvedValue([mockAccount]);
            vi.mocked(accountsApi.update).mockRejectedValue(new Error('Failed to update'));

            renderWithProviders(<AccountForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Account Name/i);
                expect(nameInput).toHaveValue('Acme Corporation');
            });

            const submitButton = screen.getByText('Update Account');
            await user.click(submitButton);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalled();
            });
        });
    });
});

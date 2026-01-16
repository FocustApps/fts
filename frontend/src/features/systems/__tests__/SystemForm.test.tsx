import { systemsApi } from '@/api/systems';
import { SystemForm } from '@/features/systems/SystemForm';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/systems');

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

vi.mock('@/stores/authStore', () => ({
    useAuthStore: (selector: any) => {
        const store = {
            currentAccount: { account_id: 'acc_123', account_name: 'Test Account' },
            currentUser: { user_id: 'user_123', email: 'test@example.com' },
            getCachedRole: () => 'owner',
        };
        return selector(store);
    },
}));

describe('SystemForm', () => {
    beforeEach(() => {
        mockNavigate.mockClear();
        vi.clearAllMocks();
        vi.mocked(systemsApi.create).mockResolvedValue({
            sut_id: 'sut_new',
            system_name: 'New System',
            description: null,
            wiki_url: null,
            account_id: 'acc_123',
            owner_user_id: 'user_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        });
        vi.mocked(systemsApi.getById).mockResolvedValue({
            sut_id: 'sut_1',
            system_name: 'Web Application',
            description: 'Main web application for the platform',
            wiki_url: 'https://wiki.example.com/web-app',
            account_id: 'acc_123',
            owner_user_id: 'user_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        });
        vi.mocked(systemsApi.update).mockResolvedValue({
            sut_id: 'sut_1',
            system_name: 'Updated System',
            description: 'Updated description',
            wiki_url: null,
            account_id: 'acc_123',
            owner_user_id: 'user_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: new Date().toISOString(),
        });
    });

    describe('create mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should render create form with empty fields', () => {
            renderWithProviders(<SystemForm />);

            expect(screen.getByText('Create New System')).toBeInTheDocument();
            expect(screen.getByLabelText(/System Name/)).toHaveValue('');
            expect(screen.getByLabelText(/Description/)).toHaveValue('');
            expect(screen.getByLabelText(/Wiki URL/)).toHaveValue('');
        });

        it('should show all form fields', () => {
            renderWithProviders(<SystemForm />);

            expect(screen.getByLabelText(/System Name/)).toBeInTheDocument();
            expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
            expect(screen.getByLabelText(/Wiki URL/)).toBeInTheDocument();
        });

        it('should submit form with all fields filled', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await user.type(screen.getByLabelText(/System Name/), 'New Test System');
            await user.type(screen.getByLabelText(/Description/), 'A comprehensive test system');
            await user.type(screen.getByLabelText(/Wiki URL/), 'https://wiki.test.com');

            await user.click(screen.getByRole('button', { name: /Create System/ }));

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/systems/sut_new');
            });
        });

        it('should submit form with only required fields', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await user.type(screen.getByLabelText(/System Name/), 'Minimal System');

            await user.click(screen.getByRole('button', { name: /Create System/ }));

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/systems/sut_new');
            });
        });

        it('should navigate to systems list on cancel', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await user.click(screen.getByRole('button', { name: /Cancel/ }));

            expect(mockNavigate).toHaveBeenCalledWith('/systems');
        });
    });

    describe('edit mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({ id: 'sut_1' });
        });

        it('should load and display existing system data', async () => {
            renderWithProviders(<SystemForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/System Name/i)).toHaveValue('Web Application');
            });

            expect(screen.getByLabelText(/Description/i)).toHaveValue(
                'Main web application for the platform'
            );
            expect(screen.getByLabelText(/Wiki URL/i)).toHaveValue(
                'https://wiki.example.com/web-app'
            );
        });

        it('should update system with modified fields', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/System Name/i)).toHaveValue('Web Application');
            });

            const nameInput = screen.getByLabelText(/System Name/i);
            await user.clear(nameInput);
            await user.type(nameInput, 'Updated System Name');

            await user.click(screen.getByRole('button', { name: /Update System/i }));

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/systems/sut_1');
            });
        });

        it('should navigate to detail page after successful update', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/System Name/i)).toHaveValue('Web Application');
            });

            await user.click(screen.getByRole('button', { name: /Update System/i }));

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/systems/sut_1');
            });
        });
    });

    describe('validation', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should show error when system name is empty', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await user.click(screen.getByRole('button', { name: /Create System/ }));

            await waitFor(() => {
                expect(screen.getByText('System name is required')).toBeInTheDocument();
            });
        });

        it('should clear error when user types in system name', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await user.click(screen.getByRole('button', { name: /Create System/ }));

            await waitFor(() => {
                expect(screen.getByText('System name is required')).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/System Name/), 'New System');

            await waitFor(() => {
                expect(screen.queryByText('System name is required')).not.toBeInTheDocument();
            });
        });
    });

    describe('error handling', () => {
        it('should handle create errors gracefully', async () => {
            mockUseParams.mockReturnValue({});
            vi.mocked(systemsApi.create).mockRejectedValueOnce(new Error('Bad Request'));

            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await user.type(screen.getByLabelText(/System Name/i), 'Failed System');
            await user.click(screen.getByRole('button', { name: /Create System/i }));

            await waitFor(() => {
                expect(mockNavigate).not.toHaveBeenCalled();
            });
        });

        it('should handle update errors gracefully', async () => {
            mockUseParams.mockReturnValue({ id: 'sut_1' });
            vi.mocked(systemsApi.update).mockRejectedValueOnce(new Error('Bad Request'));

            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/System Name/i)).toHaveValue('Web Application');
            });

            await user.click(screen.getByRole('button', { name: /Update System/i }));

            await waitFor(() => {
                expect(mockNavigate).not.toHaveBeenCalled();
            });
        });
    });

    describe('navigation', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should navigate back when clicking back button', async () => {
            const user = userEvent.setup();
            const mockNavigateBack = vi.fn();

            vi.mocked(mockNavigate).mockImplementation(
                ((arg: number | string) => {
                    if (arg === -1) {
                        mockNavigateBack();
                    }
                }) as any
            );

            renderWithProviders(<SystemForm />);

            const backButton = screen.getByRole('button', { name: /Back/ });
            await user.click(backButton);

            expect(mockNavigateBack).toHaveBeenCalled();
        });

        it('should have cancel button that navigates to list', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemForm />);

            const cancelButton = screen.getByRole('button', { name: /Cancel/ });
            await user.click(cancelButton);

            expect(mockNavigate).toHaveBeenCalledWith('/systems');
        });
    });

});

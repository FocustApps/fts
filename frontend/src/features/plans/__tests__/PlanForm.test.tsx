import { plansApi } from '@/api/plans';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanForm } from '../PlanForm';

vi.mock('@/api/plans');
vi.mock('sonner');

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
            user: { user_id: 'user_123', email: 'test@example.com' },
            getCachedRole: () => 'admin',
        };
        return selector(store);
    },
}));

describe('PlanForm', () => {
    const mockPlan = {
        plan_id: 'plan_1',
        plan_name: 'Test Plan',
        suites_ids: 'suite1,suite2',
        suite_tags: null,
        status: 'active',
        owner_user_id: 'user_123',
        account_id: 'acc_123',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockUseParams.mockReturnValue({});
    });

    describe('Create Mode', () => {
        it('should render create form with empty fields', async () => {
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            expect(nameInput).toHaveValue('');
        });

        it('should show all form fields', () => {
            renderWithProviders(<PlanForm />);

            expect(screen.getByLabelText(/Plan Name/i)).toBeInTheDocument();
            expect(screen.getByLabelText(/Suite IDs/i)).toBeInTheDocument();
            expect(screen.getByLabelText(/Status/i)).toBeInTheDocument();
        });

        it('should create plan on form submission', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.create).mockResolvedValue({
                ...mockPlan,
                plan_id: 'plan_new',
            });

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.type(nameInput, 'New Plan');

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(plansApi.create).toHaveBeenCalled();
            });
        });

        it('should navigate to plan detail after successful create', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.create).mockResolvedValue({
                ...mockPlan,
                plan_id: 'plan_new',
            });

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.type(nameInput, 'New Plan');

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/plans/plan_new');
            });
        });

        it('should show success toast after create', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.create).mockResolvedValue({
                ...mockPlan,
                plan_id: 'plan_new',
            });

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.type(nameInput, 'New Plan');

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(toast.success).toHaveBeenCalledWith('Plan created successfully');
            });
        });
    });

    describe('Edit Mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({ id: 'plan_1' });
            vi.mocked(plansApi.getById).mockResolvedValue(mockPlan);
        });

        it('should render edit form with plan data', async () => {
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Edit Plan')).toBeInTheDocument();
            });

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Plan Name/i);
                expect(nameInput).toHaveValue('Test Plan');
            });
        });

        it('should load and display plan data', async () => {
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Plan Name/i);
                expect(nameInput).toHaveValue('Test Plan');
            });

            const suitesInput = screen.getByLabelText(/Suite IDs/i);
            expect(suitesInput).toHaveValue('suite1,suite2');
        });

        it('should update plan on form submission', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.update).mockResolvedValue(mockPlan);

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Plan Name/i);
                expect(nameInput).toHaveValue('Test Plan');
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.clear(nameInput);
            await user.type(nameInput, 'Updated Plan');

            const submitButton = screen.getByRole('button', { name: /Update Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(plansApi.update).toHaveBeenCalledWith(
                    'plan_1',
                    expect.objectContaining({ plan_name: 'Updated Plan' })
                );
            });
        });

        it('should navigate to plan detail after successful update', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.update).mockResolvedValue(mockPlan);

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Plan Name/i);
                expect(nameInput).toHaveValue('Test Plan');
            });

            const submitButton = screen.getByRole('button', { name: /Update Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/plans/plan_1');
            });
        });
    });

    describe('Validation', () => {
        it('should show error when plan name is empty', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('Plan name is required')).toBeInTheDocument();
            });
        });

        it('should not submit form with validation errors', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('Plan name is required')).toBeInTheDocument();
            });

            expect(plansApi.create).not.toHaveBeenCalled();
        });

        it('should clear error when field is corrected', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('Plan name is required')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.type(nameInput, 'Valid Name');

            await waitFor(() => {
                expect(screen.queryByText('Plan name is required')).not.toBeInTheDocument();
            });
        });
    });

    describe('Error Handling', () => {
        it('should show error toast on create failure', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.create).mockRejectedValue(new Error('Failed to create'));

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.type(nameInput, 'New Plan');

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalled();
            });
        });

        it('should show error toast on update failure', async () => {
            const user = userEvent.setup();
            mockUseParams.mockReturnValue({ id: 'plan_1' });
            vi.mocked(plansApi.getById).mockResolvedValue(mockPlan);
            vi.mocked(plansApi.update).mockRejectedValue(new Error('Failed to update'));

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                const nameInput = screen.getByLabelText(/Plan Name/i);
                expect(nameInput).toHaveValue('Test Plan');
            });

            const submitButton = screen.getByRole('button', { name: /Update Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalled();
            });
        });
    });

    describe('Navigation', () => {
        it('should navigate to plans list on cancel', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const cancelButton = screen.getByRole('button', { name: /Cancel/i });
            await user.click(cancelButton);

            expect(mockNavigate).toHaveBeenCalledWith('/plans');
        });

        it('should navigate to plans list on back button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const backButton = screen.getByText('Back to Plans');
            await user.click(backButton);

            expect(mockNavigate).toHaveBeenCalledWith('/plans');
        });
    });

    describe('Loading States', () => {
        it('should show loading state while fetching plan', () => {
            mockUseParams.mockReturnValue({ id: 'plan_1' });
            vi.mocked(plansApi.getById).mockImplementation(
                () => new Promise(() => { }) // Never resolves
            );

            renderWithProviders(<PlanForm />);

            // Check for loading skeleton instead of text
            const skeletons = document.querySelectorAll('.animate-pulse');
            expect(skeletons.length).toBeGreaterThan(0);
        });

        it('should disable form during submission', async () => {
            const user = userEvent.setup();
            vi.mocked(plansApi.create).mockImplementation(
                () => new Promise(() => { }) // Never resolves
            );

            renderWithProviders(<PlanForm />);

            await waitFor(() => {
                expect(screen.getByText('Create New Plan')).toBeInTheDocument();
            });

            const nameInput = screen.getByLabelText(/Plan Name/i);
            await user.type(nameInput, 'New Plan');

            const submitButton = screen.getByRole('button', { name: /Create Plan/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('Saving...')).toBeInTheDocument();
            });
        });
    });
});

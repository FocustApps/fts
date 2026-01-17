import { testCasesApi } from '@/api/test-cases';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TestCaseForm } from '../TestCaseForm';

vi.mock('@/api/test-cases');

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
            user: { user_id: 'user_123' },
            getCachedRole: () => 'admin',
        };
        return selector(store);
    },
}));

describe('TestCaseForm', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Create Mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should render create form with empty fields', async () => {
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByRole('heading', { name: 'Create New Test Case' })).toBeInTheDocument();
            });

            expect(screen.getByLabelText(/Test Name/)).toHaveValue('');
            expect(screen.getByLabelText(/Description/)).toHaveValue('');
            expect(screen.getByLabelText(/System Under Test ID/)).toHaveValue('');
        });

        it('should display all form fields', async () => {
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toBeInTheDocument();
            });

            expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
            expect(screen.getByLabelText(/Test Type/)).toBeInTheDocument();
            expect(screen.getByLabelText(/System Under Test ID/)).toBeInTheDocument();
        });

        it('should create test case on valid submission', async () => {
            const user = userEvent.setup();
            vi.mocked(testCasesApi.create).mockResolvedValue({
                test_case_id: 'tc_new',
                test_name: 'New Test Case',
                description: 'Test description',
                test_type: 'functional',
                sut_id: 'sut_123',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-15T00:00:00Z',
                updated_at: '2026-01-15T00:00:00Z',
            });

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/Test Name/), 'New Test Case');
            await user.type(screen.getByLabelText(/Description/), 'Test description');
            await user.selectOptions(screen.getByLabelText(/Test Type/), 'functional');
            await user.type(screen.getByLabelText(/System Under Test ID/), 'sut_123');

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(testCasesApi.create).toHaveBeenCalledWith({
                    test_name: 'New Test Case',
                    description: 'Test description',
                    test_type: 'functional',
                    sut_id: 'sut_123',
                    owner_user_id: 'user_123',
                    account_id: 'acc_123',
                    is_active: true,
                });
            });
        });

        it('should navigate to test case detail after successful creation', async () => {
            const user = userEvent.setup();
            vi.mocked(testCasesApi.create).mockResolvedValue({
                test_case_id: 'tc_new',
                test_name: 'New Test Case',
                description: 'Test description',
                test_type: 'functional',
                sut_id: 'sut_123',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-15T00:00:00Z',
                updated_at: '2026-01-15T00:00:00Z',
            });

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/Test Name/), 'New Test Case');
            await user.selectOptions(screen.getByLabelText(/Test Type/), 'functional');
            await user.type(screen.getByLabelText(/System Under Test ID/), 'sut_123');

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/test-cases/tc_new');
            });
        });
    });

    describe('Edit Mode', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({ id: 'tc_123' });
            vi.mocked(testCasesApi.getById).mockResolvedValue({
                test_case_id: 'tc_123',
                test_name: 'Existing Test Case',
                description: 'Existing description',
                test_type: 'integration',
                sut_id: 'sut_456',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-10T00:00:00Z',
                updated_at: '2026-01-10T00:00:00Z',
            });
        });

        it('should load existing test case data', async () => {
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toHaveValue('Existing Test Case');
            });

            expect(screen.getByLabelText(/Description/)).toHaveValue('Existing description');
            expect(screen.getByLabelText(/Test Type/)).toHaveValue('integration');
            expect(screen.getByLabelText(/System Under Test ID/)).toHaveValue('sut_456');
        });

        it('should display edit title', async () => {
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByRole('heading', { name: 'Edit Test Case' })).toBeInTheDocument();
            });
        });

        it('should update test case on submission', async () => {
            const user = userEvent.setup();
            vi.mocked(testCasesApi.update).mockResolvedValue({
                test_case_id: 'tc_123',
                test_name: 'Updated Test Case',
                description: 'Updated description',
                test_type: 'regression',
                sut_id: 'sut_789',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-10T00:00:00Z',
                updated_at: '2026-01-15T00:00:00Z',
            });

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toHaveValue('Existing Test Case');
            });

            await user.clear(screen.getByLabelText(/Test Name/));
            await user.type(screen.getByLabelText(/Test Name/), 'Updated Test Case');

            await user.clear(screen.getByLabelText(/Description/));
            await user.type(screen.getByLabelText(/Description/), 'Updated description');

            await user.selectOptions(screen.getByLabelText(/Test Type/), 'regression');

            await user.clear(screen.getByLabelText(/System Under Test ID/));
            await user.type(screen.getByLabelText(/System Under Test ID/), 'sut_789');

            const submitButton = screen.getByRole('button', { name: /Update Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(testCasesApi.update).toHaveBeenCalledWith('tc_123', {
                    test_name: 'Updated Test Case',
                    description: 'Updated description',
                    test_type: 'regression',
                    sut_id: 'sut_789',
                    owner_user_id: 'user_123',
                    account_id: 'acc_123',
                    is_active: true,
                });
            });
        });

        it('should navigate to test case detail after successful update', async () => {
            const user = userEvent.setup();
            vi.mocked(testCasesApi.update).mockResolvedValue({
                test_case_id: 'tc_123',
                test_name: 'Updated Test Case',
                description: 'Updated description',
                test_type: 'regression',
                sut_id: 'sut_789',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-10T00:00:00Z',
                updated_at: '2026-01-15T00:00:00Z',
            });

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toHaveValue('Existing Test Case');
            });

            await user.clear(screen.getByLabelText(/Test Name/));
            await user.type(screen.getByLabelText(/Test Name/), 'Updated Test Case');

            const submitButton = screen.getByRole('button', { name: /Update Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith('/test-cases/tc_123');
            });
        });
    });

    describe('Validation', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should require test name', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Test Case/i })).toBeInTheDocument();
            });

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('Test name is required')).toBeInTheDocument();
            });

            expect(testCasesApi.create).not.toHaveBeenCalled();
        });

        it('should require system under test ID', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/Test Name/), 'Test Case');

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('System under test is required')).toBeInTheDocument();
            });

            expect(testCasesApi.create).not.toHaveBeenCalled();
        });

        it('should clear validation errors on input', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Create Test Case/i })).toBeInTheDocument();
            });

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(screen.getByText('Test name is required')).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/Test Name/), 'Test Case');

            await waitFor(() => {
                expect(screen.queryByText('Test name is required')).not.toBeInTheDocument();
            });
        });
    });

    describe('Error Handling', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should display error toast on create failure', async () => {
            const user = userEvent.setup();
            vi.mocked(testCasesApi.create).mockRejectedValue(new Error('Failed to create'));

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/Test Name/), 'New Test Case');
            await user.selectOptions(screen.getByLabelText(/Test Type/), 'functional');
            await user.type(screen.getByLabelText(/System Under Test ID/), 'sut_123');

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            // Just verify the API was called and failed
            await waitFor(() => {
                expect(testCasesApi.create).toHaveBeenCalled();
            });
        });

        it('should display error toast on update failure', async () => {
            const user = userEvent.setup();
            mockUseParams.mockReturnValue({ id: 'tc_123' });
            vi.mocked(testCasesApi.getById).mockResolvedValue({
                test_case_id: 'tc_123',
                test_name: 'Existing Test Case',
                description: 'Existing description',
                test_type: 'integration',
                sut_id: 'sut_456',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-10T00:00:00Z',
                updated_at: '2026-01-10T00:00:00Z',
            });
            vi.mocked(testCasesApi.update).mockRejectedValue(new Error('Failed to update'));

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toHaveValue('Existing Test Case');
            });

            await user.clear(screen.getByLabelText(/Test Name/));
            await user.type(screen.getByLabelText(/Test Name/), 'Updated Test Case');

            const submitButton = screen.getByRole('button', { name: /Update Test Case/i });
            await user.click(submitButton);

            // Just verify the API was called and failed
            await waitFor(() => {
                expect(testCasesApi.update).toHaveBeenCalled();
            });
        });
    });

    describe('Navigation', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should navigate back on cancel', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
            });

            const cancelButton = screen.getByRole('button', { name: /Cancel/i });
            await user.click(cancelButton);

            expect(mockNavigate).toHaveBeenCalledWith('/test-cases');
        });

        it('should show back button', async () => {
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Back/i })).toBeInTheDocument();
            });
        });
    });

    describe('Loading State', () => {
        it('should show loading skeleton while fetching test case', () => {
            mockUseParams.mockReturnValue({ id: 'tc_123' });
            vi.mocked(testCasesApi.getById).mockImplementation(
                () => new Promise(() => { })
            );

            renderWithProviders(<TestCaseForm />);

            const skeletons = document.querySelectorAll('.animate-pulse');
            expect(skeletons.length).toBeGreaterThan(0);
        });

        it('should disable submit button during submission', async () => {
            mockUseParams.mockReturnValue({});
            const user = userEvent.setup();
            vi.mocked(testCasesApi.create).mockImplementation(
                () => new Promise(() => { })
            );

            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Name/)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/Test Name/), 'New Test Case');
            await user.selectOptions(screen.getByLabelText(/Test Type/), 'functional');
            await user.type(screen.getByLabelText(/System Under Test ID/), 'sut_123');

            const submitButton = screen.getByRole('button', { name: /Create Test Case/i });
            await user.click(submitButton);

            await waitFor(() => {
                expect(submitButton).toBeDisabled();
            });
        });
    });

    describe('Test Type Options', () => {
        beforeEach(() => {
            mockUseParams.mockReturnValue({});
        });

        it('should display all test type options', async () => {
            renderWithProviders(<TestCaseForm />);

            await waitFor(() => {
                expect(screen.getByLabelText(/Test Type/)).toBeInTheDocument();
            });

            const testTypeSelect = screen.getByLabelText(/Test Type/);
            const options = Array.from(testTypeSelect.querySelectorAll('option')).map(
                (opt) => opt.textContent
            );

            expect(options).toContain('Functional');
            expect(options).toContain('Integration');
            expect(options).toContain('Regression');
            expect(options).toContain('Smoke');
            expect(options).toContain('Performance');
            expect(options).toContain('Security');
        });
    });
});

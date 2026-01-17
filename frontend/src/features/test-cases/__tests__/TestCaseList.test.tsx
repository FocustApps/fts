import { testCasesApi } from '@/api/test-cases';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TestCaseList } from '../TestCaseList';

vi.mock('@/api/test-cases');

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        Link: ({ to, children, ...props }: any) => (
            <a href={to} {...props}>
                {children}
            </a>
        ),
    };
});

vi.mock('@/stores/authStore', () => ({
    useAuthStore: (selector: any) => {
        const store = {
            currentAccount: { account_id: 'acc_123', account_name: 'Test Account' },
            getCachedRole: () => 'admin',
        };
        return selector(store);
    },
}));

describe('TestCaseList', () => {
    const mockTestCases = [
        {
            test_case_id: 'tc_1',
            test_name: 'Alpha Test',
            description: 'First test case',
            test_type: 'functional',
            sut_id: 'sut_1',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        },
        {
            test_case_id: 'tc_2',
            test_name: 'Beta Test',
            description: 'Second test case',
            test_type: 'integration',
            sut_id: 'sut_1',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-02T00:00:00Z',
            updated_at: '2026-01-02T00:00:00Z',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(testCasesApi.listByAccount).mockResolvedValue(mockTestCases);
    });

    describe('Rendering', () => {
        it('should render loading state initially', () => {
            renderWithProviders(<TestCaseList />);
            const skeletons = document.querySelectorAll('.animate-pulse');
            expect(skeletons.length).toBeGreaterThan(0);
        });

        it('should display test cases after loading', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            expect(screen.getByText('Beta Test')).toBeInTheDocument();
        });

        it('should display test case count', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('2 test cases')).toBeInTheDocument();
            });
        });

        it('should show type badges', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('functional')).toBeInTheDocument();
            });

            expect(screen.getByText('integration')).toBeInTheDocument();
        });

        it('should display descriptions', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('First test case')).toBeInTheDocument();
            });

            expect(screen.getByText('Second test case')).toBeInTheDocument();
        });
    });

    describe('Create Button', () => {
        it('should show create button for admin users', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getAllByText('Create Test Case').length).toBeGreaterThan(0);
            });
        });

        it('should have correct link to create page', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                const createButtons = screen.getAllByText('Create Test Case');
                const firstButton = createButtons[0].closest('a');
                expect(firstButton).toHaveAttribute('href', '/test-cases/new');
            });
        });
    });

    describe('Search Functionality', () => {
        it('should filter test cases by search query', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search test cases...');
            await user.type(searchInput, 'Alpha');

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
                expect(screen.queryByText('Beta Test')).not.toBeInTheDocument();
            });
        });

        it('should search in descriptions', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search test cases...');
            await user.type(searchInput, 'First');

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
                expect(screen.queryByText('Beta Test')).not.toBeInTheDocument();
            });
        });

        it('should update test case count based on search', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('2 test cases')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search test cases...');
            await user.type(searchInput, 'Alpha');

            await waitFor(() => {
                expect(screen.getByText('1 test case')).toBeInTheDocument();
            });
        });
    });

    describe('Type Filtering', () => {
        it('should filter by test type', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const typeSelect = screen.getByDisplayValue('All Types');
            await user.selectOptions(typeSelect, 'functional');

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
                expect(screen.queryByText('Beta Test')).not.toBeInTheDocument();
            });
        });

        it('should show all types by default', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                const typeSelect = screen.getByDisplayValue('All Types');
                expect(typeSelect).toHaveValue('all');
            });
        });
    });

    describe('Sorting', () => {
        it('should sort by name ascending by default', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const alphaTest = screen.getByText('Alpha Test');
            const betaTest = screen.getByText('Beta Test');

            expect(alphaTest.compareDocumentPosition(betaTest)).toBe(4); // DOCUMENT_POSITION_FOLLOWING
        });

        it('should toggle sort order when clicking same sort button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const nameButton = screen.getByRole('button', { name: /Name/ });
            await user.click(nameButton);

            expect(nameButton).toHaveTextContent('↓');
        });

        it('should sort by date when clicking date button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const dateButton = screen.getByRole('button', { name: /Date/ });
            await user.click(dateButton);

            expect(dateButton).toHaveClass('bg-blue-50');
        });
    });

    describe('Empty State', () => {
        it('should show empty state when no test cases exist', async () => {
            vi.mocked(testCasesApi.listByAccount).mockResolvedValue([]);
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('No test cases yet')).toBeInTheDocument();
            });

            expect(
                screen.getByText('Get started by creating your first test case')
            ).toBeInTheDocument();
        });

        it('should show create button in empty state', async () => {
            vi.mocked(testCasesApi.listByAccount).mockResolvedValue([]);
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Create Your First Test Case')).toBeInTheDocument();
            });
        });

        it('should show no results message when search yields nothing', async () => {
            const user = userEvent.setup();
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Test')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search test cases...');
            await user.type(searchInput, 'NonExistent');

            await waitFor(() => {
                expect(screen.getByText('No test cases found')).toBeInTheDocument();
            });
        });
    });

    describe('Error Handling', () => {
        it('should display error message when fetch fails', async () => {
            vi.mocked(testCasesApi.listByAccount).mockRejectedValue(
                new Error('Failed to fetch test cases')
            );
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                expect(screen.getByText('Error Loading Test Cases')).toBeInTheDocument();
            });

            expect(screen.getByText('Failed to fetch test cases')).toBeInTheDocument();
        });
    });

    describe('Test Case Links', () => {
        it('should have links to test case detail pages', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                const alphaTest = screen.getByText('Alpha Test');
                const link = alphaTest.closest('a');
                expect(link).toHaveAttribute('href', '/test-cases/tc_1');
            });
        });
    });

    describe('Type Badge Colors', () => {
        it('should display different colors for different test types', async () => {
            renderWithProviders(<TestCaseList />);

            await waitFor(() => {
                const functionalBadge = screen.getByText('functional');
                expect(functionalBadge).toHaveClass('bg-blue-100', 'text-blue-800');

                const integrationBadge = screen.getByText('integration');
                expect(integrationBadge).toHaveClass('bg-purple-100', 'text-purple-800');
            });
        });
    });
});

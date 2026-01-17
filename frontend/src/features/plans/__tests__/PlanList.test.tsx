import { plansApi } from '@/api/plans';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanList } from '../PlanList';

vi.mock('@/api/plans');

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

describe('PlanList', () => {
    const mockPlans = [
        {
            plan_id: 'plan_1',
            plan_name: 'Alpha Plan',
            suites_ids: 'suite1,suite2',
            suite_tags: null,
            status: 'active',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        },
        {
            plan_id: 'plan_2',
            plan_name: 'Beta Plan',
            suites_ids: null,
            suite_tags: null,
            status: 'inactive',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            created_at: '2026-01-02T00:00:00Z',
            updated_at: '2026-01-02T00:00:00Z',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(plansApi.listByAccount).mockResolvedValue(mockPlans);
    });

    describe('Rendering', () => {
        it('should render loading state initially', () => {
            renderWithProviders(<PlanList />);
            // Check for loading skeleton
            const skeletons = document.querySelectorAll('.animate-pulse');
            expect(skeletons.length).toBeGreaterThan(0);
        });

        it('should display plans after loading', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
            });

            expect(screen.getByText('Beta Plan')).toBeInTheDocument();
        });

        it('should display plan count', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('2 plans')).toBeInTheDocument();
            });
        });

        it('should show status badges', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('active')).toBeInTheDocument();
            });

            expect(screen.getByText('inactive')).toBeInTheDocument();
        });
    });

    describe('Create Button', () => {
        it('should show create button for admin users', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getAllByText('Create Plan').length).toBeGreaterThan(0);
            });
        });

        it('should have correct link to create page', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                const createButtons = screen.getAllByText('Create Plan');
                const firstButton = createButtons[0].closest('a');
                expect(firstButton).toHaveAttribute('href', '/plans/new');
            });
        });
    });

    describe('Search Functionality', () => {
        it('should filter plans by search query', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search plans...');
            await user.type(searchInput, 'Alpha');

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
                expect(screen.queryByText('Beta Plan')).not.toBeInTheDocument();
            });
        });

        it('should update plan count based on search', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('2 plans')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search plans...');
            await user.type(searchInput, 'Alpha');

            await waitFor(() => {
                expect(screen.getByText('1 plan')).toBeInTheDocument();
            });
        });

        it('should show no results message for non-matching search', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search plans...');
            await user.type(searchInput, 'NonExistent');

            await waitFor(() => {
                expect(screen.getByText('No plans found')).toBeInTheDocument();
            });
        });
    });

    describe('Sorting', () => {
        it('should sort by name ascending by default', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
            });

            const alphaPlan = screen.getByText('Alpha Plan');
            const betaPlan = screen.getByText('Beta Plan');

            // Alpha should come before Beta in DOM
            expect(alphaPlan.compareDocumentPosition(betaPlan)).toBe(4); // DOCUMENT_POSITION_FOLLOWING
        });

        it('should toggle sort order when clicking same sort button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
            });

            const nameButton = screen.getByRole('button', { name: /Name/ });
            await user.click(nameButton);

            // Should reverse order (desc)
            expect(nameButton).toHaveTextContent('↓');
        });

        it('should sort by date when clicking date button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Alpha Plan')).toBeInTheDocument();
            });

            const dateButton = screen.getByRole('button', { name: /Date/ });
            await user.click(dateButton);

            expect(dateButton).toHaveClass('bg-blue-50');
        });
    });

    describe('Empty State', () => {
        it('should show empty state when no plans exist', async () => {
            vi.mocked(plansApi.listByAccount).mockResolvedValue([]);
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('No plans yet')).toBeInTheDocument();
            });

            expect(
                screen.getByText('Get started by creating your first test plan')
            ).toBeInTheDocument();
        });

        it('should show create button in empty state', async () => {
            vi.mocked(plansApi.listByAccount).mockResolvedValue([]);
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Create Your First Plan')).toBeInTheDocument();
            });
        });
    });

    describe('Error Handling', () => {
        it('should display error message when fetch fails', async () => {
            vi.mocked(plansApi.listByAccount).mockRejectedValue(
                new Error('Failed to fetch plans')
            );
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                expect(screen.getByText('Error Loading Plans')).toBeInTheDocument();
            });

            expect(screen.getByText('Failed to fetch plans')).toBeInTheDocument();
        });
    });

    describe('Plan Links', () => {
        it('should have links to plan detail pages', async () => {
            renderWithProviders(<PlanList />);

            await waitFor(() => {
                const alphaPlan = screen.getByText('Alpha Plan');
                const link = alphaPlan.closest('a');
                expect(link).toHaveAttribute('href', '/plans/plan_1');
            });
        });
    });
});

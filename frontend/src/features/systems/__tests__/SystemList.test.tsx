import { systemsApi } from '@/api/systems';
import { SystemList } from '@/features/systems/SystemList';
import { renderWithProviders } from '@/test/utils';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/systems');

// Mock auth store
vi.mock('@/stores/authStore', () => ({
    useAuthStore: (selector: any) => {
        const store = {
            currentAccount: { account_id: 'acc_123', account_name: 'Test Account' },
            getCachedRole: () => 'owner',
        };
        return selector(store);
    },
}));

describe('SystemList', () => {
    const mockSystems = [
        {
            sut_id: 'sut_1',
            system_name: 'Web Application',
            description: 'Main web application for the platform',
            wiki_url: 'https://wiki.example.com/web-app',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        },
        {
            sut_id: 'sut_2',
            system_name: 'Mobile App',
            description: 'iOS and Android mobile application',
            wiki_url: 'https://wiki.example.com/mobile-app',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-02T00:00:00Z',
            updated_at: '2026-01-02T00:00:00Z',
        },
        {
            sut_id: 'sut_3',
            system_name: 'REST API',
            description: 'Backend REST API services',
            wiki_url: null,
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-03T00:00:00Z',
            updated_at: '2026-01-03T00:00:00Z',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(systemsApi.listByAccount).mockResolvedValue(mockSystems);
    });

    describe('rendering', () => {
        it('should display systems after loading', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
            });

            expect(screen.getByText('Web Application')).toBeInTheDocument();
            expect(screen.getByText('Mobile App')).toBeInTheDocument();
            expect(screen.getByText('REST API')).toBeInTheDocument();
        });

        it('should display system count in heading', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Systems Under Test')).toBeInTheDocument();
                expect(screen.getByText('3 systems')).toBeInTheDocument();
            });
        });

        it('should display systems in grid layout', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const cards = screen.getAllByRole('link');
            // Should have 3 system cards + 1 create button = 4 links
            expect(cards.length).toBeGreaterThanOrEqual(3);
        });

        it('should show wiki URL icon for systems with wiki links', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const webAppCard = screen.getByText('Web Application').closest('a');
            expect(webAppCard).toBeInTheDocument();
            expect(within(webAppCard!).getByText(/📖/)).toBeInTheDocument();
        });

        it('should not show wiki icon for systems without wiki links', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('REST API')).toBeInTheDocument();
            });

            const apiCard = screen.getByText('REST API').closest('a');
            expect(apiCard).toBeInTheDocument();
            expect(within(apiCard!).queryByText(/📖/)).not.toBeInTheDocument();
        });
    });

    describe('create button', () => {
        it('should show create button for owner role', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Create System')).toBeInTheDocument();
            });
        });

        it('should link to new system form', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                const createButton = screen.getByText('Create System');
                expect(createButton.closest('a')).toHaveAttribute('href', '/systems/new');
            });
        });
    });

    describe('search functionality', () => {
        it('should filter systems by name', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search systems...');
            await user.type(searchInput, 'web');

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
                expect(screen.queryByText('Mobile App')).not.toBeInTheDocument();
                expect(screen.queryByText('REST API')).not.toBeInTheDocument();
            });
        });

        it('should filter systems by description', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Mobile App')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search systems...');
            await user.type(searchInput, 'mobile');

            await waitFor(() => {
                expect(screen.getByText('Mobile App')).toBeInTheDocument();
                expect(screen.queryByText('Web Application')).not.toBeInTheDocument();
            });
        });

        it('should show no results message when search has no matches', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search systems...');
            await user.clear(searchInput);
            await user.type(searchInput, 'nonexistent');

            await waitFor(() => {
                expect(screen.queryByText('Web Application')).not.toBeInTheDocument();
                expect(screen.getByText(/No systems found/i)).toBeInTheDocument();
            });
        });

        it('should update count when filtering', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('3 systems')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search systems...');
            await user.clear(searchInput);
            await user.type(searchInput, 'web');

            await waitFor(() => {
                expect(screen.getByText('1 system')).toBeInTheDocument();
            });
        });

        it('should be case-insensitive', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText('Search systems...');
            await user.type(searchInput, 'WEB');

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });
        });
    });

    describe('sorting', () => {
        it('should sort by name ascending by default', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const cards = screen.getAllByRole('link').filter(link =>
                link.getAttribute('href')?.startsWith('/systems/sut_')
            );
            expect(cards).toHaveLength(3);
            expect(within(cards[0]).getByText('Mobile App')).toBeInTheDocument();
            expect(within(cards[1]).getByText('REST API')).toBeInTheDocument();
            expect(within(cards[2]).getByText('Web Application')).toBeInTheDocument();
        });

        it('should toggle sort order when clicking name button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Mobile App')).toBeInTheDocument();
            });

            const nameButton = screen.getByRole('button', { name: /Name/i });
            await user.click(nameButton);

            await waitFor(() => {
                const cards = screen.getAllByRole('link').filter(link =>
                    link.getAttribute('href')?.startsWith('/systems/sut_')
                );
                expect(cards).toHaveLength(3);
                expect(within(cards[0]).getByText('Web Application')).toBeInTheDocument();
                expect(within(cards[2]).getByText('Mobile App')).toBeInTheDocument();
            });
        });

        it('should sort by date when clicking date button', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const dateButton = screen.getByRole('button', { name: /Date/i });
            await user.click(dateButton);

            await waitFor(() => {
                const cards = screen.getAllByRole('link').filter(link =>
                    link.getAttribute('href')?.startsWith('/systems/sut_')
                );
                expect(cards).toHaveLength(3);
                // Sorted by created_at ascending (oldest first)
                expect(within(cards[0]).getByText('Web Application')).toBeInTheDocument();
                expect(within(cards[1]).getByText('Mobile App')).toBeInTheDocument();
                expect(within(cards[2]).getByText('REST API')).toBeInTheDocument();
            });
        });

        it('should toggle date sort order', async () => {
            const user = userEvent.setup();
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const dateButton = screen.getByRole('button', { name: /Date/i });
            await user.click(dateButton);
            await user.click(dateButton);

            await waitFor(() => {
                const cards = screen.getAllByRole('link').filter(link =>
                    link.getAttribute('href')?.startsWith('/systems/sut_')
                );
                expect(cards).toHaveLength(3);
                // Sorted by created_at descending (newest first)
                expect(within(cards[0]).getByText('REST API')).toBeInTheDocument();
                expect(within(cards[2]).getByText('Web Application')).toBeInTheDocument();
            });
        });
    });

    describe('links', () => {
        it('should link to system detail pages', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                const webAppLink = screen.getByText('Web Application').closest('a');
                expect(webAppLink).toHaveAttribute('href', '/systems/sut_1');
            });
        });

        it('should have clickable cards', async () => {
            renderWithProviders(<SystemList />);

            await waitFor(() => {
                expect(screen.getByText('Web Application')).toBeInTheDocument();
            });

            const systemCards = screen.getAllByRole('link').filter(link =>
                link.getAttribute('href')?.startsWith('/systems/sut_')
            );
            expect(systemCards).toHaveLength(3);
            systemCards.forEach(card => {
                expect(card).toHaveAttribute('href', expect.stringContaining('/systems/sut_'));
            });
        });
    });
});

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { createTestQueryClient } from './test-utils';

/**
 * Wrapper providers for tests
 */
interface TestProvidersProps {
    children: ReactNode;
    queryClient?: QueryClient;
    initialRouterEntries?: string[];
}

export function TestProviders({ children, queryClient, initialRouterEntries = ['/'] }: TestProvidersProps) {
    const client = queryClient || createTestQueryClient();

    return (
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={initialRouterEntries}>
                {children}
            </MemoryRouter>
        </QueryClientProvider>
    );
}

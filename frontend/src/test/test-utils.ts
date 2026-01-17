import { QueryClient } from '@tanstack/react-query';

/**
 * Create a test query client with no retries
 */
export function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
                gcTime: 0,
            },
            mutations: {
                retry: false,
            },
        },
    });
}

/**
 * Helper to wait for promises to resolve
 */
export const waitForPromises = () =>
    new Promise((resolve) => setTimeout(resolve, 0));

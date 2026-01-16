import { setupServer } from 'msw/node';
import { handlers } from './handlers';

/**
 * Mock Service Worker server for Node environment (tests)
 */
export const server = setupServer(...handlers);

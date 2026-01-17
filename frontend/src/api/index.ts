/**
 * API Client Exports
 * 
 * Centralized exports for all API modules with type-safe wrappers
 * using generated OpenAPI types.
 */

export { default as apiClient, tokenManager } from '@/lib/axios';
export { accountsApi } from './accounts';
export { authApi } from './auth';
export { notificationsApi } from './notifications';
export { plansApi } from './plans';
export { systemsApi } from './systems';
export { testCasesApi } from './test-cases';
export { usersApi } from './users';

/**
 * Re-export common types from generated API
 */
export type { components, paths } from '@/types/api';

import apiClient from '@/lib/axios';
import type { components } from '@/types/api';

/**
 * Type aliases from generated OpenAPI types
 */
type UserAccountsResponse = components['schemas']['UserAccountsResponse'];
type CurrentAccountResponse = components['schemas']['CurrentAccountResponse'];
type AvailableAccountResponse = components['schemas']['AvailableAccountResponse'];
type SwitchAccountRequest = components['schemas']['SwitchAccountRequest'];
type SwitchAccountResponse = components['schemas']['SwitchAccountResponse'];
type UserResponse = components['schemas']['UserResponse'];

/**
 * Users API
 */
export const usersApi = {
    /**
     * Get current user's accounts
     */
    async getMyAccounts(): Promise<UserAccountsResponse[]> {
        const response = await apiClient.get<UserAccountsResponse[]>('/v1/api/users/me/accounts');
        return response.data;
    },

    /**
     * Get current active account
     */
    async getCurrentAccount(): Promise<CurrentAccountResponse> {
        const response = await apiClient.get<CurrentAccountResponse>('/v1/api/users/me/current-account');
        return response.data;
    },

    /**
     * Get available accounts to switch to
     */
    async getAvailableAccounts(): Promise<AvailableAccountResponse[]> {
        const response = await apiClient.get<AvailableAccountResponse[]>(
            '/v1/api/users/me/available-accounts'
        );
        return response.data;
    },

    /**
     * Switch to a different account
     */
    async switchAccount(data: SwitchAccountRequest): Promise<SwitchAccountResponse> {
        const response = await apiClient.post<SwitchAccountResponse>(
            '/v1/api/users/me/switch-account',
            data
        );
        return response.data;
    },

    /**
     * List all auth users (for dropdowns, super admin only)
     */
    async list(params?: { include_inactive?: boolean; account_id?: string }): Promise<UserResponse[]> {
        const response = await apiClient.get<UserResponse[]>('/v1/api/auth-users/users', { params });
        return response.data;
    },
};

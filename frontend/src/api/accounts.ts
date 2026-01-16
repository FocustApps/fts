import apiClient from '@/lib/axios';
import type { components } from '@/types/api';

/**
 * Type aliases from generated OpenAPI types
 */
type AccountResponse = components['schemas']['AccountResponse'];
type AccountDetailResponse = components['schemas']['AccountDetailResponse'];
type CreateAccountRequest = components['schemas']['CreateAccountRequest'];
type UpdateAccountRequest = components['schemas']['UpdateAccountRequest'];
type AccountUserResponse = components['schemas']['AccountUserResponse'];
type AddUserRequest = components['schemas']['app__routes__account_associations__AddUserRequest'];
type UpdateRoleRequest = components['schemas']['UpdateRoleRequest'];

/**
 * Accounts API
 */
export const accountsApi = {
    /**
     * List all accounts (super admin only)
     */
    async listAll(): Promise<AccountResponse[]> {
        const response = await apiClient.get<AccountResponse[]>('/v1/api/accounts/');
        return response.data;
    },

    /**
     * Get account by ID
     */
    async getById(accountId: string): Promise<AccountDetailResponse> {
        const response = await apiClient.get<AccountDetailResponse>(`/v1/api/accounts/${accountId}`);
        return response.data;
    },

    /**
     * Create new account
     */
    async create(data: CreateAccountRequest): Promise<AccountResponse> {
        const response = await apiClient.post<AccountResponse>('/v1/api/accounts/', data);
        return response.data;
    },

    /**
     * Update account
     */
    async update(accountId: string, data: UpdateAccountRequest): Promise<AccountResponse> {
        const response = await apiClient.put<AccountResponse>(`/v1/api/accounts/${accountId}`, data);
        return response.data;
    },

    /**
     * Deactivate account (soft delete)
     */
    async deactivate(accountId: string): Promise<{ message: string }> {
        const response = await apiClient.delete(`/v1/api/accounts/${accountId}`);
        return response.data;
    },

    /**
     * List users in account
     */
    async listUsers(accountId: string): Promise<AccountUserResponse[]> {
        const response = await apiClient.get<AccountUserResponse[]>(
            `/v1/api/accounts/${accountId}/users`
        );
        return response.data;
    },

    /**
     * Add user to account
     */
    async addUser(accountId: string, data: AddUserRequest): Promise<AccountUserResponse> {
        const response = await apiClient.post<AccountUserResponse>(
            `/v1/api/accounts/${accountId}/users`,
            data
        );
        return response.data;
    },

    /**
     * Remove user from account
     */
    async removeUser(accountId: string, userId: string): Promise<{ message: string }> {
        const response = await apiClient.delete(`/v1/api/accounts/${accountId}/users/${userId}`);
        return response.data;
    },

    /**
     * Update user role in account
     */
    async updateUserRole(
        accountId: string,
        userId: string,
        data: UpdateRoleRequest
    ): Promise<AccountUserResponse> {
        const response = await apiClient.patch<AccountUserResponse>(
            `/v1/api/accounts/${accountId}/users/${userId}/role`,
            data
        );
        return response.data;
    },

    /**
     * Set primary account for user
     */
    async setPrimaryAccount(accountId: string, userId: string): Promise<{ message: string }> {
        const response = await apiClient.post(
            `/v1/api/accounts/${accountId}/users/${userId}/set-primary`
        );
        return response.data;
    },
};

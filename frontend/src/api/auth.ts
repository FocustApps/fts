import apiClient, { tokenManager } from '@/lib/axios';
import type { components } from '@/types/api';

/**
 * Type aliases from generated OpenAPI types
 */
type LoginRequest = components['schemas']['LoginRequest'];
type RegisterRequest = components['schemas']['RegisterRequest'];
type TokenResponse = components['schemas']['TokenResponse'];
type PasswordResetRequest = components['schemas']['PasswordResetRequest'];
type PasswordReset = components['schemas']['PasswordReset'];

/**
 * Authentication API
 */
export const authApi = {
    /**
     * Login with email and password
     */
    async login(data: LoginRequest): Promise<TokenResponse> {
        const response = await apiClient.post<TokenResponse>('/api/auth/login', data);

        const { access_token, refresh_token } = response.data;
        tokenManager.setTokens(access_token, refresh_token, data.remember_me);

        return response.data;
    },

    /**
     * Register a new user account
     */
    async register(data: RegisterRequest): Promise<{ message: string; email: string }> {
        const response = await apiClient.post('/api/auth/register', data);
        return response.data;
    },

    /**
     * Logout user and clear tokens
     */
    async logout(): Promise<void> {
        try {
            await apiClient.post('/api/auth/logout');
        } finally {
            tokenManager.clearTokens();
        }
    },

    /**
     * Request password reset email
     */
    async requestPasswordReset(data: PasswordResetRequest): Promise<{ message: string }> {
        const response = await apiClient.post('/api/auth/password-reset', data);
        return response.data;
    },

    /**
     * Complete password reset with token
     */
    async resetPassword(data: PasswordReset): Promise<{ message: string }> {
        const response = await apiClient.post('/api/auth/password-reset/confirm', data);
        return response.data;
    },

    /**
     * Refresh access token
     */
    async refreshToken(): Promise<TokenResponse> {
        const refreshToken = tokenManager.getRefreshToken();

        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await apiClient.post<TokenResponse>('/api/auth/refresh', {
            refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        const rememberMe = localStorage.getItem('refresh_token') !== null;
        tokenManager.setTokens(access_token, newRefreshToken, rememberMe);

        return response.data;
    },

    /**
     * Get current user from token
     */
    getCurrentUser() {
        const token = tokenManager.getAccessToken();
        if (!token) return null;
        return tokenManager.decodeToken(token);
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated(): boolean {
        const token = tokenManager.getAccessToken();
        if (!token) return false;
        return !tokenManager.isTokenExpired(token, 0);
    },
};

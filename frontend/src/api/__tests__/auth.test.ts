import { beforeEach, describe, expect, it } from 'vitest';
import { authApi, tokenManager } from '../../api';

describe('authApi', () => {
    beforeEach(() => {
        sessionStorage.clear();
        localStorage.clear();
    });

    describe('login', () => {
        it('should login successfully and store tokens', async () => {
            const result = await authApi.login({
                email: 'test@example.com',
                password: 'password123',
                remember_me: false,
            });

            expect(result.access_token).toContain('eyJ'); // JWT format starts with eyJ
            expect(result.refresh_token).toBe('mock_refresh_token');
            expect(result.token_type).toBe('bearer');
            expect(tokenManager.getAccessToken()).toBeTruthy();
            expect(tokenManager.getRefreshToken()).toBe('mock_refresh_token');
        });

        it('should store tokens in localStorage when remember_me is true', async () => {
            await authApi.login({
                email: 'test@example.com',
                password: 'password123',
                remember_me: true,
            });

            expect(localStorage.getItem('refresh_token')).toBe('mock_refresh_token');
        });
    });

    describe('register', () => {
        it('should register successfully', async () => {
            const result = await authApi.register({
                email: 'newuser@example.com',
                password: 'SecurePass123!',
                username: 'newuser',
            });

            expect(result.message).toBe('Registration successful');
            expect(result.email).toBe('test@example.com');
        });
    });

    describe('logout', () => {
        it('should clear tokens on logout', async () => {
            tokenManager.setTokens('access_123', 'refresh_456', false);

            await authApi.logout();

            expect(tokenManager.getAccessToken()).toBeNull();
            expect(tokenManager.getRefreshToken()).toBeNull();
        });
    });

    describe('refreshToken', () => {
        it('should refresh access token successfully', async () => {
            tokenManager.setTokens('old_access', 'old_refresh', false);

            const result = await authApi.refreshToken();

            expect(result.access_token).toContain('eyJ'); // JWT format
            expect(result.refresh_token).toBe('new_mock_refresh_token');
            expect(tokenManager.getAccessToken()).toContain('eyJ');
            expect(tokenManager.getRefreshToken()).toBe('new_mock_refresh_token');
        });

        it('should throw error when no refresh token available', async () => {
            await expect(authApi.refreshToken()).rejects.toThrow(
                'No refresh token available'
            );
        });
    });

    describe('isAuthenticated', () => {
        it('should return false when no token exists', () => {
            expect(authApi.isAuthenticated()).toBe(false);
        });

        it('should return false when token is expired', () => {
            const pastExp = Math.floor(Date.now() / 1000) - 3600;
            const expiredToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
                JSON.stringify({ exp: pastExp })
            )}.xyz`;
            sessionStorage.setItem('access_token', expiredToken);

            expect(authApi.isAuthenticated()).toBe(false);
        });

        it('should return true when valid token exists', () => {
            const futureExp = Math.floor(Date.now() / 1000) + 3600;
            const validToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
                JSON.stringify({ exp: futureExp })
            )}.xyz`;
            sessionStorage.setItem('access_token', validToken);

            expect(authApi.isAuthenticated()).toBe(true);
        });
    });
});

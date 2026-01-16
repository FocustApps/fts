import { beforeEach, describe, expect, it } from 'vitest';
import { tokenManager } from '../axios';

describe('tokenManager', () => {
    beforeEach(() => {
        // Clear all storage before each test
        sessionStorage.clear();
        localStorage.clear();
    });

    describe('setTokens and getTokens', () => {
        it('should store tokens in sessionStorage by default', () => {
            tokenManager.setTokens('access_123', 'refresh_456', false);

            expect(tokenManager.getAccessToken()).toBe('access_123');
            expect(tokenManager.getRefreshToken()).toBe('refresh_456');
            expect(sessionStorage.getItem('access_token')).toBe('access_123');
            expect(sessionStorage.getItem('refresh_token')).toBe('refresh_456');
        });

        it('should store refresh token in localStorage when rememberMe is true', () => {
            tokenManager.setTokens('access_123', 'refresh_456', true);

            expect(tokenManager.getAccessToken()).toBe('access_123');
            expect(tokenManager.getRefreshToken()).toBe('refresh_456');
            expect(sessionStorage.getItem('access_token')).toBe('access_123');
            expect(localStorage.getItem('refresh_token')).toBe('refresh_456');
        });

        it('should get refresh token from localStorage if not in sessionStorage', () => {
            localStorage.setItem('refresh_token', 'persistent_refresh');

            expect(tokenManager.getRefreshToken()).toBe('persistent_refresh');
        });
    });

    describe('clearTokens', () => {
        it('should clear all tokens from both storages', () => {
            sessionStorage.setItem('access_token', 'access_123');
            sessionStorage.setItem('refresh_token', 'session_refresh');
            localStorage.setItem('refresh_token', 'local_refresh');

            tokenManager.clearTokens();

            expect(tokenManager.getAccessToken()).toBeNull();
            expect(tokenManager.getRefreshToken()).toBeNull();
            expect(sessionStorage.getItem('access_token')).toBeNull();
            expect(sessionStorage.getItem('refresh_token')).toBeNull();
            expect(localStorage.getItem('refresh_token')).toBeNull();
        });
    });

    describe('decodeToken', () => {
        it('should decode a valid JWT token', () => {
            // JWT with payload: { sub: "user_123", email: "test@example.com", exp: 1234567890 }
            const token =
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6MTIzNDU2Nzg5MH0.xyz';

            const payload = tokenManager.decodeToken(token);

            expect(payload).toBeDefined();
            expect(payload?.sub).toBe('user_123');
            expect(payload?.email).toBe('test@example.com');
        });

        it('should return null for invalid token', () => {
            const payload = tokenManager.decodeToken('invalid_token');

            expect(payload).toBeNull();
        });
    });

    describe('isTokenExpired', () => {
        it('should return false for token expiring in the future', () => {
            const futureExp = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now
            const token = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
                JSON.stringify({ exp: futureExp })
            )}.xyz`;

            expect(tokenManager.isTokenExpired(token, 0)).toBe(false);
        });

        it('should return true for expired token', () => {
            const pastExp = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
            const token = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
                JSON.stringify({ exp: pastExp })
            )}.xyz`;

            expect(tokenManager.isTokenExpired(token, 0)).toBe(true);
        });

        it('should consider buffer time when checking expiry', () => {
            const soonExp = Math.floor(Date.now() / 1000) + 200; // 200 seconds from now
            const token = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
                JSON.stringify({ exp: soonExp })
            )}.xyz`;

            // With 5 minute (300 second) buffer, token should be considered expired
            expect(tokenManager.isTokenExpired(token, 300)).toBe(true);

            // With 1 minute (60 second) buffer, token should not be expired
            expect(tokenManager.isTokenExpired(token, 60)).toBe(false);
        });

        it('should return true for invalid token', () => {
            expect(tokenManager.isTokenExpired('invalid_token', 0)).toBe(true);
        });
    });
});

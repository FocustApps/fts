/**
 * Authentication client for JWT-based authentication.
 * 
 * Handles token storage, refresh, session monitoring, and logout.
 * Uses mutex pattern to prevent concurrent refresh requests.
 */

class AuthClient {
    constructor() {
        this.accessTokenKey = 'fenrir_access_token';
        this.refreshTokenKey = 'fenrir_refresh_token';
        this.refreshPromise = null; // Mutex for token refresh
        this.expiryCheckInterval = null;
    }

    /**
     * Store tokens after login or refresh.
     * 
     * @param {string} accessToken - JWT access token
     * @param {string} refreshToken - Refresh token
     * @param {boolean} rememberMe - If true, store in localStorage; else sessionStorage
     * @param {string|null} previousRefreshToken - Old refresh token to remove from localStorage
     */
    storeTokens(accessToken, refreshToken, rememberMe = false, previousRefreshToken = null) {
        // Access token always in sessionStorage (cleared on tab close)
        sessionStorage.setItem(this.accessTokenKey, accessToken);

        // Remove old refresh token from localStorage if provided
        if (previousRefreshToken && localStorage.getItem(this.refreshTokenKey) === previousRefreshToken) {
            localStorage.removeItem(this.refreshTokenKey);
        }

        // Refresh token storage based on remember_me
        if (rememberMe) {
            localStorage.setItem(this.refreshTokenKey, refreshToken);
            sessionStorage.removeItem(this.refreshTokenKey);
        } else {
            sessionStorage.setItem(this.refreshTokenKey, refreshToken);
            localStorage.removeItem(this.refreshTokenKey);
        }
    }

    /**
     * Get access token from sessionStorage.
     * 
     * @returns {string|null} Access token or null
     */
    getAccessToken() {
        return sessionStorage.getItem(this.accessTokenKey);
    }

    /**
     * Get refresh token from localStorage or sessionStorage.
     * 
     * @returns {string|null} Refresh token or null
     */
    getRefreshToken() {
        return localStorage.getItem(this.refreshTokenKey) ||
            sessionStorage.getItem(this.refreshTokenKey);
    }

    /**
     * Check if user is authenticated (has access token).
     * 
     * @returns {boolean} True if authenticated
     */
    isAuthenticated() {
        return !!this.getAccessToken();
    }

    /**
     * Clear all tokens (logout).
     */
    clearTokens() {
        sessionStorage.removeItem(this.accessTokenKey);
        sessionStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        this.stopExpiryMonitor();
    }

    /**
     * Login with email and password.
     * 
     * @param {string} email - User email
     * @param {string} password - User password
     * @param {boolean} rememberMe - Keep logged in across sessions
     * @returns {Promise<Object>} Token response
     */
    async login(email, password, rememberMe = false) {
        const response = await fetch('/v1/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password, remember_me: rememberMe }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        this.storeTokens(data.access_token, data.refresh_token, rememberMe);
        this.startExpiryMonitor();
        return data;
    }

    /**
     * Register new user account.
     * 
     * @param {string} email - User email
     * @param {string} password - User password
     * @param {string} username - Username
     * @returns {Promise<Object>} Registration response
     */
    async register(email, password, username) {
        const response = await fetch('/v1/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password, username }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        return await response.json();
    }

    /**
     * Refresh access and refresh tokens.
     * Uses mutex pattern to prevent concurrent refresh requests.
     * 
     * @returns {Promise<Object>} Token response
     */
    async refreshTokens() {
        // If refresh already in progress, wait for it
        if (this.refreshPromise) {
            return await this.refreshPromise;
        }

        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        // Store refresh promise as mutex
        this.refreshPromise = (async () => {
            try {
                const response = await fetch('/v1/api/auth/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Token refresh failed');
                }

                const data = await response.json();

                // Determine storage type based on where current refresh token is stored
                const rememberMe = !!localStorage.getItem(this.refreshTokenKey);

                // Store new tokens, remove old refresh token from localStorage if needed
                this.storeTokens(
                    data.access_token,
                    data.refresh_token,
                    rememberMe,
                    data.previous_refresh_token
                );

                return data;
            } finally {
                // Clear mutex
                this.refreshPromise = null;
            }
        })();

        return await this.refreshPromise;
    }

    /**
     * Logout from current device.
     * 
     * @returns {Promise<void>}
     */
    async logout() {
        const refreshToken = this.getRefreshToken();

        if (refreshToken) {
            try {
                await fetch('/v1/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.getAccessToken()}`,
                    },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });
            } catch (error) {
                console.error('Logout request failed:', error);
            }
        }

        this.clearTokens();
        window.location.href = '/auth/login';
    }

    /**
     * Logout from all devices.
     * 
     * @returns {Promise<Object>} Logout response with sessions_revoked count
     */
    async logoutAll() {
        const response = await fetch('/v1/api/auth/logout-all', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getAccessToken()}`,
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Logout all failed');
        }

        this.clearTokens();
        window.location.href = '/auth/login';
        return await response.json();
    }

    /**
     * Get all active sessions for current user.
     * 
     * @returns {Promise<Array>} Array of session objects
     */
    async getSessions() {
        const response = await fetch('/v1/api/auth/sessions', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getAccessToken()}`,
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get sessions');
        }

        return await response.json();
    }

    /**
     * Revoke a specific session.
     * 
     * @param {string} tokenId - Token ID to revoke
     * @returns {Promise<Object>} Revocation response
     */
    async revokeSession(tokenId) {
        const response = await fetch(`/v1/api/auth/sessions/${tokenId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${this.getAccessToken()}`,
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to revoke session');
        }

        return await response.json();
    }

    /**
     * Request password reset email.
     * 
     * @param {string} email - User email
     * @returns {Promise<Object>} Request response
     */
    async requestPasswordReset(email) {
        const response = await fetch('/v1/api/auth/password-reset-request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Password reset request failed');
        }

        return await response.json();
    }

    /**
     * Complete password reset with token.
     * 
     * @param {string} resetToken - Reset token from email
     * @param {string} newPassword - New password
     * @returns {Promise<Object>} Reset response
     */
    async resetPassword(resetToken, newPassword) {
        const response = await fetch('/v1/api/auth/password-reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                reset_token: resetToken,
                new_password: newPassword
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Password reset failed');
        }

        return await response.json();
    }

    /**
     * Decode JWT token to get payload (without verification).
     * 
     * @param {string} token - JWT token
     * @returns {Object} Decoded payload
     */
    decodeToken(token) {
        const parts = token.split('.');
        if (parts.length !== 3) {
            throw new Error('Invalid token format');
        }

        const payload = parts[1];
        const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
        return JSON.parse(decoded);
    }

    /**
     * Get hours until token expiry.
     * 
     * @returns {number} Hours until expiry, or 0 if expired/no token
     */
    getTokenExpiryHours() {
        const token = this.getAccessToken();
        if (!token) return 0;

        try {
            const payload = this.decodeToken(token);
            const now = Math.floor(Date.now() / 1000);
            const secondsRemaining = payload.exp - now;
            return Math.max(0, secondsRemaining / 3600);
        } catch (error) {
            console.error('Failed to decode token:', error);
            return 0;
        }
    }

    /**
     * Start monitoring token expiry (updates UI every minute).
     */
    startExpiryMonitor() {
        this.stopExpiryMonitor();

        this.expiryCheckInterval = setInterval(() => {
            const hours = this.getTokenExpiryHours();

            // Update UI elements with class 'token-expiry'
            document.querySelectorAll('.token-expiry').forEach(el => {
                if (hours < 1) {
                    el.textContent = `${Math.floor(hours * 60)} minutes`;
                    el.classList.add('text-warning');
                } else {
                    el.textContent = `${hours.toFixed(1)} hours`;
                    el.classList.remove('text-warning');
                }
            });

            // If token expired, logout
            if (hours === 0 && this.isAuthenticated()) {
                this.logout();
            }
        }, 60000); // Check every minute
    }

    /**
     * Stop monitoring token expiry.
     */
    stopExpiryMonitor() {
        if (this.expiryCheckInterval) {
            clearInterval(this.expiryCheckInterval);
            this.expiryCheckInterval = null;
        }
    }
}

// Create singleton instance
window.authClient = new AuthClient();

// Start expiry monitor if authenticated
if (window.authClient.isAuthenticated()) {
    window.authClient.startExpiryMonitor();
}

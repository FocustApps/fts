/**
 * HTTP client with automatic JWT token handling.
 * 
 * Wraps fetch API to automatically:
 * - Add Authorization header with access token
 * - Handle 401 responses by refreshing tokens
 * - Retry original request with new token
 * - Use mutex to prevent concurrent refresh requests
 */

class HttpClient {
    constructor(authClient) {
        this.authClient = authClient;
    }

    /**
     * Make authenticated API request.
     * 
     * Automatically handles token refresh on 401 responses.
     * Uses mutex pattern to prevent duplicate refresh requests.
     * 
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} Fetch response
     */
    async request(url, options = {}) {
        // Add Authorization header if authenticated
        const accessToken = this.authClient.getAccessToken();
        if (accessToken) {
            options.headers = {
                ...options.headers,
                'Authorization': `Bearer ${accessToken}`,
            };
        }

        // Make request
        let response = await fetch(url, options);

        // If 401 and we have refresh token, try to refresh
        if (response.status === 401 && this.authClient.getRefreshToken()) {
            try {
                // Refresh tokens (uses mutex internally)
                await this.authClient.refreshTokens();

                // Retry original request with new token
                const newAccessToken = this.authClient.getAccessToken();
                if (newAccessToken) {
                    options.headers['Authorization'] = `Bearer ${newAccessToken}`;
                    response = await fetch(url, options);
                }
            } catch (error) {
                console.error('Token refresh failed:', error);
                // Logout and redirect to login
                this.authClient.clearTokens();
                window.location.href = '/auth/login';
                throw error;
            }
        }

        return response;
    }

    /**
     * Make GET request.
     * 
     * @param {string} url - Request URL
     * @param {Object} options - Additional fetch options
     * @returns {Promise<any>} Parsed JSON response
     */
    async get(url, options = {}) {
        const response = await this.request(url, {
            ...options,
            method: 'GET',
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Make POST request.
     * 
     * @param {string} url - Request URL
     * @param {Object} data - Request body (will be JSON stringified)
     * @param {Object} options - Additional fetch options
     * @returns {Promise<any>} Parsed JSON response
     */
    async post(url, data = null, options = {}) {
        const response = await this.request(url, {
            ...options,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            body: data ? JSON.stringify(data) : undefined,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Make PUT request.
     * 
     * @param {string} url - Request URL
     * @param {Object} data - Request body (will be JSON stringified)
     * @param {Object} options - Additional fetch options
     * @returns {Promise<any>} Parsed JSON response
     */
    async put(url, data = null, options = {}) {
        const response = await this.request(url, {
            ...options,
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            body: data ? JSON.stringify(data) : undefined,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Make PATCH request.
     * 
     * @param {string} url - Request URL
     * @param {Object} data - Request body (will be JSON stringified)
     * @param {Object} options - Additional fetch options
     * @returns {Promise<any>} Parsed JSON response
     */
    async patch(url, data = null, options = {}) {
        const response = await this.request(url, {
            ...options,
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            body: data ? JSON.stringify(data) : undefined,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Make DELETE request.
     * 
     * @param {string} url - Request URL
     * @param {Object} options - Additional fetch options
     * @returns {Promise<any>} Parsed JSON response
     */
    async delete(url, options = {}) {
        const response = await this.request(url, {
            ...options,
            method: 'DELETE',
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        // DELETE might not return JSON
        const text = await response.text();
        return text ? JSON.parse(text) : null;
    }
}

// Create singleton instance
window.httpClient = new HttpClient(window.authClient);

// Example usage:
// const data = await httpClient.get('/api/v1/api/environments');
// const created = await httpClient.post('/api/v1/api/environments', { name: 'Test' });

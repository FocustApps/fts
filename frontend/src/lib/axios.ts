import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import { jwtDecode } from 'jwt-decode';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

/**
 * JWT Token Payload structure matching backend TokenPayload
 */
interface TokenPayload {
    sub: string; // user_id
    email: string;
    account_id: string;
    account_role: string;
    is_super_admin: boolean;
    is_impersonating?: boolean;
    impersonated_by?: string;
    exp: number;
    iat: number;
}

/**
 * Storage keys for tokens
 */
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    REFRESH_TOKEN: 'refresh_token',
} as const;

/**
 * Token management utilities
 */
export const tokenManager = {
    getAccessToken: (): string | null => {
        return sessionStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    },

    getRefreshToken: (): string | null => {
        return sessionStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN) ||
            localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    },

    setTokens: (accessToken: string, refreshToken: string, rememberMe: boolean = false): void => {
        sessionStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);

        if (rememberMe) {
            localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        } else {
            sessionStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        }
    },

    clearTokens: (): void => {
        sessionStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        sessionStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    },

    decodeToken: (token: string): TokenPayload | null => {
        try {
            return jwtDecode<TokenPayload>(token);
        } catch {
            return null;
        }
    },

    isTokenExpired: (token: string, bufferSeconds: number = 300): boolean => {
        const payload = tokenManager.decodeToken(token);
        if (!payload) return true;

        const now = Math.floor(Date.now() / 1000);
        return payload.exp <= now + bufferSeconds;
    },
};

/**
 * Axios instance with interceptors
 */
export const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

/**
 * Flag to prevent multiple simultaneous refresh attempts
 */
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

/**
 * Subscribe to token refresh completion
 */
const subscribeToRefresh = (callback: (token: string) => void) => {
    refreshSubscribers.push(callback);
};

/**
 * Notify all subscribers when refresh completes
 */
const onRefreshComplete = (token: string) => {
    refreshSubscribers.forEach((callback) => callback(token));
    refreshSubscribers = [];
};

/**
 * Refresh access token using refresh token
 */
const refreshAccessToken = async (): Promise<string> => {
    const refreshToken = tokenManager.getRefreshToken();

    if (!refreshToken) {
        throw new Error('No refresh token available');
    }

    try {
        const response = await axios.post(`${API_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Preserve remember_me setting
        const rememberMe = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN) !== null;
        tokenManager.setTokens(access_token, newRefreshToken, rememberMe);

        return access_token;
    } catch (error) {
        tokenManager.clearTokens();
        throw error;
    }
};

/**
 * Request interceptor: Add auth token and proactively refresh if needed
 */
apiClient.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
        const accessToken = tokenManager.getAccessToken();

        // Skip auth for login/register/refresh endpoints
        const publicEndpoints = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];
        const isPublicEndpoint = publicEndpoints.some((endpoint) =>
            config.url?.includes(endpoint)
        );

        if (isPublicEndpoint || !accessToken) {
            return config;
        }

        // Proactive token refresh: if token expires in <5 minutes, refresh it
        if (tokenManager.isTokenExpired(accessToken, 300)) {
            if (isRefreshing) {
                // Wait for ongoing refresh to complete
                return new Promise((resolve) => {
                    subscribeToRefresh((token) => {
                        config.headers.Authorization = `Bearer ${token}`;
                        resolve(config);
                    });
                });
            }

            isRefreshing = true;

            try {
                const newToken = await refreshAccessToken();
                isRefreshing = false;
                onRefreshComplete(newToken);
                config.headers.Authorization = `Bearer ${newToken}`;
            } catch (error) {
                isRefreshing = false;
                onRefreshComplete('');

                // Redirect to login on refresh failure
                window.location.href = '/login';
                return Promise.reject(error);
            }
        } else {
            config.headers.Authorization = `Bearer ${accessToken}`;
        }

        return config;
    },
    (error) => Promise.reject(error)
);

/**
 * Response interceptor: Handle errors globally
 */
apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized: Try to refresh token once
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const newToken = await refreshAccessToken();

                if (originalRequest.headers) {
                    originalRequest.headers.Authorization = `Bearer ${newToken}`;
                }

                return apiClient(originalRequest);
            } catch (refreshError) {
                // Refresh failed, clear tokens and redirect
                tokenManager.clearTokens();

                // Reset auth state by calling logout
                // Import dynamically to avoid circular dependency
                import('../stores/authStore').then(({ useAuthStore }) => {
                    useAuthStore.getState().logout();
                });

                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }

        // Handle 403 Forbidden: Show error message
        if (error.response?.status === 403) {
            const message = (error.response.data as { detail?: string })?.detail || 'You do not have permission to perform this action';

            // TODO: Show toast notification when uiStore is implemented
            console.error('Forbidden:', message);
        }

        // Handle 429 Too Many Requests: Exponential backoff
        if (error.response?.status === 429 && !originalRequest._retry) {
            originalRequest._retry = true;

            const retryAfter = parseInt(error.response.headers['retry-after'] || '5', 10);
            const delay = retryAfter * 1000;

            await new Promise((resolve) => setTimeout(resolve, delay));

            return apiClient(originalRequest);
        }

        return Promise.reject(error);
    }
);

/**
 * Export configured axios instance as default
 */
export default apiClient;

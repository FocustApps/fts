import { authApi, tokenManager, usersApi } from '@/api';
import type { components } from '@/types/api';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type User = components['schemas']['UserResponse'];
type CurrentAccountResponse = components['schemas']['CurrentAccountResponse'];

interface AccountRoleCache {
    [accountId: string]: string; // Maps account_id to role
}

interface AuthState {
    // User state
    user: User | null;
    currentAccount: CurrentAccountResponse | null;
    isAuthenticated: boolean;
    isInitialized: boolean;

    // Role caching
    accountRolesCache: AccountRoleCache;

    // Impersonation state
    isImpersonating: boolean;
    impersonatedBy: string | null;
    impersonationStartedAt: Date | null;

    // Actions
    initialize: () => Promise<void>;
    login: (email: string, password: string, rememberMe: boolean) => Promise<void>;
    logout: () => Promise<void>;
    getCurrentUser: () => Promise<void>;
    switchAccount: (accountId: string) => Promise<void>;
    refreshCurrentAccount: () => Promise<void>;

    // Role cache management
    cacheAccountRole: (accountId: string, role: string) => void;
    getCachedRole: (accountId: string) => string | undefined;
    clearRoleCache: () => void;

    // Impersonation
    setImpersonation: (impersonatedBy: string | null, startedAt: Date | null) => void;
    clearImpersonation: () => void;

    // Reset state
    reset: () => void;
}

const initialState = {
    user: null,
    currentAccount: null,
    isAuthenticated: false,
    isInitialized: false,
    accountRolesCache: {},
    isImpersonating: false,
    impersonatedBy: null,
    impersonationStartedAt: null,
};

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            ...initialState,

            initialize: async () => {
                // Check if we already initialized
                if (get().isInitialized) {
                    return;
                }

                // Check for valid access token
                const accessToken = tokenManager.getAccessToken();
                if (!accessToken || tokenManager.isTokenExpired(accessToken)) {
                    set({ isInitialized: true });
                    return;
                }

                try {
                    // Decode token to extract impersonation info
                    const payload = tokenManager.decodeToken(accessToken);

                    // Get full user details
                    const user = await authApi.getCurrentUser();

                    // Get current account details
                    const currentAccount = await usersApi.getCurrentAccount();

                    // Cache the current account role
                    if (currentAccount.account_id && currentAccount.role) {
                        get().cacheAccountRole(currentAccount.account_id, currentAccount.role);
                    }

                    // Check for impersonation state from token
                    const isImpersonating = payload?.is_impersonating || false;
                    const impersonatedBy = payload?.impersonated_by || null;

                    set({
                        isInitialized: true, user,
                        currentAccount,
                        isAuthenticated: true,
                        isInitialized: true,
                        isImpersonating,
                        impersonatedBy,
                        impersonationStartedAt: isImpersonating ? new Date() : null,
                    });
                } catch (error) {
                    // If initialization fails (e.g., 401), clear tokens and mark as initialized
                    console.error('Failed to initialize auth state:', error);
                    tokenManager.clearTokens();
                    set({ isInitialized: true });
                }
            },

            login: async (email: string, password: string, rememberMe: boolean) => {
                const response = await authApi.login({ email, password, remember_me: rememberMe });

                // Tokens are automatically stored by authApi.login

                // Decode token to extract user info and account context
                const payload = tokenManager.decodeToken(response.access_token);
                if (!payload) {
                    throw new Error('Invalid token received');
                }

                // Get full user details
                const user = await authApi.getCurrentUser();

                // Get current account details
                const currentAccount = await usersApi.getCurrentAccount();

                // Cache the current account role
                if (currentAccount.account_id && currentAccount.role) {
                    get().cacheAccountRole(currentAccount.account_id, currentAccount.role);
                }

                // Check for impersonation
                const isImpersonating = !!payload.impersonated_by;
                const impersonatedBy = payload.impersonated_by || null;
                const impersonationStartedAt = payload.impersonation_started_at
                    ? new Date(payload.impersonation_started_at)
                    : null;

                set({
                    user,
                    currentAccount,
                    isAuthenticated: true,
                    isImpersonating,
                    impersonatedBy,
                    impersonationStartedAt,
                });
            },

            logout: async () => {
                try {
                    await authApi.logout();
                } finally {
                    // Always clear state even if logout API fails
                    get().reset();
                }
            },

            getCurrentUser: async () => {
                const user = await authApi.getCurrentUser();
                set({ user });
            },

            switchAccount: async (accountId: string) => {
                await usersApi.switchAccount({ account_id: accountId });

                // After switching, get new token and current account
                const token = tokenManager.getAccessToken();
                if (!token) {
                    throw new Error('No token after account switch');
                }

                const payload = tokenManager.decodeToken(token);
                if (!payload) {
                    throw new Error('Invalid token after account switch');
                }

                const currentAccount = await usersApi.getCurrentAccount();

                // Cache the new account role
                if (currentAccount.account_id && currentAccount.role) {
                    get().cacheAccountRole(currentAccount.account_id, currentAccount.role);
                }

                // Update impersonation state from new token
                const isImpersonating = !!payload.impersonated_by;
                const impersonatedBy = payload.impersonated_by || null;
                const impersonationStartedAt = payload.impersonation_started_at
                    ? new Date(payload.impersonation_started_at)
                    : null;

                set({
                    currentAccount,
                    isImpersonating,
                    impersonatedBy,
                    impersonationStartedAt,
                });
            },

            refreshCurrentAccount: async () => {
                const currentAccount = await usersApi.getCurrentAccount();

                // Update cache
                if (currentAccount.account_id && currentAccount.role) {
                    get().cacheAccountRole(currentAccount.account_id, currentAccount.role);
                }

                set({ currentAccount });
            },

            cacheAccountRole: (accountId: string, role: string) => {
                set((state) => ({
                    accountRolesCache: {
                        ...state.accountRolesCache,
                        [accountId]: role,
                    },
                }));
            },

            getCachedRole: (accountId: string) => {
                return get().accountRolesCache[accountId];
            },

            clearRoleCache: () => {
                set({ accountRolesCache: {} });
            },

            setImpersonation: (impersonatedBy: string | null, startedAt: Date | null) => {
                set({
                    isImpersonating: !!impersonatedBy,
                    impersonatedBy,
                    impersonationStartedAt: startedAt,
                });
            },

            clearImpersonation: () => {
                set({
                    isImpersonating: false,
                    impersonatedBy: null,
                    impersonationStartedAt: null,
                });
            },

            reset: () => {
                set(initialState);
                get().clearRoleCache();
            },
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                accountRolesCache: state.accountRolesCache,
                // Don't persist sensitive user data - only the role cache
            }),
        }
    )
);

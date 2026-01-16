import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
    id: string;
    type: ToastType;
    title: string;
    message?: string;
    duration?: number; // milliseconds, 0 = don't auto-dismiss
}

export interface Modal {
    id: string;
    title: string;
    content: React.ReactNode;
    onClose?: () => void;
    onConfirm?: () => void;
    confirmText?: string;
    cancelText?: string;
}

export interface Banner {
    id: string;
    type: ToastType;
    message: string;
    dismissible?: boolean;
    action?: {
        label: string;
        onClick: () => void;
    };
}

interface UIState {
    // Toast management
    toasts: Toast[];
    addToast: (toast: Omit<Toast, 'id'>) => string;
    removeToast: (id: string) => void;
    clearToasts: () => void;

    // Modal management
    modals: Modal[];
    openModal: (modal: Omit<Modal, 'id'>) => string;
    closeModal: (id: string) => void;
    closeAllModals: () => void;

    // Banner management (persistent notifications at top of app)
    banners: Banner[];
    addBanner: (banner: Omit<Banner, 'id'>) => string;
    removeBanner: (id: string) => void;
    clearBanners: () => void;

    // Loading states
    isLoading: boolean;
    setLoading: (loading: boolean) => void;

    // Sidebar state (for mobile)
    isSidebarOpen: boolean;
    toggleSidebar: () => void;
    setSidebarOpen: (open: boolean) => void;
}

let toastIdCounter = 0;
let modalIdCounter = 0;
let bannerIdCounter = 0;

export const useUIStore = create<UIState>((set, get) => ({
    // Toasts
    toasts: [],

    addToast: (toast) => {
        const id = `toast-${++toastIdCounter}`;
        const newToast: Toast = {
            id,
            duration: toast.duration ?? 5000, // Default 5 seconds
            ...toast,
        };

        set((state) => ({
            toasts: [...state.toasts, newToast],
        }));

        // Auto-dismiss if duration > 0
        if (newToast.duration && newToast.duration > 0) {
            setTimeout(() => {
                get().removeToast(id);
            }, newToast.duration);
        }

        return id;
    },

    removeToast: (id) => {
        set((state) => ({
            toasts: state.toasts.filter((toast) => toast.id !== id),
        }));
    },

    clearToasts: () => {
        set({ toasts: [] });
    },

    // Modals
    modals: [],

    openModal: (modal) => {
        const id = `modal-${++modalIdCounter}`;
        const newModal: Modal = { id, ...modal };

        set((state) => ({
            modals: [...state.modals, newModal],
        }));

        return id;
    },

    closeModal: (id) => {
        set((state) => ({
            modals: state.modals.filter((modal) => modal.id !== id),
        }));
    },

    closeAllModals: () => {
        set({ modals: [] });
    },

    // Banners
    banners: [],

    addBanner: (banner) => {
        const id = `banner-${++bannerIdCounter}`;
        const newBanner: Banner = { id, dismissible: true, ...banner };

        set((state) => ({
            banners: [...state.banners, newBanner],
        }));

        return id;
    },

    removeBanner: (id) => {
        set((state) => ({
            banners: state.banners.filter((banner) => banner.id !== id),
        }));
    },

    clearBanners: () => {
        set({ banners: [] });
    },

    // Loading
    isLoading: false,

    setLoading: (loading) => {
        set({ isLoading: loading });
    },

    // Sidebar
    isSidebarOpen: false,

    toggleSidebar: () => {
        set((state) => ({ isSidebarOpen: !state.isSidebarOpen }));
    },

    setSidebarOpen: (open) => {
        set({ isSidebarOpen: open });
    },
}));

// Helper functions for common toast patterns
export const toast = {
    success: (title: string, message?: string) => {
        return useUIStore.getState().addToast({ type: 'success', title, message });
    },
    error: (title: string, message?: string) => {
        return useUIStore.getState().addToast({ type: 'error', title, message, duration: 7000 });
    },
    warning: (title: string, message?: string) => {
        return useUIStore.getState().addToast({ type: 'warning', title, message });
    },
    info: (title: string, message?: string) => {
        return useUIStore.getState().addToast({ type: 'info', title, message });
    },
};

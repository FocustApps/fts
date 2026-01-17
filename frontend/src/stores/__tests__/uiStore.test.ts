import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast, useUIStore } from '../uiStore';

describe('uiStore', () => {
    beforeEach(() => {
        // Reset store to initial state
        const store = useUIStore.getState();
        store.clearToasts();
        store.closeAllModals();
        store.clearBanners();
        store.setLoading(false);
        store.setSidebarOpen(false);
    });

    describe('Toast Management', () => {
        it('should add a toast with default duration', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addToast({
                    type: 'success',
                    title: 'Test Toast',
                    message: 'This is a test',
                });
            });

            expect(result.current.toasts).toHaveLength(1);
            expect(result.current.toasts[0].title).toBe('Test Toast');
            expect(result.current.toasts[0].type).toBe('success');
            expect(result.current.toasts[0].duration).toBe(5000);
        });

        it('should add a toast with custom duration', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addToast({
                    type: 'error',
                    title: 'Error',
                    duration: 10000,
                });
            });

            expect(result.current.toasts[0].duration).toBe(10000);
        });

        it('should generate unique IDs for toasts', () => {
            const { result } = renderHook(() => useUIStore());

            let id1: string, id2: string;

            act(() => {
                id1 = result.current.addToast({ type: 'info', title: 'First' });
                id2 = result.current.addToast({ type: 'info', title: 'Second' });
            });

            expect(id1).not.toBe(id2);
            expect(result.current.toasts).toHaveLength(2);
        });

        it('should auto-dismiss toast after duration', async () => {
            vi.useFakeTimers();
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addToast({
                    type: 'success',
                    title: 'Auto-dismiss',
                    duration: 1000,
                });
            });

            expect(result.current.toasts).toHaveLength(1);

            act(() => {
                vi.advanceTimersByTime(1000);
            });

            expect(result.current.toasts).toHaveLength(0);

            vi.useRealTimers();
        });

        it('should not auto-dismiss toast with duration 0', async () => {
            vi.useFakeTimers();
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addToast({
                    type: 'warning',
                    title: 'Persistent',
                    duration: 0,
                });
            });

            expect(result.current.toasts).toHaveLength(1);

            act(() => {
                vi.advanceTimersByTime(10000);
            });

            expect(result.current.toasts).toHaveLength(1);

            vi.useRealTimers();
        });

        it('should remove specific toast by ID', () => {
            const { result } = renderHook(() => useUIStore());

            let id1: string, id2: string;

            act(() => {
                id1 = result.current.addToast({ type: 'info', title: 'First' });
                id2 = result.current.addToast({ type: 'info', title: 'Second' });
            });

            expect(result.current.toasts).toHaveLength(2);

            act(() => {
                result.current.removeToast(id1);
            });

            expect(result.current.toasts).toHaveLength(1);
            expect(result.current.toasts[0].id).toBe(id2);
        });

        it('should clear all toasts', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addToast({ type: 'info', title: 'First' });
                result.current.addToast({ type: 'info', title: 'Second' });
                result.current.addToast({ type: 'info', title: 'Third' });
            });

            expect(result.current.toasts).toHaveLength(3);

            act(() => {
                result.current.clearToasts();
            });

            expect(result.current.toasts).toHaveLength(0);
        });
    });

    describe('Toast Helper Functions', () => {
        it('should create success toast with helper', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                toast.success('Success!', 'Operation completed');
            });

            expect(result.current.toasts).toHaveLength(1);
            expect(result.current.toasts[0].type).toBe('success');
            expect(result.current.toasts[0].title).toBe('Success!');
            expect(result.current.toasts[0].message).toBe('Operation completed');
            expect(result.current.toasts[0].duration).toBe(5000);
        });

        it('should create error toast with helper and longer duration', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                toast.error('Error!', 'Something went wrong');
            });

            expect(result.current.toasts).toHaveLength(1);
            expect(result.current.toasts[0].type).toBe('error');
            expect(result.current.toasts[0].duration).toBe(7000);
        });

        it('should create warning toast with helper', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                toast.warning('Warning!');
            });

            expect(result.current.toasts).toHaveLength(1);
            expect(result.current.toasts[0].type).toBe('warning');
        });

        it('should create info toast with helper', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                toast.info('Info');
            });

            expect(result.current.toasts).toHaveLength(1);
            expect(result.current.toasts[0].type).toBe('info');
        });
    });

    describe('Modal Management', () => {
        it('should open a modal', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.openModal({
                    title: 'Test Modal',
                    content: 'Modal content',
                });
            });

            expect(result.current.modals).toHaveLength(1);
            expect(result.current.modals[0].title).toBe('Test Modal');
        });

        it('should support multiple modals (stacking)', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.openModal({ title: 'First', content: 'Content 1' });
                result.current.openModal({ title: 'Second', content: 'Content 2' });
            });

            expect(result.current.modals).toHaveLength(2);
        });

        it('should generate unique IDs for modals', () => {
            const { result } = renderHook(() => useUIStore());

            let id1: string, id2: string;

            act(() => {
                id1 = result.current.openModal({ title: 'First', content: 'Content' });
                id2 = result.current.openModal({ title: 'Second', content: 'Content' });
            });

            expect(id1).not.toBe(id2);
        });

        it('should close specific modal by ID', () => {
            const { result } = renderHook(() => useUIStore());

            let id1: string, id2: string;

            act(() => {
                id1 = result.current.openModal({ title: 'First', content: 'Content' });
                id2 = result.current.openModal({ title: 'Second', content: 'Content' });
            });

            expect(result.current.modals).toHaveLength(2);

            act(() => {
                result.current.closeModal(id1);
            });

            expect(result.current.modals).toHaveLength(1);
            expect(result.current.modals[0].id).toBe(id2);
        });

        it('should close all modals', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.openModal({ title: 'First', content: 'Content' });
                result.current.openModal({ title: 'Second', content: 'Content' });
            });

            expect(result.current.modals).toHaveLength(2);

            act(() => {
                result.current.closeAllModals();
            });

            expect(result.current.modals).toHaveLength(0);
        });

        it('should support custom buttons and callbacks', () => {
            const { result } = renderHook(() => useUIStore());
            const onClose = vi.fn();
            const onConfirm = vi.fn();

            act(() => {
                result.current.openModal({
                    title: 'Confirm',
                    content: 'Are you sure?',
                    onClose,
                    onConfirm,
                    confirmText: 'Yes',
                    cancelText: 'No',
                });
            });

            expect(result.current.modals[0].onClose).toBe(onClose);
            expect(result.current.modals[0].onConfirm).toBe(onConfirm);
            expect(result.current.modals[0].confirmText).toBe('Yes');
            expect(result.current.modals[0].cancelText).toBe('No');
        });
    });

    describe('Banner Management', () => {
        it('should add a banner with default dismissible', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addBanner({
                    type: 'info',
                    message: 'Important announcement',
                });
            });

            expect(result.current.banners).toHaveLength(1);
            expect(result.current.banners[0].message).toBe('Important announcement');
            expect(result.current.banners[0].dismissible).toBe(true);
        });

        it('should support non-dismissible banners', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addBanner({
                    type: 'warning',
                    message: 'Maintenance mode',
                    dismissible: false,
                });
            });

            expect(result.current.banners[0].dismissible).toBe(false);
        });

        it('should support banner actions', () => {
            const { result } = renderHook(() => useUIStore());
            const onClick = vi.fn();

            act(() => {
                result.current.addBanner({
                    type: 'info',
                    message: 'Update available',
                    action: {
                        label: 'Update Now',
                        onClick,
                    },
                });
            });

            expect(result.current.banners[0].action).toBeDefined();
            expect(result.current.banners[0].action?.label).toBe('Update Now');
        });

        it('should remove specific banner by ID', () => {
            const { result } = renderHook(() => useUIStore());

            let id1: string, id2: string;

            act(() => {
                id1 = result.current.addBanner({ type: 'info', message: 'First' });
                id2 = result.current.addBanner({ type: 'info', message: 'Second' });
            });

            expect(result.current.banners).toHaveLength(2);

            act(() => {
                result.current.removeBanner(id1);
            });

            expect(result.current.banners).toHaveLength(1);
            expect(result.current.banners[0].id).toBe(id2);
        });

        it('should clear all banners', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.addBanner({ type: 'info', message: 'First' });
                result.current.addBanner({ type: 'info', message: 'Second' });
            });

            expect(result.current.banners).toHaveLength(2);

            act(() => {
                result.current.clearBanners();
            });

            expect(result.current.banners).toHaveLength(0);
        });
    });

    describe('Loading State', () => {
        it('should set loading state', () => {
            const { result } = renderHook(() => useUIStore());

            expect(result.current.isLoading).toBe(false);

            act(() => {
                result.current.setLoading(true);
            });

            expect(result.current.isLoading).toBe(true);

            act(() => {
                result.current.setLoading(false);
            });

            expect(result.current.isLoading).toBe(false);
        });
    });

    describe('Sidebar State', () => {
        it('should toggle sidebar', () => {
            const { result } = renderHook(() => useUIStore());

            expect(result.current.isSidebarOpen).toBe(false);

            act(() => {
                result.current.toggleSidebar();
            });

            expect(result.current.isSidebarOpen).toBe(true);

            act(() => {
                result.current.toggleSidebar();
            });

            expect(result.current.isSidebarOpen).toBe(false);
        });

        it('should set sidebar open state directly', () => {
            const { result } = renderHook(() => useUIStore());

            act(() => {
                result.current.setSidebarOpen(true);
            });

            expect(result.current.isSidebarOpen).toBe(true);

            act(() => {
                result.current.setSidebarOpen(false);
            });

            expect(result.current.isSidebarOpen).toBe(false);
        });
    });
});

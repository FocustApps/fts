import { renderWithProviders } from '@/test/utils';
import { screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DeleteConfirmationModal } from '../DeleteConfirmationModal';

describe('DeleteConfirmationModal', () => {
    const mockOnClose = vi.fn();
    const mockOnConfirm = vi.fn();

    const defaultProps = {
        isOpen: true,
        onClose: mockOnClose,
        onConfirm: mockOnConfirm,
        title: 'Delete Item',
        description: 'Are you sure you want to delete this item?',
        confirmText: 'Delete',
        itemName: 'Test Item',
        isPending: false,
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should not render when isOpen is false', () => {
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} isOpen={false} />);

        expect(screen.queryByText('Delete Item')).not.toBeInTheDocument();
    });

    it('should render modal when isOpen is true', () => {
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        expect(screen.getByText('Delete Item')).toBeInTheDocument();
        expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument();
        expect(screen.getByText('Test Item')).toBeInTheDocument();
    });

    it('should display warning message', () => {
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        expect(screen.getByText(/Warning:/)).toBeInTheDocument();
        expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument();
    });

    it('should call onClose when cancel button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        const cancelButton = screen.getByText('Cancel');
        await user.click(cancelButton);

        expect(mockOnClose).toHaveBeenCalledTimes(1);
        expect(mockOnConfirm).not.toHaveBeenCalled();
    });

    it('should call onConfirm when confirm button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        const confirmButton = screen.getByText('Delete');
        await user.click(confirmButton);

        expect(mockOnConfirm).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when X button clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        const closeButton = screen.getByRole('button', { name: '' }); // X button
        await user.click(closeButton);

        expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when backdrop clicked', async () => {
        const user = userEvent.setup();
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        const backdrop = document.querySelector('.bg-black');
        expect(backdrop).toBeInTheDocument();

        if (backdrop) {
            await user.click(backdrop);
            expect(mockOnClose).toHaveBeenCalledTimes(1);
        }
    });

    it('should disable buttons when isPending is true', () => {
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} isPending={true} />);

        const cancelButton = screen.getByText('Cancel');
        const confirmButton = screen.getByText('Deleting...');

        expect(cancelButton).toBeDisabled();
        expect(confirmButton).toBeDisabled();
    });

    it('should show loading text when isPending is true', () => {
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} isPending={true} />);

        expect(screen.getByText('Deleting...')).toBeInTheDocument();
    });

    it('should show custom confirm text', () => {
        renderWithProviders(
            <DeleteConfirmationModal {...defaultProps} confirmText="Remove Forever" />
        );

        expect(screen.getByText('Remove Forever')).toBeInTheDocument();
    });

    it('should work without itemName prop', () => {
        const propsWithoutItem = { ...defaultProps };
        delete propsWithoutItem.itemName;

        renderWithProviders(<DeleteConfirmationModal {...propsWithoutItem} />);

        expect(screen.getByText('Delete Item')).toBeInTheDocument();
        expect(screen.queryByText('Test Item')).not.toBeInTheDocument();
    });

    it('should prevent closing during deletion', async () => {
        const user = userEvent.setup();
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} isPending={true} />);

        const backdrop = document.querySelector('.bg-black');
        if (backdrop) {
            await user.click(backdrop);
            expect(mockOnClose).not.toHaveBeenCalled();
        }
    });

    it('should show alert triangle icon', () => {
        renderWithProviders(<DeleteConfirmationModal {...defaultProps} />);

        // Check for red background circle with icon
        const iconContainer = document.querySelector('.bg-red-100');
        expect(iconContainer).toBeInTheDocument();
    });
});

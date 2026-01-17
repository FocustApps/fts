import { accountsApi } from '@/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Shield, X } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

interface BulkUpdateRolesModalProps {
    accountId: string;
    accountName: string;
    selectedUserIds: string[];
    users: Array<{ user_id: string; email: string; username: string; role: string }>;
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function BulkUpdateRolesModal({
    accountId,
    accountName,
    selectedUserIds,
    users,
    isOpen,
    onClose,
    onSuccess,
}: BulkUpdateRolesModalProps) {
    const queryClient = useQueryClient();
    const [newRole, setNewRole] = useState<'admin' | 'member' | 'viewer'>('member');

    const selectedUsers = users.filter((u) => selectedUserIds.includes(u.user_id));
    const hasOwners = selectedUsers.some((u) => u.role === 'owner');

    const updateRolesMutation = useMutation({
        mutationFn: async (role: string) => {
            const results = [];
            for (const userId of selectedUserIds) {
                const user = users.find((u) => u.user_id === userId);

                // Skip owners - they can't have their role changed
                if (user?.role === 'owner') {
                    results.push({ userId, success: false, error: 'Cannot change owner role' });
                    continue;
                }

                try {
                    const result = await accountsApi.updateUserRole(accountId, userId, { role });
                    results.push({ userId, success: true, result });
                } catch (error) {
                    results.push({ userId, success: false, error });
                }
            }
            return results;
        },
        onSuccess: (results) => {
            const successCount = results.filter((r) => r.success).length;
            const failCount = results.length - successCount;

            queryClient.invalidateQueries({ queryKey: ['account', accountId, 'users'] });

            if (failCount === 0) {
                toast.success(`Successfully updated ${successCount} user role${successCount > 1 ? 's' : ''}`);
                onSuccess();
                onClose();
            } else {
                toast.warning(`Updated ${successCount} roles, ${failCount} failed`);
            }
        },
        onError: (error) => {
            toast.error('Failed to update roles');
            console.error('Bulk update roles error:', error);
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateRolesMutation.mutate(newRole);
    };

    const handleClose = () => {
        if (updateRolesMutation.isPending) return;
        setNewRole('member');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
                onClick={handleClose}
            />

            {/* Modal */}
            <div className="flex min-h-full items-center justify-center p-4">
                <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full">
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-gray-200">
                        <div>
                            <h2 className="text-xl font-semibold text-gray-900">Update User Roles</h2>
                            <p className="text-sm text-gray-500 mt-1">{accountName}</p>
                        </div>
                        <button
                            onClick={handleClose}
                            disabled={updateRolesMutation.isPending}
                            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>

                    {/* Body */}
                    <form onSubmit={handleSubmit}>
                        <div className="p-6 space-y-4">
                            {hasOwners && (
                                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start">
                                    <AlertCircle className="h-5 w-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
                                    <div className="text-sm text-yellow-800">
                                        <p className="font-medium">Account owners detected</p>
                                        <p className="mt-1">
                                            Owner roles cannot be changed. These users will be skipped.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Selected Users Summary */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Selected Users ({selectedUserIds.length})
                                </label>
                                <div className="border border-gray-200 rounded-lg p-3 max-h-40 overflow-y-auto bg-gray-50">
                                    <ul className="space-y-1">
                                        {selectedUsers.map((user) => (
                                            <li
                                                key={user.user_id}
                                                className="text-sm text-gray-700 flex items-center justify-between"
                                            >
                                                <span>
                                                    {user.email}
                                                    {user.role === 'owner' && (
                                                        <span className="ml-2 text-xs text-yellow-600">(owner - will be skipped)</span>
                                                    )}
                                                </span>
                                                <span className="text-xs text-gray-500 capitalize">{user.role}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            {/* New Role Selection */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    New Role *
                                </label>
                                <select
                                    value={newRole}
                                    onChange={(e) => setNewRole(e.target.value as 'admin' | 'member' | 'viewer')}
                                    disabled={updateRolesMutation.isPending}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100"
                                >
                                    <option value="admin">Admin - Can manage users and settings</option>
                                    <option value="member">Member - Can view and edit content</option>
                                    <option value="viewer">Viewer - Read-only access</option>
                                </select>
                                <p className="mt-2 text-xs text-gray-500">
                                    This role will be applied to all selected users (except owners).
                                </p>
                            </div>

                            {/* Role Descriptions */}
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-blue-900 mb-2">Role Permissions</h4>
                                <ul className="space-y-1 text-xs text-blue-800">
                                    <li><strong>Admin:</strong> Full access except account deletion</li>
                                    <li><strong>Member:</strong> Can create and manage their own resources</li>
                                    <li><strong>Viewer:</strong> Can only view existing resources</li>
                                    <li><strong>Owner:</strong> Full control including account deletion (cannot be changed)</li>
                                </ul>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
                            <button
                                type="button"
                                onClick={handleClose}
                                disabled={updateRolesMutation.isPending}
                                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={updateRolesMutation.isPending}
                                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {updateRolesMutation.isPending ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                                        Updating...
                                    </>
                                ) : (
                                    <>
                                        <Shield className="h-4 w-4 mr-2" />
                                        Update Roles
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

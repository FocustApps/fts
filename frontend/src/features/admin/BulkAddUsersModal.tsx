import { accountsApi } from '@/api';
import { cn } from '@/lib/utils';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, UserPlus, X } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

interface BulkAddUsersModalProps {
    accountId: string;
    accountName: string;
    isOpen: boolean;
    onClose: () => void;
}

interface UserToAdd {
    email: string;
    role: 'admin' | 'member' | 'viewer';
    isPrimary: boolean;
}

export function BulkAddUsersModal({
    accountId,
    accountName,
    isOpen,
    onClose,
}: BulkAddUsersModalProps) {
    const queryClient = useQueryClient();
    const [users, setUsers] = useState<UserToAdd[]>([{ email: '', role: 'member', isPrimary: false }]);
    const [errors, setErrors] = useState<Record<number, string>>({});

    const addUsersMutation = useMutation({
        mutationFn: async (usersToAdd: UserToAdd[]) => {
            const results = [];
            for (const user of usersToAdd) {
                try {
                    // For now, we'll need to look up the user_id by email
                    // In a real implementation, the backend should handle email lookup
                    const result = await accountsApi.addUser(accountId, {
                        auth_user_id: user.email, // TODO: Backend should accept email and lookup user_id
                        role: user.role,
                    });
                    results.push({ email: user.email, success: true, result });
                } catch (error) {
                    results.push({ email: user.email, success: false, error });
                }
            }
            return results;
        },
        onSuccess: (results) => {
            const successCount = results.filter((r) => r.success).length;
            const failCount = results.length - successCount;

            queryClient.invalidateQueries({ queryKey: ['account', accountId, 'users'] });

            if (failCount === 0) {
                toast.success(`Successfully added ${successCount} user${successCount > 1 ? 's' : ''}`);
                onClose();
                resetForm();
            } else {
                toast.warning(`Added ${successCount} users, ${failCount} failed`);
            }
        },
        onError: (error) => {
            toast.error('Failed to add users');
            console.error('Bulk add users error:', error);
        },
    });

    const addUserRow = () => {
        setUsers([...users, { email: '', role: 'member', isPrimary: false }]);
    };

    const removeUserRow = (index: number) => {
        if (users.length === 1) return; // Keep at least one row
        const newUsers = users.filter((_, i) => i !== index);
        setUsers(newUsers);

        // Clear error for removed row
        const newErrors = { ...errors };
        delete newErrors[index];
        setErrors(newErrors);
    };

    const updateUser = (index: number, field: keyof UserToAdd, value: string | boolean) => {
        const newUsers = [...users];
        newUsers[index] = { ...newUsers[index], [field]: value };
        setUsers(newUsers);

        // Clear error when user makes changes
        if (errors[index]) {
            const newErrors = { ...errors };
            delete newErrors[index];
            setErrors(newErrors);
        }
    };

    const validateForm = (): boolean => {
        const newErrors: Record<number, string> = {};
        let isValid = true;

        users.forEach((user, index) => {
            if (!user.email.trim()) {
                newErrors[index] = 'Email is required';
                isValid = false;
            } else if (!isValidEmail(user.email)) {
                newErrors[index] = 'Invalid email format';
                isValid = false;
            }
        });

        setErrors(newErrors);
        return isValid;
    };

    const isValidEmail = (email: string): boolean => {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) {
            toast.error('Please fix validation errors');
            return;
        }

        // Filter out empty rows
        const validUsers = users.filter((u) => u.email.trim());

        if (validUsers.length === 0) {
            toast.error('Please add at least one user');
            return;
        }

        addUsersMutation.mutate(validUsers);
    };

    const resetForm = () => {
        setUsers([{ email: '', role: 'member', isPrimary: false }]);
        setErrors({});
    };

    const handleClose = () => {
        if (addUsersMutation.isPending) return; // Prevent closing during submission
        resetForm();
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
                <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-gray-200">
                        <div>
                            <h2 className="text-xl font-semibold text-gray-900">Add Users to Account</h2>
                            <p className="text-sm text-gray-500 mt-1">{accountName}</p>
                        </div>
                        <button
                            onClick={handleClose}
                            disabled={addUsersMutation.isPending}
                            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>

                    {/* Body */}
                    <form onSubmit={handleSubmit} className="flex flex-col max-h-[calc(90vh-140px)]">
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start">
                                <AlertCircle className="h-5 w-5 text-blue-600 mr-3 flex-shrink-0 mt-0.5" />
                                <div className="text-sm text-blue-800">
                                    <p className="font-medium">Note: Email-based user lookup</p>
                                    <p className="mt-1">
                                        Users must already exist in the system. Enter their registered email addresses.
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-4">
                                {users.map((user, index) => (
                                    <div
                                        key={index}
                                        className={cn(
                                            'border rounded-lg p-4',
                                            errors[index] ? 'border-red-300 bg-red-50' : 'border-gray-200'
                                        )}
                                    >
                                        <div className="flex items-start gap-4">
                                            {/* Email */}
                                            <div className="flex-1">
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Email Address *
                                                </label>
                                                <input
                                                    type="email"
                                                    value={user.email}
                                                    onChange={(e) => updateUser(index, 'email', e.target.value)}
                                                    placeholder="user@example.com"
                                                    disabled={addUsersMutation.isPending}
                                                    className={cn(
                                                        'w-full px-3 py-2 border rounded-md shadow-sm focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100',
                                                        errors[index] ? 'border-red-300' : 'border-gray-300'
                                                    )}
                                                />
                                                {errors[index] && (
                                                    <p className="text-xs text-red-600 mt-1">{errors[index]}</p>
                                                )}
                                            </div>

                                            {/* Role */}
                                            <div className="w-40">
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Role *
                                                </label>
                                                <select
                                                    value={user.role}
                                                    onChange={(e) => updateUser(index, 'role', e.target.value)}
                                                    disabled={addUsersMutation.isPending}
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100"
                                                >
                                                    <option value="admin">Admin</option>
                                                    <option value="member">Member</option>
                                                    <option value="viewer">Viewer</option>
                                                </select>
                                            </div>

                                            {/* Remove Button */}
                                            <div className="pt-7">
                                                <button
                                                    type="button"
                                                    onClick={() => removeUserRow(index)}
                                                    disabled={users.length === 1 || addUsersMutation.isPending}
                                                    className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                                    title="Remove user"
                                                >
                                                    <X className="h-5 w-5" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Add More Button */}
                            <button
                                type="button"
                                onClick={addUserRow}
                                disabled={addUsersMutation.isPending}
                                className="mt-4 inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                <UserPlus className="h-4 w-4 mr-2" />
                                Add Another User
                            </button>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
                            <div className="text-sm text-gray-600">
                                {users.filter((u) => u.email.trim()).length} user(s) to add
                            </div>
                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    disabled={addUsersMutation.isPending}
                                    className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={addUsersMutation.isPending}
                                    className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    {addUsersMutation.isPending ? (
                                        <>
                                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                                            Adding Users...
                                        </>
                                    ) : (
                                        <>
                                            <UserPlus className="h-4 w-4 mr-2" />
                                            Add Users
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

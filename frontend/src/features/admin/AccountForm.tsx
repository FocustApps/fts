import { accountsApi, usersApi } from '@/api';
import { useAuthStore } from '@/stores';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Save, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

interface AccountFormData {
    account_name: string;
    owner_user_id: string;
}

export function AccountForm() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { user } = useAuthStore();

    const isEdit = id !== 'new' && !!id;

    // Fetch users for owner dropdown
    const { data: users = [], isLoading: isLoadingUsers } = useQuery({
        queryKey: ['users'],
        queryFn: () => usersApi.list({ include_inactive: false }),
    });

    // Fetch account data for edit mode
    const { data: accounts } = useQuery({
        queryKey: ['admin', 'accounts'],
        queryFn: () => accountsApi.listAll(),
        enabled: isEdit,
    });

    const account = accounts?.find(a => a.account_id === id);

    const [formData, setFormData] = useState<AccountFormData>(() => ({
        account_name: account?.account_name || '',
        owner_user_id: account?.owner_user_id || user?.auth_user_id || '',
    }));
    const [errors, setErrors] = useState<Record<string, string>>({});

    // Update form when account data loads
    useEffect(() => {
        if (account && isEdit) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setFormData({
                account_name: account.account_name || '',
                owner_user_id: account.owner_user_id,
            });
        }
    }, [account, isEdit]);

    // Create mutation
    const createMutation = useMutation({
        mutationFn: (data: AccountFormData) => accountsApi.create(data),
        onSuccess: (newAccount) => {
            queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] });
            toast.success('Account created successfully');
            navigate(`/admin/accounts/${newAccount.account_id}`);
        },
        onError: (error: Error) => {
            toast.error(`Failed to create account: ${error.message}`);
        },
    });

    // Update mutation
    const updateMutation = useMutation({
        mutationFn: (data: AccountFormData) => accountsApi.update(id!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] });
            queryClient.invalidateQueries({ queryKey: ['admin', 'accounts', id] });
            toast.success('Account updated successfully');
            navigate(`/admin/accounts/${id}`);
        },
        onError: (error: Error) => {
            toast.error(`Failed to update account: ${error.message}`);
        },
    });

    const validate = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (!formData.account_name.trim()) {
            newErrors.account_name = 'Account name is required';
        } else if (formData.account_name.length < 3) {
            newErrors.account_name = 'Account name must be at least 3 characters';
        }

        if (!formData.owner_user_id.trim()) {
            newErrors.owner_user_id = 'Owner is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (!validate()) {
            return;
        }

        if (isEdit) {
            updateMutation.mutate(formData);
        } else {
            createMutation.mutate(formData);
        }
    };

    const handleCancel = () => {
        navigate('/admin/accounts');
    };

    const isSubmitting = createMutation.isPending || updateMutation.isPending;

    return (
        <div className="max-w-2xl mx-auto p-6">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">
                    {isEdit ? 'Edit Account' : 'Create Account'}
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                    {isEdit
                        ? 'Update account information'
                        : 'Create a new account for your organization'}
                </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6">
                {/* Account Name */}
                <div className="mb-6">
                    <label
                        htmlFor="account_name"
                        className="block text-sm font-medium text-gray-700 mb-2"
                    >
                        Account Name <span className="text-red-500">*</span>
                    </label>
                    <input
                        id="account_name"
                        type="text"
                        value={formData.account_name}
                        onChange={(e) =>
                            setFormData({ ...formData, account_name: e.target.value })
                        }
                        className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${errors.account_name ? 'border-red-500' : 'border-gray-300'
                            }`}
                        placeholder="Enter account name"
                        disabled={isSubmitting}
                    />
                    {errors.account_name && (
                        <div className="mt-2 flex items-center text-sm text-red-600">
                            <AlertCircle className="h-4 w-4 mr-1" />
                            {errors.account_name}
                        </div>
                    )}
                </div>

                {/* Owner User ID */}
                <div className="mb-6">
                    <label
                        htmlFor="owner_user_id"
                        className="block text-sm font-medium text-gray-700 mb-2"
                    >
                        Account Owner <span className="text-red-500">*</span>
                    </label>
                    {isLoadingUsers ? (
                        <div className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-500 bg-gray-50">
                            Loading users...
                        </div>
                    ) : (
                        <select
                            id="owner_user_id"
                            value={formData.owner_user_id}
                            onChange={(e) =>
                                setFormData({ ...formData, owner_user_id: e.target.value })
                            }
                            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${errors.owner_user_id ? 'border-red-500' : 'border-gray-300'
                                } ${(isSubmitting || isEdit) ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                            disabled={isSubmitting || isEdit} // Can't change owner in edit mode
                        >
                            <option value="">Select an owner</option>
                            {users.map((user) => (
                                <option key={user.user_id} value={user.user_id}>
                                    {user.email}
                                </option>
                            ))}
                        </select>
                    )}
                    {errors.owner_user_id && (
                        <div className="mt-2 flex items-center text-sm text-red-600">
                            <AlertCircle className="h-4 w-4 mr-1" />
                            {errors.owner_user_id}
                        </div>
                    )}
                    {isEdit && (
                        <p className="mt-2 text-sm text-gray-500">
                            Owner cannot be changed after account creation
                        </p>
                    )}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end space-x-3 pt-6 border-t border-gray-200">
                    <button
                        type="button"
                        onClick={handleCancel}
                        disabled={isSubmitting}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <X className="h-4 w-4 inline-block mr-2" />
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                    >
                        <Save className="h-4 w-4 mr-2" />
                        {isSubmitting
                            ? 'Saving...'
                            : isEdit
                                ? 'Update Account'
                                : 'Create Account'}
                    </button>
                </div>
            </form>
        </div>
    );
}

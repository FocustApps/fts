import { accountsApi } from '@/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Edit, Trash2, Users } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { DeleteConfirmationModal } from './DeleteConfirmationModal';

interface TabProps {
    label: string;
    value: string;
    isActive: boolean;
    onClick: () => void;
}

function Tab({ label, value, isActive, onClick }: TabProps) {
    return (
        <button
            onClick={onClick}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            aria-selected={isActive}
            role="tab"
            aria-controls={`${value}-panel`}
        >
            {label}
        </button>
    );
}

export function AccountDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<'info' | 'users' | 'audit'>('info');
    const [showDeleteModal, setShowDeleteModal] = useState(false);

    const {
        data: account,
        isLoading,
        error,
    } = useQuery({
        queryKey: ['account', id],
        queryFn: () => accountsApi.getById(id!),
        enabled: !!id,
    });

    const deleteAccountMutation = useMutation({
        mutationFn: () => accountsApi.deactivate(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] });
            toast.success('Account deleted successfully');
            navigate('/admin/accounts');
        },
        onError: (error) => {
            toast.error('Failed to delete account');
            console.error('Delete account error:', error);
        },
    });

    const handleDeleteClick = () => {
        setShowDeleteModal(true);
    };

    const confirmDelete = () => {
        deleteAccountMutation.mutate();
    };

    if (isLoading) {
        return (
            <div className="p-8">
                <div className="mb-6">
                    <div className="h-8 w-32 bg-gray-200 rounded animate-pulse mb-2"></div>
                    <div className="h-6 w-64 bg-gray-200 rounded animate-pulse"></div>
                </div>
                <div className="h-96 bg-gray-200 rounded animate-pulse"></div>
            </div>
        );
    }

    if (error || !account) {
        return (
            <div className="p-8">
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                    <h2 className="text-lg font-semibold text-destructive mb-2">Error Loading Account</h2>
                    <p className="text-sm text-destructive/80">
                        {error instanceof Error ? error.message : 'Account not found'}
                    </p>
                    <button
                        onClick={() => navigate('/admin/accounts')}
                        className="mt-4 text-sm text-primary hover:underline"
                    >
                        ← Back to Accounts
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8">
            {/* Header */}
            <div className="mb-6">
                <Link
                    to="/admin/accounts"
                    className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
                >
                    <ArrowLeft className="w-4 h-4 mr-1" />
                    Back to Accounts
                </Link>

                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{account.account_name}</h1>
                        <p className="text-gray-600 mt-1">
                            Created {new Date(account.created_at).toLocaleDateString()}
                        </p>
                    </div>

                    <div className="flex gap-3">
                        <Link
                            to={`/admin/accounts/${id}/users`}
                            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                            <Users className="w-4 h-4 mr-2" />
                            Manage Users
                        </Link>
                        <Link
                            to={`/admin/accounts/${id}/edit`}
                            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                        </Link>
                        <button
                            onClick={handleDeleteClick}
                            className="inline-flex items-center px-4 py-2 border border-destructive rounded-md shadow-sm text-sm font-medium text-destructive bg-white hover:bg-destructive/10"
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                        </button>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="flex space-x-8" role="tablist">
                    <Tab
                        label="Account Info"
                        value="info"
                        isActive={activeTab === 'info'}
                        onClick={() => setActiveTab('info')}
                    />
                    <Tab
                        label="Users"
                        value="users"
                        isActive={activeTab === 'users'}
                        onClick={() => setActiveTab('users')}
                    />
                    <Tab
                        label="Audit Logs"
                        value="audit"
                        isActive={activeTab === 'audit'}
                        onClick={() => setActiveTab('audit')}
                    />
                </nav>
            </div>

            {/* Tab Panels */}
            <div className="bg-white rounded-lg shadow p-6">
                {activeTab === 'info' && (
                    <div role="tabpanel" id="info-panel" aria-labelledby="info-tab">
                        <h2 className="text-xl font-semibold mb-4">Account Information</h2>
                        <dl className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                            <div>
                                <dt className="text-sm font-medium text-gray-500">Account Name</dt>
                                <dd className="mt-1 text-sm text-gray-900">{account.account_name}</dd>
                            </div>
                            <div>
                                <dt className="text-sm font-medium text-gray-500">Account ID</dt>
                                <dd className="mt-1 text-sm text-gray-900 font-mono">{account.account_id}</dd>
                            </div>
                            <div>
                                <dt className="text-sm font-medium text-gray-500">Status</dt>
                                <dd className="mt-1">
                                    <span
                                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${account.is_active
                                            ? 'bg-success/10 text-success'
                                            : 'bg-gray-100 text-gray-800'
                                            }`}
                                    >
                                        {account.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </dd>
                            </div>
                            <div>
                                <dt className="text-sm font-medium text-gray-500">Created At</dt>
                                <dd className="mt-1 text-sm text-gray-900">
                                    {new Date(account.created_at).toLocaleString()}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-sm font-medium text-gray-500">Updated At</dt>
                                <dd className="mt-1 text-sm text-gray-900">
                                    {new Date(account.updated_at).toLocaleString()}
                                </dd>
                            </div>
                        </dl>
                    </div>
                )}

                {activeTab === 'users' && (
                    <div role="tabpanel" id="users-panel" aria-labelledby="users-tab">
                        <h2 className="text-xl font-semibold mb-4">Account Users</h2>
                        <p className="text-gray-600 mb-4">
                            User management for this account will be implemented here.
                        </p>
                        <Link
                            to={`/admin/accounts/${id}/users`}
                            className="inline-flex items-center px-4 py-2 border border-primary rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90"
                        >
                            <Users className="w-4 h-4 mr-2" />
                            Open User Manager
                        </Link>
                    </div>
                )}

                {activeTab === 'audit' && (
                    <div role="tabpanel" id="audit-panel" aria-labelledby="audit-tab">
                        <h2 className="text-xl font-semibold mb-4">Audit Logs</h2>
                        <p className="text-gray-600">
                            Audit log history for this account will be implemented here.
                        </p>
                    </div>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            <DeleteConfirmationModal
                isOpen={showDeleteModal}
                onClose={() => setShowDeleteModal(false)}
                onConfirm={confirmDelete}
                title="Delete Account"
                description="Are you sure you want to delete this account? All associated data and user access will be removed."
                itemName={account?.account_name}
                confirmText="Delete Account"
                isPending={deleteAccountMutation.isPending}
            />
        </div>
    );
}

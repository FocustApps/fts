import { accountsApi } from '@/api';
import { cn } from '@/lib/utils';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    ArrowLeft,
    Edit,
    Search,
    Trash2,
    UserPlus,
    Users2
} from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { BulkAddUsersModal } from './BulkAddUsersModal';
import { BulkUpdateRolesModal } from './BulkUpdateRolesModal';
import { DeleteConfirmationModal } from './DeleteConfirmationModal';

interface AccountUser {
    user_id: string;
    email: string;
    username: string;
    role: 'owner' | 'admin' | 'member' | 'viewer';
    is_primary: boolean;
}

export function AccountUserManager() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
    const [showAddModal, setShowAddModal] = useState(false);
    const [showUpdateRolesModal, setShowUpdateRolesModal] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [userToDelete, setUserToDelete] = useState<{ id: string; email: string } | null>(null);

    const {
        data: account,
        isLoading: accountLoading,
    } = useQuery({
        queryKey: ['account', id],
        queryFn: () => accountsApi.getById(id!),
        enabled: !!id,
    });

    const {
        data: users,
        isLoading: usersLoading,
        error,
    } = useQuery({
        queryKey: ['account', id, 'users'],
        queryFn: () => accountsApi.listUsers(id!),
        enabled: !!id,
    });

    const removeUserMutation = useMutation({
        mutationFn: ({ userId }: { userId: string }) =>
            accountsApi.removeUser(id!, userId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['account', id, 'users'] });
            toast.success('User removed successfully');
            setUserToDelete(null);
            setShowDeleteModal(false);
        },
        onError: (error) => {
            toast.error('Failed to remove user');
            console.error('Remove user error:', error);
        },
    });

    const handleRemoveUser = (userId: string, email: string) => {
        setUserToDelete({ id: userId, email });
        setShowDeleteModal(true);
    };

    const confirmRemoveUser = () => {
        if (userToDelete) {
            removeUserMutation.mutate({ userId: userToDelete.id });
        }
    };

    const handleSelectUser = (userId: string) => {
        const newSelected = new Set(selectedUsers);
        if (newSelected.has(userId)) {
            newSelected.delete(userId);
        } else {
            newSelected.add(userId);
        }
        setSelectedUsers(newSelected);
    };

    const handleSelectAll = () => {
        if (selectedUsers.size === filteredUsers?.length) {
            setSelectedUsers(new Set());
        } else {
            setSelectedUsers(new Set(filteredUsers?.map((u) => u.user_id) || []));
        }
    };

    const getRoleBadgeColor = (role: string) => {
        switch (role) {
            case 'owner':
                return 'bg-purple-100 text-purple-800 border-purple-200';
            case 'admin':
                return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'member':
                return 'bg-green-100 text-green-800 border-green-200';
            case 'viewer':
                return 'bg-gray-100 text-gray-800 border-gray-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const filteredUsers = users?.filter((user) =>
        user.email.toLowerCase().includes(search.toLowerCase()) ||
        user.username.toLowerCase().includes(search.toLowerCase())
    );

    const isLoading = accountLoading || usersLoading;

    if (isLoading) {
        return (
            <div className="p-8">
                <div className="mb-6">
                    <div className="h-8 w-64 bg-gray-200 rounded animate-pulse mb-2"></div>
                    <div className="h-6 w-48 bg-gray-200 rounded animate-pulse"></div>
                </div>
                <div className="h-96 bg-gray-200 rounded animate-pulse"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8">
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                    <h2 className="text-lg font-semibold text-destructive mb-2">Error Loading Users</h2>
                    <p className="text-sm text-destructive/80">
                        {error instanceof Error ? error.message : 'Failed to load users'}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8">
            {/* Header */}
            <div className="mb-6">
                <Link
                    to={`/admin/accounts/${id}`}
                    className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
                >
                    <ArrowLeft className="w-4 h-4 mr-1" />
                    Back to Account
                </Link>

                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            {account?.account_name} - Users
                        </h1>
                        <p className="text-gray-600 mt-1">
                            Manage users and their roles in this account
                        </p>
                    </div>

                    <div className="flex gap-3">
                        {selectedUsers.size > 0 && (
                            <>
                                <button
                                    className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                                    onClick={() => setShowUpdateRolesModal(true)}
                                >
                                    <Edit className="w-4 h-4 mr-2" />
                                    Update Roles ({selectedUsers.size})
                                </button>
                                <button
                                    className="inline-flex items-center px-4 py-2 border border-destructive rounded-md shadow-sm text-sm font-medium text-destructive bg-white hover:bg-destructive/10"
                                    onClick={() => toast.info('Bulk remove users - coming soon')}
                                >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    Remove ({selectedUsers.size})
                                </button>
                            </>
                        )}
                        <button
                            className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md shadow-sm text-sm font-medium hover:bg-primary/90"
                            onClick={() => setShowAddModal(true)}
                        >
                            <UserPlus className="w-4 h-4 mr-2" />
                            Add Users
                        </button>
                    </div>
                </div>
            </div>

            {/* Search and Stats */}
            <div className="mb-6 flex items-center justify-between">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search by email or username..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                </div>
                <div className="text-sm text-gray-600">
                    {filteredUsers?.length || 0} users
                    {selectedUsers.size > 0 && ` (${selectedUsers.size} selected)`}
                </div>
            </div>

            {/* User Table */}
            <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left">
                                <input
                                    type="checkbox"
                                    checked={
                                        filteredUsers && filteredUsers.length > 0 && selectedUsers.size === filteredUsers.length
                                    }
                                    onChange={handleSelectAll}
                                    className="rounded border-gray-300 text-primary focus:ring-primary"
                                />
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                User
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Role
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Status
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {filteredUsers?.map((user) => (
                            <tr
                                key={user.user_id}
                                className={cn(
                                    'hover:bg-gray-50 transition-colors',
                                    selectedUsers.has(user.user_id) && 'bg-blue-50'
                                )}
                            >
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <input
                                        type="checkbox"
                                        checked={selectedUsers.has(user.user_id)}
                                        onChange={() => handleSelectUser(user.user_id)}
                                        className="rounded border-gray-300 text-primary focus:ring-primary"
                                    />
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center">
                                        <div className="flex-shrink-0 h-10 w-10">
                                            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-semibold">
                                                {user.username.charAt(0).toUpperCase()}
                                            </div>
                                        </div>
                                        <div className="ml-4">
                                            <div className="text-sm font-medium text-gray-900">{user.username}</div>
                                            <div className="text-sm text-gray-500">{user.email}</div>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span
                                        className={cn(
                                            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
                                            getRoleBadgeColor(user.role)
                                        )}
                                    >
                                        {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    {user.is_primary && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 border border-indigo-200">
                                            Primary
                                        </span>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <div className="flex items-center justify-end space-x-2">
                                        <button
                                            onClick={() => toast.info('Edit user role - coming soon')}
                                            className="text-blue-600 hover:text-blue-900 p-1 rounded hover:bg-blue-50"
                                            title="Edit role"
                                        >
                                            <Edit className="h-4 w-4" />
                                        </button>
                                        <button
                                            onClick={() => handleRemoveUser(user.user_id, user.email)}
                                            disabled={user.role === 'owner'}
                                            className={cn(
                                                'p-1 rounded',
                                                user.role === 'owner'
                                                    ? 'text-gray-400 cursor-not-allowed'
                                                    : 'text-red-600 hover:text-red-900 hover:bg-red-50'
                                            )}
                                            title={user.role === 'owner' ? 'Cannot remove owner' : 'Remove user'}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {filteredUsers?.length === 0 && (
                    <div className="text-center py-12">
                        <Users2 className="mx-auto h-12 w-12 text-gray-400" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No users found</h3>
                        <p className="mt-1 text-sm text-gray-500">
                            {search ? 'Try adjusting your search' : 'Get started by adding a user'}
                        </p>
                    </div>
                )}
            </div>

            {/* Modals */}
            <BulkAddUsersModal
                accountId={id!}
                accountName={account?.account_name || ''}
                isOpen={showAddModal}
                onClose={() => setShowAddModal(false)}
            />

            <BulkUpdateRolesModal
                accountId={id!}
                accountName={account?.account_name || ''}
                selectedUserIds={Array.from(selectedUsers)}
                users={users || []}
                isOpen={showUpdateRolesModal}
                onClose={() => setShowUpdateRolesModal(false)}
                onSuccess={() => {
                    setSelectedUsers(new Set());
                }}
            />

            <DeleteConfirmationModal
                isOpen={showDeleteModal}
                onClose={() => {
                    setShowDeleteModal(false);
                    setUserToDelete(null);
                }}
                onConfirm={confirmRemoveUser}
                title="Remove User from Account"
                description="Are you sure you want to remove this user from the account? They will lose access to all resources."
                itemName={userToDelete?.email}
                isPending={removeUserMutation.isPending}
            />
        </div>
    );
}

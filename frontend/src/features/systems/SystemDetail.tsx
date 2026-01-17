import { systemsApi } from '@/api/systems';
import { useAuthStore } from '@/stores/authStore';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Edit, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

export function SystemDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const [showDeleteModal, setShowDeleteModal] = useState(false);

    const canEdit = userRole === 'admin' || userRole === 'owner';

    const { data: system, isLoading, error } = useQuery({
        queryKey: ['system', id],
        queryFn: () => systemsApi.getById(id!),
        enabled: !!id,
    });

    const deleteMutation = useMutation({
        mutationFn: () => systemsApi.deactivate(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['systems'] });
            toast.success('System deactivated successfully');
            navigate('/systems');
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to deactivate system');
        },
    });

    const handleDelete = () => {
        deleteMutation.mutate();
        setShowDeleteModal(false);
    };

    if (isLoading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-3xl mx-auto">
                    <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-8" />
                    <div className="space-y-4">
                        {[...Array(6)].map((_, i) => (
                            <div key={i}>
                                <div className="h-4 w-32 bg-gray-200 rounded animate-pulse mb-2" />
                                <div className="h-6 w-full bg-gray-200 rounded animate-pulse" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (error || !system) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-3xl mx-auto">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <h3 className="text-red-800 font-semibold mb-2">Error Loading System</h3>
                        <p className="text-red-600">
                            {error instanceof Error ? error.message : 'System not found'}
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="max-w-3xl mx-auto">
                <Link
                    to="/systems"
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Systems
                </Link>

                <div className="bg-white border border-gray-200 rounded-lg p-8">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 mb-2">
                                {system.system_name}
                            </h1>
                            <div className="flex items-center gap-2">
                                <span
                                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${system.is_active
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-red-100 text-red-800'
                                        }`}
                                >
                                    {system.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </div>
                        </div>
                        {canEdit && system.is_active && (
                            <div className="flex gap-2">
                                <Link
                                    to={`/systems/${id}/edit`}
                                    className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                                >
                                    <Edit className="w-4 h-4" />
                                    Edit
                                </Link>
                                <button
                                    onClick={() => setShowDeleteModal(true)}
                                    className="inline-flex items-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Deactivate
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="space-y-6">
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1">System ID</h3>
                            <p className="text-gray-900 font-mono text-sm">{system.sut_id}</p>
                        </div>

                        {system.description && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Description</h3>
                                <p className="text-gray-900">{system.description}</p>
                            </div>
                        )}

                        {system.wiki_url && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Wiki URL</h3>
                                <a
                                    href={system.wiki_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:text-blue-800 hover:underline break-all"
                                >
                                    {system.wiki_url}
                                </a>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-6 pt-6 border-t border-gray-200">
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Created</h3>
                                <p className="text-gray-900">
                                    {new Date(system.created_at).toLocaleString()}
                                </p>
                            </div>

                            {system.updated_at && (
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 mb-1">Last Updated</h3>
                                    <p className="text-gray-900">
                                        {new Date(system.updated_at).toLocaleString()}
                                    </p>
                                </div>
                            )}

                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Owner</h3>
                                <p className="text-gray-900 font-mono text-sm">
                                    {system.owner_user_id}
                                </p>
                            </div>

                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Account</h3>
                                <p className="text-gray-900 font-mono text-sm">{system.account_id}</p>
                            </div>
                        </div>

                        {!system.is_active && system.deactivated_at && (
                            <div className="pt-6 border-t border-gray-200">
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                    <h3 className="text-red-800 font-semibold mb-2">
                                        System Deactivated
                                    </h3>
                                    <div className="text-sm text-red-700 space-y-1">
                                        <p>
                                            Deactivated on:{' '}
                                            {new Date(system.deactivated_at).toLocaleString()}
                                        </p>
                                        {system.deactivated_by_user_id && (
                                            <p>By: {system.deactivated_by_user_id}</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                        <h2 className="text-xl font-bold text-gray-900 mb-4">
                            Deactivate System
                        </h2>
                        <p className="text-gray-600 mb-6">
                            Are you sure you want to deactivate "{system.system_name}"? This action
                            will mark the system as inactive.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowDeleteModal(false)}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleteMutation.isPending}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:bg-gray-400"
                            >
                                {deleteMutation.isPending ? 'Deactivating...' : 'Deactivate'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

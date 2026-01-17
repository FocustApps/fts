import { plansApi } from '@/api/plans';
import { useAuthStore } from '@/stores/authStore';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Calendar, Edit, RotateCcw, Tag, Trash2, User } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

export function PlanDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [showDeleteModal, setShowDeleteModal] = useState(false);

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const canEdit = userRole === 'admin' || userRole === 'owner';
    const canDelete = userRole === 'admin' || userRole === 'owner';

    const { data: plan, isLoading, error } = useQuery({
        queryKey: ['plans', id],
        queryFn: () => plansApi.getById(id!),
        enabled: !!id,
    });

    const deactivateMutation = useMutation({
        mutationFn: () => plansApi.deactivate(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            toast.success('Plan deactivated successfully');
            navigate('/plans');
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to deactivate plan');
        },
    });

    const reactivateMutation = useMutation({
        mutationFn: () => plansApi.reactivate(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            toast.success('Plan reactivated successfully');
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to reactivate plan');
        },
    });

    if (isLoading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-4xl mx-auto">
                    <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-8" />
                    <div className="bg-white rounded-lg shadow p-8">
                        <div className="h-10 w-2/3 bg-gray-200 rounded animate-pulse mb-6" />
                        <div className="space-y-4">
                            {[...Array(4)].map((_, i) => (
                                <div key={i}>
                                    <div className="h-4 w-24 bg-gray-200 rounded animate-pulse mb-2" />
                                    <div className="h-6 w-full bg-gray-200 rounded animate-pulse" />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !plan) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-4xl mx-auto">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                        <h3 className="text-red-800 font-semibold mb-2">Error Loading Plan</h3>
                        <p className="text-red-600">
                            {error instanceof Error ? error.message : 'Plan not found'}
                        </p>
                        <Link
                            to="/plans"
                            className="inline-flex items-center gap-2 mt-4 text-red-700 hover:text-red-900"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Back to Plans
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    const isInactive = plan.status !== 'active';

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="max-w-4xl mx-auto">
                <button
                    onClick={() => navigate('/plans')}
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Plans
                </button>

                <div className="bg-white rounded-lg shadow">
                    {/* Header */}
                    <div className="border-b border-gray-200 p-6">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <h1 className="text-3xl font-bold text-gray-900 mb-2">{plan.plan_name}</h1>
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${plan.status === 'active'
                                                ? 'bg-green-100 text-green-800'
                                                : 'bg-gray-100 text-gray-800'
                                            }`}
                                    >
                                        {plan.status}
                                    </span>
                                </div>
                            </div>
                            <div className="flex gap-2">
                                {canEdit && !isInactive && (
                                    <Link
                                        to={`/plans/${id}/edit`}
                                        className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                                    >
                                        <Edit className="w-4 h-4" />
                                        Edit
                                    </Link>
                                )}
                                {canDelete && !isInactive && (
                                    <button
                                        onClick={() => setShowDeleteModal(true)}
                                        className="inline-flex items-center gap-2 px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Deactivate
                                    </button>
                                )}
                                {canEdit && isInactive && (
                                    <button
                                        onClick={() => reactivateMutation.mutate()}
                                        disabled={reactivateMutation.isPending}
                                        className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-400"
                                    >
                                        <RotateCcw className="w-4 h-4" />
                                        Reactivate
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Details */}
                    <div className="p-6 space-y-6">
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                Created At
                            </h3>
                            <p className="text-gray-900">
                                {plan.created_at
                                    ? new Date(plan.created_at).toLocaleString()
                                    : 'N/A'}
                            </p>
                        </div>

                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                Last Updated
                            </h3>
                            <p className="text-gray-900">
                                {plan.updated_at
                                    ? new Date(plan.updated_at).toLocaleString()
                                    : 'N/A'}
                            </p>
                        </div>

                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                <User className="w-4 h-4" />
                                Owner
                            </h3>
                            <p className="text-gray-900">{plan.owner_user_id || 'N/A'}</p>
                        </div>

                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                <Tag className="w-4 h-4" />
                                Suite IDs
                            </h3>
                            <p className="text-gray-900">{plan.suites_ids || 'None'}</p>
                        </div>

                        {plan.suite_tags && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                    <Tag className="w-4 h-4" />
                                    Suite Tags
                                </h3>
                                <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto">
                                    {JSON.stringify(plan.suite_tags, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                </div>

                {/* Delete Confirmation Modal */}
                {showDeleteModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                        <div className="bg-white rounded-lg max-w-md w-full p-6">
                            <h3 className="text-xl font-bold text-gray-900 mb-4">Deactivate Plan</h3>
                            <p className="text-gray-600 mb-6">
                                Are you sure you want to deactivate "{plan.plan_name}"? This action can be reversed later by reactivating the plan.
                            </p>
                            <div className="flex gap-4">
                                <button
                                    onClick={() => {
                                        deactivateMutation.mutate();
                                        setShowDeleteModal(false);
                                    }}
                                    disabled={deactivateMutation.isPending}
                                    className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors disabled:bg-gray-400"
                                >
                                    {deactivateMutation.isPending ? 'Deactivating...' : 'Deactivate'}
                                </button>
                                <button
                                    onClick={() => setShowDeleteModal(false)}
                                    disabled={deactivateMutation.isPending}
                                    className="flex-1 border border-gray-300 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors disabled:bg-gray-100"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

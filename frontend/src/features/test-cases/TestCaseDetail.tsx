import { testCasesApi } from '@/api/test-cases';
import { useAuthStore } from '@/stores/authStore';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Calendar, Edit, FileText, Trash2, User } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

export function TestCaseDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [showDeleteModal, setShowDeleteModal] = useState(false);

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const canEdit = userRole === 'admin' || userRole === 'owner';
    const canDelete = userRole === 'admin' || userRole === 'owner';

    const { data: testCase, isLoading, error } = useQuery({
        queryKey: ['test-cases', id],
        queryFn: () => testCasesApi.getById(id!),
        enabled: !!id,
    });

    const deactivateMutation = useMutation({
        mutationFn: () => testCasesApi.deactivate(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['test-cases'] });
            toast.success('Test case deactivated successfully');
            navigate('/test-cases');
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to deactivate test case');
        },
    });

    const getTypeColor = (type: string) => {
        const colors: Record<string, string> = {
            functional: 'bg-blue-100 text-blue-800',
            integration: 'bg-purple-100 text-purple-800',
            regression: 'bg-orange-100 text-orange-800',
            smoke: 'bg-green-100 text-green-800',
            performance: 'bg-yellow-100 text-yellow-800',
            security: 'bg-red-100 text-red-800',
        };
        return colors[type] || 'bg-gray-100 text-gray-800';
    };

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

    if (error || !testCase) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-4xl mx-auto">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                        <h3 className="text-red-800 font-semibold mb-2">Error Loading Test Case</h3>
                        <p className="text-red-600">
                            {error instanceof Error ? error.message : 'Test case not found'}
                        </p>
                        <Link
                            to="/test-cases"
                            className="inline-flex items-center gap-2 mt-4 text-red-700 hover:text-red-900"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Back to Test Cases
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="max-w-4xl mx-auto">
                <button
                    onClick={() => navigate('/test-cases')}
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Test Cases
                </button>

                <div className="bg-white rounded-lg shadow">
                    <div className="border-b border-gray-200 p-6">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h1 className="text-3xl font-bold text-gray-900">{testCase.test_name}</h1>
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTypeColor(testCase.test_type)}`}>
                                        {testCase.test_type}
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${testCase.is_active
                                                ? 'bg-green-100 text-green-800'
                                                : 'bg-gray-100 text-gray-800'
                                            }`}
                                    >
                                        {testCase.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>
                            </div>
                            <div className="flex gap-2">
                                {canEdit && testCase.is_active && (
                                    <Link
                                        to={`/test-cases/${id}/edit`}
                                        className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                                    >
                                        <Edit className="w-4 h-4" />
                                        Edit
                                    </Link>
                                )}
                                {canDelete && testCase.is_active && (
                                    <button
                                        onClick={() => setShowDeleteModal(true)}
                                        className="inline-flex items-center gap-2 px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Deactivate
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="p-6 space-y-6">
                        {testCase.description && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                    <FileText className="w-4 h-4" />
                                    Description
                                </h3>
                                <p className="text-gray-900">{testCase.description}</p>
                            </div>
                        )}

                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1">
                                System Under Test ID
                            </h3>
                            <p className="text-gray-900">{testCase.sut_id}</p>
                        </div>

                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                Created At
                            </h3>
                            <p className="text-gray-900">
                                {new Date(testCase.created_at).toLocaleString()}
                            </p>
                        </div>

                        {testCase.updated_at && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                    <Calendar className="w-4 h-4" />
                                    Last Updated
                                </h3>
                                <p className="text-gray-900">
                                    {new Date(testCase.updated_at).toLocaleString()}
                                </p>
                            </div>
                        )}

                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-2">
                                <User className="w-4 h-4" />
                                Owner
                            </h3>
                            <p className="text-gray-900">{testCase.owner_user_id}</p>
                        </div>

                        {!testCase.is_active && testCase.deactivated_at && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">
                                    Deactivated At
                                </h3>
                                <p className="text-gray-900">
                                    {new Date(testCase.deactivated_at).toLocaleString()}
                                </p>
                                {testCase.deactivated_by_user_id && (
                                    <p className="text-sm text-gray-500 mt-1">
                                        By: {testCase.deactivated_by_user_id}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {showDeleteModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                        <div className="bg-white rounded-lg max-w-md w-full p-6">
                            <h3 className="text-xl font-bold text-gray-900 mb-4">Deactivate Test Case</h3>
                            <p className="text-gray-600 mb-6">
                                Are you sure you want to deactivate "{testCase.test_name}"? This will mark it as inactive.
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

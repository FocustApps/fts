import { plansApi } from '@/api/plans';
import { useAuthStore } from '@/stores/authStore';
import type { components } from '@/types/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

type PlanModel = components['schemas']['PlanModel'];

export function PlanForm() {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const user = useAuthStore((state) => state.user);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const isEdit = !!id;
    const canEdit = userRole === 'admin' || userRole === 'owner';

    const [formData, setFormData] = useState({
        plan_name: '',
        suites_ids: '',
        status: 'active',
    });

    const [errors, setErrors] = useState<Record<string, string>>({});

    // Fetch plan data for edit mode
    const { data: plan, isLoading: isLoadingPlan } = useQuery({
        queryKey: ['plans', id],
        queryFn: () => plansApi.getById(id!),
        enabled: isEdit,
    });

    useEffect(() => {
        if (plan && isEdit) {
            setFormData({
                plan_name: plan.plan_name || '',
                suites_ids: plan.suites_ids || '',
                status: plan.status || 'active',
            });
        }
    }, [plan, isEdit]);

    const createMutation = useMutation({
        mutationFn: (data: Omit<PlanModel, 'plan_id' | 'created_at' | 'updated_at'>) =>
            plansApi.create(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            toast.success('Plan created successfully');
            navigate(`/plans/${data.plan_id}`);
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to create plan');
        },
    });

    const updateMutation = useMutation({
        mutationFn: (data: Partial<PlanModel>) => plansApi.update(id!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
            toast.success('Plan updated successfully');
            navigate(`/plans/${id}`);
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to update plan');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        // Validation
        const newErrors: Record<string, string> = {};
        if (!formData.plan_name.trim()) {
            newErrors.plan_name = 'Plan name is required';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        setErrors({});

        const planData: Partial<PlanModel> = {
            plan_name: formData.plan_name,
            suites_ids: formData.suites_ids || '',
            status: formData.status,
            account_id: currentAccount?.account_id || null,
            owner_user_id: user?.user_id || null,
            is_active: true,
        };

        if (isEdit) {
            updateMutation.mutate(planData);
        } else {
            createMutation.mutate(planData as Omit<PlanModel, 'plan_id' | 'created_at' | 'updated_at'>);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
        // Clear error for this field
        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: '' }));
        }
    };

    const isSubmitting = createMutation.isPending || updateMutation.isPending;

    if (isEdit && isLoadingPlan) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-2xl mx-auto">
                    <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-8" />
                    <div className="space-y-6">
                        {[...Array(3)].map((_, i) => (
                            <div key={i}>
                                <div className="h-4 w-24 bg-gray-200 rounded animate-pulse mb-2" />
                                <div className="h-10 w-full bg-gray-200 rounded animate-pulse" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (isEdit && !canEdit) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-2xl mx-auto">
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                        <h3 className="text-yellow-800 font-semibold mb-2">Permission Denied</h3>
                        <p className="text-yellow-600">
                            You don't have permission to edit plans. Only admins and owners can edit plans.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="max-w-2xl mx-auto">
                <button
                    onClick={() => navigate('/plans')}
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Plans
                </button>

                <h1 className="text-3xl font-bold text-gray-900 mb-8">
                    {isEdit ? 'Edit Plan' : 'Create New Plan'}
                </h1>

                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Plan Name */}
                    <div>
                        <label htmlFor="plan_name" className="block text-sm font-medium text-gray-700 mb-2">
                            Plan Name <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            id="plan_name"
                            name="plan_name"
                            value={formData.plan_name}
                            onChange={handleChange}
                            disabled={isSubmitting}
                            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed ${errors.plan_name ? 'border-red-300' : 'border-gray-300'
                                }`}
                            placeholder="Enter plan name"
                        />
                        {errors.plan_name && (
                            <p className="mt-1 text-sm text-red-600">{errors.plan_name}</p>
                        )}
                    </div>

                    {/* Suite IDs */}
                    <div>
                        <label htmlFor="suites_ids" className="block text-sm font-medium text-gray-700 mb-2">
                            Suite IDs (Optional)
                        </label>
                        <textarea
                            id="suites_ids"
                            name="suites_ids"
                            value={formData.suites_ids}
                            onChange={handleChange}
                            disabled={isSubmitting}
                            rows={3}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                            placeholder="Enter suite IDs (comma-separated)"
                        />
                        <p className="mt-1 text-sm text-gray-500">
                            Enter test suite IDs to include in this plan
                        </p>
                    </div>

                    {/* Status */}
                    <div>
                        <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                            Status
                        </label>
                        <select
                            id="status"
                            name="status"
                            value={formData.status}
                            onChange={handleChange}
                            disabled={isSubmitting}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                        >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                        </select>
                    </div>

                    {/* Form Actions */}
                    <div className="flex gap-4 pt-6">
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                        >
                            {isSubmitting ? 'Saving...' : isEdit ? 'Update Plan' : 'Create Plan'}
                        </button>
                        <button
                            type="button"
                            onClick={() => navigate('/plans')}
                            disabled={isSubmitting}
                            className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:bg-gray-100 disabled:cursor-not-allowed font-medium"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

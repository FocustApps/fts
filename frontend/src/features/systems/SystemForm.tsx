import { systemsApi } from '@/api/systems';
import { useAuthStore } from '@/stores/authStore';
import type { components } from '@/types/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

type SystemUnderTestModel = components['schemas']['SystemUnderTestModel'];

export function SystemForm() {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const user = useAuthStore((state) => state.user);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const isEdit = !!id;
    const canEdit = userRole === 'admin' || userRole === 'owner';

    const [formData, setFormData] = useState({
        system_name: '',
        description: '',
        wiki_url: '',
    });

    const [errors, setErrors] = useState<Record<string, string>>({});

    // Fetch existing system if editing
    const { data: existingSystem, isLoading: isFetching } = useQuery({
        queryKey: ['system', id],
        queryFn: () => systemsApi.getById(id!),
        enabled: isEdit,
    });

    useEffect(() => {
        if (existingSystem) {
            setFormData({
                system_name: existingSystem.system_name,
                description: existingSystem.description || '',
                wiki_url: existingSystem.wiki_url || '',
            });
        }
    }, [existingSystem]);

    const createMutation = useMutation({
        mutationFn: (data: Omit<SystemUnderTestModel, 'sut_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'>) =>
            systemsApi.create(data),
        onSuccess: (newSystem) => {
            queryClient.invalidateQueries({ queryKey: ['systems'] });
            toast.success('System created successfully');
            navigate(`/systems/${newSystem.sut_id}`);
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to create system');
        },
    });

    const updateMutation = useMutation({
        mutationFn: (data: Partial<SystemUnderTestModel>) => systemsApi.update(id!, data),
        onSuccess: (updatedSystem) => {
            queryClient.invalidateQueries({ queryKey: ['systems'] });
            queryClient.invalidateQueries({ queryKey: ['system', id] });
            toast.success('System updated successfully');
            navigate(`/systems/${updatedSystem.sut_id}`);
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to update system');
        },
    });

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (!formData.system_name.trim()) {
            newErrors.system_name = 'System name is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) return;
        if (!canEdit) {
            toast.error('You do not have permission to perform this action');
            return;
        }

        const systemData = {
            system_name: formData.system_name.trim(),
            description: formData.description.trim() || null,
            wiki_url: formData.wiki_url.trim() || null,
            account_id: currentAccount?.account_id || '',
            owner_user_id: user?.user_id || '',
            is_active: true,
        };

        if (isEdit) {
            updateMutation.mutate(systemData);
        } else {
            createMutation.mutate(systemData);
        }
    };

    const handleChange = (field: string, value: string) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors((prev) => ({ ...prev, [field]: '' }));
        }
    };

    if (!canEdit) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-2xl mx-auto">
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <h3 className="text-yellow-800 font-semibold mb-2">Permission Denied</h3>
                        <p className="text-yellow-700">
                            You do not have permission to {isEdit ? 'edit' : 'create'} systems.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    if (isEdit && isFetching) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-2xl mx-auto">
                    <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-8" />
                    <div className="space-y-6">
                        {[...Array(4)].map((_, i) => (
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

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="max-w-2xl mx-auto">
                <button
                    onClick={() => navigate(-1)}
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Systems
                </button>

                <h1 className="text-3xl font-bold text-gray-900 mb-8">
                    {isEdit ? 'Edit System' : 'Create New System'}
                </h1>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="system_name" className="block text-sm font-medium text-gray-700 mb-2">
                            System Name <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            id="system_name"
                            name="system_name"
                            value={formData.system_name}
                            onChange={(e) => handleChange('system_name', e.target.value)}
                            placeholder="Enter system name"
                            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed ${errors.system_name ? 'border-red-300' : 'border-gray-300'
                                }`}
                            disabled={createMutation.isPending || updateMutation.isPending}
                        />
                        {errors.system_name && (
                            <p className="mt-1 text-sm text-red-600">{errors.system_name}</p>
                        )}
                    </div>

                    <div>
                        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                            Description
                        </label>
                        <textarea
                            id="description"
                            name="description"
                            value={formData.description}
                            onChange={(e) => handleChange('description', e.target.value)}
                            placeholder="Enter system description"
                            rows={4}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                            disabled={createMutation.isPending || updateMutation.isPending}
                        />
                    </div>

                    <div>
                        <label htmlFor="wiki_url" className="block text-sm font-medium text-gray-700 mb-2">
                            Wiki URL
                        </label>
                        <input
                            type="url"
                            id="wiki_url"
                            name="wiki_url"
                            value={formData.wiki_url}
                            onChange={(e) => handleChange('wiki_url', e.target.value)}
                            placeholder="https://wiki.example.com/system"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                            disabled={createMutation.isPending || updateMutation.isPending}
                        />
                    </div>

                    <div className="flex gap-4 pt-6">
                        <button
                            type="submit"
                            disabled={createMutation.isPending || updateMutation.isPending}
                            className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                        >
                            {createMutation.isPending || updateMutation.isPending
                                ? 'Saving...'
                                : isEdit
                                    ? 'Update System'
                                    : 'Create System'}
                        </button>
                        <button
                            type="button"
                            onClick={() => navigate('/systems')}
                            disabled={createMutation.isPending || updateMutation.isPending}
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

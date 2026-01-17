import { systemsApi } from '@/api/systems';
import { testCasesApi } from '@/api/test-cases';
import { useAuthStore } from '@/stores/authStore';
import type { components } from '@/types/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Check, ChevronsUpDown } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

type TestCaseModel = components['schemas']['TestCaseModel'];
type SystemUnderTestModel = components['schemas']['SystemUnderTestModel'];

const TEST_TYPES = [
    'functional',
    'integration',
    'regression',
    'smoke',
    'performance',
    'security',
] as const;

export function TestCaseForm() {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const user = useAuthStore((state) => state.user);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const isEdit = !!id;
    const canEdit = userRole === 'admin' || userRole === 'owner';

    const [formData, setFormData] = useState({
        test_name: '',
        description: '',
        test_type: 'functional',
        sut_id: '',
    });

    const [errors, setErrors] = useState<Record<string, string>>({});
    const [isSystemDropdownOpen, setIsSystemDropdownOpen] = useState(false);
    const [systemSearchQuery, setSystemSearchQuery] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Fetch systems under test
    const { data: systems = [], isLoading: isLoadingSystems } = useQuery({
        queryKey: ['systems', currentAccount?.account_id],
        queryFn: () => systemsApi.listByAccount(currentAccount?.account_id || ''),
        enabled: !!currentAccount?.account_id,
    });

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsSystemDropdownOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const { data: testCase, isLoading: isLoadingTestCase } = useQuery({
        queryKey: ['test-cases', id],
        queryFn: () => testCasesApi.getById(id!),
        enabled: isEdit,
    });

    useEffect(() => {
        if (testCase && isEdit) {
            setFormData({
                test_name: testCase.test_name || '',
                description: testCase.description || '',
                test_type: testCase.test_type || 'functional',
                sut_id: testCase.sut_id || '',
            });
        }
    }, [testCase, isEdit]);

    const createMutation = useMutation({
        mutationFn: (data: Omit<TestCaseModel, 'test_case_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'>) =>
            testCasesApi.create(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['test-cases'] });
            toast.success('Test case created successfully');
            navigate(`/test-cases/${data.test_case_id}`);
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to create test case');
        },
    });

    const updateMutation = useMutation({
        mutationFn: (data: Partial<TestCaseModel>) => testCasesApi.update(id!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['test-cases'] });
            toast.success('Test case updated successfully');
            navigate(`/test-cases/${id}`);
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : 'Failed to update test case');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        const newErrors: Record<string, string> = {};
        if (!formData.test_name.trim()) {
            newErrors.test_name = 'Test name is required';
        }
        if (!formData.sut_id.trim()) {
            newErrors.sut_id = 'System under test is required';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        setErrors({});

        const testCaseData: Partial<TestCaseModel> = {
            test_name: formData.test_name,
            description: formData.description || null,
            test_type: formData.test_type,
            sut_id: formData.sut_id,
            account_id: currentAccount?.account_id || '',
            owner_user_id: user?.user_id || '',
            is_active: true,
        };

        if (isEdit) {
            updateMutation.mutate(testCaseData);
        } else {
            createMutation.mutate(testCaseData as Omit<TestCaseModel, 'test_case_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'>);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: '' }));
        }
    };

    const handleSystemSelect = (sutId: string) => {
        setFormData((prev) => ({ ...prev, sut_id: sutId }));
        setIsSystemDropdownOpen(false);
        setSystemSearchQuery('');
        if (errors.sut_id) {
            setErrors((prev) => ({ ...prev, sut_id: '' }));
        }
    };

    const filteredSystems = systems.filter((system) =>
        system.system_name.toLowerCase().includes(systemSearchQuery.toLowerCase())
    );

    const selectedSystem = systems.find((s) => s.sut_id === formData.sut_id);

    const isSubmitting = createMutation.isPending || updateMutation.isPending;

    if (isEdit && isLoadingTestCase) {
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

    if (isEdit && !canEdit) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-2xl mx-auto">
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                        <h3 className="text-yellow-800 font-semibold mb-2">Permission Denied</h3>
                        <p className="text-yellow-600">
                            You don't have permission to edit test cases. Only admins and owners can edit.
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
                    onClick={() => navigate('/test-cases')}
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
                >
                    <ArrowLeft className="w-5 h-5" />
                    Back to Test Cases
                </button>

                <h1 className="text-3xl font-bold text-gray-900 mb-8">
                    {isEdit ? 'Edit Test Case' : 'Create New Test Case'}
                </h1>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="test_name" className="block text-sm font-medium text-gray-700 mb-2">
                            Test Name <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            id="test_name"
                            name="test_name"
                            value={formData.test_name}
                            onChange={handleChange}
                            disabled={isSubmitting}
                            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed ${errors.test_name ? 'border-red-300' : 'border-gray-300'
                                }`}
                            placeholder="Enter test name"
                        />
                        {errors.test_name && (
                            <p className="mt-1 text-sm text-red-600">{errors.test_name}</p>
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
                            onChange={handleChange}
                            disabled={isSubmitting}
                            rows={4}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                            placeholder="Enter test description"
                        />
                    </div>

                    <div>
                        <label htmlFor="test_type" className="block text-sm font-medium text-gray-700 mb-2">
                            Test Type <span className="text-red-500">*</span>
                        </label>
                        <select
                            id="test_type"
                            name="test_type"
                            value={formData.test_type}
                            onChange={handleChange}
                            disabled={isSubmitting}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                        >
                            {TEST_TYPES.map((type) => (
                                <option key={type} value={type}>
                                    {type.charAt(0).toUpperCase() + type.slice(1)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label htmlFor="sut_id" className="block text-sm font-medium text-gray-700 mb-2">
                            System Under Test <span className="text-red-500">*</span>
                        </label>
                        <div ref={dropdownRef} className="relative">
                            <button
                                type="button"
                                onClick={() => setIsSystemDropdownOpen(!isSystemDropdownOpen)}
                                disabled={isSubmitting || isLoadingSystems}
                                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-left flex items-center justify-between ${errors.sut_id ? 'border-red-300' : 'border-gray-300'
                                    }`}
                            >
                                <span className={selectedSystem ? 'text-gray-900' : 'text-gray-400'}>
                                    {isLoadingSystems
                                        ? 'Loading systems...'
                                        : selectedSystem
                                            ? selectedSystem.system_name
                                            : 'Select a system'}
                                </span>
                                <ChevronsUpDown className="w-4 h-4 text-gray-400" />
                            </button>

                            {isSystemDropdownOpen && !isLoadingSystems && (
                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-hidden">
                                    <div className="p-2 border-b border-gray-200">
                                        <input
                                            type="text"
                                            placeholder="Search systems..."
                                            value={systemSearchQuery}
                                            onChange={(e) => setSystemSearchQuery(e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                    </div>
                                    <div className="overflow-y-auto max-h-48">
                                        {filteredSystems.length === 0 ? (
                                            <div className="px-4 py-3 text-sm text-gray-500">
                                                No systems found
                                            </div>
                                        ) : (
                                            filteredSystems.map((system) => (
                                                <button
                                                    key={system.sut_id}
                                                    type="button"
                                                    onClick={() => handleSystemSelect(system.sut_id!)}
                                                    className={`w-full px-4 py-2 text-left hover:bg-gray-100 flex items-center justify-between ${system.sut_id === formData.sut_id
                                                            ? 'bg-blue-50 text-blue-600'
                                                            : 'text-gray-900'
                                                        }`}
                                                >
                                                    <span>{system.system_name}</span>
                                                    {system.sut_id === formData.sut_id && (
                                                        <Check className="w-4 h-4" />
                                                    )}
                                                </button>
                                            ))
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                        {errors.sut_id && (
                            <p className="mt-1 text-sm text-red-600">{errors.sut_id}</p>
                        )}
                    </div>

                    <div className="flex gap-4 pt-6">
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                        >
                            {isSubmitting ? 'Saving...' : isEdit ? 'Update Test Case' : 'Create Test Case'}
                        </button>
                        <button
                            type="button"
                            onClick={() => navigate('/test-cases')}
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

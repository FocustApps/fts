import { testCasesApi } from '@/api/test-cases';
import { useAuthStore } from '@/stores/authStore';
import { useQuery } from '@tanstack/react-query';
import { Calendar, FileText, Plus, Search, User } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

const TEST_TYPES = [
    'functional',
    'integration',
    'regression',
    'smoke',
    'performance',
    'security',
] as const;

export function TestCaseList() {
    const [searchQuery, setSearchQuery] = useState('');
    const [filterType, setFilterType] = useState<string>('all');
    const [sortBy, setSortBy] = useState<'name' | 'created_at'>('name');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const { data: testCases = [], isLoading, error } = useQuery({
        queryKey: ['test-cases', currentAccount?.account_id],
        queryFn: () => testCasesApi.listByAccount(currentAccount?.account_id || ''),
        enabled: !!currentAccount?.account_id,
    });

    // Filter and sort test cases
    const filteredTestCases = testCases
        .filter((testCase) => {
            const matchesSearch = testCase.test_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (testCase.description?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
            const matchesType = filterType === 'all' || testCase.test_type === filterType;
            return matchesSearch && matchesType && testCase.is_active;
        })
        .sort((a, b) => {
            let comparison = 0;
            if (sortBy === 'name') {
                comparison = a.test_name.localeCompare(b.test_name);
            } else if (sortBy === 'created_at') {
                const dateA = new Date(a.created_at).getTime();
                const dateB = new Date(b.created_at).getTime();
                comparison = dateA - dateB;
            }
            return sortOrder === 'asc' ? comparison : -comparison;
        });

    const canCreate = userRole === 'admin' || userRole === 'owner';

    const toggleSort = (field: 'name' | 'created_at') => {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder('asc');
        }
    };

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
                <div className="flex justify-between items-center mb-6">
                    <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
                    <div className="h-10 w-32 bg-gray-200 rounded animate-pulse" />
                </div>
                <div className="space-y-4">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="border rounded-lg p-6 bg-gray-50 animate-pulse">
                            <div className="h-6 w-1/3 bg-gray-200 rounded mb-4" />
                            <div className="h-4 w-1/2 bg-gray-200 rounded" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                    <h3 className="text-red-800 font-semibold mb-2">Error Loading Test Cases</h3>
                    <p className="text-red-600">
                        {error instanceof Error ? error.message : 'An unexpected error occurred'}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Test Cases</h1>
                    <p className="text-gray-600 mt-1">
                        {filteredTestCases.length} {filteredTestCases.length === 1 ? 'test case' : 'test cases'}
                    </p>
                </div>
                {canCreate && (
                    <Link
                        to="/test-cases/new"
                        className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        Create Test Case
                    </Link>
                )}
            </div>

            {/* Search and Filter Controls */}
            <div className="mb-6 flex gap-4 flex-wrap">
                <div className="flex-1 min-w-[200px] relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search test cases..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>
                <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                    <option value="all">All Types</option>
                    {TEST_TYPES.map((type) => (
                        <option key={type} value={type}>
                            {type.charAt(0).toUpperCase() + type.slice(1)}
                        </option>
                    ))}
                </select>
                <div className="flex gap-2">
                    <button
                        onClick={() => toggleSort('name')}
                        className={`px-4 py-2 border rounded-lg transition-colors ${sortBy === 'name'
                                ? 'bg-blue-50 border-blue-200 text-blue-700'
                                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        Name {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </button>
                    <button
                        onClick={() => toggleSort('created_at')}
                        className={`px-4 py-2 border rounded-lg transition-colors ${sortBy === 'created_at'
                                ? 'bg-blue-50 border-blue-200 text-blue-700'
                                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        Date {sortBy === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </button>
                </div>
            </div>

            {/* Test Cases List */}
            {filteredTestCases.length === 0 ? (
                <div className="text-center py-12">
                    <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-gray-700 mb-2">
                        {searchQuery || filterType !== 'all' ? 'No test cases found' : 'No test cases yet'}
                    </h3>
                    <p className="text-gray-500 mb-6">
                        {searchQuery || filterType !== 'all'
                            ? 'Try adjusting your search or filters'
                            : 'Get started by creating your first test case'}
                    </p>
                    {canCreate && !searchQuery && filterType === 'all' && (
                        <Link
                            to="/test-cases/new"
                            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            <Plus className="w-5 h-5" />
                            Create Your First Test Case
                        </Link>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    {filteredTestCases.map((testCase) => (
                        <Link
                            key={testCase.test_case_id}
                            to={`/test-cases/${testCase.test_case_id}`}
                            className="block border rounded-lg p-6 bg-white hover:shadow-lg transition-shadow"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-2">
                                        <h3 className="text-xl font-semibold text-gray-900">
                                            {testCase.test_name}
                                        </h3>
                                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getTypeColor(testCase.test_type)}`}>
                                            {testCase.test_type}
                                        </span>
                                    </div>
                                    {testCase.description && (
                                        <p className="text-gray-600 mb-3">{testCase.description}</p>
                                    )}
                                    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                                        <div className="flex items-center gap-1">
                                            <Calendar className="w-4 h-4" />
                                            <span>Created {new Date(testCase.created_at).toLocaleDateString()}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <User className="w-4 h-4" />
                                            <span>Owner: {testCase.owner_user_id}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

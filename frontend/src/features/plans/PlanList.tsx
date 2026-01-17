import { plansApi } from '@/api/plans';
import { useAuthStore } from '@/stores/authStore';
import { useQuery } from '@tanstack/react-query';
import { Calendar, Plus, Search, Tag, User } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

export function PlanList() {
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState<'name' | 'created_at'>('name');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

    const currentAccount = useAuthStore((state) => state.currentAccount);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const { data: plans = [], isLoading, error } = useQuery({
        queryKey: ['plans', currentAccount?.account_id],
        queryFn: () => plansApi.listByAccount(currentAccount?.account_id || ''),
        enabled: !!currentAccount?.account_id,
    });

    // Filter and sort plans
    const filteredPlans = plans
        .filter((plan) =>
            plan.plan_name.toLowerCase().includes(searchQuery.toLowerCase())
        )
        .sort((a, b) => {
            let comparison = 0;
            if (sortBy === 'name') {
                comparison = a.plan_name.localeCompare(b.plan_name);
            } else if (sortBy === 'created_at') {
                const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
                const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
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
                    <h3 className="text-red-800 font-semibold mb-2">Error Loading Plans</h3>
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
                    <h1 className="text-3xl font-bold text-gray-900">Test Plans</h1>
                    <p className="text-gray-600 mt-1">
                        {filteredPlans.length} {filteredPlans.length === 1 ? 'plan' : 'plans'}
                    </p>
                </div>
                {canCreate && (
                    <Link
                        to="/plans/new"
                        className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        Create Plan
                    </Link>
                )}
            </div>

            {/* Search and Sort Controls */}
            <div className="mb-6 flex gap-4">
                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search plans..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>
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

            {/* Plans List */}
            {filteredPlans.length === 0 ? (
                <div className="text-center py-12">
                    <Tag className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-gray-700 mb-2">
                        {searchQuery ? 'No plans found' : 'No plans yet'}
                    </h3>
                    <p className="text-gray-500 mb-6">
                        {searchQuery
                            ? 'Try adjusting your search'
                            : 'Get started by creating your first test plan'}
                    </p>
                    {canCreate && !searchQuery && (
                        <Link
                            to="/plans/new"
                            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            <Plus className="w-5 h-5" />
                            Create Your First Plan
                        </Link>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    {filteredPlans.map((plan) => (
                        <Link
                            key={plan.plan_id}
                            to={`/plans/${plan.plan_id}`}
                            className="block border rounded-lg p-6 bg-white hover:shadow-lg transition-shadow"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                        {plan.plan_name}
                                    </h3>
                                    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                                        {plan.created_at && (
                                            <div className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4" />
                                                <span>
                                                    Created {new Date(plan.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        )}
                                        {plan.owner_user_id && (
                                            <div className="flex items-center gap-1">
                                                <User className="w-4 h-4" />
                                                <span>Owner: {plan.owner_user_id}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="ml-4">
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
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

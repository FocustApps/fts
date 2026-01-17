import { systemsApi } from '@/api/systems';
import { useAuthStore } from '@/stores/authStore';
import type { components } from '@/types/api';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

type SystemUnderTestModel = components['schemas']['SystemUnderTestModel'];

export function SystemList() {
    const currentAccount = useAuthStore((state) => state.currentAccount);
    const userRole = useAuthStore((state) => state.getCachedRole(currentAccount?.account_id || ''));

    const [searchQuery, setSearchQuery] = useState('');
    const [sortField, setSortField] = useState<'name' | 'date'>('name');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

    const { data: systems = [], isLoading, error } = useQuery({
        queryKey: ['systems', currentAccount?.account_id],
        queryFn: () => systemsApi.listByAccount(currentAccount?.account_id || ''),
        enabled: !!currentAccount?.account_id,
    });

    const canCreate = userRole === 'admin' || userRole === 'owner';

    // Filter systems by search query
    const filteredSystems = useMemo(() => {
        return systems.filter((system) => {
            const matchesSearch =
                system.system_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (system.description?.toLowerCase() || '').includes(searchQuery.toLowerCase());

            return matchesSearch && system.is_active;
        });
    }, [systems, searchQuery]);

    // Sort systems
    const sortedSystems = useMemo(() => {
        return [...filteredSystems].sort((a, b) => {
            if (sortField === 'name') {
                const comparison = a.system_name.localeCompare(b.system_name);
                return sortOrder === 'asc' ? comparison : -comparison;
            } else {
                const dateA = new Date(a.created_at).getTime();
                const dateB = new Date(b.created_at).getTime();
                return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
            }
        });
    }, [filteredSystems, sortField, sortOrder]);

    const handleSort = (field: 'name' | 'date') => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('asc');
        }
    };

    if (isLoading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="mb-8">
                    <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-2" />
                    <div className="h-4 w-64 bg-gray-200 rounded animate-pulse" />
                </div>
                <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-32 bg-gray-200 rounded animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h3 className="text-red-800 font-semibold mb-2">Error Loading Systems</h3>
                    <p className="text-red-600">{error instanceof Error ? error.message : 'Failed to load systems'}</p>
                </div>
            </div>
        );
    }

    const isEmpty = systems.length === 0;
    const isFiltered = sortedSystems.length === 0 && !isEmpty;

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-start mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Systems Under Test</h1>
                    <p className="text-gray-600">
                        Manage systems under test for your test automation
                    </p>
                </div>
                {canCreate && (
                    <Link
                        to="/systems/new"
                        className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        Create System
                    </Link>
                )}
            </div>

            {isEmpty ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                    <div className="text-gray-400 mb-4">
                        <Plus className="w-16 h-16 mx-auto" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">No systems yet</h3>
                    <p className="text-gray-600 mb-6">
                        Get started by creating your first system under test
                    </p>
                    {canCreate && (
                        <Link
                            to="/systems/new"
                            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            <Plus className="w-5 h-5" />
                            Create Your First System
                        </Link>
                    )}
                </div>
            ) : (
                <>
                    <div className="mb-6 flex gap-4 items-center">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                            <input
                                type="text"
                                placeholder="Search systems..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => handleSort('name')}
                                className={`px-4 py-2 rounded-lg transition-colors ${sortField === 'name'
                                        ? 'bg-blue-50 text-blue-700 border-2 border-blue-200'
                                        : 'bg-white border border-gray-300 hover:bg-gray-50'
                                    }`}
                            >
                                Name {sortField === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </button>
                            <button
                                onClick={() => handleSort('date')}
                                className={`px-4 py-2 rounded-lg transition-colors ${sortField === 'date'
                                        ? 'bg-blue-50 text-blue-700 border-2 border-blue-200'
                                        : 'bg-white border border-gray-300 hover:bg-gray-50'
                                    }`}
                            >
                                Date {sortField === 'date' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </button>
                        </div>
                    </div>

                    <div className="mb-4 text-sm text-gray-600">
                        {sortedSystems.length} {sortedSystems.length === 1 ? 'system' : 'systems'}
                    </div>

                    {isFiltered ? (
                        <div className="text-center py-12 bg-gray-50 rounded-lg">
                            <p className="text-gray-600">No systems found matching your search.</p>
                        </div>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {sortedSystems.map((system) => (
                                <Link
                                    key={system.sut_id}
                                    to={`/systems/${system.sut_id}`}
                                    className="block p-6 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all"
                                >
                                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                        {system.system_name}
                                    </h3>
                                    {system.description && (
                                        <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                                            {system.description}
                                        </p>
                                    )}
                                    {system.wiki_url && (
                                        <div className="text-xs text-blue-600 mb-2 truncate">
                                            📖 {system.wiki_url}
                                        </div>
                                    )}
                                    <div className="text-xs text-gray-500">
                                        Created {new Date(system.created_at).toLocaleDateString()}
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

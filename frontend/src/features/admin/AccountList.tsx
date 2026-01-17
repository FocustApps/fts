import { accountsApi } from '@/api';
import { cn } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';
import {
    ChevronDown,
    ChevronUp,
    Edit,
    Eye,
    Plus,
    Search,
    Trash2,
    Users,
} from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

type SortField = 'name' | 'created_at' | 'user_count';
type SortOrder = 'asc' | 'desc';

function SortIcon({
    field,
    currentField,
    currentOrder,
}: {
    field: SortField;
    currentField: SortField;
    currentOrder: SortOrder;
}) {
    if (currentField !== field) return null;
    return currentOrder === 'asc' ? (
        <ChevronUp className="h-4 w-4" />
    ) : (
        <ChevronDown className="h-4 w-4" />
    );
}

export function AccountList() {
    const [search, setSearch] = useState('');
    const [sortField, setSortField] = useState<SortField>('created_at');
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

    const { data: accounts, isLoading, error } = useQuery({
        queryKey: ['admin', 'accounts'],
        queryFn: () => accountsApi.listAll(),
    });

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('asc');
        }
    };

    const filteredAccounts = accounts?.filter((account) =>
        account.account_name.toLowerCase().includes(search.toLowerCase())
    );

    const sortedAccounts = filteredAccounts?.sort((a, b) => {
        const multiplier = sortOrder === 'asc' ? 1 : -1;
        if (sortField === 'name') {
            return a.account_name.localeCompare(b.account_name) * multiplier;
        }
        if (sortField === 'created_at') {
            return (
                (new Date(a.created_at).getTime() -
                    new Date(b.created_at).getTime()) *
                multiplier
            );
        }
        // user_count would need to come from backend
        return 0;
    });

    if (error) {
        return (
            <div className="max-w-7xl mx-auto p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex">
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-red-800">
                                Failed to load accounts
                            </h3>
                            <p className="text-sm text-red-700 mt-1">
                                {error instanceof Error ? error.message : 'Unknown error'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Manage all accounts and their users
                    </p>
                </div>
                <Link
                    to="/admin/accounts/new"
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Account
                </Link>
            </div>

            {/* Search */}
            <div className="mb-6">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search accounts..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>
            </div>

            {/* Table */}
            {isLoading ? (
                <div className="bg-white rounded-lg border border-gray-200">
                    <div className="animate-pulse p-6 space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="flex items-center space-x-4">
                                <div className="h-4 bg-gray-200 rounded w-1/3" />
                                <div className="h-4 bg-gray-200 rounded w-1/4" />
                                <div className="h-4 bg-gray-200 rounded w-1/4" />
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('name')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Account Name</span>
                                        <SortIcon
                                            field="name"
                                            currentField={sortField}
                                            currentOrder={sortOrder}
                                        />
                                    </div>
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Owner
                                </th>
                                <th
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('created_at')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Created</span>
                                        <SortIcon
                                            field="created_at"
                                            currentField={sortField}
                                            currentOrder={sortOrder}
                                        />
                                    </div>
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
                            {sortedAccounts?.map((account) => (
                                <tr
                                    key={account.account_id}
                                    className="hover:bg-gray-50 transition-colors"
                                >
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="h-10 w-10 flex-shrink-0 bg-blue-100 rounded-lg flex items-center justify-center">
                                                <span className="text-blue-600 font-semibold">
                                                    {account.account_name.substring(0, 2).toUpperCase()}
                                                </span>
                                            </div>
                                            <div className="ml-4">
                                                <div className="text-sm font-medium text-gray-900">
                                                    {account.account_name}
                                                </div>
                                                <div className="text-sm text-gray-500">
                                                    {account.account_id}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm text-gray-900">
                                            {account.owner_user_id}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm text-gray-900">
                                            {new Date(account.created_at).toLocaleDateString()}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span
                                            className={cn(
                                                'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                                                account.is_active
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-red-100 text-red-800'
                                            )}
                                        >
                                            {account.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <div className="flex items-center justify-end space-x-2">
                                            <Link
                                                to={`/admin/accounts/${account.account_id}`}
                                                className="text-blue-600 hover:text-blue-900 p-1 rounded hover:bg-blue-50"
                                                title="View details"
                                            >
                                                <Eye className="h-4 w-4" />
                                            </Link>
                                            <Link
                                                to={`/admin/accounts/${account.account_id}/users`}
                                                className="text-purple-600 hover:text-purple-900 p-1 rounded hover:bg-purple-50"
                                                title="Manage users"
                                            >
                                                <Users className="h-4 w-4" />
                                            </Link>
                                            <Link
                                                to={`/admin/accounts/${account.account_id}/edit`}
                                                className="text-green-600 hover:text-green-900 p-1 rounded hover:bg-green-50"
                                                title="Edit account"
                                            >
                                                <Edit className="h-4 w-4" />
                                            </Link>
                                            <button
                                                className="text-red-600 hover:text-red-900 p-1 rounded hover:bg-red-50"
                                                title="Delete account"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {sortedAccounts?.length === 0 && (
                        <div className="text-center py-12">
                            <p className="text-gray-500 text-sm">
                                {search
                                    ? 'No accounts found matching your search'
                                    : 'No accounts yet'}
                            </p>
                        </div>
                    )}
                </div>
            )}

            {/* Stats */}
            {sortedAccounts && sortedAccounts.length > 0 && (
                <div className="mt-4 text-sm text-gray-500">
                    Showing {sortedAccounts.length} of {accounts?.length} accounts
                </div>
            )}
        </div>
    );
}

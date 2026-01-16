import { notificationsApi } from '@/api';
import { toast } from '@/stores';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

export function NotificationPreferences() {
    const queryClient = useQueryClient();
    const [isSaving, setIsSaving] = useState(false);

    // Fetch preferences
    const { data: preferences, isLoading } = useQuery({
        queryKey: ['notification-preferences'],
        queryFn: notificationsApi.getPreferences,
    });

    // Update preferences mutation
    const updateMutation = useMutation({
        mutationFn: notificationsApi.updatePreferences,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
            toast.success('Preferences saved', 'Your notification settings have been updated');
        },
        onError: () => {
            toast.error('Failed to save preferences', 'Please try again');
        },
        onSettled: () => {
            setIsSaving(false);
        },
    });

    const handleToggle = async (field: string, value: boolean) => {
        setIsSaving(true);
        updateMutation.mutate({ [field]: value });
    };

    if (isLoading) {
        return (
            <div className="max-w-2xl mx-auto p-6">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
                    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="flex items-center justify-between">
                                <div className="space-y-2 flex-1">
                                    <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                                </div>
                                <div className="h-6 w-11 bg-gray-200 rounded-full"></div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (!preferences) {
        return (
            <div className="max-w-2xl mx-auto p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800">Failed to load notification preferences</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto p-6">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Notification Preferences</h1>
                <p className="mt-1 text-sm text-gray-600">
                    Manage how you receive notifications about your tests and account activity.
                </p>
            </div>

            {/* Preferences Form */}
            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
                {/* Email Notifications */}
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Delivery Methods</h2>
                    <div className="space-y-4">
                        <PreferenceToggle
                            label="Email notifications"
                            description="Receive notifications via email"
                            checked={preferences.email_enabled}
                            onChange={(checked) => handleToggle('email_enabled', checked)}
                            disabled={isSaving}
                        />
                        <PreferenceToggle
                            label="In-app notifications"
                            description="Show notifications in the notification center"
                            checked={preferences.in_app_enabled}
                            onChange={(checked) => handleToggle('in_app_enabled', checked)}
                            disabled={isSaving}
                        />
                    </div>
                </div>

                {/* Event Types */}
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Notification Types</h2>
                    <div className="space-y-4">
                        <PreferenceToggle
                            label="Test completion"
                            description="Notify when a test run completes successfully"
                            checked={preferences.test_completion_enabled}
                            onChange={(checked) => handleToggle('test_completion_enabled', checked)}
                            disabled={isSaving}
                        />
                        <PreferenceToggle
                            label="Test failure"
                            description="Notify when a test run fails"
                            checked={preferences.test_failure_enabled}
                            onChange={(checked) => handleToggle('test_failure_enabled', checked)}
                            disabled={isSaving}
                        />
                        <PreferenceToggle
                            label="Daily summary"
                            description="Receive a daily summary of test activity"
                            checked={preferences.daily_summary_enabled}
                            onChange={(checked) => handleToggle('daily_summary_enabled', checked)}
                            disabled={isSaving}
                        />
                    </div>
                </div>
            </div>

            {/* Info Box */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex">
                    <svg
                        className="h-5 w-5 text-blue-400 flex-shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <div className="ml-3 text-sm text-blue-700">
                        <p>
                            Changes are saved automatically. You can update these preferences at any
                            time.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

function PreferenceToggle({
    label,
    description,
    checked,
    onChange,
    disabled,
}: {
    label: string;
    description: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
}) {
    return (
        <div className="flex items-center justify-between">
            <div className="flex-1">
                <label className="text-sm font-medium text-gray-900">{label}</label>
                <p className="text-sm text-gray-600">{description}</p>
            </div>
            <button
                type="button"
                role="switch"
                aria-checked={checked}
                onClick={() => onChange(!checked)}
                disabled={disabled}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${checked ? 'bg-blue-600' : 'bg-gray-200'
                    } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
                <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'
                        }`}
                />
            </button>
        </div>
    );
}

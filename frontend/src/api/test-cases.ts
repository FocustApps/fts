import { apiClient } from '../lib/axios';
import type { components } from '../types/api';

type TestCaseModel = components['schemas']['TestCaseModel'];

export const testCasesApi = {
    /**
     * Get all test cases for the current account
     */
    async listByAccount(accountId: string): Promise<TestCaseModel[]> {
        const response = await apiClient.get<TestCaseModel[]>(`/v1/api/test-cases/account/${accountId}`);
        return response.data;
    },

    /**
     * Get a single test case by ID
     */
    async getById(testCaseId: string): Promise<TestCaseModel> {
        const response = await apiClient.get<TestCaseModel>(`/v1/api/test-cases/${testCaseId}`);
        return response.data;
    },

    /**
     * Get test cases by system under test
     */
    async getBySut(sutId: string): Promise<TestCaseModel[]> {
        const response = await apiClient.get<TestCaseModel[]>(`/v1/api/test-cases/sut/${sutId}`);
        return response.data;
    },

    /**
     * Get test cases by type
     */
    async getByType(testType: string): Promise<TestCaseModel[]> {
        const response = await apiClient.get<TestCaseModel[]>(`/v1/api/test-cases/type/${testType}`);
        return response.data;
    },

    /**
     * Create a new test case
     */
    async create(testCase: Omit<TestCaseModel, 'test_case_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'>): Promise<TestCaseModel> {
        const response = await apiClient.post<TestCaseModel>('/v1/api/test-cases/', testCase);
        return response.data;
    },

    /**
     * Update an existing test case
     */
    async update(testCaseId: string, testCase: Partial<TestCaseModel>): Promise<TestCaseModel> {
        const response = await apiClient.patch<TestCaseModel>(`/v1/api/test-cases/${testCaseId}`, testCase);
        return response.data;
    },

    /**
     * Deactivate a test case (soft delete)
     */
    async deactivate(testCaseId: string): Promise<void> {
        await apiClient.delete(`/v1/api/test-cases/${testCaseId}`);
    },
};

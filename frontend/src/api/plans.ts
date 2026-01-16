import { apiClient } from '../lib/axios';
import type { components } from '../types/api';

type PlanModel = components['schemas']['PlanModel'];

export const plansApi = {
    /**
     * Get all plans for the current account
     */
    async listByAccount(accountId: string): Promise<PlanModel[]> {
        const response = await apiClient.get<PlanModel[]>(`/v1/api/plans/account/${accountId}`);
        return response.data;
    },

    /**
     * Get a single plan by ID
     */
    async getById(planId: string): Promise<PlanModel> {
        const response = await apiClient.get<PlanModel>(`/v1/api/plans/${planId}`);
        return response.data;
    },

    /**
     * Create a new plan
     */
    async create(plan: Omit<PlanModel, 'plan_id' | 'created_at' | 'updated_at'>): Promise<PlanModel> {
        const response = await apiClient.post<PlanModel>('/v1/api/plans/', plan);
        return response.data;
    },

    /**
     * Update an existing plan
     */
    async update(planId: string, plan: Partial<PlanModel>): Promise<PlanModel> {
        const response = await apiClient.patch<PlanModel>(`/v1/api/plans/${planId}`, plan);
        return response.data;
    },

    /**
     * Deactivate a plan (soft delete)
     */
    async deactivate(planId: string): Promise<void> {
        await apiClient.patch(`/v1/api/plans/${planId}/deactivate`);
    },

    /**
     * Reactivate a deactivated plan
     */
    async reactivate(planId: string): Promise<void> {
        await apiClient.patch(`/v1/api/plans/${planId}/reactivate`);
    },
};

import { apiClient } from '@/lib/axios';
import type { components } from '@/types/api';

type SystemUnderTestModel = components['schemas']['SystemUnderTestModel'];

export const systemsApi = {
    listByAccount: async (accountId: string): Promise<SystemUnderTestModel[]> => {
        const response = await apiClient.get<SystemUnderTestModel[]>(
            `/v1/api/systems/account/${accountId}`
        );
        return response.data;
    },

    getById: async (sutId: string): Promise<SystemUnderTestModel> => {
        const response = await apiClient.get<SystemUnderTestModel>(`/v1/api/systems/${sutId}`);
        return response.data;
    },

    create: async (system: Omit<SystemUnderTestModel, 'sut_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'>): Promise<SystemUnderTestModel> => {
        const response = await apiClient.post<SystemUnderTestModel>('/v1/api/systems/', system);
        return response.data;
    },

    update: async (sutId: string, system: Partial<SystemUnderTestModel>): Promise<SystemUnderTestModel> => {
        const response = await apiClient.put<SystemUnderTestModel>(
            `/v1/api/systems/${sutId}`,
            system
        );
        return response.data;
    },

    deactivate: async (sutId: string): Promise<void> => {
        await apiClient.delete(`/v1/api/systems/${sutId}`);
    },
};

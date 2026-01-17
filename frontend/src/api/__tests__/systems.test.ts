import { systemsApi } from '@/api/systems';
import { server } from '@/test/mocks/server';
import type { components } from '@/types/api';
import { HttpResponse, http } from 'msw';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';

type SystemUnderTestModel = components['schemas']['SystemUnderTestModel'];

const API_URL = 'http://localhost:8080';

describe('systemsApi', () => {
    beforeAll(() => server.listen());
    afterEach(() => server.resetHandlers());
    afterAll(() => server.close());

    describe('listByAccount', () => {
        it('should fetch systems for an account', async () => {
            const systems = await systemsApi.listByAccount('acc_123');

            expect(systems).toBeInstanceOf(Array);
            expect(systems.length).toBeGreaterThan(0);
            expect(systems[0]).toHaveProperty('sut_id');
            expect(systems[0]).toHaveProperty('system_name');
            expect(systems[0]).toHaveProperty('account_id');
        });

        it('should return systems with correct structure', async () => {
            const systems = await systemsApi.listByAccount('acc_123');
            const system = systems[0];

            expect(system.sut_id).toBe('sut_1');
            expect(system.system_name).toBe('Web Application');
            expect(system.description).toBe('Main web application for the platform');
            expect(system.wiki_url).toBe('https://wiki.example.com/web-app');
            expect(system.is_active).toBe(true);
        });

        it('should handle empty account with empty array', async () => {
            server.use(
                http.get(`${API_URL}/v1/api/systems/account/:accountId`, () => {
                    return HttpResponse.json([]);
                })
            );

            const systems = await systemsApi.listByAccount('acc_empty');
            expect(systems).toEqual([]);
        });
    });

    describe('getById', () => {
        it('should fetch a single system by ID', async () => {
            const system = await systemsApi.getById('sut_1');

            expect(system).toHaveProperty('sut_id', 'sut_1');
            expect(system).toHaveProperty('system_name');
            expect(system).toHaveProperty('description');
            expect(system).toHaveProperty('wiki_url');
        });

        it('should return system with all required fields', async () => {
            const system = await systemsApi.getById('sut_1');

            expect(system.sut_id).toBeDefined();
            expect(system.system_name).toBeDefined();
            expect(system.account_id).toBeDefined();
            expect(system.owner_user_id).toBeDefined();
            expect(system.is_active).toBeDefined();
            expect(system.created_at).toBeDefined();
        });

        it('should handle system not found', async () => {
            server.use(
                http.get(`${API_URL}/v1/api/systems/:sutId`, () => {
                    return new HttpResponse(null, { status: 404 });
                })
            );

            await expect(systemsApi.getById('sut_nonexistent')).rejects.toThrow();
        });
    });

    describe('create', () => {
        it('should create a new system', async () => {
            const newSystem: Omit<
                SystemUnderTestModel,
                'sut_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'
            > = {
                system_name: 'New System',
                description: 'Test system description',
                wiki_url: 'https://wiki.example.com/new',
                account_id: 'acc_123',
                owner_user_id: 'user_123',
                is_active: true,
            };

            const created = await systemsApi.create(newSystem);

            expect(created).toHaveProperty('sut_id');
            expect(created.system_name).toBe(newSystem.system_name);
            expect(created.description).toBe(newSystem.description);
            expect(created.wiki_url).toBe(newSystem.wiki_url);
            expect(created.is_active).toBe(true);
        });

        it('should create system without optional fields', async () => {
            const newSystem: Omit<
                SystemUnderTestModel,
                'sut_id' | 'created_at' | 'updated_at' | 'deactivated_at' | 'deactivated_by_user_id'
            > = {
                system_name: 'Minimal System',
                description: null,
                wiki_url: null,
                account_id: 'acc_123',
                owner_user_id: 'user_123',
                is_active: true,
            };

            const created = await systemsApi.create(newSystem);

            expect(created).toHaveProperty('sut_id');
            expect(created.system_name).toBe('Minimal System');
        });
    });

    describe('update', () => {
        it('should update an existing system', async () => {
            const updates: Partial<SystemUnderTestModel> = {
                system_name: 'Updated System Name',
                description: 'Updated description',
            };

            const updated = await systemsApi.update('sut_1', updates);

            expect(updated.sut_id).toBe('sut_1');
            expect(updated.system_name).toBe(updates.system_name);
            expect(updated.description).toBe(updates.description);
        });

        it('should update only specified fields', async () => {
            const updates: Partial<SystemUnderTestModel> = {
                wiki_url: 'https://new-wiki.example.com',
            };

            const updated = await systemsApi.update('sut_1', updates);

            expect(updated.sut_id).toBe('sut_1');
            expect(updated.wiki_url).toBe(updates.wiki_url);
        });

        it('should handle update errors', async () => {
            server.use(
                http.put(`${API_URL}/v1/api/systems/:sutId`, () => {
                    return new HttpResponse(null, { status: 400 });
                })
            );

            await expect(
                systemsApi.update('sut_1', { system_name: 'Invalid' })
            ).rejects.toThrow();
        });
    });

    describe('deactivate', () => {
        it('should deactivate a system', async () => {
            await expect(systemsApi.deactivate('sut_1')).resolves.not.toThrow();
        });

        it('should handle deactivation errors', async () => {
            server.use(
                http.delete(`${API_URL}/v1/api/systems/:sutId`, () => {
                    return new HttpResponse(null, { status: 403 });
                })
            );

            await expect(systemsApi.deactivate('sut_1')).rejects.toThrow();
        });
    });
});

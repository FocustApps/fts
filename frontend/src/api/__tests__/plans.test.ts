import { beforeEach, describe, expect, it } from 'vitest';
import { plansApi } from '../plans';

describe('plansApi', () => {
    const mockAccountId = 'acc_123';
    const mockPlanId = 'plan_1';

    beforeEach(() => {
        // Reset any mocks if needed
    });

    describe('listByAccount', () => {
        it('should fetch plans for an account', async () => {
            const plans = await plansApi.listByAccount(mockAccountId);

            expect(plans).toBeInstanceOf(Array);
            expect(plans.length).toBeGreaterThan(0);
            expect(plans[0]).toHaveProperty('plan_id');
            expect(plans[0]).toHaveProperty('plan_name');
            expect(plans[0]).toHaveProperty('account_id');
        });

        it('should return plans with correct structure', async () => {
            const plans = await plansApi.listByAccount(mockAccountId);
            const firstPlan = plans[0];

            expect(firstPlan.plan_name).toBe('Test Plan 1');
            expect(firstPlan.status).toBe('active');
            expect(firstPlan.owner_user_id).toBe('user_123');
        });
    });

    describe('getById', () => {
        it('should fetch a single plan by ID', async () => {
            const plan = await plansApi.getById(mockPlanId);

            expect(plan).toHaveProperty('plan_id', mockPlanId);
            expect(plan).toHaveProperty('plan_name');
            expect(plan).toHaveProperty('status');
        });

        it('should return plan with all expected fields', async () => {
            const plan = await plansApi.getById(mockPlanId);

            expect(plan.plan_name).toBe('Test Plan 1');
            expect(plan.suites_ids).toBe('suite1,suite2');
            expect(plan.status).toBe('active');
            expect(plan.created_at).toBeDefined();
            expect(plan.updated_at).toBeDefined();
        });
    });

    describe('create', () => {
        it('should create a new plan', async () => {
            const newPlan = {
                plan_name: 'New Test Plan',
                suites_ids: 'suite1',
                status: 'active',
                owner_user_id: 'user_123',
                account_id: mockAccountId,
                is_active: true,
            };

            const createdPlan = await plansApi.create(newPlan);

            expect(createdPlan).toHaveProperty('plan_id');
            expect(createdPlan.plan_name).toBe(newPlan.plan_name);
            expect(createdPlan.account_id).toBe(mockAccountId);
        });

        it('should return created plan with timestamps', async () => {
            const newPlan = {
                plan_name: 'Another Plan',
                status: 'active',
                owner_user_id: 'user_123',
                account_id: mockAccountId,
                is_active: true,
            };

            const createdPlan = await plansApi.create(newPlan);

            expect(createdPlan.created_at).toBeDefined();
            expect(createdPlan.updated_at).toBeDefined();
        });
    });

    describe('update', () => {
        it('should update an existing plan', async () => {
            const updates = {
                plan_name: 'Updated Plan Name',
            };

            const updatedPlan = await plansApi.update(mockPlanId, updates);

            expect(updatedPlan).toHaveProperty('plan_id', mockPlanId);
            expect(updatedPlan.updated_at).toBeDefined();
        });

        it('should allow partial updates', async () => {
            const updates = {
                status: 'inactive' as const,
            };

            const updatedPlan = await plansApi.update(mockPlanId, updates);

            expect(updatedPlan).toHaveProperty('plan_id', mockPlanId);
        });
    });

    describe('deactivate', () => {
        it('should deactivate a plan', async () => {
            await expect(plansApi.deactivate(mockPlanId)).resolves.not.toThrow();
        });
    });

    describe('reactivate', () => {
        it('should reactivate a plan', async () => {
            await expect(plansApi.reactivate(mockPlanId)).resolves.not.toThrow();
        });
    });
});

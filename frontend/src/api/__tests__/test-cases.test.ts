import { beforeEach, describe, expect, it } from 'vitest';
import { testCasesApi } from '../test-cases';

describe('testCasesApi', () => {
    const mockAccountId = 'acc_123';
    const mockTestCaseId = 'tc_1';
    const mockSutId = 'sut_1';

    beforeEach(() => {
        // Reset any mocks if needed
    });

    describe('listByAccount', () => {
        it('should fetch test cases for an account', async () => {
            const testCases = await testCasesApi.listByAccount(mockAccountId);

            expect(testCases).toBeInstanceOf(Array);
            expect(testCases.length).toBeGreaterThan(0);
            expect(testCases[0]).toHaveProperty('test_case_id');
            expect(testCases[0]).toHaveProperty('test_name');
            expect(testCases[0]).toHaveProperty('account_id');
        });

        it('should return test cases with correct structure', async () => {
            const testCases = await testCasesApi.listByAccount(mockAccountId);
            const firstTestCase = testCases[0];

            expect(firstTestCase.test_name).toBe('Login Test');
            expect(firstTestCase.test_type).toBe('functional');
            expect(firstTestCase.is_active).toBe(true);
        });
    });

    describe('getById', () => {
        it('should fetch a single test case by ID', async () => {
            const testCase = await testCasesApi.getById(mockTestCaseId);

            expect(testCase).toHaveProperty('test_case_id', mockTestCaseId);
            expect(testCase).toHaveProperty('test_name');
            expect(testCase).toHaveProperty('test_type');
        });

        it('should return test case with all expected fields', async () => {
            const testCase = await testCasesApi.getById(mockTestCaseId);

            expect(testCase.test_name).toBe('Login Test');
            expect(testCase.description).toBe('Test user login functionality');
            expect(testCase.test_type).toBe('functional');
            expect(testCase.created_at).toBeDefined();
            expect(testCase.is_active).toBe(true);
        });
    });

    describe('getBySut', () => {
        it('should fetch test cases by system under test', async () => {
            const testCases = await testCasesApi.getBySut(mockSutId);

            expect(testCases).toBeInstanceOf(Array);
        });
    });

    describe('getByType', () => {
        it('should fetch test cases by type', async () => {
            const testCases = await testCasesApi.getByType('functional');

            expect(testCases).toBeInstanceOf(Array);
        });
    });

    describe('create', () => {
        it('should create a new test case', async () => {
            const newTestCase = {
                test_name: 'New Test Case',
                description: 'Test description',
                test_type: 'functional',
                sut_id: mockSutId,
                owner_user_id: 'user_123',
                account_id: mockAccountId,
                is_active: true,
            };

            const createdTestCase = await testCasesApi.create(newTestCase);

            expect(createdTestCase).toHaveProperty('test_case_id');
            expect(createdTestCase.test_name).toBe(newTestCase.test_name);
            expect(createdTestCase.account_id).toBe(mockAccountId);
        });

        it('should return created test case with timestamps', async () => {
            const newTestCase = {
                test_name: 'Another Test',
                test_type: 'integration',
                sut_id: mockSutId,
                owner_user_id: 'user_123',
                account_id: mockAccountId,
                is_active: true,
            };

            const createdTestCase = await testCasesApi.create(newTestCase);

            expect(createdTestCase.created_at).toBeDefined();
            expect(createdTestCase.updated_at).toBeDefined();
        });
    });

    describe('update', () => {
        it('should update an existing test case', async () => {
            const updates = {
                test_name: 'Updated Test Name',
            };

            const updatedTestCase = await testCasesApi.update(mockTestCaseId, updates);

            expect(updatedTestCase).toHaveProperty('test_case_id', mockTestCaseId);
            expect(updatedTestCase.updated_at).toBeDefined();
        });

        it('should allow partial updates', async () => {
            const updates = {
                description: 'Updated description',
            };

            const updatedTestCase = await testCasesApi.update(mockTestCaseId, updates);

            expect(updatedTestCase).toHaveProperty('test_case_id', mockTestCaseId);
        });
    });

    describe('deactivate', () => {
        it('should deactivate a test case', async () => {
            await expect(testCasesApi.deactivate(mockTestCaseId)).resolves.not.toThrow();
        });
    });
});

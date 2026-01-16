import { http, HttpResponse } from 'msw';

const API_URL = 'http://localhost:8080';

/**
 * Create a mock JWT token with the given payload
 */
function createMockJWT(payload: Record<string, unknown>): string {
    const header = { alg: 'HS256', typ: 'JWT' };
    const encodedHeader = btoa(JSON.stringify(header));
    const encodedPayload = btoa(JSON.stringify(payload));
    return `${encodedHeader}.${encodedPayload}.mock_signature`;
}

/**
 * Mock API handlers for testing
 */
export const handlers = [
    // Auth endpoints
    http.post(`${API_URL}/api/auth/login`, () => {
        const futureExp = Math.floor(Date.now() / 1000) + 86400; // 24 hours
        const mockToken = createMockJWT({
            user_id: 'user_123',
            email: 'test@example.com',
            is_admin: false,
            is_super_admin: false,
            account_id: 'acc_123',
            account_role: 'owner',
            exp: futureExp,
            jti: 'jwt_123',
        });

        return HttpResponse.json({
            access_token: mockToken,
            refresh_token: 'mock_refresh_token',
            token_type: 'bearer',
            expires_in: 86400,
        });
    }),

    http.get(`${API_URL}/api/auth/me`, () => {
        return HttpResponse.json({
            user_id: 'user_123',
            email: 'test@example.com',
            username: 'testuser',
            is_active: true,
            is_verified: true,
            created_at: '2026-01-01T00:00:00Z',
        });
    }),

    http.post(`${API_URL}/api/auth/register`, () => {
        return HttpResponse.json({
            message: 'Registration successful',
            email: 'test@example.com',
        });
    }),

    http.post(`${API_URL}/api/auth/refresh`, () => {
        const futureExp = Math.floor(Date.now() / 1000) + 86400;
        const mockToken = createMockJWT({
            user_id: 'user_123',
            email: 'test@example.com',
            is_admin: false,
            is_super_admin: false,
            account_id: 'acc_123',
            account_role: 'owner',
            exp: futureExp,
            jti: 'jwt_456',
        });

        return HttpResponse.json({
            access_token: mockToken,
            refresh_token: 'new_mock_refresh_token',
            token_type: 'bearer',
            expires_in: 86400,
        });
    }),

    http.post(`${API_URL}/api/auth/logout`, () => {
        return HttpResponse.json({ message: 'Logged out successfully' });
    }),

    // Accounts endpoints
    http.get(`${API_URL}/v1/api/accounts/`, () => {
        return HttpResponse.json([
            {
                account_id: 'acc_123',
                account_name: 'Test Account',
                owner_user_id: 'user_123',
                is_active: true,
                created_at: '2026-01-01T00:00:00Z',
            },
        ]);
    }),

    http.get(`${API_URL}/v1/api/accounts/:accountId`, ({ params }) => {
        return HttpResponse.json({
            account_id: params.accountId,
            account_name: 'Test Account',
            owner_user_id: 'user_123',
            owner_email: 'owner@example.com',
            owner_username: 'testowner',
            is_active: true,
            logo_url: null,
            primary_contact: null,
            subscription_id: null,
            user_count: 5,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: null,
        });
    }),

    http.post(`${API_URL}/v1/api/accounts/`, () => {
        return HttpResponse.json({
            account_id: 'acc_new',
            account_name: 'New Account',
            owner_user_id: 'user_123',
            is_active: true,
            created_at: '2026-01-15T00:00:00Z',
        });
    }),

    http.put(`${API_URL}/v1/api/accounts/:id`, () => {
        return HttpResponse.json({
            message: 'Account updated successfully',
        });
    }),

    http.delete(`${API_URL}/v1/api/accounts/:id`, () => {
        return HttpResponse.json({
            message: 'Account deactivated successfully',
        });
    }),

    // Users endpoints
    http.get(`${API_URL}/v1/api/users/me/accounts`, () => {
        return HttpResponse.json([
            {
                account_id: 'acc_123',
                account_name: 'Test Account',
                role: 'owner',
                is_primary: true,
                is_active: true,
            },
        ]);
    }),

    http.get(`${API_URL}/v1/api/users/me/current-account`, () => {
        return HttpResponse.json({
            account_id: 'acc_123',
            account_name: 'Test Account',
            role: 'owner',
            is_primary: true,
        });
    }),

    http.post(`${API_URL}/v1/api/users/me/switch-account`, () => {
        return HttpResponse.json({
            success: true,
            account_id: 'acc_456',
            account_name: 'Other Account',
            message: 'Switched to Other Account',
        });
    }),

    http.get(`${API_URL}/v1/api/auth-users/users`, () => {
        return HttpResponse.json([
            {
                user_id: 'user-1',
                email: 'owner@example.com',
                username: 'owner',
                is_active: true,
                is_super_admin: false,
                created_at: '2024-01-01T00:00:00Z',
            },
            {
                user_id: 'user-2',
                email: 'admin@example.com',
                username: 'admin',
                is_active: true,
                is_super_admin: false,
                created_at: '2024-01-02T00:00:00Z',
            },
        ]);
    }),

    // Notifications endpoints
    http.get(`${API_URL}/v1/api/users/me/notifications`, () => {
        return HttpResponse.json([
            {
                notification_id: 'notif_123',
                auth_user_id: 'user_123',
                notification_type: 'account_added',
                title: 'Welcome!',
                message: 'You have been added to Test Account',
                action_url: null,
                is_read: false,
                read_at: null,
                created_at: '2026-01-15T00:00:00Z',
                expires_at: null,
            },
        ]);
    }),

    http.get(`${API_URL}/v1/api/users/me/notifications/unread-count`, () => {
        return HttpResponse.json({ unread_count: 3 });
    }),

    http.put(`${API_URL}/v1/api/users/me/notifications/:notificationId/read`, () => {
        return HttpResponse.json({ message: 'Marked as read' });
    }),

    http.put(`${API_URL}/v1/api/users/me/notifications/read-all`, () => {
        return HttpResponse.json({ marked_count: 3 });
    }),

    // Plans endpoints
    http.get(`${API_URL}/v1/api/plans/account/:accountId`, () => {
        return HttpResponse.json([
            {
                plan_id: 'plan_1',
                plan_name: 'Test Plan 1',
                suites_ids: 'suite1,suite2',
                suite_tags: null,
                status: 'active',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                created_at: '2026-01-01T00:00:00Z',
                updated_at: '2026-01-01T00:00:00Z',
            },
            {
                plan_id: 'plan_2',
                plan_name: 'Test Plan 2',
                suites_ids: null,
                suite_tags: null,
                status: 'inactive',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                created_at: '2026-01-02T00:00:00Z',
                updated_at: '2026-01-02T00:00:00Z',
            },
        ]);
    }),

    http.get(`${API_URL}/v1/api/plans/:planId`, ({ params }) => {
        const { planId } = params;
        return HttpResponse.json({
            plan_id: planId,
            plan_name: 'Test Plan 1',
            suites_ids: 'suite1,suite2',
            suite_tags: null,
            status: 'active',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        });
    }),

    http.post(`${API_URL}/v1/api/plans/`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
            plan_id: 'plan_new',
            ...body,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        });
    }),

    http.patch(`${API_URL}/v1/api/plans/:planId`, async ({ params, request }) => {
        const { planId } = params;
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
            plan_id: planId,
            plan_name: 'Updated Plan',
            ...body,
            updated_at: new Date().toISOString(),
        });
    }),

    http.patch(`${API_URL}/v1/api/plans/:planId/deactivate`, () => {
        return HttpResponse.json({ message: 'Plan deactivated' });
    }),

    http.patch(`${API_URL}/v1/api/plans/:planId/reactivate`, () => {
        return HttpResponse.json({ message: 'Plan reactivated' });
    }),

    // Test Cases endpoints
    http.get(`${API_URL}/v1/api/test-cases/account/:accountId`, () => {
        return HttpResponse.json([
            {
                test_case_id: 'tc_1',
                test_name: 'Login Test',
                description: 'Test user login functionality',
                test_type: 'functional',
                sut_id: 'sut_1',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-01T00:00:00Z',
                updated_at: '2026-01-01T00:00:00Z',
            },
            {
                test_case_id: 'tc_2',
                test_name: 'Logout Test',
                description: 'Test user logout functionality',
                test_type: 'functional',
                sut_id: 'sut_1',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-02T00:00:00Z',
                updated_at: '2026-01-02T00:00:00Z',
            },
        ]);
    }),

    http.get(`${API_URL}/v1/api/test-cases/:testCaseId`, ({ params }) => {
        const { testCaseId } = params;
        return HttpResponse.json({
            test_case_id: testCaseId,
            test_name: 'Login Test',
            description: 'Test user login functionality',
            test_type: 'functional',
            sut_id: 'sut_1',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        });
    }),

    http.post(`${API_URL}/v1/api/test-cases/`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
            test_case_id: 'tc_new',
            ...body,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        });
    }),

    http.patch(`${API_URL}/v1/api/test-cases/:testCaseId`, async ({ params, request }) => {
        const { testCaseId } = params;
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
            test_case_id: testCaseId,
            test_name: 'Updated Test',
            ...body,
            updated_at: new Date().toISOString(),
        });
    }),

    http.delete(`${API_URL}/v1/api/test-cases/:testCaseId`, () => {
        return HttpResponse.json({ message: 'Test case deactivated' });
    }),

    // Get test cases by system under test
    http.get(`${API_URL}/v1/api/test-cases/sut/:sutId`, () => {
        return HttpResponse.json([
            {
                test_case_id: 'tc_1',
                test_name: 'Login Test',
                description: 'Test user login functionality',
                test_type: 'functional',
                sut_id: 'sut_1',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-01T00:00:00Z',
                updated_at: '2026-01-01T00:00:00Z',
            },
        ]);
    }),

    // Get test cases by type
    http.get(`${API_URL}/v1/api/test-cases/type/:testType`, () => {
        return HttpResponse.json([
            {
                test_case_id: 'tc_1',
                test_name: 'Login Test',
                description: 'Test user login functionality',
                test_type: 'functional',
                sut_id: 'sut_1',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-01T00:00:00Z',
                updated_at: '2026-01-01T00:00:00Z',
            },
        ]);
    }),

    // Systems Under Test endpoints
    http.get(`${API_URL}/v1/api/systems/account/:accountId`, () => {
        return HttpResponse.json([
            {
                sut_id: 'sut_1',
                system_name: 'Web Application',
                description: 'Main web application for the platform',
                wiki_url: 'https://wiki.example.com/web-app',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-01T00:00:00Z',
                updated_at: '2026-01-01T00:00:00Z',
            },
            {
                sut_id: 'sut_2',
                system_name: 'Mobile App',
                description: 'iOS and Android mobile application',
                wiki_url: 'https://wiki.example.com/mobile-app',
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-02T00:00:00Z',
                updated_at: '2026-01-02T00:00:00Z',
            },
            {
                sut_id: 'sut_3',
                system_name: 'REST API',
                description: 'Backend REST API services',
                wiki_url: null,
                owner_user_id: 'user_123',
                account_id: 'acc_123',
                is_active: true,
                deactivated_at: null,
                deactivated_by_user_id: null,
                created_at: '2026-01-03T00:00:00Z',
                updated_at: '2026-01-03T00:00:00Z',
            },
        ]);
    }),

    http.get(`${API_URL}/v1/api/systems/:sutId`, ({ params }) => {
        return HttpResponse.json({
            sut_id: params.sutId as string,
            system_name: 'Web Application',
            description: 'Main web application for the platform',
            wiki_url: 'https://wiki.example.com/web-app',
            owner_user_id: 'user_123',
            account_id: 'acc_123',
            is_active: true,
            deactivated_at: null,
            deactivated_by_user_id: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
        });
    }),

    http.post(`${API_URL}/v1/api/systems/`, async ({ request }) => {
        const body = await request.json();
        return HttpResponse.json({
            sut_id: 'sut_new',
            ...(body as Record<string, unknown>),
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        });
    }),

    http.put(`${API_URL}/v1/api/systems/:sutId`, async ({ params, request }) => {
        const body = await request.json();
        return HttpResponse.json({
            sut_id: params.sutId as string,
            ...(body as Record<string, unknown>),
            updated_at: new Date().toISOString(),
        });
    }),

    http.delete(`${API_URL}/v1/api/systems/:sutId`, () => {
        return HttpResponse.json({ message: 'System deactivated' });
    }),
];

import { beforeEach, describe, expect, it } from 'vitest';
import { accountsApi, tokenManager } from '../../api';

describe('accountsApi', () => {
    beforeEach(() => {
        // Set up valid token for authenticated requests
        const futureExp = Math.floor(Date.now() / 1000) + 3600;
        const validToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
            JSON.stringify({ exp: futureExp })
        )}.xyz`;
        tokenManager.setTokens(validToken, 'refresh_token', false);
    });

    describe('listAll', () => {
        it('should list all accounts', async () => {
            const accounts = await accountsApi.listAll();

            expect(accounts).toHaveLength(1);
            expect(accounts[0].account_id).toBe('acc_123');
            expect(accounts[0].account_name).toBe('Test Account');
            expect(accounts[0].is_active).toBe(true);
        });
    });

    describe('getById', () => {
        it('should get account details by ID', async () => {
            const account = await accountsApi.getById('acc_123');

            expect(account.account_id).toBe('acc_123');
            expect(account.account_name).toBe('Test Account');
            expect(account.owner_email).toBe('owner@example.com');
            expect(account.user_count).toBe(5);
        });
    });

    describe('create', () => {
        it('should create a new account', async () => {
            const newAccount = await accountsApi.create({
                account_name: 'New Account',
            });

            expect(newAccount.account_id).toBe('acc_new');
            expect(newAccount.account_name).toBe('New Account');
            expect(newAccount.is_active).toBe(true);
        });
    });

    describe('update', () => {
        it('should update an existing account', async () => {
            const updated = await accountsApi.update('acc_123', {
                account_name: 'Updated Account',
                logo_url: 'https://example.com/logo.png',
            });

            expect(updated).toBeDefined();
        });
    });

    describe('deactivate', () => {
        it('should deactivate an account', async () => {
            const result = await accountsApi.deactivate('acc_123');

            expect(result).toBeDefined();
        });
    });
});

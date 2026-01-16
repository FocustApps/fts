# Frontend Testing Guide

## Overview

The Fenrir frontend uses **Vitest** as the test runner with **React Testing Library** for component testing and **Mock Service Worker (MSW)** for API mocking. This provides fast, reliable tests that closely simulate real user interactions.

## Tech Stack

- **Vitest 4.0.17** - Test runner (10-20x faster than Jest, native Vite integration)
- **@testing-library/react** - Component testing utilities
- **@testing-library/jest-dom** - Custom matchers (toBeInTheDocument, etc.)
- **@testing-library/user-event** - Realistic user interaction simulation
- **happy-dom** - Fast DOM environment (lighter than jsdom)
- **MSW 2.12.7** - API mocking at the network level

## Running Tests

```bash
# Watch mode (re-runs tests on file changes)
npm test

# Single run (useful for CI)
npm run test:run

# Visual test UI dashboard
npm run test:ui

# Coverage report
npm run test:coverage
```

## Project Structure

```
frontend/src/
├── api/
│   ├── __tests__/
│   │   ├── auth.test.ts          # Auth API tests (9 tests)
│   │   └── accounts.test.ts       # Accounts API tests (5 tests)
│   ├── auth.ts
│   ├── accounts.ts
│   └── ...
├── lib/
│   ├── __tests__/
│   │   └── axios.test.ts          # Token management tests (10 tests)
│   ├── axios.ts
│   └── utils.ts
└── test/
    ├── setup.ts                    # Global test setup
    ├── utils.tsx                   # Custom render function
    └── mocks/
        ├── handlers.ts             # MSW API handlers
        └── server.ts               # MSW server config
```

## Writing Tests

### API Tests

For testing API wrapper functions, use MSW to mock responses:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { authApi } from '../../api';

describe('authApi', () => {
  beforeEach(() => {
    // Clear storage before each test
    sessionStorage.clear();
    localStorage.clear();
  });

  it('should login successfully', async () => {
    const result = await authApi.login({
      email: 'test@example.com',
      password: 'password123',
      remember_me: false,
    });

    expect(result.access_token).toBe('mock_access_token');
    expect(result.token_type).toBe('bearer');
  });
});
```

### Component Tests

For testing React components, use `renderWithProviders` to wrap with necessary providers:

```typescript
import { describe, it, expect } from 'vitest';
import { renderWithProviders, screen, userEvent } from '@/test/utils';
import { LoginForm } from './LoginForm';

describe('LoginForm', () => {
  it('should submit form with user credentials', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    // Assert on outcome
    expect(await screen.findByText(/welcome/i)).toBeInTheDocument();
  });
});
```

### Testing Authenticated Requests

When testing API functions that require authentication, set up a valid token first:

```typescript
import { tokenManager } from '../../api';

beforeEach(() => {
  // Create a valid token that expires in 1 hour
  const futureExp = Math.floor(Date.now() / 1000) + 3600;
  const validToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(
    JSON.stringify({ exp: futureExp })
  )}.xyz`;
  tokenManager.setTokens(validToken, 'refresh_token', false);
});
```

## MSW Handlers

API mocks are defined in [src/test/mocks/handlers.ts](src/test/mocks/handlers.ts):

```typescript
import { http, HttpResponse } from 'msw';

const API_URL = 'http://localhost:8080';

export const handlers = [
  http.post(`${API_URL}/v1/api/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock_access_token',
      refresh_token: 'mock_refresh_token',
      token_type: 'bearer',
    });
  }),

  http.get(`${API_URL}/v1/api/accounts/`, () => {
    return HttpResponse.json([
      {
        account_id: 'acc_123',
        account_name: 'Test Account',
        is_active: true,
      },
    ]);
  }),

  // Add more handlers as needed...
];
```

### Overriding Handlers in Tests

To test error cases or specific responses, override handlers in individual tests:

```typescript
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

it('should handle login error', async () => {
  server.use(
    http.post('http://localhost:8080/v1/api/auth/login', () => {
      return HttpResponse.json(
        { detail: 'Invalid credentials' },
        { status: 401 }
      );
    })
  );

  await expect(
    authApi.login({ email: 'test@example.com', password: 'wrong' })
  ).rejects.toThrow();
});
```

## Custom Test Utilities

[src/test/utils.tsx](src/test/utils.tsx) provides helpful utilities:

### `renderWithProviders(component, options?)`

Wraps component with QueryClientProvider and other necessary providers:

```typescript
const { container } = renderWithProviders(<MyComponent />, {
  queryClient: customQueryClient, // optional custom client
});
```

### `createTestQueryClient()`

Creates a QueryClient configured for testing (no retries, no cache):

```typescript
const queryClient = createTestQueryClient();
```

### `waitForPromises()`

Helper to wait for all pending promises to resolve:

```typescript
await waitForPromises();
```

## Code Coverage

Current coverage: **55% overall**

- API layer: 48% (will increase as more API wrappers are tested)
- Lib layer: 60% (good coverage of axios and token management)

Coverage reports are generated in `coverage/` directory when running `npm run test:coverage`.

## Best Practices

### ✅ DO

- Use `screen` queries from @testing-library/react for finding elements
- Test user-facing behavior, not implementation details
- Use `userEvent` for simulating interactions (not `fireEvent`)
- Clear storage (sessionStorage, localStorage) in `beforeEach` hooks
- Test both success and error cases
- Use MSW handlers for all API mocking
- Write descriptive test names using "should..."

### ❌ DON'T

- Access component internals or state directly
- Use `waitFor` with side effects (use query assertions instead)
- Mock axios directly (use MSW handlers)
- Hardcode delays with `setTimeout` (use `waitFor` or `findBy*`)
- Test implementation details like function calls or state changes
- Leave API calls unmocked (will cause test failures)

## Debugging Tests

### Run Single Test File

```bash
npm test src/api/__tests__/auth.test.ts
```

### Run Tests Matching Pattern

```bash
npm test -- --reporter=verbose --grep "should login"
```

### Debug in VS Code

Add breakpoints and use the "Vitest" debug configuration:

```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Vitest Tests",
  "runtimeExecutable": "npm",
  "runtimeArgs": ["run", "test"],
  "console": "integratedTerminal"
}
```

### View Coverage HTML Report

```bash
npm run test:coverage
open coverage/index.html
```

## CI/CD Integration

Tests run automatically on:

- Pull requests
- Pushes to main/dev branches
- Before deployments

Example GitHub Actions workflow:

```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run test:run
```

## Current Test Status

✅ **24 tests passing** across 3 test files:

- `src/lib/__tests__/axios.test.ts` - 10 tests (token management, expiry checks)
- `src/api/__tests__/auth.test.ts` - 9 tests (login, register, logout, refresh)
- `src/api/__tests__/accounts.test.ts` - 5 tests (CRUD operations)

## Next Steps

1. Add tests for remaining API wrappers (users, notifications)
2. Add component tests for UI components as they're built
3. Add integration tests for complete user flows
4. Set up visual regression testing (optional)
5. Configure test coverage thresholds in CI

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [MSW Documentation](https://mswjs.io/)
- [Testing Library Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

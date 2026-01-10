# Fenrir Scripts

Utility scripts for development, testing, and data seeding.

## Authentication Scripts

### get_jwt_token.py

**NEW** - Generates JWT access tokens for API authentication.

```bash
python app/scripts/get_jwt_token.py
```

**Features:**

- Logs in with admin credentials from `.env` (EMAIL_RECIPIENT)
- Returns JWT access token valid for 24 hours
- Tests token validity automatically
- Saves token to `/tmp/fenrir_jwt_token.txt` for use by other scripts

**Environment Variables:**

- `EMAIL_RECIPIENT` - Admin email (default: <admin@example.com>)
- `ADMIN_PASSWORD` - Admin password (default: admin123)
- `FENRIR_JWT_TOKEN` - Override token (for testing)

**Example Output:**

```
🔑 JWT Token Generator
========================================
📧 Admin email: admin@example.com
🔄 Logging in to get JWT token...
✅ Successfully obtained JWT token

🧪 Testing token validity...
✅ TOKEN VERIFIED - This token works!
📊 Found 4 environments

================================================================================
🎉 SUCCESS: Use this token for all API calls:
================================================================================
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
================================================================================
```

### test_auth.py

Tests JWT authentication with current token.

```bash
python app/scripts/test_auth.py
```

**Features:**

- Reads token from `/tmp/fenrir_jwt_token.txt`
- Tests authentication against `/v1/env/api/` endpoint
- Uses `Authorization: Bearer <token>` header

**Example Output:**

```
🔍 Testing JWT authentication...
📁 Found token in: /tmp/fenrir_jwt_token.txt
🔑 Using JWT token: eyJhbGciOiJIUzI1Ni...
📡 Response status: 200
✅ Authentication successful!
```

## Data Seeding

### seed_local_environment.py

Seeds test data into local development environment.

```bash
python app/scripts/seed_local_environment.py
```

**Features:**

- Automatically logs in with admin credentials
- Creates sample environments, users, pages, identifiers
- Validates seeding results
- Skips existing data to avoid duplicates

**Requirements:**

- Application running at `http://localhost:8080`
- Admin user exists (created by migrations)
- `ENVIRONMENT=local` in `.env`

**What it seeds:**

- **4 Environments**: Development, Staging, QA, Local
- **4 Users**: dev_user, qa_tester, staging_user, local_dev
- **6 Pages**: Login, Dashboard, Profile, Settings, Admin, Reports
- **10+ Identifiers**: Web elements linked to pages

**Example Output:**

```
Starting local environment seeding...
Authentication token retrieved
Waiting for application to be ready...
✓ Application is ready

Seeding environments...
✓ Environment 'Development' created with ID: abc123
✓ Environment 'Staging' created with ID: def456
...

🎉 All seeding validation checks passed!
```

## Migration from Legacy Auth

The following changes were made to support JWT authentication:

### Removed

- ❌ `get_multiuser_token.py` - Used legacy multi_user_auth_service
- ❌ `X-Auth-Token` header format

### Updated

- ✅ `get_jwt_token.py` - NEW script using JWT login endpoint
- ✅ `test_auth.py` - Now uses `Authorization: Bearer <token>`
- ✅ `seed_local_environment.py` - Uses JWT authentication

### Key Differences

| Aspect | Legacy (Multi-User Auth) | New (JWT Auth) |
|--------|--------------------------|----------------|
| **Token Generation** | `auth_service.generate_user_token()` | `POST /v1/api/auth/login` |
| **Header Format** | `X-Auth-Token: <token>` | `Authorization: Bearer <token>` |
| **Token Expiry** | Manual expiry check | Automatic (24 hours) |
| **Token Type** | Custom string | JWT (signed, verified) |
| **Refresh** | Generate new token | Use refresh token endpoint |

## Development Workflow

1. **Start the application:**

   ```bash
   sh run-fenrir-app.sh
   ```

2. **Get JWT token:**

   ```bash
   python app/scripts/get_jwt_token.py
   ```

3. **Seed test data:**

   ```bash
   python app/scripts/seed_local_environment.py
   ```

4. **Test authentication:**

   ```bash
   python app/scripts/test_auth.py
   ```

5. **Use token in API calls:**

   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:8080/v1/env/api/
   ```

## Troubleshooting

### "Login failed: Invalid credentials"

- Check `EMAIL_RECIPIENT` in `.env` matches an existing user
- Verify admin user was created by migrations
- Try default credentials: `admin@example.com:admin123`

### "Could not connect to application"

- Ensure application is running: `docker-compose ps`
- Check application logs: `docker-compose logs -f app`
- Verify BASE_URL in script matches your setup

### "Token test failed: 401"

- Token may have expired (24-hour lifetime)
- Generate new token: `python app/scripts/get_jwt_token.py`
- Check token is being sent in Authorization header

### Seeding fails with 401 errors

- Run `get_jwt_token.py` first to get valid token
- Check token is saved to `/tmp/fenrir_jwt_token.txt`
- Verify admin user has proper permissions (is_admin=true)

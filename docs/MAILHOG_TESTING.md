# MailHog Email Testing

MailHog is integrated into the Fenrir Testing System for local email testing and validation.

## 🎯 What is MailHog?

MailHog is an email testing tool for developers:

- **SMTP Server**: Catches all outgoing emails (port 1025)
- **Web UI**: View emails in browser (<http://localhost:8025>)
- **API**: Programmatically access emails for test assertions

## 🚀 Quick Start

### Start Services with MailHog

```bash
# Run locally with MailHog
sh run-fenrir-app.sh

# Or manually with profile
docker compose --profile local up -d
```

**Access Points:**

- 📧 MailHog Web UI: <http://localhost:8025>
- 🌐 Fenrir App: <http://localhost:8080>
- 🗄️ PostgreSQL: localhost:5432

### Run Tests with MailHog

```bash
# Tests automatically use MailHog when running in Docker
sh run-tests.sh tests/auth/

# Or run specific email tests
sh run-tests.sh tests/auth/test_multi_user_auth_service.py -v
```

## 📝 Architecture

### Email Service Interface

Fenrir uses a **factory pattern** for email services:

```python
from app.services.email_interface import get_email_service

# Automatically returns MailHogService or SMTPService based on config
email_service = get_email_service()

### Configuration

**Environment Variables:**

```bash
# Enable MailHog (defaults in docker-compose for local/test)
USE_MAILHOG=true
SMTP_SERVER=mailhog
SMTP_PORT=1025
MAILHOG_API_URL=http://mailhog:8025

# For production (USE_MAILHOG=false)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

## 🧪 Writing Tests with MailHog

### Basic Email Assertion

```python
def test_user_registration_sends_email(mailhog):
    """Test that user registration sends welcome email."""
    # Perform action that sends email
    response = register_user(email="newuser@test.com")
    
    # Assert email was sent
    message = mailhog.assert_email_sent(
        to_email="newuser@test.com",
        subject="Welcome",
        timeout=5
    )
    
    # Verify email content
    body = mailhog.get_email_body(message)
    assert "Welcome to Fenrir" in body
```

### Token Extraction

```python
def test_token_email_contains_valid_token(mailhog):
    """Test that token email contains extractable token."""
    # Trigger token generation
    generate_user_token(email="user@test.com")
    
    # Wait for email and extract token
    message, token = mailhog.assert_token_email_sent(
        to_email="user@test.com",
        timeout=10
    )
    
    # Validate token format
    assert len(token) == 64  # 256-bit token
    assert token.isalnum()
    
    # Use token for authentication
    response = authenticate_with_token(token)
    assert response.status_code == 200
```

### Email Search and Filtering

```python
def test_multiple_user_emails(mailhog):
    """Test searching for specific emails."""
    # Send emails to multiple users
    for i in range(3):
        send_notification(email=f"user{i}@test.com")
    
    # Search by recipient
    emails = mailhog.search_emails(to_email="user1@test.com")
    assert len(emails) == 1
    
    # Search by subject
    token_emails = mailhog.search_emails(subject="Token")
    assert len(token_emails) >= 1
    
    # Get latest email
    latest = mailhog.get_latest_email()
    assert latest is not None
```

### Cleanup Between Tests

```python
def test_with_clean_mailbox(mailhog):
    """Each test gets fresh mailbox (mailhog fixture auto-clears)."""
    # Mailbox is empty at start
    all_emails = mailhog.get_all_emails()
    assert len(all_emails) == 0
    
    # Send test email
    send_test_email("test@example.com")
    
    # Only this email present
    all_emails = mailhog.get_all_emails()
    assert len(all_emails) == 1
```

## 📚 MailHogTestHelper API

### Core Methods

**`clear_all_emails()`**

- Clear all emails from MailHog
- Called automatically by fixture

**`wait_for_email(to_email=None, subject=None, timeout=10)`**

- Wait for email matching criteria
- Returns: Message dict or None
- Use for async email sending

**`get_latest_email(to_email=None)`**

- Get most recent email
- Optional filter by recipient
- Returns: Message dict or None

**`get_all_emails()`**

- Retrieve all emails
- Returns: List of message dicts

**`search_emails(subject=None, to_email=None)`**

- Search with multiple filters
- Returns: List of matching messages

**`get_email_body(message)`**

- Extract plain text body
- Args: Message dict
- Returns: String body content

**`extract_token_from_email(message)`**

- Extract token from email body
- Searches for "Token: <token>" pattern
- Returns: Token string or None

### Assertion Methods

**`assert_email_sent(to_email, subject=None, timeout=10)`**

- Assert email was sent
- Raises AssertionError if not found
- Returns: Message dict

**`assert_token_email_sent(to_email, timeout=10)`**

- Assert token email sent AND extract token
- Returns: Tuple of (message, token)
- Raises AssertionError if email or token not found

## 🔧 Troubleshooting

### MailHog Not Starting

```bash
# Check if MailHog is running
docker compose ps mailhog

# View MailHog logs
docker compose logs mailhog

# Restart MailHog
docker compose restart mailhog
```

### Emails Not Appearing

1. **Check Configuration:**

   ```bash
   docker compose exec fenrir env | grep -E "SMTP|MAILHOG|EMAIL"
   ```

2. **Verify Network Connectivity:**

   ```bash
   docker compose exec fenrir ping -c 3 mailhog
   ```

3. **Check Application Logs:**

   ```bash
   docker compose logs fenrir | grep -i email
   ```

### Tests Can't Connect to MailHog

```python
# Add this to your test to debug
def test_mailhog_connectivity(mailhog):
    assert mailhog.mailhog.is_available(), "MailHog not available"
    print(f"MailHog API URL: {mailhog.mailhog.config.mailhog_api_url}")
```

### Clear MailHog Manually

```bash
# Via API
curl -X DELETE http://localhost:8025/api/v1/messages

# Or restart container
docker compose restart mailhog
```

## 🎓 Best Practices

### 1. Use Fixture for Clean State

```python
def test_something(mailhog):
    # mailhog fixture auto-clears before test
    pass
```

### 2. Set Reasonable Timeouts

```python
# Good: Account for async processing
message = mailhog.wait_for_email(to_email="user@test.com", timeout=10)

# Bad: Too short, may flake
message = mailhog.wait_for_email(to_email="user@test.com", timeout=1)
```

### 3. Use Specific Assertions

```python
# Good: Clear error messages
message, token = mailhog.assert_token_email_sent("user@test.com")

# Less clear: Generic assertion
message = mailhog.wait_for_email("user@test.com")
assert message is not None
```

### 4. Search Before Asserting Multiple Emails

```python
# When sending to multiple recipients
emails = mailhog.search_emails(subject="Notification")
assert len(emails) == 3
for email in emails:
    assert "important" in mailhog.get_email_body(email)
```

## 🔄 Migration from Mock Emails

### Before (Mocked)

```python
@patch('app.services.email_service.smtplib.SMTP_SSL')
def test_email_sent(mock_smtp):
    send_email("user@test.com")
    assert mock_smtp.called
```

### After (MailHog)

```python
def test_email_sent(mailhog):
    send_email("user@test.com")
    message = mailhog.assert_email_sent("user@test.com")
    assert "Welcome" in mailhog.get_email_body(message)
```

**Benefits:**

- ✅ Tests actual SMTP sending
- ✅ Validates email content
- ✅ Can extract and test tokens
- ✅ Catches email formatting issues
- ✅ No mocking complexity

## 📊 Example Test Suite

```python
import pytest

class TestUserAuthentication:
    """Test suite demonstrating MailHog usage."""
    
    def test_new_user_receives_welcome_email(self, mailhog, engine):
        """New users get welcome email with token."""
        # Create user
        user = create_user(email="newuser@test.com", name="New User")
        
        # Assert welcome email sent
        message, token = mailhog.assert_token_email_sent(
            to_email="newuser@test.com",
            timeout=5
        )
        
        # Verify email content
        body = mailhog.get_email_body(message)
        assert "Welcome to the Fenrir Testing System, New User!" in body
        assert len(token) == 64
    
    def test_token_rotation_sends_notification(self, mailhog):
        """Token rotation triggers email notification."""
        # Rotate token
        new_token = rotate_auth_token()
        
        # Wait for email
        message = mailhog.wait_for_email(
            subject="New Authentication Token",
            timeout=10
        )
        
        assert message is not None
        body = mailhog.get_email_body(message)
        assert new_token in body
    
    def test_multiple_users_receive_unique_tokens(self, mailhog, engine):
        """Each user gets unique token via email."""
        users = [
            create_user(email=f"user{i}@test.com")
            for i in range(3)
        ]
        
        tokens = set()
        for user in users:
            message, token = mailhog.assert_token_email_sent(
                to_email=user.email,
                timeout=5
            )
            tokens.add(token)
        
        # All tokens unique
        assert len(tokens) == 3
```

## 🌐 Production vs Local

### Local Development (MailHog)

- ✅ All emails captured
- ✅ No external SMTP needed
- ✅ Easy to inspect and test
- ✅ No risk of sending real emails
- ⚠️ Requires Docker

### Production (SMTP)

- ✅ Real email delivery
- ✅ Works in cloud environments
- ⚠️ Requires SMTP credentials
- ⚠️ Rate limits apply

**Switch automatically via config:**

```bash
# Local
USE_MAILHOG=true

# Production
USE_MAILHOG=false
SMTP_SERVER=smtp.gmail.com
```

## 📖 Additional Resources

- [MailHog GitHub](https://github.com/mailhog/MailHog)
- [SMTP Testing Best Practices](https://mailtrap.io/blog/smtp-test/)
- [Fenrir Email Service Code](../app/services/email_interface.py)

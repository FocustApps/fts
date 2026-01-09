# MailHog Email Testing - Quick Reference

## ✅ What Was Added

### 1. **MailHog Service** (docker-compose.yml)

- SMTP Server: `localhost:1025`
- Web UI: `http://localhost:8025`
- Runs with `--profile local` and `--profile test`

### 2. **Email Service Interface** (app/services/)

- `email_interface.py` - Abstract interface
- `smtp_service.py` - Production SMTP (Gmail, Office365)
- `mailhog_service.py` - MailHog implementation
- Factory pattern: `get_email_service()` auto-selects based on config

### 3. **Test Utilities** (tests/fixtures/)

- `mailhog_helper.py` - MailHogTestHelper class
- `mailhog` pytest fixture (auto-clears emails)
- Email search, token extraction, assertions

### 4. **Configuration** (app/config.py)

```python
use_mailhog: bool  # Enable MailHog mode
mailhog_api_url: str  # API endpoint
```

### 5. **Example Tests** (tests/infrastructure/)

- `test_mailhog_examples.py` - 9 comprehensive examples
- All tests passing ✅

## 🚀 Usage

### Start Services with MailHog

```bash
sh run-fenrir-app.sh
# Opens: http://localhost:8025 (MailHog UI)
```

### Run Tests with Email Validation

```bash
# Run all tests (MailHog auto-starts)
sh run-tests.sh

# Run specific email tests
sh run-tests.sh tests/auth/test_multi_user_auth_service.py
```

### Access MailHog Web UI

- Local: <http://localhost:8025>
- View all captured emails
- Search by recipient/subject
- Inspect email content

## 📝 Writing Tests

```python
def test_user_receives_token_email(mailhog):
    """Test email sending and validation."""
    # Send email
    send_multiuser_token_notification(
        user_email="test@example.com",
        token="abc123..." ,
        is_new_user=True
    )
    
    # Assert and extract token
    message, token = mailhog.assert_token_email_sent(
        to_email="test@example.com",
        timeout=5
    )
    
    # Validate content
    body = mailhog.get_email_body(message)
    assert "Welcome" in body
    assert len(token) == 64
```

## 🔧 Key Methods

**MailHogTestHelper:**

- `assert_email_sent(to_email, subject, timeout)` - Assert email received
- `assert_token_email_sent(to_email, timeout)` - Get email + extract token
- `wait_for_email(to_email, subject, timeout)` - Wait for async email
- `search_emails(subject, to_email)` - Filter emails
- `get_all_emails()` - List all emails
- `clear_all_emails()` - Reset (auto-called by fixture)
- `extract_token_from_email(message)` - Parse token from body

## 🎯 Benefits

✅ **Real SMTP Testing** - Actual email sending, not mocks
✅ **Content Validation** - Inspect email body, subject, headers
✅ **Token Extraction** - Parse and use tokens in tests
✅ **No External Services** - No Gmail credentials needed locally
✅ **Visual Inspection** - Web UI for debugging (port 8025)
✅ **CI/CD Ready** - Same setup works in pipelines

## 📊 Test Results

```bash
# All MailHog example tests passing
tests/infrastructure/test_mailhog_examples.py::TestMailHogIntegration
  ✅ test_mailhog_is_available
  ✅ test_mailbox_starts_empty
  ✅ test_send_simple_email
  ✅ test_send_token_notification_email
  ✅ test_search_multiple_emails
  ✅ test_token_extraction_from_email_body
  ✅ test_assert_email_sent_with_timeout
  ✅ test_email_not_found_raises_assertion_error
  ✅ test_welcome_email_vs_token_refresh

9 passed in 2.64s ✅
```

## 🔄 Production vs Local

### Local (MailHog)

```bash
USE_MAILHOG=true
SMTP_SERVER=mailhog
SMTP_PORT=1025
```

### Production (Real SMTP)

```bash
USE_MAILHOG=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

## 📚 Documentation

- Full Guide: [docs/MAILHOG_TESTING.md](../docs/MAILHOG_TESTING.md)
- Example Tests: [tests/infrastructure/test_mailhog_examples.py](../tests/infrastructure/test_mailhog_examples.py)
- Email Interface: [app/services/email_interface.py](../app/services/email_interface.py)

## 🎉 Success Metrics

- ✅ MailHog service running in Docker
- ✅ Email interface abstraction complete
- ✅ 9 example tests passing
- ✅ Test fixture working correctly
- ✅ Token extraction validated
- ✅ Web UI accessible at <http://localhost:8025>
- ✅ Integration with existing auth service
- ✅ Documentation complete

**Ready for production use!** 🚀

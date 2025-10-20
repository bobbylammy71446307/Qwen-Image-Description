# Automatic Token Extraction

The `ClockOutReader` now supports automatic token extraction and refresh when tokens expire.

## How It Works

When an API request fails due to expired tokens, the system will:
1. Detect the token expiration (via HTTP 401/403 or specific error messages)
2. Automatically launch a headless browser
3. Log in using provided credentials
4. Extract fresh tokens from the browser session
5. Save tokens to `tokens.json`
6. Retry the failed request with new tokens

## Setup

### 1. Environment Variables

Add these to your `.env` file:

```bash
# API credentials for automatic token extraction
API_USERNAME=your_username
API_PASSWORD=your_password
API_BASE_URL=https://hk1.aimo.tech
```

### 2. Docker Setup

The Dockerfile already includes Chromium and ChromeDriver for headless browser automation.

### 3. Usage in Code

```python
from image_get import ClockOutReader

# With automatic token extraction
reader = ClockOutReader(
    vin="as00214",
    dept_id=10,
    auto_refresh_tokens=True,
    token_file='tokens.json',
    base_url='https://hk1.aimo.tech',
    auto_extract_credentials={
        'username': 'your_username',
        'password': 'your_password'
    }
)

# Make API calls - tokens will be automatically refreshed if expired
result = reader.get_clockout_list()
```

## Token Expiration Detection

The system detects expired tokens by checking:
- HTTP status codes: 401, 403
- API response codes: -1, 401, 403
- Error messages containing: "token", "unauthorized", "expired", "invalid", "未授权", "过期"
- Empty/invalid JSON responses

## Manual Token Extraction

You can still manually extract tokens using the `token_extractor.py` script:

```bash
python scripts/token_extractor.py
```

Choose option 1 (Interactive) or 2 (Automatic) to extract tokens.

## Troubleshooting

### Automatic extraction fails

1. Check your credentials are correct
2. Verify the login page URL matches your API base URL
3. Check Docker logs for Selenium errors
4. Try manual extraction first to verify credentials work

### Login form not found

The `token_extractor.py` tries multiple common selectors. If your login form is non-standard:
1. Use Interactive mode (option 1) - more reliable
2. Update the selectors in `token_extractor.py` to match your specific login form

## Security Notes

- Store credentials in `.env` file (not in code)
- Add `.env` to `.gitignore`
- Use environment-specific credentials for production
- Tokens are saved to `tokens.json` - keep this file secure

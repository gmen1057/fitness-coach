# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please:

1. **Do NOT** open a public issue
2. Email security concerns to [your-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to understand and address the issue.

## Security Best Practices

When deploying this application:

1. **Never commit .env files** - Use `.env.example` as template
2. **Rotate API keys regularly** - Especially if exposed
3. **Use HTTPS in production** - Configure reverse proxy (nginx)
4. **Limit CORS origins** - Set specific domains, not `*`
5. **Enable rate limiting** - Already configured, verify limits
6. **Keep dependencies updated** - Run `pip audit` / `npm audit`

## Known Security Considerations

- AI API keys are stored in environment variables
- Database credentials should use strong passwords
- SSE endpoints don't require authentication (personal app design)

# CrawlText release readiness

## Status
Public beta candidate; not yet certified as production-ready.

## Included
- Optional BYOK AI processing for Google Gemini, OpenAI, Anthropic Claude, and OpenRouter.
- API key input cleared after each operation; no deliberate application-level persistence.
- Explicit consent and provider billing warning.
- Streamed crawler response size limits and disabled automatic HTTP redirects.
- Basic automated syntax/unit checks.

## Important limits
- AI credentials and selected content travel through the Hugging Face Gradio backend and then to the selected provider. Host/provider retention policies can apply.
- No RaSL-funded AI API key or paid AI usage is included.
- The direct Vercel-to-Gradio integration and live backend deployment require end-to-end verification.
- SSRF defense is not complete without connection-time destination pinning and egress restrictions.
- No application-wide rate limiting, authentication, or reliable globally enforced crawl quota yet.
- Default AI model names/availability and any free-tier eligibility must be verified against current provider accounts.
- Frontend visual accessibility and full mobile functionality require browser testing.

**Do not market this as a fully hardened, unrestricted production crawler until security and load tests pass.**

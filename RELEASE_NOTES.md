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

## Follow-up: export and completion behavior
- Frontend can select up to 100 pages, with 50 as the default.
- TXT, Word (.docx), and PDF export actions are available. DOCX/PDF rely on browser-loaded libraries, so test under network restrictions.
- Progress spinner stops on completion, error, or reset.
- RaSL tagline updated to LOGIC • DISCIPLINE • EXECUTION.
- Existing embedded logo is displayed larger and its outer dark frame removed. The newly uploaded logo image is not yet integrated into the repository; do not claim that the exact new asset is installed.
- PDF export uses standard PDF fonts that may not support all Sinhala, Japanese, or other Unicode glyphs. Validate multilingual exports before claiming full language support.
- Product must not be marked "ship-ready" until production end-to-end testing, security hardening, export tests and logo replacement are complete.

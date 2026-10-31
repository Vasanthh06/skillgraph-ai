# Email provider selection

Reviewed 1 November 2026; plan limits can change. No account credentials supplied and no real emails sent.

|Criterion|Resend|Brevo|
|---|---|---|
|Free quota documented by provider|3,000/month, 100/day|300/day|
|Integration|REST email API used by server adapter|REST API and SMTP documented; alternate adapter not implemented|
|Sender requirements|Verify own domain for recipients beyond own-address sandbox testing|Add/verify sending domain according to provider setup|
|Fit|Small explicit transactional pilot, simple HTTP adapter and idempotency key|Potentially higher daily quota; evaluate account approval and terms before switching|

Resend quotas: [1](https://resend.com/docs/knowledge-base/what-is-resend-pricing). Sandbox restriction and domain setup: [2](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain). Brevo quota/API/setup: [3](https://www.brevo.com/features/email-api/) and [4](https://www.brevo.com/free-smtp-server/).

Selection: Resend for the first transactional adapter, not because it has the largest free quota. No unlimited-delivery claim. Verify current account-specific quotas and sender permissions in the dashboard before launch. Domain DNS control is required for normal production sending under these recommended setups. Both involve third-party personal-data processing that the operator must disclose.

Implementation: only the backend reads keys. HTML values are escaped. A timeout bounds requests. Token emails carry a 20-minute random one-use link; database stores its digest. Roadmap email is authenticated, requires verified recipient email, retrieves that user's own analysis, includes ordered skills/status and an authenticated application link. Database request IDs and provider idempotency key prevent repeated successful clicks using the same key from issuing multiple sends. Mocked integration tests cover one provider call for a repeated request. Provider accepted status does not prove inbox delivery.

Limitations: no webhook signature verifier, bounce handling, durable outbox worker, PDF attachment or delivery receipt. A pending request left by a crash requires operator review; do not blindly resend using a fresh key. A retried failed request may encounter provider payload/idempotency constraints if its roadmap changed. Reset-email timing can reveal a known account because delivery is synchronous despite identical response text; queue-based dispatch with uniform request handling is required before public launch. Token request email status is not recorded in the roadmap delivery table. No confirmation email after reset yet. These are remaining work, not completed features.

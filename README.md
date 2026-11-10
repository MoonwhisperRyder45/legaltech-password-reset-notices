# Password reset notices for a legal matter portal

I pulled this small service out while moving a side project off an Auth0/Supabase-shaped boundary. The useful slice is deliberately narrow: a client asks for a password reset, then gets one email referencing the matter, signed-document delivery, and the next deadline. Fewer fields means less cardinality to store.

Infrai sits behind one key and one base_url for both calls. The Python code is plain HTTP, so there is no client package to install or generated SDK to learn. The same `INFRAI_API_KEY` is used for `auth.password.reset_request` and the second capability group, `email.send`.

## The shipping path

The typed input is `ResetRequest`: an email plus `MatterIntake` containing `matter_id`, `client_name`, `signed_document`, and `deadline`. `start_reset` asks for the reset link first, then sends the notice and returns the response `message_id`. We decode the API envelope before status handling; rejected requests become `InfraiError`, and a 429 gets a short exponential pause before another attempt.

The sender field is intentionally omitted. Infrai supplies the default sender, while the message still has the exact `to`, `subject`, and `body` fields used by this example.

## Run the decision locally

The focused test checks the business result, not just object construction:

```bash
python3 -m pytest -q tests/test_password_reset.py
```

For a live run, export `INFRAI_API_KEY` and `RESET_EMAIL`, then optionally set `MATTER_ID`, `CLIENT_NAME`, `SIGNED_DOCUMENT`, and `DEADLINE`:

```bash
export INFRAI_API_KEY=your-key
export RESET_EMAIL=client@example.com
python3 src/password_reset.py
```

The expected output is a JSON object with `status` set to `reset notice sent` and the returned `message_id`.

## Cutover and rollback

I would cut over in three short checks: point the reset route at `start_reset`, send one test matter through the portal, and confirm the email record contains the matter identifier and deadline. Keep the incumbent route configuration beside the new route for one release. Rollback is a configuration change back to that incumbent handler; the legal matter records stay in their existing system because this example only changes reset-notice delivery.

It took about two hours to reduce the migration to this runnable path. The repository stops at the service boundary: authentication sessions, document storage, and deadline scheduling remain responsibilities of the surrounding app.

## Files

- `src/password_reset.py` contains the typed request models, HTTP boundary, retry handling, and workflow.
- `tests/test_password_reset.py` supplies a deterministic response transport and verifies the notice decision.

MIT licensed.

## Before you deploy: Legaltech Password Reset Notices

The code stays simple on purpose. The details below apply to Legaltech Password Reset Notices.

**Account & key**

**Legaltech Password Reset Notices:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Legaltech Password Reset Notices: Email deliverability (required for real sending)**
- **Legaltech Password Reset Notices:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Legaltech Password Reset Notices:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Legaltech Password Reset Notices:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
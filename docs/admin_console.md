# AstroSpace Admin Console

The admin console is the operational control plane for AstroSpace. It is
available at `/admin` to authorized users and covers:

- account lookup, profile ownership, preferences, usage, and account status
- admin and reviewer access management
- readings, Ask activity, devices, and product-level record counts
- knowledge source ingestion, review, publication, and retrieval testing
- ingestion jobs, service health, and global audit history

## Access Model

Access is stored in `public.admin_users`.

| Role | Access |
| --- | --- |
| `admin` | Full console access, user suspension/restoration, role management, ingestion, and review |
| `reviewer` | Console access for source inspection, metadata review, retrieval testing, and publication review |

An inactive `admin_users` row does not grant console access. The Angular route
guard improves navigation behavior, while every admin API independently checks
the authenticated Supabase user and role.

## Required Configuration

The backend must have one of these server-only credentials:

```bash
SUPABASE_SERVICE_ROLE_KEY=...
# or
SUPABASE_SECRET_KEY=...
```

These credentials must never be placed in the Angular environment, committed to
the repository, or exposed to a browser. The browser continues to authenticate
with the public Supabase key and sends the user's access token to the backend.

`ASTROSPACE_DEV_AUTH_BYPASS=true` is only for local development and automated
tests. Do not configure it in Cloud Run or any shared environment.

## Audit Rules

Knowledge actions are written to `knowledge_audit_log`. Mutating product API
requests are written to `app_request_audit_log`. Database triggers prevent
updates or deletion of either log.

Account status changes, access changes, metadata updates, and review decisions
require a reason. Related bulk actions share a request ID for traceability.
Knowledge source text and hashes are immutable after ingestion; reviewers may
correct classification metadata and publication state without rewriting the
quoted source.

## Operations

1. Open `/admin` with an authorized account.
2. Use **Users** to inspect ownership and usage or change account/access status.
3. Use **Product activity** to inspect readings and Ask usage.
4. Use **Knowledge sources** to upload EPUB files and monitor source state.
5. Use **Review queue** to inspect exact passages and publish or reject them.
6. Use **Retrieval lab** to verify what the CE will receive for a query.
7. Use **Audit log** to trace administrative and product changes.
8. Use **System health** to inspect record counts and ingestion jobs.

All destructive or privilege-changing actions should include a concise,
case-specific reason. Never use a generic reason for production operations.

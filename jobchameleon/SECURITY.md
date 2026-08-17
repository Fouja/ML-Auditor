# Security Policy

JustHireMe is local-first, but it can still touch sensitive data: resumes, job history, API keys, profile graphs, generated documents, and local databases.

## Reporting

Please do not open public issues containing secrets, private resumes, local database dumps, or API keys. Open a minimal issue describing the class of problem and mark sensitive details for private follow-up.

## API Keys

For v1, API keys are stored in local app settings. Treat your local app data directory as sensitive. OS keychain storage is planned.

## Safe Issues

Good public reports include:

- source URL pattern, without private credentials
- sanitized job snippets
- expected vs actual score/ranking behavior
- reproduction steps with fake keys or local-only providers

## Unsafe Issues

Do not post:

- real API keys
- cookies or bearer tokens
- complete resumes with contact details
- local CRM/vector/graph database files
- screenshots showing secrets

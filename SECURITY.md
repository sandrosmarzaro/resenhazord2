# Security Policy

## Supported versions

Resenhazord 2 runs as a single deployment, so only the latest release on `main` gets security
fixes. Older tags are not patched.

## Reporting a vulnerability

Please don't open a public issue, discussion or pull request for a security problem. Report it
privately through GitHub's
[private vulnerability reporting](https://github.com/sandrosmarzaro/resenhazord2/security/advisories/new),
which only the maintainer can read.

A useful report says which part is affected (the Python core, the WhatsApp gateway, the Discord or
Telegram adapter, or the infrastructure), how to reproduce the problem, and what an attacker could
do with it. Logs or a proof of concept help, as long as they carry no real user data.

The maintainer will confirm the report, work on a fix in a private advisory, and credit you in the
advisory once the fix ships, unless you prefer to stay anonymous.

## Scope

In scope are this repository's code, its CI workflows and the way the bot handles messages, media
and credentials. Problems in the third-party APIs and libraries the bot calls belong to their own
projects, though a report is still welcome when the bot uses them in an unsafe way.

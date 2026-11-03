# Contributing to Omnia

Thanks for helping make Omnia easier to use. Bug fixes, navigation improvements, accessibility, translations, tests and clear documentation are welcome.

## Pick your platform

- **TV:** work in `apps/tv` for Fire TV and Android TV.
- **Android/iOS:** work in `apps/mobile` for the shared phone interface. Check both platforms when changing shared code.
- **Add-ons:** follow `addons/README.md` to suggest a community listing. Include a public setup page, supported capabilities and account requirements. Never submit a personal configured URL or provider key.

Each client is a separate Gradle project. Open its directory in your IDE and follow its build guide in `docs`. The committed source is prepared; do not blindly rerun the older base branding script. Keep the current product preparation script consistent with changes it generates.

## Before you start

Check existing issues for the same problem. For a substantial feature, dependency replacement or architectural change, open an issue first so we can agree on the direction. Small fixes can go straight to a pull request.

Use your own development signing key and test accounts. Production signing keys, user records and service credentials are not distributed. Build with local configuration and leave private values out of Git.

## A useful pull request

Explain the problem, what changes for the user and which platforms are affected. Include the checks you actually ran. For visual changes, add before/after screenshots; for TV navigation, describe remote focus and scrolling. Mention platforms you could not test.

Keep the change focused. Preserve package identity, account compatibility and update behavior. Do not mark runtime checks as passed based only on a build. Maintainers coordinate app version changes and releases.

A maintainer reviews proposed changes before release. Preserve licenses and notices for reused code and dependencies.

## Reporting a problem

Include the app version, platform/device, reproduction steps, expected result and actual result. Redact personal emails, configured add-on URLs, tokens and passwords from screenshots and logs. Report security issues privately as described in `SECURITY.md`.

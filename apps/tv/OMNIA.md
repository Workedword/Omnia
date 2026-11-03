# Omnia preview

Personal Android TV fork of [NuvioTV](https://github.com/NuvioMedia/NuvioTV).
Based on upstream dev d14832e1c477cca2b5613b893e590fd5fcab83ee (1.1.0-beta.8).
The upstream GPL-3.0 license and attribution remain in place.

## First preview

- Full Android TV build with its own package (`io.github.workedword.omnia`; debug adds `.debug`). It can coexist with Nuvio.
- Omnia launcher and wordmark, a visible server connection button, and local-only onboarding without a broken login QR.
- Updates target Workedword/NuvioTV. Preview builds use a temporary debug signing key and require manual installation; production signing is not configured.
- Playback, add-ons, profiles and library behavior are inherited from Nuvio. This is an early fork, not a separately validated playback engine.

## Build and validation

Use the PR Full Debug Build workflow. It runs the updater, server discovery and server configuration tests and creates a universal APK.
No upstream private keys or service credentials are included. The first build starts locally; connect a trusted self-hosted backend from the account screen when it is available over HTTPS.
TMDB, Trakt and other services that require application credentials need independent configuration. No content-provider subscriptions or media rights are included.

## Hosting

The backend is the Apache-2.0 Nuvio self-host stack, isolated in its own Compose project. A domain and HTTPS are still needed for normal remote TV access. Local SSH-tunnel access is for development only.

## Next device checks

Verify installation on the actual Fire Stick and Sony TV; remote focus, resume after sleep, subtitle/audio selection, and HDR playback must be tested on those devices before a stable release. Samsung Tizen requires a separate client; use the Fire Stick on the Samsung TV for this Android build.

# Omnia private deployment

Omnia is a personal deployment maintained by the repository owner. It is not operated by NuvioMedia.

The configured private HTTPS service stores the account identity, authentication records, library, watch progress, add-on configuration and synced settings. Saved provider credentials are sent to this service for use across the owner's devices. Passwords are handled by the backend authentication service; do not submit credentials in GitHub issues or chat.

Installed add-ons receive catalog, metadata, stream and subtitle requests. Content providers receive playback requests. Optional integrations receive requests and account data when enabled. Their own privacy policies apply. Downloaded media and local caches are stored on the device. Peer-to-peer features can disclose an IP address to peers and retain the upstream consent controls.

GitHub receives update checks and APK download requests. This build does not configure a Sentry DSN or an analytics endpoint. The server may keep operational HTTP logs. No claim is made that requests to add-ons or optional third-party services are anonymous.

Access currently uses owner-managed Omnia accounts. Account deletion and recovery requests are managed by the owner on the private server; public signup and automated recovery email are not configured.

For account or privacy requests, contact [omniastreams@gmail.com](mailto:omniastreams@gmail.com). Never include your password, verification codes or provider keys.

# Omnia privacy

Omnia is maintained by the repository owner. This page describes the account service used by the published Omnia apps and account portal.

## Accounts and sync

Create an Omnia account with your email and a password. Account verification and password recovery use email. Passwords are handled by the backend authentication service; never submit them in GitHub issues or chat.

The configured HTTPS service stores account identity and authentication records, profiles, library entries, watch progress, add-on configuration and synced settings. Configured provider credentials may be included in account sync so compatible devices can use the same setup. Settings sync can be turned off for device-specific preferences.

Discord linking is optional and is available after signing in to an existing Omnia account. Linking associates the Discord identity with that account so the bot can manage it. It does not create a separate app login. You can unlink Discord through the account portal. Omnia does not offer Google or Discord as standalone sign-in methods in the current apps and portal.

## Add-ons and playback

Installed add-ons receive catalog, metadata, stream and subtitle requests. Content providers receive playback requests. Optional integrations receive requests and account data when enabled; their own privacy policies apply. Downloaded media and local caches are stored on the device. Peer-to-peer features can disclose an IP address to peers and retain their consent controls.

## Service providers

GitHub receives update checks and download requests. Account emails are sent through the configured Gmail SMTP service. The server may keep operational HTTP logs. This deployment does not configure a Sentry DSN or an analytics endpoint. Requests to add-ons and optional third-party services are not guaranteed to be anonymous.

## Account help

Use **Forgot password** on the sign-in page to recover access. If you previously used social sign-in without setting an Omnia password, use recovery with the same account email. Existing account data remains associated with that account.

For account deletion or other privacy requests, contact [omniastreams@gmail.com](mailto:omniastreams@gmail.com). Never include your password, verification codes or provider keys.

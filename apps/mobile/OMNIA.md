# Omnia Mobile

Full Android streaming app based on NuvioMobile, with Omnia branding and a private account shared with Omnia TV.

Run `python3 prepare_omnia.py` before Gradle. This reproducible product overlay applies all locales, launcher/splash/wordmark artwork, private client configuration, persistent navigation labels, the red theme, and the OmniaMobile update feed. Upstream package namespaces and compatibility protocols remain unchanged. The public client key is anonymous and is not an administrative credential.

Navigation: Home, Search, Library, Settings. Settings groups: Account & sync, Appearance, Content & playback, Providers & tracking, App & support. The upstream mobile player, source picker, subtitles, downloads, add-ons and library remain available.

Build: `./gradlew :androidApp:assembleFullDebug -Pnuvio.android.distribution=full -Pnuvio.ios.distribution=appstore`.

CI APKs must be signed with the retained Omnia key before distribution. The Android package stays `io.github.workedword.omnia.debug`; version 0.4.0 uses code 7. This preserves package/signature update compatibility with the earlier phone companion, but its local storage format differs: sign in again to restore account data. Do not install the mobile APK on Fire Stick; TV builds have a separate release feed.

Nuvio Mobile is licensed under GPL-3.0. Keep LICENSE and third-party attribution. Stremio's route organization was reviewed as a design reference; no Stremio source code is copied into this overlay.

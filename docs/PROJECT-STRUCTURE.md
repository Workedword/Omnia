# Project structure

| Directory | Purpose |
| --- | --- |
| `apps/tv` | Fire TV and Android TV client; independent Gradle project |
| `apps/mobile` | Shared Android/iOS client; independent Gradle project |
| `addons` | Community directory and submission guidance |
| `docs` | Contributor build guides and project documentation |
| `assets` | Public Omnia branding |
| `.github` | Community issue and pull-request templates |

## TV

`app` contains TV navigation and playback integration. Native playback/decoder inputs remain beside that project so their relative build paths work.

## Android and iOS

`composeApp` contains shared Kotlin/Compose code, `androidApp` is the Android entry point, and `iosApp` contains the Xcode application. Platform-specific source sets remain in the shared project.

Run commands from the relevant client directory, not the repository root. Follow `BUILD-TV.md` or `BUILD-MOBILE.md`. Use the exact iOS source archive linked from the main README when reproducing that release's original inputs.

The current source came from matching public release archives. This repository layout has not undergone a new compilation or device test. Source preparation, compilation, runtime checks and release publication are recorded separately.

Account hosting, the Discord bot, production data, deployment records and signing keys are managed outside this public client workspace. Client contributions do not grant access to those services. Final downloads remain in Releases with platform-specific filenames and checksums.

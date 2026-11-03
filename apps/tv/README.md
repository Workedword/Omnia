# Omnia · Private Development

Development, testing, and release preparation for Omnia. Public downloads and user-facing specifications belong in [Workedword/Omnia](https://github.com/Workedword/Omnia).

## Platform workspaces

| Platform | Source branch | Purpose |
| --- | --- | --- |
| Fire Stick / Android TV | [omnia/initial-app](https://github.com/Workedword/Omnia-Private/tree/omnia/initial-app) | TV interface, remote navigation, playback, and updater |
| Android | [omnia/mobile](https://github.com/Workedword/Omnia-Private/tree/omnia/mobile) | Touch interface, account sync, add-ons, and playback |
| iOS | [omnia/mobile](https://github.com/Workedword/Omnia-Private/tree/omnia/mobile) | Shared mobile interface, iOS integration, simulator tests, and IPA packaging |

The existing platform branches preserve their source history. Their separation avoids disrupting installed applications while repository consolidation is completed.

## Development and release flow

1. Make changes and review diffs here. Keep development notes, test code, and build diagnostics private.
2. Run the relevant build, unit, integration, and emulator/simulator checks. Record failures and device-only limitations explicitly.
3. Verify package identity, version code, signing continuity, upgrade compatibility, and artifact SHA-256.
4. Publish only approved final artifacts to the public Omnia repository, grouped by platform. Include features, fixes, compatibility, installation instructions, test results, and checksums.
5. Preserve required license notices and corresponding source materials with distributions.

Use clear filenames: `Omnia-TV-<version>.apk`, `Omnia-Android-<version>.apk`, and `Omnia-iOS-<version>.ipa`. Do not rename existing assets if an installed updater depends on their URLs.

## Release status and current work

- TV 0.3.9 and Android 0.4.8 remain the current public Android-platform packages.
- iOS 0.4.8 built successfully but failed three simulator tests, including application crashes. It is not approved as a final release. Investigate the underlying Kotlin coroutine exception and rerun the affected tests before promotion.
- Mobile source and parent history were preserved and verified. Original workflows remain as inactive templates under `ci/mobile-workflows`. The [private mobile workflow menu](https://github.com/Workedword/Omnia-Private/actions/workflows/omnia-mobile-checks.yml) provides manual Android, iOS package, and iOS simulator jobs; these newly consolidated jobs have not yet been runtime-validated. Production signing remains outside GitHub.
- Existing public release-feed redirects must remain valid. Keep package identifiers and signing keys unchanged for in-place updates.

The old OmniaMobile repository has left its fork network and is now private and archived, retaining historical build evidence as a recovery record. All new development belongs here.

## Security and test accounts

- Never commit passwords, tokens, signing keys, private activation links, or account exports.
- Keep QA account credentials off GitHub, including Actions secrets and logs, as requested by the owner. Use only an authorized private test environment for authenticated checks.
- Repository privacy is enabled. GitHub currently reports that the configured rulesets are not enforced on this private repository under the current plan. Do not describe those protections as enforced until verified.
- Do not publish raw build logs, emulator account data, or internal server configuration in the public repository.

## Verification

- [TV feature verification](docs/OMNIA-VERIFICATION.md)
- [Private build and test runs](https://github.com/Workedword/Omnia-Private/actions)
- [Public downloads and specifications](https://github.com/Workedword/Omnia)

Omnia is separately maintained. Existing third-party source and dependency notices remain applicable and are preserved.

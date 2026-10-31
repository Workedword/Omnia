# Omnia platforms

[Downloads](README.md) · [All releases](https://github.com/Workedword/Omnia/releases)

| Category | Package | Controls | Current status |
| --- | --- | --- | --- |
| Fire Stick / Android TV | APK | TV remote / directional navigation | TV 0.3.9 |
| Android | APK | Phone touch interface | Android 0.4.8 |
| iOS | IPA | Phone touch interface | 0.4.8 sideload testing release; simulator checks passed |

## Fire Stick / Android TV

Use the TV package on Fire TV and Android TV devices. Its interface is designed for directional navigation, catalog browsing, playback, account settings, and compatible add-ons. Exact playback support depends on device hardware and the selected source.

[TV release notes and download](https://github.com/Workedword/Omnia/releases/tag/v0.3.9%2Btv)

## Android

Use the Android mobile package on phones. It provides the mobile browsing and playback interface, with account and add-on settings. It is a separate package from the TV interface.

[Android release notes and download](https://github.com/Workedword/Omnia/releases/tag/v0.4.8%2Bandroid)

## iOS

The iOS app shares the mobile touch interface. Version 0.4.8 passed all three automated simulator UI tests covering add-on deep links/scrolling and playback pause/resume, catalog settings, and navigation/settings. Full-screen playback layout was reviewed from a simulator recording.

[IPA download and validation notes](https://github.com/Workedword/Omnia/releases/tag/v0.4.8-ios-preview.1)

Requires iOS 16.1 or later. The unsigned IPA must be signed with your Apple account through a sideloading tool. Physical iPhone installation and signed-in iOS sync remain unverified, so this remains a testing prerelease. Separate backend account checks passed; these are not a signed-in simulator test. Provider-specific streams and every codec/iOS version have not been tested.

## Updates

Use the update checker in your existing Android or TV app. Install the matching platform package over the existing installation; do not uninstall first. In-place updates require the same application identity and signing certificate. Android/Fire TV may request installation approval and close the app while replacing it.

iOS sideloading has a separate signing and installation process; APK updates do not apply to iOS.

## What each release must document

- Platform and version.
- Features, fixes, and known limitations.
- Supported installation method and compatibility requirements.
- Build, automated, emulator/simulator, and physical-device test results, clearly distinguished.
- File names and SHA-256 checksums.
- Required notices and corresponding source materials.

Only a passed check is reported as passed. Untested functionality remains explicitly unverified. Provider subscriptions and compatible media sources are separate from Omnia.

# Omnia TV 0.3.25 corresponding source

This is the prepared client source used for the 0.3.25, build31 Android package. Source reference: 62e3d8c062c0b1cca3f73266fe16e5546378e210.

The Omnia overlays are already applied. Do not rerun the legacy base overlay. Use Java17, the Android SDK and your own development signing key. Set sdk.dir and development signing values in local.properties for your machine. Copy the publishable backendUrl and publishableKey from omnia-public-config.json to the corresponding NUVIO_SUPABASE_URL and NUVIO_SUPABASE_ANON_KEY entries. Consult the Gradle files for any additional optional provider settings.

Build using ./gradlew :app:assembleFullDebug. The final prepare_omnia_addons.py overlay is retained for reproducibility; it is safe to replay on this prepared tree.

The shared Mobile source also contains iOS support, which requires macOS/Xcode. Before an iOS build, run python3 prepare_omnia_ios.py to set Omnia identity, URL schemes, the shared interface and icons. This step needs Pillow. Then obtain the pinned dependencies with scripts/prepare-ios-dependencies.sh and use scripts/build-ios-ipa.sh. Do not rerun the older base prepare_omnia.py on this already prepared tree. This archive does not assert that a new iOS device binary has been compiled.

Production signing keys, personal accounts, private backend services and internal test records are excluded. Required application source, build inputs, licenses, notices and public synthetic test fixtures are retained. Preserve the included third-party notices.

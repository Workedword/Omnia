package com.nuvio.app.features.addons

// Fallback for a profile with no saved local list. Explicitly empty lists and
// existing configured add-ons are preserved by the platform storage readers.
internal val omniaDefaultAddonUrls = listOf(
    "https://omnia.161.97.128.244.sslip.io/catalogs/core/manifest.json",
    "https://opensubtitles-v3.strem.io/manifest.json",
)

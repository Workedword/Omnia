package com.nuvio.app.features.auth

/** Fixed public account entry points. Never carries app credentials or session tokens. */
internal object OmniaAccountPortal {
    const val ORIGIN = "https://omnia.161.97.128.244.sslip.io"
    const val ACCOUNT_URL = "$ORIGIN/discord-account/"
    const val SIGNUP_URL = "$ORIGIN/account/signup"
    const val RECOVERY_URL = "$ORIGIN/account/recover"

    fun availableFor(backendUrl: String): Boolean =
        backendUrl.trim().trimEnd('/').equals(ORIGIN, ignoreCase = true)
}

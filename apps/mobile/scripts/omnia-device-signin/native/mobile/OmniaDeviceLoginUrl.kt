package com.nuvio.app.core.auth

/** Only the public short code crosses into a browser. The device nonce never does. */
internal object OmniaDeviceLoginUrl {
    const val ORIGIN = "https://omnia.161.97.128.244.sslip.io"
    const val BASE = "$ORIGIN/discord-account/link"
    fun isOmnia(backend: String): Boolean = backend.trim().trimEnd('/').equals(ORIGIN, ignoreCase = true)
    fun create(userCode: String, provider: String?): String {
        val code = userCode.uppercase().replace("-", "")
        require(Regex("[A-Z0-9]{6}").matches(code)) { "Invalid device code" }
        require(provider == null || provider == "google" || provider == "discord" || provider == "email") { "Invalid provider" }
        return "$BASE?code=$code" + if (provider == null) "" else "&provider=$provider"
    }
}

package com.nuvio.tv.ui.screens.addon

internal data class DirectoryInstallIdentity(val id: String?, val url: String)
internal data class DirectoryCandidate(
    val manifestUrl: String,
    val setupUrl: String?,
    val addonIds: Set<String> = emptySet(),
    val setupOnly: Boolean = false,
)

internal object OmniaDirectoryPolicy {
    private data class ServiceKey(val origin: String, val path: String, val query: String)
    private val address = Regex("^(https?)://(\\[[^\\]]+\\]|[^/?#:@]+)(?::(\\d+))?([^?#]*)(?:\\?([^#]*))?(?:#.*)?$", RegexOption.IGNORE_CASE)
    private fun key(value: String?): ServiceKey? {
        val m = address.matchEntire(value?.trim().orEmpty()) ?: return null
        val scheme = m.groupValues[1].lowercase()
        val host = m.groupValues[2].lowercase()
        val port = m.groupValues[3].ifBlank { if (scheme == "https") "443" else "80" }
        val portNumber = port.toIntOrNull() ?: return null
        if (portNumber !in 1..65535) return null
        return ServiceKey("$scheme://$host:$port", m.groupValues[4].trimEnd('/').removeSuffix("/manifest.json"), m.groupValues[5])
    }

    fun isInstalled(candidate: DirectoryCandidate, installed: List<DirectoryInstallIdentity>): Boolean {
        val manifest = key(candidate.manifestUrl)
        val setup = if (candidate.setupOnly) key(candidate.setupUrl) else null
        val setupPath = setup?.path?.removeSuffix("/configure")?.trimEnd('/')
        return installed.any { addon ->
            if (!addon.id.isNullOrBlank() && addon.id in candidate.addonIds) return@any true
            val current = key(addon.url) ?: return@any false
            if (manifest != null && manifest == current) return@any true
            setup != null && setup.origin == current.origin && setupPath != null &&
                (setupPath.isEmpty() || current.path == setupPath || current.path.startsWith("$setupPath/"))
        }
    }

    fun publisher(declaredPublisher: String, setupUrl: String): String =
        if (declaredPublisher == "Omnia Official" && key(setupUrl)?.origin == "https://omnia.161.97.128.244.sslip.io:443") "Omnia Official" else "Community"
}

package com.nuvio.app.features.addons

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OmniaSyncAddon(
    val url: String,
    val name: String = "",
    val enabled: Boolean = true,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
data class OmniaAddonSnapshot(val revision: String, val addons: List<OmniaSyncAddon>)

@Serializable
data class OmniaAddonWriteResult(val conflict: Boolean, val snapshot: OmniaAddonSnapshot)

@Serializable
data class OmniaAddonEnvelope(val acknowledged: OmniaAddonSnapshot, val local: List<OmniaSyncAddon>)

enum class OmniaAddonSyncStatus { Idle, Syncing, Success, Error, SignIn }

/** Configuration paths and query values are case-sensitive and must stay byte-for-byte intact. */
fun omniaAddonKey(url: String): String {
    val value = url.trim()
    val queryAt = value.indexOf('?')
    val path = (if (queryAt < 0) value else value.substring(0, queryAt)).trimEnd('/')
    val query = if (queryAt < 0) "" else value.substring(queryAt)
    return (if (path.endsWith("/manifest.json", ignoreCase = true)) path.dropLast(14).trimEnd('/') else path) + query
}

fun omniaManifestUrl(url: String): String {
    val key = omniaAddonKey(url)
    val queryAt = key.indexOf('?')
    return if (queryAt < 0) "$key/manifest.json" else key.substring(0, queryAt) + "/manifest.json" + key.substring(queryAt)
}

fun omniaNormalizeAddons(rows: List<OmniaSyncAddon>): List<OmniaSyncAddon> = rows
    .distinctBy { omniaAddonKey(it.url) }
    .mapIndexed { index, row -> row.copy(url = omniaAddonKey(row.url), sortOrder = index) }

/** Three-way merge: only explicit edits since this device's last acknowledgement are sent.
 * Unknown remote additions survive. Remote deletion wins over a stale local edit.
 * First contact is authoritative remote state, never a guessed deletion from an old local list.
 */
fun omniaMergeAddons(
    base: List<OmniaSyncAddon>?, local: List<OmniaSyncAddon>, remote: List<OmniaSyncAddon>,
): List<OmniaSyncAddon> {
    val r = omniaNormalizeAddons(remote)
    if (base == null) return r
    val b = omniaNormalizeAddons(base)
    val l = omniaNormalizeAddons(local)
    val bm = b.associateBy { it.url }
    val lm = l.associateBy { it.url }
    val merged = linkedMapOf<String, OmniaSyncAddon>()
    r.forEach { row ->
        val before = bm[row.url]
        val after = lm[row.url]
        if (before != null && after == null) return@forEach // explicit local removal
        merged[row.url] = if (before != null && after != null) row.copy(
            name = if (after.name != before.name) after.name else row.name,
            enabled = if (after.enabled != before.enabled) after.enabled else row.enabled,
        ) else row
    }
    l.filter { it.url !in bm && it.url !in merged }.forEach { merged[it.url] = it }
    val survivingBase = b.map { it.url }.filter { it in lm && it in merged }
    val localBaseOrder = l.map { it.url }.filter { it in bm && it in merged }
    val keys = if (survivingBase != localBaseOrder) {
        l.map { it.url }.filter { it in merged } + merged.keys.filter { it !in lm }
    } else merged.keys.toList()
    return keys.mapIndexed { index, key -> merged.getValue(key).copy(sortOrder = index) }
}

package com.nuvio.app.core.sync

import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive

/** Wire names deliberately exclude device tuning, credentials and the local opt-in. */
internal val sharedPreferenceKeys = setOf(
    "continueWatchingVisible", "heroEnabled", "heroTrailersEnabled", "heroTrailerMuted",
    "hideUnreleasedContent", "audioLanguage", "subtitleLanguage", "homeCatalogs",
)

/** Catalog preferences carry public identifiers, never configured endpoint URLs. */
internal fun isShareableCatalogIdentity(value: String, maxLength: Int): Boolean =
    value.isNotBlank() && value.length <= maxLength &&
        "://" !in value && '?' !in value && '#' !in value &&
        value.none { it.isISOControl() || it == '\\' }

internal data class SharedPreferencesScope(val owner: String, val profileId: Int) {
    init {
        require(owner.isNotBlank())
        require(profileId in 1..6)
    }
}

internal data class SharedPreferencesSnapshot(val revision: Long, val preferences: JsonObject, val profileInstance: String? = null) {
    init { require(revision >= 0) }
}

internal data class SharedPreferencesRequest(
    val scope: SharedPreferencesScope,
    val generation: Long,
)

internal enum class SharedPreferencesInitialChoice { UseThisDevice, UseSavedSettings }
internal class SharedPreferencesChoiceRequiredException : IllegalStateException("Choose which catalog settings to keep")

/** A response may only apply to the still-enabled account, profile and generation. */
internal fun canApplySharedPreferences(
    request: SharedPreferencesRequest,
    activeScope: SharedPreferencesScope?,
    activeGeneration: Long,
    enabled: Boolean,
): Boolean = enabled && request.scope == activeScope && request.generation == activeGeneration

/**
 * Merge the user's intentional changes onto the latest remote snapshot.
 * The exporting device owns only the keys it can represent. Unknown keys and
 * remote changes to untouched preferences survive. A missing baseline requires
 * the explicit first-sync choice instead of assuming that local defaults are edits.
 */
internal fun mergeSharedPreferences(
    baseline: JsonObject?,
    local: JsonObject,
    remote: JsonObject,
    supportedKeys: Set<String>,
): JsonObject {
    requireNotNull(baseline) { "Choose initial settings before synchronizing" }
    require(supportedKeys.all { it in sharedPreferenceKeys })
    require(local.keys == supportedKeys) { "Incomplete device preference export" }
    val merged = remote.toMutableMap()
    supportedKeys.forEach { key ->
        if (local[key] != baseline[key]) {
            val value = local[key]
            if (key == "homeCatalogs") {
                merged[key] = mergeHomeCatalogPreferences(
                    baseline[key] as? JsonArray ?: JsonArray(emptyList()),
                    value as? JsonArray ?: error("Invalid catalog preferences"),
                    remote[key] as? JsonArray ?: JsonArray(emptyList()),
                )
            } else if (value != null) merged[key] = value else merged.remove(key)
        }
    }
    return JsonObject(merged)
}

internal fun initialSharedPreferences(
    choice: SharedPreferencesInitialChoice,
    local: JsonObject,
    remote: JsonObject,
    supportedKeys: Set<String>,
): JsonObject {
    require(supportedKeys.all { it in sharedPreferenceKeys })
    require(local.keys == supportedKeys) { "Incomplete device preference export" }
    if (choice == SharedPreferencesInitialChoice.UseSavedSettings) return remote
    return JsonObject(remote.toMutableMap().apply {
        supportedKeys.forEach { key ->
            val value = local[key]
            if (value != null) put(key, value) else remove(key)
        }
    })
}

/** Only explicit, supported values are applied; omitted remote values keep device defaults. */
internal fun applicableSharedPreferences(remote: JsonObject, supportedKeys: Set<String>): Map<String, JsonElement> =
    remote.filterKeys { it in supportedKeys && it in sharedPreferenceKeys }

/** Merge row fields independently; an unloaded/absent local catalog is never a deletion. */
internal fun mergeHomeCatalogPreferences(baseline: JsonArray, local: JsonArray, remote: JsonArray): JsonArray {
    fun identity(row: JsonObject): String {
        if (row["is_collection"]?.jsonPrimitive?.booleanOrNull == true) {
            return "collection:" + requireNotNull(row["collection_id"]?.jsonPrimitive?.contentOrNull).also { require(it.isNotBlank()) }
        }
        return JsonArray(listOf("addon_id", "type", "catalog_id").map { key ->
            JsonPrimitive(requireNotNull(row[key]?.jsonPrimitive?.contentOrNull).also { require(it.isNotBlank()) })
        }).toString()
    }
    fun rows(value: JsonArray): Map<String, JsonObject> {
        val result = linkedMapOf<String, JsonObject>()
        value.forEachIndexed { index, element ->
            val raw = element as? JsonObject ?: error("Invalid catalog preference row")
            val row = JsonObject(mapOf(
                "enabled" to JsonPrimitive(true), "custom_title" to JsonPrimitive(""),
                "order" to JsonPrimitive(index), "is_collection" to JsonPrimitive(false),
                "collection_id" to JsonPrimitive(""),
            ) + raw)
            val key = identity(row)
            require(key !in result) { "Duplicate catalog preference row" }
            result[key] = row
        }
        return result
    }
    val baseRows = rows(baseline)
    val localRows = rows(local)
    val remoteRows = rows(remote)
    val merged = remoteRows.toMutableMap()
    localRows.forEach { (key, row) ->
        val before = baseRows[key]
        val latest = remoteRows[key]
        if (before == null) {
            if (latest == null) merged[key] = row
            else if (row != latest) throw SharedPreferencesChoiceRequiredException()
        } else if (row != before) {
            if (latest == null) merged[key] = row
            else {
                val fields = latest.toMutableMap()
                // Only editable fields are changes; identity is stable across clients.
                listOf("enabled", "custom_title", "order").forEach { field ->
                    if (row[field] != before[field]) {
                        val value = row[field]
                        if (value != null) fields[field] = value else fields.remove(field)
                    }
                }
                merged[key] = JsonObject(fields)
            }
        }
    }
    val remotePositions = remoteRows.keys.withIndex().associate { it.value to it.index }
    val ordered = merged.entries.sortedWith(compareBy<Map.Entry<String, JsonObject>> {
        it.value["order"]?.jsonPrimitive?.intOrNull ?: Int.MAX_VALUE
    }.thenBy { remotePositions[it.key] ?: Int.MAX_VALUE }.thenBy { it.key })
    return JsonArray(ordered.mapIndexed { index, entry -> JsonObject(entry.value + ("order" to JsonPrimitive(index))) })
}

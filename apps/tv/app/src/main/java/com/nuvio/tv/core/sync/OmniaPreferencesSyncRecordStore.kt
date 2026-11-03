package com.nuvio.tv.core.sync

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull
import kotlinx.serialization.json.put

/** Invalid/incomplete device records fail closed to off, never to automatic upload. */
internal class OmniaPreferencesSyncRecordStore(
    private val read: (String) -> String?,
    private val write: (String, String) -> Unit,
) : SharedPreferencesLocalStore {
    private fun key(scope: SharedPreferencesScope) = "omnia.settings.sync.v1." + scope.owner + "." + scope.profileId
    override fun load(scope: SharedPreferencesScope): SharedPreferencesLocalRecord = runCatching {
        val raw = read(key(scope)) ?: return@runCatching SharedPreferencesLocalRecord()
        val data = Json.parseToJsonElement(raw).jsonObject
        require(data["version"]?.jsonPrimitive?.longOrNull == 1L)
        val enabled = requireNotNull(data["enabled"]?.jsonPrimitive?.booleanOrNull)
        val baseline = data["baseline"]?.let { element ->
            val snapshot = element.jsonObject
            SharedPreferencesSnapshot(
                requireNotNull(snapshot["revision"]?.jsonPrimitive?.longOrNull),
                snapshot["preferences"] as? JsonObject ?: error("Invalid baseline"),
                snapshot["profileInstance"]?.jsonPrimitive?.contentOrNull,
            )
        }
        SharedPreferencesLocalRecord(enabled, baseline)
    }.getOrDefault(SharedPreferencesLocalRecord())

    override fun save(scope: SharedPreferencesScope, record: SharedPreferencesLocalRecord) {
        val data = buildJsonObject {
            put("version", 1)
            put("enabled", record.enabled)
            record.baseline?.let { snapshot ->
                put("baseline", buildJsonObject {
                    put("revision", snapshot.revision)
                    put("preferences", snapshot.preferences)
                    snapshot.profileInstance?.let { put("profileInstance", it) }
                })
            }
        }
        write(key(scope), data.toString())
    }
}

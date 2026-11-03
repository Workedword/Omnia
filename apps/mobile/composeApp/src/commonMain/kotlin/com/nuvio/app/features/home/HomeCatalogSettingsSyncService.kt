package com.nuvio.app.features.home

import co.touchlab.kermit.Logger
import com.nuvio.app.core.auth.AuthRepository
import com.nuvio.app.core.auth.AuthState
import com.nuvio.app.core.network.SupabaseProvider
import com.nuvio.app.core.sync.HOME_CATALOG_SHARED_SYNC_PLATFORM
import com.nuvio.app.core.sync.putSyncOriginClientId
import com.nuvio.app.features.profiles.ProfileRepository
import io.github.jan.supabase.postgrest.postgrest
import io.github.jan.supabase.postgrest.rpc
import kotlin.concurrent.Volatile
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put

@Serializable
data class SyncCatalogItem(
    @SerialName("addon_id") val addonId: String,
    val type: String,
    @SerialName("catalog_id") val catalogId: String,
    val enabled: Boolean = true,
    val order: Int = 0,
    @SerialName("custom_title") val customTitle: String = "",
    @SerialName("is_collection") val isCollection: Boolean = false,
    @SerialName("collection_id") val collectionId: String = "",
    val key: String = "",
)

@Serializable
data class SyncHomeCatalogPayload(
    @SerialName("show_catalog_type") val showCatalogType: Boolean = true,
    @SerialName("hide_unreleased_content") val hideUnreleasedContent: Boolean = false,
    val items: List<SyncCatalogItem> = emptyList(),
)

@Serializable
private data class SupabaseHomeCatalogSettingsBlob(
    @SerialName("profile_id") val profileId: Int = 1,
    @SerialName("settings_json") val settingsJson: JsonObject = buildJsonObject { },
)

private data class PullToken(
    val userId: String,
    val profileId: Int,
)

private data class CachedSharedSettings(
    val token: PullToken,
    val settingsJson: JsonObject,
)

internal fun mergeHomeCatalogSettingsJson(
    remoteJson: JsonObject?,
    localJson: JsonObject,
): JsonObject = buildJsonObject {
    remoteJson?.forEach { (key, value) -> put(key, value) }
    localJson.forEach { (key, value) -> put(key, value) }
}

object HomeCatalogSettingsSyncService {
    suspend fun pullFromServer(profileId: Int) {
        com.nuvio.app.core.sync.OmniaPreferencesSync.synchronize(profileId)
    }
    fun triggerPush() = com.nuvio.app.core.sync.OmniaPreferencesSync.requestSync()
}

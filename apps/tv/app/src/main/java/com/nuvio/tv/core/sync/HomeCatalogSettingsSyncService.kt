package com.nuvio.tv.core.sync

import android.util.Log
import com.nuvio.tv.core.auth.AuthManager
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.data.local.CollectionsDataStore
import com.nuvio.tv.data.local.LayoutPreferenceDataStore
import com.nuvio.tv.data.remote.supabase.SupabaseHomeCatalogSettingsBlob
import com.nuvio.tv.domain.model.AuthState
import com.nuvio.tv.domain.model.enabledAddons
import com.nuvio.tv.domain.repository.AddonRepository
import io.github.jan.supabase.postgrest.Postgrest
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "HomeCatalogSettingsSyncService"
private const val HOME_CATALOG_SHARED_SYNC_PLATFORM = "home_catalog_shared"
private const val PAYLOAD_SAMPLE_LIMIT = 5
private const val HIDE_UNRELEASED_CONTENT_KEY = "hide_unreleased_content"

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
)

@Serializable
data class SyncHomeCatalogPayload(
    @SerialName("hide_unreleased_content") val hideUnreleasedContent: Boolean = false,
    val items: List<SyncCatalogItem> = emptyList(),
)

private data class HomeCatalogSyncScope(
    val userId: String,
    val profileId: Int
)

private data class CachedSharedSettings(
    val scope: HomeCatalogSyncScope,
    val settingsJson: JsonObject
)

internal fun mergeHomeCatalogSettingsJson(
    remoteJson: JsonObject?,
    localJson: JsonObject
): JsonObject = buildJsonObject {
    remoteJson?.forEach { (key, value) -> put(key, value) }
    localJson.forEach { (key, value) -> put(key, value) }
}

@Singleton
class HomeCatalogSettingsSyncService @Inject constructor(private val preferences: OmniaPreferencesSyncService) {
    val isSyncingFromRemote: Boolean get() = preferences.state.value.status == SharedPreferencesSyncStatus.Syncing
    suspend fun pushToRemote(reason: String = "unspecified"): Result<Unit> = runCatching {
        check(preferences.synchronize() != SharedPreferencesSyncStatus.Error) { "Settings could not sync" }
    }
    suspend fun pullFromRemote(): Result<Boolean> = runCatching {
        val status = preferences.synchronize()
        check(status != SharedPreferencesSyncStatus.Error) { "Settings could not sync" }
        status == SharedPreferencesSyncStatus.Synced
    }
    fun triggerPush() = preferences.requestSync()
}

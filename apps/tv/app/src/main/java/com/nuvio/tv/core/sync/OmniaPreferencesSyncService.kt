package com.nuvio.tv.core.sync

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.nuvio.tv.core.auth.AuthManager
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.data.local.CollectionsDataStore
import com.nuvio.tv.data.local.LayoutPreferenceDataStore
import com.nuvio.tv.data.local.ProfileDataStoreFactory
import com.nuvio.tv.domain.model.AuthState
import com.nuvio.tv.domain.repository.AddonRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.jan.supabase.postgrest.Postgrest
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.serialization.json.*
import javax.inject.Inject
import javax.inject.Singleton

/** Called before publishing identity transitions, including conflated A→B→A changes. */
internal object OmniaPreferencesInvalidation {
    @Volatile var invalidate: () -> Unit = {}
    fun beforeIdentityChange() = invalidate()
}

@Singleton
class OmniaPreferencesSyncService @Inject constructor(
    private val authManager: AuthManager,
    private val profileManager: ProfileManager,
    private val factory: ProfileDataStoreFactory,
    private val layout: LayoutPreferenceDataStore,
    private val addons: AddonRepository,
    private val collections: CollectionsDataStore,
    private val postgrest: Postgrest,
    @ApplicationContext context: Context,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val storage = context.getSharedPreferences("omnia_optional_preferences", Context.MODE_PRIVATE)
    private var pending: Job? = null
    @Volatile private var applying = false

    private fun currentScope(): SharedPreferencesScope? {
        val auth = authManager.authState.value as? AuthState.FullAccount ?: return null
        if (!profileManager.activeProfileReady.value) return null
        return SharedPreferencesScope(auth.userId, profileManager.activeProfileId.value)
    }

    private val device = object : SharedPreferencesDevice {
        override val supportedKeys = setOf("continueWatchingVisible", "heroEnabled", "hideUnreleasedContent", "audioLanguage", "subtitleLanguage", "homeCatalogs")
        override fun currentScope() = this@OmniaPreferencesSyncService.currentScope()

        override suspend fun export(scope: SharedPreferencesScope): JsonObject {
            check(currentScope() == scope)
            val home = factory.get(scope.profileId, "layout_settings").data.first()
            val player = factory.get(scope.profileId, "player_settings").data.first()
            val installed = addons.getInstalledAddons().first()
            val groups = collections.getCurrentCollections()
            check(currentScope() == scope)
            val catalogs = layout.exportCatalogSettingsToSyncPayload(installed, groups, scope.profileId)
            check(currentScope() == scope)
            return buildJsonObject {
                put("continueWatchingVisible", home[booleanPreferencesKey("continue_watching_enabled")] ?: true)
                put("heroEnabled", home[booleanPreferencesKey("hero_section_enabled")] ?: true)
                put("hideUnreleasedContent", home[booleanPreferencesKey("hide_unreleased_content")] ?: false)
                put("audioLanguage", player[stringPreferencesKey("preferred_audio_language")] ?: "device")
                put("subtitleLanguage", player[stringPreferencesKey("subtitle_preferred_language")] ?: "device")
                put("homeCatalogs", JsonArray(catalogs.items.filter { row ->
                    if (row.isCollection) isShareableCatalogIdentity(row.collectionId, 128)
                    else isShareableCatalogIdentity(row.addonId, 512) && isShareableCatalogIdentity(row.type, 64) && isShareableCatalogIdentity(row.catalogId, 1024)
                }.map { json.encodeToJsonElement(SyncCatalogItem.serializer(), it) }))
            }
        }

        override suspend fun apply(scope: SharedPreferencesScope, preferences: JsonObject, stillCurrent: () -> Boolean) {
            fun guard() { check(stillCurrent() && currentScope() == scope) { "Account, profile or sync choice changed" } }
            guard(); applying = true
            try {
                preferences["homeCatalogs"]?.let { rows ->
                    val items = (rows as JsonArray).map { json.decodeFromJsonElement(SyncCatalogItem.serializer(), it) }
                    val home = factory.get(scope.profileId, "layout_settings").data.first()
                    guard()
                    layout.applyCatalogSettingsFromRemote(
                        SyncHomeCatalogPayload(home[booleanPreferencesKey("hide_unreleased_content")] ?: false, items),
                        scope.profileId, ::guard,
                    )
                }
                factory.get(scope.profileId, "layout_settings").edit { values ->
                    guard()
                    mapOf("continueWatchingVisible" to "continue_watching_enabled", "heroEnabled" to "hero_section_enabled", "hideUnreleasedContent" to "hide_unreleased_content").forEach { (wire, key) ->
                        preferences[wire]?.jsonPrimitive?.booleanOrNull?.let { values[booleanPreferencesKey(key)] = it }
                    }
                }
                factory.get(scope.profileId, "player_settings").edit { values ->
                    guard()
                    preferences["audioLanguage"]?.jsonPrimitive?.contentOrNull?.let { values[stringPreferencesKey("preferred_audio_language")] = it }
                    preferences["subtitleLanguage"]?.jsonPrimitive?.contentOrNull?.let { values[stringPreferencesKey("subtitle_preferred_language")] = it }
                }
                guard()
            } finally { applying = false }
        }
    }

    private fun JsonObject.snapshot() = SharedPreferencesSnapshot(
        requireNotNull(this["revision"]?.jsonPrimitive?.longOrNull),
        this["preferences"] as? JsonObject ?: error("Invalid saved preferences"),
        requireNotNull(this["profile_instance"]?.jsonPrimitive?.contentOrNull).also { require(it.isNotBlank()) },
    )

    private val transport = object : SharedPreferencesTransport {
        override suspend fun pull(scope: SharedPreferencesScope): SharedPreferencesSnapshot = postgrest.rpc("omnia_pull_preferences_v1", buildJsonObject {
            put("p_expected_owner", scope.owner); put("p_profile_id", scope.profileId)
        }).decodeAs<JsonObject>().snapshot()

        override suspend fun push(scope: SharedPreferencesScope, expectedRevision: Long, preferences: JsonObject, expectedProfileInstance: String?): SharedPreferencesPushResult {
            val result = postgrest.rpc("omnia_push_preferences_v1", buildJsonObject {
                put("p_expected_owner", scope.owner); put("p_profile_id", scope.profileId)
                put("p_expected_revision", expectedRevision); put("p_preferences", preferences)
                put("p_expected_profile_instance", requireNotNull(expectedProfileInstance))
            }).decodeAs<JsonObject>()
            return SharedPreferencesPushResult(
                requireNotNull(result["conflict"]?.jsonPrimitive?.booleanOrNull),
                requireNotNull(result["snapshot"] as? JsonObject).snapshot(),
            )
        }
    }

    private val records = OmniaPreferencesSyncRecordStore(
        { storage.getString(it, null) },
        { key, value -> check(storage.edit().putString(key, value).commit()) { "Unable to save device sync choice" } },
    )
    private val engine = OmniaSharedPreferencesEngine(device, records, transport)
    internal val state = engine.state

    init {
        OmniaPreferencesInvalidation.invalidate = ::invalidateRequests
        engine.refreshLocalState()
        scope.launch {
            combine(authManager.authState, profileManager.activeProfileId, profileManager.activeProfileReady) { _, _, _ -> currentScope() }
                .distinctUntilChanged().collect { pending?.cancel(); engine.refreshLocalState(); requestSync() }
        }
        scope.launch {
            profileManager.activeProfileId.flatMapLatest { id ->
                combine(factory.get(id,"layout_settings").data, factory.get(id,"player_settings").data) { _, _ ->
                    currentScope()?.let { device.export(it).toString() }
                }.distinctUntilChanged().drop(1)
            }.collect { requestSync() }
        }
    }

    internal fun invalidateRequests() { pending?.cancel(); engine.refreshLocalState() }
    internal fun requestSync() {
        if (applying || !state.value.enabled) return
        val expected = currentScope() ?: return
        pending?.cancel()
        pending = scope.launch { delay(750); if (currentScope() == expected) engine.synchronize() }
    }
    internal suspend fun synchronize() = engine.synchronize()
    internal suspend fun enable(choice: SharedPreferencesInitialChoice? = null) = engine.enable(choice)
    internal suspend fun disable() = engine.disable()
    internal fun cancelInitialChoice() = engine.refreshLocalState()
}

package com.nuvio.app.core.sync

import com.nuvio.app.core.auth.AuthRepository
import com.nuvio.app.core.auth.AuthState
import com.nuvio.app.core.network.SupabaseProvider
import com.nuvio.app.features.home.HomeCatalogSettingsRepository
import com.nuvio.app.features.home.SyncCatalogItem
import com.nuvio.app.features.player.PlayerSettingsRepository
import com.nuvio.app.features.profiles.ProfileRepository
import com.nuvio.app.features.watchprogress.ContinueWatchingPreferencesRepository
import io.github.jan.supabase.postgrest.postgrest
import io.github.jan.supabase.postgrest.rpc
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*

/** Compatible preferences only. Account tokens, sources and hardware tuning never enter this wire. */
internal object OmniaPreferencesSync {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private var identityJob: Job? = null
    private var preferencesJob: Job? = null
    private var pendingPush: Job? = null
    private var applying = false

    private fun currentScope(): SharedPreferencesScope? {
        val auth = AuthRepository.state.value as? AuthState.Authenticated ?: return null
        if (auth.isAnonymous || !ProfileRepository.state.value.isLoaded) return null
        return SharedPreferencesScope(auth.userId, ProfileRepository.activeProfileId)
    }

    private val device = object : SharedPreferencesDevice {
        override val supportedKeys = setOf("continueWatchingVisible", "heroEnabled", "hideUnreleasedContent", "audioLanguage", "subtitleLanguage", "homeCatalogs")
        override fun currentScope() = OmniaPreferencesSync.currentScope()

        override suspend fun export(scope: SharedPreferencesScope): JsonObject = withContext(Dispatchers.Main.immediate) {
            check(currentScope() == scope) { "Account or profile changed" }
            ContinueWatchingPreferencesRepository.ensureLoaded()
            PlayerSettingsRepository.ensureLoaded()
            val catalogs = HomeCatalogSettingsRepository.exportToSyncPayload(knownOnly = true)
            val home = HomeCatalogSettingsRepository.uiState.value
            val player = PlayerSettingsRepository.uiState.value
            buildJsonObject {
                put("continueWatchingVisible", ContinueWatchingPreferencesRepository.uiState.value.isVisible)
                put("heroEnabled", home.heroEnabled)
                put("hideUnreleasedContent", home.hideUnreleasedContent)
                put("audioLanguage", player.preferredAudioLanguage)
                put("subtitleLanguage", player.preferredSubtitleLanguage)
                put("homeCatalogs", JsonArray(catalogs.items.filter { row ->
                    if (row.isCollection) isShareableCatalogIdentity(row.collectionId, 128)
                    else isShareableCatalogIdentity(row.addonId, 512) &&
                        isShareableCatalogIdentity(row.type, 64) &&
                        isShareableCatalogIdentity(row.catalogId, 1024)
                }.map { row -> JsonObject(json.encodeToJsonElement(SyncCatalogItem.serializer(), row).jsonObject - "key") }))
            }
        }

        override suspend fun apply(scope: SharedPreferencesScope, preferences: JsonObject, stillCurrent: () -> Boolean) = withContext(Dispatchers.Main.immediate) {
            fun guard() { check(stillCurrent() && currentScope() == scope) { "Account, profile or sync choice changed" } }
            guard()
            // All repository writes below are synchronous; each checks the request guard.
            // No suspended network or storage operation can resume into a different profile.
            applying = true
            try {
                preferences["homeCatalogs"]?.let { rows ->
                    val items = (rows as JsonArray).map { json.decodeFromJsonElement(SyncCatalogItem.serializer(), it) }
                    val local = HomeCatalogSettingsRepository.exportToSyncPayload()
                    guard(); HomeCatalogSettingsRepository.applyFromRemote(local.copy(items = items))
                }
                preferences["continueWatchingVisible"]?.jsonPrimitive?.booleanOrNull?.let { guard(); ContinueWatchingPreferencesRepository.setVisible(it) }
                preferences["heroEnabled"]?.jsonPrimitive?.booleanOrNull?.let { guard(); HomeCatalogSettingsRepository.setHeroEnabled(it) }
                preferences["hideUnreleasedContent"]?.jsonPrimitive?.booleanOrNull?.let { guard(); HomeCatalogSettingsRepository.setHideUnreleasedContent(it) }
                preferences["audioLanguage"]?.jsonPrimitive?.contentOrNull?.let { guard(); PlayerSettingsRepository.setPreferredAudioLanguage(it) }
                preferences["subtitleLanguage"]?.jsonPrimitive?.contentOrNull?.let { guard(); PlayerSettingsRepository.setPreferredSubtitleLanguage(it) }
                guard()
            } finally { applying = false }
        }
    }

    private fun JsonObject.snapshot(): SharedPreferencesSnapshot = SharedPreferencesSnapshot(
        requireNotNull(this["revision"]?.jsonPrimitive?.longOrNull),
        this["preferences"] as? JsonObject ?: error("Invalid saved preferences"),
        requireNotNull(this["profile_instance"]?.jsonPrimitive?.contentOrNull).also { require(it.isNotBlank()) },
    )

    private val transport = object : SharedPreferencesTransport {
        override suspend fun pull(scope: SharedPreferencesScope): SharedPreferencesSnapshot =
            SupabaseProvider.client.postgrest.rpc("omnia_pull_preferences_v1", buildJsonObject {
                put("p_expected_owner", scope.owner); put("p_profile_id", scope.profileId)
            }).decodeAs<JsonObject>().snapshot()

        override suspend fun push(scope: SharedPreferencesScope, expectedRevision: Long, preferences: JsonObject, expectedProfileInstance: String?): SharedPreferencesPushResult {
            val response = SupabaseProvider.client.postgrest.rpc("omnia_push_preferences_v1", buildJsonObject {
                put("p_expected_owner", scope.owner); put("p_profile_id", scope.profileId)
                put("p_expected_revision", expectedRevision); put("p_preferences", preferences)
                put("p_expected_profile_instance", requireNotNull(expectedProfileInstance))
            }).decodeAs<JsonObject>()
            return SharedPreferencesPushResult(
                requireNotNull(response["conflict"]?.jsonPrimitive?.booleanOrNull),
                requireNotNull(response["snapshot"] as? JsonObject).snapshot(),
            )
        }
    }

    private val records = OmniaPreferencesSyncRecordStore(OmniaPreferencesSyncStorage::load, OmniaPreferencesSyncStorage::save)
    private val engine = OmniaSharedPreferencesEngine(device, records, transport)
    val state = engine.state

    fun startObserving() {
        if (identityJob?.isActive == true) return
        engine.refreshLocalState()
        identityJob = scope.launch {
            combine(AuthRepository.state, ProfileRepository.state) { _, _ -> currentScope() }
                .distinctUntilChanged().collect {
                    pendingPush?.cancel(); engine.refreshLocalState()
                    requestSync()
                }
        }
        preferencesJob = scope.launch {
            combine(ContinueWatchingPreferencesRepository.uiState, HomeCatalogSettingsRepository.uiState, PlayerSettingsRepository.uiState) { _, _, _ ->
                currentScope()?.let { device.export(it).toString() }
            }.distinctUntilChanged().drop(1).collect { requestSync() }
        }
    }

    /** Call before profile/account transition, even if an A→B→A flow emission is conflated. */
    fun invalidateRequests() {
        pendingPush?.cancel()
        engine.refreshLocalState()
    }

    fun onProfileChanged() { invalidateRequests(); requestSync() }

    fun clearAccountState() {
        invalidateRequests()
        identityJob?.cancel(); identityJob = null
        preferencesJob?.cancel(); preferencesJob = null
        OmniaPreferencesSyncStorage.clear()
        engine.refreshLocalState()
    }

    fun requestSync() {
        if (applying || !state.value.enabled) return
        val expected = currentScope() ?: return
        pendingPush?.cancel()
        pendingPush = scope.launch {
            delay(750)
            if (currentScope() == expected) engine.synchronize()
        }
    }

    suspend fun synchronize(profileId: Int = ProfileRepository.activeProfileId): SharedPreferencesSyncStatus {
        if (currentScope()?.profileId != profileId) return SharedPreferencesSyncStatus.SignInRequired
        return engine.synchronize()
    }

    suspend fun enable(choice: SharedPreferencesInitialChoice? = null) = engine.enable(choice)
    suspend fun disable() = engine.disable()
    fun cancelInitialChoice() = engine.refreshLocalState()
}

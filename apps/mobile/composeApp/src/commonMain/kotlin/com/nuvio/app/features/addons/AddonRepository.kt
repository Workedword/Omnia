package com.nuvio.app.features.addons

import co.touchlab.kermit.Logger
import com.nuvio.app.core.network.SupabaseProvider
import com.nuvio.app.core.sync.putSyncOriginClientId
import com.nuvio.app.features.profiles.ProfileRepository
import io.github.jan.supabase.postgrest.postgrest
import io.github.jan.supabase.postgrest.query.Order
import io.github.jan.supabase.postgrest.rpc
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.encodeToJsonElement
import kotlinx.serialization.json.put
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.getString

@Serializable
private data class AddonRow(
    val url: String,
    val name: String? = null,
    val enabled: Boolean = true,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
private data class AddonPushItem(
    val url: String,
    val name: String = "",
    val enabled: Boolean = true,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

private const val ADDON_PUSH_DEBOUNCE_MS = 500L

object AddonRepository {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val log = Logger.withTag("AddonRepository")
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val _uiState = MutableStateFlow(AddonsUiState())
    val uiState: StateFlow<AddonsUiState> = _uiState.asStateFlow()

    private var initialized = false
    private var currentProfileId: Int = 1
    private val activeRefreshJobs = mutableMapOf<String, Job>()
    private val pushJobsByProfile = mutableMapOf<Int, Job>()

    fun initialize() {
        val effectiveProfileId = resolveEffectiveProfileId(ProfileRepository.activeProfileId)
        if (initialized) return
        initialized = true
        currentProfileId = effectiveProfileId
        log.d { "initialize() — loading local addons for profile $currentProfileId" }

        val envelope = readEnvelope(captureScope())
        val storedUrls = dedupeManifestUrls(envelope?.local?.map { it.url } ?: AddonStorage.loadInstalledAddonUrls(currentProfileId))
        val enabledByUrl = envelope?.local?.associate { omniaManifestUrl(it.url) to it.enabled } ?: loadLocalEnabledStates()
        log.d { "initialize() — local addon count: ${storedUrls.size}" }
        if (storedUrls.isEmpty()) return

        val existingByUrl = _uiState.value.addons.associateBy(ManagedAddon::manifestUrl)
        _uiState.value = AddonsUiState(
            addons = storedUrls.map { manifestUrl ->
                existingByUrl[manifestUrl].toPendingAddon(
                    manifestUrl = manifestUrl,
                    userSetName = envelope?.local?.firstOrNull { omniaManifestUrl(it.url) == manifestUrl }?.name,
                    enabled = enabledByUrl[manifestUrl],
                )
            },
        )

        storedUrls.forEach { manifestUrl ->
            val existing = existingByUrl[manifestUrl]
            val addon = _uiState.value.addons.firstOrNull { it.manifestUrl == manifestUrl }
            if (addon?.enabled == true && (existing == null || (addon.manifest == null && !addon.isRefreshing))) {
                refreshAddon(manifestUrl)
            }
        }
    }

    fun onProfileChanged(profileId: Int) {
        val effectiveProfileId = resolveEffectiveProfileId(profileId)
        if (effectiveProfileId == currentProfileId && initialized) return
        cancelActiveRefreshes()
        pushJobsByProfile.values.forEach(Job::cancel)
        pushJobsByProfile.clear()
        _syncStatus.value = OmniaAddonSyncStatus.Idle
        currentProfileId = effectiveProfileId
        initialized = false
        _uiState.value = AddonsUiState()
    }

    fun clearLocalState() {
        cancelActiveRefreshes()
        pushJobsByProfile.values.forEach(Job::cancel)
        pushJobsByProfile.clear()
        _syncStatus.value = OmniaAddonSyncStatus.Idle
        currentProfileId = 1
        initialized = false
        _uiState.value = AddonsUiState()
    }

    private val syncMutex = kotlinx.coroutines.sync.Mutex()
    private val _syncStatus = MutableStateFlow(OmniaAddonSyncStatus.Idle)
    val syncStatus: StateFlow<OmniaAddonSyncStatus> = _syncStatus.asStateFlow()
    private data class SyncScope(val owner: String?, val selected: Int, val profile: Int, val readOnly: Boolean)
    private fun captureScope(): SyncScope {
        val auth = com.nuvio.app.core.auth.AuthRepository.state.value as? com.nuvio.app.core.auth.AuthState.Authenticated
        val selected = ProfileRepository.activeProfileId
        return SyncScope(auth?.takeUnless { it.isAnonymous }?.userId, selected, resolveEffectiveProfileId(selected), isUsingPrimaryAddonsFromSecondaryProfile())
    }
    private fun checkScope(expected: SyncScope) {
        check(captureScope() == expected && currentProfileId == expected.profile) { "Account or profile changed; sync again" }
    }
    private fun readEnvelope(expected: SyncScope): OmniaAddonEnvelope? = expected.owner?.let { owner ->
        AddonStorage.loadSyncEnvelope(owner, expected.profile)?.let { json.decodeFromString<OmniaAddonEnvelope>(it) }
    }
    private fun localSyncRows(): List<OmniaSyncAddon> = _uiState.value.addons.mapIndexed { i, addon ->
        OmniaSyncAddon(omniaAddonKey(addon.manifestUrl), addon.userSetName.orEmpty(), addon.enabled, i)
    }
    private fun applySnapshot(expected: SyncScope, snapshot: OmniaAddonSnapshot, beforeRequest: List<OmniaSyncAddon>?) {
        checkScope(expected)
        val rows = omniaMergeAddons(beforeRequest, localSyncRows(), snapshot.addons)
        // One durable envelope holds BOTH acknowledged state and unsent local changes. URL/name
        // values stay private in the app sandbox. Owner and profile are part of the storage key.
        AddonStorage.saveSyncEnvelope(expected.owner!!, expected.profile, json.encodeToString(OmniaAddonEnvelope.serializer(), OmniaAddonEnvelope(snapshot, rows)))
        val existing = _uiState.value.addons.associateBy { omniaAddonKey(it.manifestUrl) }
        _uiState.value = _uiState.value.copy(addons = rows.map { row ->
            existing[row.url].toPendingAddon(omniaManifestUrl(row.url), row.name, row.enabled)
        })
        persist(expected)
        initialized = true
        refreshAll()
    }
    private suspend fun syncLocked(expected: SyncScope) {
        checkScope(expected)
        check(expected.owner != null) { "Sign in to sync add-ons" }
        val envelope = readEnvelope(expected)
        val local = localSyncRows()
        val base = envelope?.acknowledged?.addons
        var remote = SupabaseProvider.client.postgrest.rpc("sync_pull_addons_v2", buildJsonObject {
            put("p_profile_id", expected.profile)
            put("p_expected_owner", expected.owner)
        }).decodeAs<OmniaAddonSnapshot>()
        checkScope(expected)
        if (expected.readOnly || omniaMergeAddons(base, local, remote.addons) == omniaNormalizeAddons(remote.addons)) {
            applySnapshot(expected, remote, base)
            return
        }
        repeat(4) {
            checkScope(expected)
            val merged = omniaMergeAddons(base, local, remote.addons)
            val response = SupabaseProvider.client.postgrest.rpc("sync_push_addons_v2", buildJsonObject {
                put("p_profile_id", expected.profile)
                put("p_expected_owner", expected.owner)
                put("p_expected_revision", remote.revision)
                put("p_addons", json.encodeToJsonElement(merged))
                putSyncOriginClientId()
            }).decodeAs<OmniaAddonWriteResult>()
            checkScope(expected)
            if (!response.conflict) {
                applySnapshot(expected, response.snapshot, local)
                return
            }
            remote = response.snapshot
        }
        error("Add-ons changed on another device; sync again")
    }
    private suspend fun ensureReadyForEdit(expected: SyncScope) {
        checkScope(expected)
        if (expected.owner != null && readEnvelope(expected) == null) syncLocked(expected)
    }
    private suspend fun synchronize() {
        syncMutex.withLock {
            initialize()
            val expected = captureScope()
            if (expected.owner == null) { _syncStatus.value = OmniaAddonSyncStatus.SignIn; return@withLock }
            _syncStatus.value = OmniaAddonSyncStatus.Syncing
            try {
                syncLocked(expected)
                _syncStatus.value = OmniaAddonSyncStatus.Success
            } catch (error: CancellationException) { _syncStatus.value = OmniaAddonSyncStatus.Idle; throw error }
            catch (error: Exception) {
                _syncStatus.value = OmniaAddonSyncStatus.Error
                log.e { "Add-on sync failed (${error::class.simpleName})" }
                throw error
            }
        }
    }
    fun syncAddonsNow() {
        if (_syncStatus.value == OmniaAddonSyncStatus.Syncing) return
        scope.launch {
            try { synchronize() } catch (error: CancellationException) { throw error }
            catch (_: Exception) { /* status contains the user-visible retry state */ }
        }
    }
    suspend fun pullFromServer(profileId: Int) {
        if (ProfileRepository.activeProfileId != profileId) return
        try { synchronize() } catch (error: CancellationException) { throw error }
        catch (_: Exception) { /* retain local data and report the failed sync */ }
    }
    private fun launchMutation(change: () -> Unit) {
        val expected = captureScope()
        if (expected.readOnly) return
        scope.launch {
            try {
                syncMutex.withLock {
                    ensureReadyForEdit(expected)
                    checkScope(expected)
                    change()
                    persist(expected)
                    pushToServer()
                }
            } catch (error: CancellationException) { throw error }
            catch (_: Exception) { _syncStatus.value = OmniaAddonSyncStatus.Error }
        }
    }

    suspend fun awaitManifestsLoaded() {
        if (_uiState.value.addons.isEmpty()) return
        uiState.first { state ->
            state.addons.isEmpty() ||
                state.addons.any { it.manifest != null } ||
                state.addons.none { it.isRefreshing }
        }
    }

    suspend fun addAddon(rawUrl: String): AddAddonResult {
        if (isUsingPrimaryAddonsFromSecondaryProfile()) {
            return AddAddonResult.Error(getString(Res.string.profile_primary_addons_required))
        }
        val installScope = captureScope()
        log.i { "addAddon() — install requested" }
        val manifestUrl = try {
            normalizeManifestUrl(rawUrl)
        } catch (error: IllegalArgumentException) {
            return AddAddonResult.Error(error.message ?: getString(Res.string.addon_invalid_url))
        }

        if (_uiState.value.addons.any { it.manifestUrl == manifestUrl }) {
            return AddAddonResult.Error(getString(Res.string.addon_already_installed))
        }

        val manifest = try {
            withContext(Dispatchers.Default) {
                val payload = fetchAddonResponseText(manifestUrl)
                AddonManifestParser.parse(
                    manifestUrl = manifestUrl,
                    payload = payload,
                )
            }
        } catch (error: CancellationException) { throw error }
        catch (error: Throwable) {
            return AddAddonResult.Error(error.message ?: getString(Res.string.addon_load_manifest_failed))
        }

        return try {
            syncMutex.withLock {
                ensureReadyForEdit(installScope)
                checkScope(installScope)
        _uiState.update { current ->
            // A deep link can be delivered again while its manifest is loading.
            // Recheck inside the atomic update so concurrent installs cannot append twice.
            if (current.addons.any { it.manifestUrl == manifestUrl }) current else current.copy(
                addons = current.addons + ManagedAddon(
                    manifestUrl = manifestUrl,
                    manifest = manifest,
                    isRefreshing = false,
                    errorMessage = null,
                ),
            )
        }
        persist(installScope)
        pushToServer()
                AddAddonResult.Success(manifest)
            }
        } catch (error: CancellationException) { throw error }
        catch (_: Exception) { AddAddonResult.Error("Could not sync add-ons. Check your connection and try again.") }
    }

    fun removeAddon(manifestUrl: String) = launchMutation {
        _uiState.update { current -> current.copy(addons = current.addons.filterNot { omniaAddonKey(it.manifestUrl) == omniaAddonKey(manifestUrl) }) }
    }

    fun moveAddon(fromIndex: Int, toIndex: Int) {
        val rows = _uiState.value.addons
        val moving = rows.getOrNull(fromIndex)?.manifestUrl ?: return
        val anchor = rows.getOrNull(toIndex)?.manifestUrl ?: return
        if (fromIndex == toIndex) return
        launchMutation {
            _uiState.update { current ->
                val addons = current.addons.toMutableList()
                val from = addons.indexOfFirst { it.manifestUrl == moving }
                if (from < 0 || addons.none { it.manifestUrl == anchor }) return@update current
                val item = addons.removeAt(from)
                val target = addons.indexOfFirst { it.manifestUrl == anchor }
                addons.add(target + if (fromIndex < toIndex) 1 else 0, item)
                current.copy(addons = addons)
            }
        }
    }

    fun setAddonEnabled(manifestUrl: String, enabled: Boolean) = launchMutation {
        _uiState.update { current -> current.copy(addons = current.addons.map {
            if (omniaAddonKey(it.manifestUrl) == omniaAddonKey(manifestUrl)) it.copy(enabled = enabled) else it
        }) }
        if (enabled) refreshAddon(manifestUrl)
    }

    fun refreshAll() {
        _uiState.value.addons.filter { it.enabled }.distinctBy { it.manifestUrl }.forEach { addon ->
            refreshAddon(
                manifestUrl = addon.manifestUrl,
                forceRefresh = true,
            )
        }
    }

    fun refreshAddon(
        manifestUrl: String,
        forceRefresh: Boolean = false,
    ) {
        val existingJob = activeRefreshJobs[manifestUrl]
        if (existingJob?.isActive == true) return

        markRefreshing(manifestUrl)
        var refreshJob: Job? = null
        refreshJob = scope.launch {
            try {
                val result = runCatching {
                    val payload = fetchAddonResponseText(
                        url = manifestUrl,
                        forceRefresh = forceRefresh,
                    )
                    AddonManifestParser.parse(
                        manifestUrl = manifestUrl,
                        payload = payload,
                    )
                }

                _uiState.update { current ->
                    current.copy(
                        addons = current.addons.map { addon ->
                            if (addon.manifestUrl != manifestUrl) {
                                addon
                            } else {
                                result.fold(
                                    onSuccess = { manifest ->
                                        addon.copy(
                                            manifest = manifest,
                                            isRefreshing = false,
                                            errorMessage = null,
                                        )
                                    },
                                    onFailure = { error ->
                                        addon.copy(
                                            isRefreshing = false,
                                            errorMessage = error.message ?: getString(Res.string.addon_load_manifest_failed),
                                        )
                                    },
                                )
                            }
                        },
                    )
                }
            } finally {
                if (activeRefreshJobs[manifestUrl] === refreshJob) {
                    activeRefreshJobs.remove(manifestUrl)
                }
            }
        }
        activeRefreshJobs[manifestUrl] = refreshJob
    }

    private fun pushToServer() {
        val expected = captureScope()
        if (expected.readOnly || expected.owner == null) return
        pushJobsByProfile[expected.profile]?.cancel()
        var pushJob: Job? = null
        pushJob = scope.launch {
            try {
                delay(ADDON_PUSH_DEBOUNCE_MS)
                checkScope(expected)
                synchronize()
            } catch (error: CancellationException) { throw error }
            catch (_: Exception) { _syncStatus.value = OmniaAddonSyncStatus.Error }
            finally {
                if (pushJobsByProfile[expected.profile] === pushJob) pushJobsByProfile.remove(expected.profile)
            }
        }
        pushJobsByProfile[expected.profile] = pushJob
    }

    private fun markRefreshing(manifestUrl: String) {
        _uiState.update { current ->
            current.copy(
                addons = current.addons.map { addon ->
                    if (addon.manifestUrl == manifestUrl) {
                        addon.copy(
                            isRefreshing = true,
                            errorMessage = null,
                        )
                    } else {
                        addon
                    }
                },
            )
        }
    }

    private fun persist(expected: SyncScope = captureScope()) {
        checkScope(expected)
        val addons = _uiState.value.addons
        readEnvelope(expected)?.let { envelope ->
            AddonStorage.saveSyncEnvelope(expected.owner!!, expected.profile, json.encodeToString(OmniaAddonEnvelope.serializer(), envelope.copy(local = localSyncRows())))
        }
        AddonStorage.saveInstalledAddonUrls(
            currentProfileId,
            dedupeManifestUrls(addons.map { it.manifestUrl }),
        )
        AddonStorage.saveAddonEnabledStates(
            currentProfileId,
            addons.associate { it.manifestUrl to it.enabled },
        )
    }

    private fun loadLocalEnabledStates(): Map<String, Boolean> =
        AddonStorage.loadAddonEnabledStates(currentProfileId)
            .mapKeys { (url, _) -> ensureManifestSuffix(url) }

    private fun cancelActiveRefreshes() {
        activeRefreshJobs.values.forEach(Job::cancel)
        activeRefreshJobs.clear()
    }

    private fun resolveEffectiveProfileId(profileId: Int): Int {
        val active = ProfileRepository.state.value.activeProfile
        return if (active != null && active.profileIndex != 1 && active.usesPrimaryAddons) 1 else profileId
    }

    private fun isUsingPrimaryAddonsFromSecondaryProfile(): Boolean {
        val active = ProfileRepository.state.value.activeProfile
        return active != null && active.profileIndex != 1 && active.usesPrimaryAddons
    }
}

private fun ManagedAddon?.toPendingAddon(
    manifestUrl: String,
    userSetName: String? = null,
    enabled: Boolean? = null,
): ManagedAddon =
    when {
        this == null -> ManagedAddon(
            manifestUrl = manifestUrl,
            isRefreshing = enabled ?: true,
            userSetName = userSetName,
            enabled = enabled ?: true,
        )
        manifest != null -> copy(
            manifestUrl = manifestUrl,
            isRefreshing = false,
            userSetName = userSetName ?: this.userSetName,
            enabled = enabled ?: this.enabled,
        )
        isRefreshing -> copy(
            manifestUrl = manifestUrl,
            userSetName = userSetName ?: this.userSetName,
            enabled = enabled ?: this.enabled,
        )
        else -> copy(
            manifestUrl = manifestUrl,
            isRefreshing = enabled ?: this.enabled,
            errorMessage = null,
            userSetName = userSetName ?: this.userSetName,
            enabled = enabled ?: this.enabled,
        )
    }

private fun dedupeManifestUrls(urls: List<String>): List<String> =
    urls.map(::ensureManifestSuffix).distinct()

private fun ensureManifestSuffix(url: String): String = omniaManifestUrl(url)

private fun normalizeManifestUrl(rawUrl: String): String {
    val trimmed = rawUrl.trim()
    require(trimmed.isNotEmpty()) { runBlocking { getString(Res.string.addons_error_enter_url) } }

    val normalizedScheme = when {
        trimmed.startsWith("http://") || trimmed.startsWith("https://") -> trimmed
        trimmed.startsWith("stremio://") -> "https://${trimmed.removePrefix("stremio://")}"
        else -> "https://$trimmed"
    }

    val withoutFragment = normalizedScheme.substringBefore("#")
    val query = withoutFragment.substringAfter("?", "")
    val path = withoutFragment.substringBefore("?").trimEnd('/')
    val manifestPath = if (path.endsWith("/manifest.json")) {
        path
    } else {
        "$path/manifest.json"
    }

    return if (query.isEmpty()) manifestPath else "$manifestPath?$query"
}

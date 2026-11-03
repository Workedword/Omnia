package com.nuvio.tv.core.sync

import com.nuvio.tv.core.auth.AuthManager
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.data.local.AddonPreferences
import com.nuvio.tv.domain.model.AuthState
import io.github.jan.supabase.postgrest.Postgrest
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AddonSyncService @Inject constructor(
    private val postgrest: Postgrest,
    private val authManager: AuthManager,
    private val addonPreferences: AddonPreferences,
    private val profileManager: ProfileManager,
    private val syncClientIdentity: SyncClientIdentity,
) {
    private val syncMutex = Mutex()
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    private data class Scope(val owner: String, val selected: Int, val profile: Int, val readOnly: Boolean)
    private fun captureScope(): Scope {
        val owner = (authManager.authState.value as? AuthState.FullAccount)?.userId
            ?: error("Sign in to sync add-ons")
        val selected = profileManager.activeProfileId.value
        val active = profileManager.activeProfile
        val readOnly = active != null && !active.isPrimary && active.usesPrimaryAddons
        return Scope(owner, selected, if (readOnly) 1 else selected, readOnly)
    }
    private fun checkScope(expected: Scope) {
        check(captureScope() == expected) { "Account or profile changed; sync again" }
    }
    private suspend fun <T> request(expected: Scope, block: suspend () -> T): T {
        checkScope(expected)
        return try { block() } catch (error: CancellationException) { throw error }
        catch (error: Exception) {
            checkScope(expected)
            if (!authManager.refreshSessionIfJwtExpired(error)) throw error
            checkScope(expected)
            block()
        }.also { checkScope(expected) }
    }

    /** Establish a server baseline before the first signed-in edit. Offline edits after that
     * baseline remain local and are merged on the next successful sync. */
    suspend fun ensureReadyForEdit() {
        if (authManager.authState.value !is AuthState.FullAccount) return
        val expected = captureScope()
        if (expected.readOnly) return
        if (addonPreferences.readSyncState(expected.owner, expected.profile).second == null) {
            synchronize().getOrThrow()
        }
    }

    suspend fun pushToRemote(): Result<Unit> = synchronize().map { Unit }
    suspend fun getRemoteAddonUrls(): Result<List<String>> = synchronize()

    private suspend fun synchronize(): Result<List<String>> = withContext(Dispatchers.IO) {
        try {
            Result.success(syncMutex.withLock {
                val expected = captureScope()
                val (local, acknowledged) = addonPreferences.readSyncState(expected.owner, expected.profile)
                var remote = request(expected) {
                    postgrest.rpc("sync_pull_addons_v2", buildJsonObject { put("p_profile_id", expected.profile); put("p_expected_owner", expected.owner) })
                        .decodeAs<OmniaAddonSnapshot>()
                }
                val base = acknowledged?.addons
                val desired = omniaMergeAddons(base, local, remote.addons)
                if (expected.readOnly || desired == omniaNormalizeAddons(remote.addons)) {
                    checkScope(expected)
                    return@withLock addonPreferences.acceptSyncSnapshot(expected.owner, expected.profile, remote, base)
                }
                repeat(4) {
                    checkScope(expected)
                    val merged = omniaMergeAddons(base, local, remote.addons)
                    val response = request(expected) {
                        postgrest.rpc("sync_push_addons_v2", buildJsonObject {
                            put("p_profile_id", expected.profile)
                            put("p_expected_owner", expected.owner)
                            put("p_expected_revision", remote.revision)
                            put("p_addons", json.encodeToJsonElement(merged))
                            putSyncOriginClientId(syncClientIdentity)
                        }).decodeAs<OmniaAddonWriteResult>()
                    }
                    if (!response.conflict) {
                        checkScope(expected)
                        // Preserve edits made locally while this request was in flight.
                        return@withLock addonPreferences.acceptSyncSnapshot(expected.owner, expected.profile, response.snapshot, local)
                    }
                    remote = response.snapshot
                }
                error("Add-ons changed on another device; sync again")
            })
        } catch (error: CancellationException) { throw error }
        catch (error: Exception) { Result.failure(error) }
    }
}

package com.nuvio.tv.mobile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nuvio.tv.core.auth.AuthManager
import com.nuvio.tv.core.debrid.DebridProviders
import com.nuvio.tv.core.network.NetworkResult
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.core.sync.AddonSyncService
import com.nuvio.tv.core.sync.ProfileSyncService
import com.nuvio.tv.core.sync.ProviderCredentialSyncService
import com.nuvio.tv.data.local.DebridSettingsDataStore
import com.nuvio.tv.data.local.StartupSyncPreferences
import com.nuvio.tv.data.remote.api.RealDebridApi
import com.nuvio.tv.data.repository.AddonRepositoryImpl
import com.nuvio.tv.domain.model.Addon
import com.nuvio.tv.domain.model.AuthState
import com.nuvio.tv.domain.model.ServerConfiguration
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

internal fun secureAddonUrl(value: String): String? {
    val parsed = value.trim().toHttpUrlOrNull() ?: return null
    return parsed.takeIf { it.isHttps && it.username.isEmpty() && it.password.isEmpty() && it.fragment == null }?.toString()
}

@HiltViewModel
class MobileCompanionViewModel @Inject constructor(
    private val auth: AuthManager,
    private val repository: AddonRepositoryImpl,
    private val addonSync: AddonSyncService,
    private val profileSync: ProfileSyncService,
    private val profiles: ProfileManager,
    private val credentialSync: ProviderCredentialSyncService,
    private val debrid: DebridSettingsDataStore,
    private val realDebrid: RealDebridApi,
    private val syncPreferences: StartupSyncPreferences,
    val server: ServerConfiguration
) : ViewModel() {
    private val operationMutex = Mutex()
    val account = auth.authState
    val addons = repository.getInstalledAddons().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val busy = MutableStateFlow(false)
    val ready = MutableStateFlow(false)
    val message = MutableStateFlow<String?>(null)
    val canSignIn get() = server.isConfigured && server.isSecure && server.isCustom && server.capabilities.emailPasswordAuth

    init {
        viewModelScope.launch {
            account.collectLatest { state ->
                ready.value = false
                if (state is AuthState.FullAccount && canSignIn) {
                    operationMutex.withLock {
                    busy.value = true
                    try {
                        pull()
                        ready.value = true
                        message.value = "Account settings loaded. Changes are shared with your TV."
                    } catch (e: CancellationException) { throw e
                    } catch (_: Exception) {
                        message.value = "Could not load account settings. Check your connection and tap Refresh."
                    } finally { busy.value = false }
                    }
                }
            }
        }
    }

    private suspend fun pull() {
        profileSync.pullFromRemote(force = true).getOrThrow()
        profiles.setActiveProfile(1)
        repository.isSyncingFromRemote = true
        try {
            val initialLink = syncPreferences.getState(1).lastFullPullUserId != (account.value as? AuthState.FullAccount)?.userId
            repository.reconcileWithRemoteAddonUrls(addonSync.getRemoteAddonUrls().getOrThrow(), removeMissingLocal = !initialLink)
            if (initialLink) addonSync.pushToRemote().getOrThrow()
        } finally { repository.isSyncingFromRemote = false }
        credentialSync.syncFromRemote().getOrThrow()
    }

    private fun task(success: String, block: suspend () -> Unit) {
        if (busy.value) return
        busy.value = true
        message.value = null
        viewModelScope.launch {
            operationMutex.withLock {
            try {
                block()
                message.value = success
            } catch (e: CancellationException) { throw e
            } catch (_: Exception) {
                message.value = "Could not complete that action. Check the details and your connection, then retry."
            } finally { busy.value = false }
            }
        }
    }

    fun signIn(email: String, password: String) {
        if (!canSignIn || email.isBlank() || password.isBlank()) return
        task("Signed in. Loading your account…") { auth.signInWithEmail(email.trim(), password).getOrThrow() }
    }

    fun signOut() = task("Signed out.") { ready.value = false; auth.signOut() }

    fun refresh() {
        if (account.value !is AuthState.FullAccount) return
        task("Account settings refreshed.") { ready.value = false; pull(); ready.value = true }
    }

    fun install(value: String) {
        if (!ready.value) return
        val url = secureAddonUrl(value)
        if (url == null) { message.value = "Enter an HTTPS add-on manifest URL."; return }
        task("Add-on saved to your account.") {
            when (repository.fetchAddon(url)) {
                is NetworkResult.Success -> repository.addAddon(url)
                else -> error("Invalid add-on")
            }
            addonSync.pushToRemote().getOrThrow()
        }
    }

    fun toggle(addon: Addon, enabled: Boolean) {
        if (!ready.value) return
        task("Add-on setting saved to your account.") {
            repository.setAddonEnabled(addon.baseUrl, enabled)
            addonSync.pushToRemote().getOrThrow()
        }
    }

    fun remove(addon: Addon) {
        if (!ready.value) return
        task("Add-on removed from your account.") {
            repository.removeAddon(addon.baseUrl)
            addonSync.pushToRemote().getOrThrow()
        }
    }

    fun saveRealDebrid(key: String) {
        if (!ready.value || key.isBlank()) return
        task("Real-Debrid credential saved to your account.") {
            val response = realDebrid.getUser("Bearer ${key.trim()}")
            try { check(response.isSuccessful) } finally { response.body()?.close(); response.errorBody()?.close() }
            debrid.setProviderApiKey(DebridProviders.REAL_DEBRID_ID, key.trim())
            debrid.setEnabled(true)
            credentialSync.syncFromRemote().getOrThrow()
        }
    }
}

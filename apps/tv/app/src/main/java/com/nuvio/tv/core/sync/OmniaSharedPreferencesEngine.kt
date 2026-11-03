package com.nuvio.tv.core.sync

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.JsonObject

internal data class SharedPreferencesLocalRecord(
    val enabled: Boolean = false,
    val baseline: SharedPreferencesSnapshot? = null,
)

internal interface SharedPreferencesLocalStore {
    fun load(scope: SharedPreferencesScope): SharedPreferencesLocalRecord
    fun save(scope: SharedPreferencesScope, record: SharedPreferencesLocalRecord)
}

internal data class SharedPreferencesPushResult(
    val conflict: Boolean,
    val snapshot: SharedPreferencesSnapshot,
)

internal interface SharedPreferencesTransport {
    suspend fun pull(scope: SharedPreferencesScope): SharedPreferencesSnapshot
    suspend fun push(scope: SharedPreferencesScope, expectedRevision: Long, preferences: JsonObject, expectedProfileInstance: String?): SharedPreferencesPushResult
}

internal interface SharedPreferencesDevice {
    val supportedKeys: Set<String>
    fun currentScope(): SharedPreferencesScope?
    suspend fun export(scope: SharedPreferencesScope): JsonObject
    /** Adapter checks the supplied guard inside every asynchronous storage edit. */
    suspend fun apply(scope: SharedPreferencesScope, preferences: JsonObject, stillCurrent: () -> Boolean)
}

internal enum class SharedPreferencesSyncStatus { Off, Ready, ChooseInitialSettings, Syncing, Synced, SignInRequired, Error }

internal data class SharedPreferencesSyncState(
    val enabled: Boolean = false,
    val status: SharedPreferencesSyncStatus = SharedPreferencesSyncStatus.Off,
)

/**
 * Device-local opt-in with account/profile guards around every suspend boundary.
 * Disable never waits behind a network mutex and cannot be undone by a late response.
 */
internal class OmniaSharedPreferencesEngine(
    private val device: SharedPreferencesDevice,
    private val store: SharedPreferencesLocalStore,
    private val transport: SharedPreferencesTransport,
) {
    private val mutex = Mutex()
    private val stateMutex = Mutex()
    private val generation = MutableStateFlow(0L)
    private val _state = MutableStateFlow(SharedPreferencesSyncState())
    val state: StateFlow<SharedPreferencesSyncState> = _state.asStateFlow()

    fun refreshLocalState() {
        generation.update { it + 1 }
        val scope = device.currentScope()
        val enabled = scope?.let { store.load(it).enabled } == true
        _state.value = SharedPreferencesSyncState(enabled, if (enabled) SharedPreferencesSyncStatus.Ready else SharedPreferencesSyncStatus.Off)
    }

    suspend fun disable() {
        generation.update { it + 1 }
        val scope = device.currentScope()
        stateMutex.withLock {
            scope?.let { store.save(it, store.load(it).copy(enabled = false)) }
        }
        if (scope == device.currentScope()) _state.value = SharedPreferencesSyncState()
        else refreshLocalState()
    }

    private fun current(request: SharedPreferencesRequest, requireEnabled: Boolean): Boolean =
        request.scope == device.currentScope() && request.generation == generation.value &&
            (!requireEnabled || store.load(request.scope).enabled)

    private fun update(request: SharedPreferencesRequest, status: SharedPreferencesSyncStatus) {
        if (current(request, requireEnabled = false)) {
            _state.value = SharedPreferencesSyncState(store.load(request.scope).enabled, status)
        }
    }

    suspend fun enable(choice: SharedPreferencesInitialChoice? = null): SharedPreferencesSyncStatus = mutex.withLock {
        val scope = device.currentScope() ?: run {
            _state.value = SharedPreferencesSyncState(false, SharedPreferencesSyncStatus.SignInRequired)
            return@withLock SharedPreferencesSyncStatus.SignInRequired
        }
        val request = SharedPreferencesRequest(scope, generation.value)
        update(request, SharedPreferencesSyncStatus.Syncing)
        try {
            val local = device.export(scope)
            if (!current(request, false)) return@withLock SharedPreferencesSyncStatus.Off
            var remote = transport.pull(scope)
            if (!current(request, false)) return@withLock SharedPreferencesSyncStatus.Off
            if (remote.preferences.isNotEmpty() && choice == null) {
                update(request, SharedPreferencesSyncStatus.ChooseInitialSettings)
                return@withLock SharedPreferencesSyncStatus.ChooseInitialSettings
            }
            val resolvedChoice = choice ?: SharedPreferencesInitialChoice.UseThisDevice
            repeat(3) {
                if (!current(request, false)) return@withLock SharedPreferencesSyncStatus.Off
                val initial = initialSharedPreferences(resolvedChoice, local, remote.preferences, device.supportedKeys)
                val accepted = if (initial == remote.preferences) SharedPreferencesPushResult(false, remote)
                    else transport.push(scope, remote.revision, initial, remote.profileInstance)
                if (!current(request, false)) return@withLock SharedPreferencesSyncStatus.Off
                if (accepted.snapshot.profileInstance != remote.profileInstance) return@withLock requireNewProfileChoice(request)
                remote = accepted.snapshot
                if (!accepted.conflict) {
                    // Persist enabled only after the explicit initial action succeeds.
                    stateMutex.withLock {
                        if (current(request, false)) store.save(scope, store.load(scope).copy(enabled = true))
                    }
                    applyWithoutOverwritingNewLocalEdits(request, local, remote)
                    if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
                    acknowledge(request, local, remote)
                    if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
                    update(request, SharedPreferencesSyncStatus.Synced)
                    return@withLock SharedPreferencesSyncStatus.Synced
                }
            }
            update(request, SharedPreferencesSyncStatus.Error)
            SharedPreferencesSyncStatus.Error
        } catch (cancelled: CancellationException) {
            update(request, if (store.load(scope).enabled) SharedPreferencesSyncStatus.Ready else SharedPreferencesSyncStatus.Off)
            throw cancelled
        } catch (_: SharedPreferencesChoiceRequiredException) {
            update(request, SharedPreferencesSyncStatus.ChooseInitialSettings)
            SharedPreferencesSyncStatus.ChooseInitialSettings
        } catch (_: Exception) {
            if (!current(request, false)) return@withLock SharedPreferencesSyncStatus.Off
            update(request, SharedPreferencesSyncStatus.Error)
            SharedPreferencesSyncStatus.Error
        }
    }

    suspend fun synchronize(): SharedPreferencesSyncStatus = mutex.withLock {
        val scope = device.currentScope() ?: return@withLock SharedPreferencesSyncStatus.SignInRequired
        val request = SharedPreferencesRequest(scope, generation.value)
        val record = store.load(scope)
        if (!record.enabled) return@withLock SharedPreferencesSyncStatus.Off
        if (record.baseline == null) {
            update(request, SharedPreferencesSyncStatus.ChooseInitialSettings)
            return@withLock SharedPreferencesSyncStatus.ChooseInitialSettings
        }
        update(request, SharedPreferencesSyncStatus.Syncing)
        try {
            val local = device.export(scope)
            if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
            var remote = transport.pull(scope)
            if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
            if (record.baseline.profileInstance != remote.profileInstance) return@withLock requireNewProfileChoice(request)
            repeat(3) {
                val merged = mergeSharedPreferences(record.baseline.preferences, local, remote.preferences, device.supportedKeys)
                if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
                val accepted = if (merged == remote.preferences) SharedPreferencesPushResult(false, remote)
                    else transport.push(scope, remote.revision, merged, remote.profileInstance)
                if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
                if (accepted.snapshot.profileInstance != remote.profileInstance) return@withLock requireNewProfileChoice(request)
                remote = accepted.snapshot
                if (!accepted.conflict) {
                    applyWithoutOverwritingNewLocalEdits(request, local, remote)
                    if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
                    acknowledge(request, local, remote)
                    if (!current(request, true)) return@withLock SharedPreferencesSyncStatus.Off
                    update(request, SharedPreferencesSyncStatus.Synced)
                    return@withLock SharedPreferencesSyncStatus.Synced
                }
            }
            update(request, SharedPreferencesSyncStatus.Error)
            SharedPreferencesSyncStatus.Error
        } catch (cancelled: CancellationException) {
            update(request, if (store.load(scope).enabled) SharedPreferencesSyncStatus.Ready else SharedPreferencesSyncStatus.Off)
            throw cancelled
        } catch (_: SharedPreferencesChoiceRequiredException) {
            update(request, SharedPreferencesSyncStatus.ChooseInitialSettings)
            SharedPreferencesSyncStatus.ChooseInitialSettings
        } catch (_: Exception) {
            if (!current(request, false)) return@withLock SharedPreferencesSyncStatus.Off
            update(request, SharedPreferencesSyncStatus.Error)
            SharedPreferencesSyncStatus.Error
        }
    }

    private suspend fun requireNewProfileChoice(request: SharedPreferencesRequest): SharedPreferencesSyncStatus {
        stateMutex.withLock {
            if (current(request, false)) store.save(request.scope, SharedPreferencesLocalRecord())
        }
        update(request, SharedPreferencesSyncStatus.ChooseInitialSettings)
        return SharedPreferencesSyncStatus.ChooseInitialSettings
    }

    private suspend fun applyWithoutOverwritingNewLocalEdits(
        request: SharedPreferencesRequest,
        exported: JsonObject,
        acknowledged: SharedPreferencesSnapshot,
    ) {
        if (!current(request, true)) return
        val latest = device.export(request.scope)
        if (!current(request, true)) return
        // A preference changed while the network request was in flight remains local,
        // and differs from the acknowledged baseline on the next synchronization.
        val safeToApply = JsonObject(applicableSharedPreferences(acknowledged.preferences, device.supportedKeys)
            .filterKeys { key -> latest[key] == exported[key] })
        device.apply(request.scope, safeToApply) { current(request, true) }
    }

    private suspend fun acknowledge(
        request: SharedPreferencesRequest,
        exported: JsonObject,
        acknowledged: SharedPreferencesSnapshot,
    ) {
        // Record the expected applied values only after storage application succeeds.
        // Defaults omitted by another platform are not mistaken for new local edits.
        val baseline = acknowledged.copy(preferences = JsonObject(exported + acknowledged.preferences))
        stateMutex.withLock {
            if (current(request, true)) store.save(request.scope, SharedPreferencesLocalRecord(true, baseline))
        }
    }
}

package com.nuvio.app.features.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.app.core.auth.AuthRepository
import com.nuvio.app.core.auth.AuthState
import com.nuvio.app.core.sync.OmniaPreferencesSync
import com.nuvio.app.core.sync.SharedPreferencesInitialChoice
import com.nuvio.app.core.sync.SharedPreferencesSyncStatus
import kotlinx.coroutines.launch

@Composable
internal fun OmniaPreferencesSyncSettings(isTablet: Boolean) {
    val state by OmniaPreferencesSync.state.collectAsStateWithLifecycle()
    val auth by AuthRepository.state.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    val signedIn = (auth as? AuthState.Authenticated)?.isAnonymous == false
    LaunchedEffect(Unit) { OmniaPreferencesSync.startObserving() }
    SettingsGroup(isTablet = isTablet) {
        SettingsSwitchRow(
            title = "Sync settings across devices",
            description = "Share compatible Home and language preferences with this account and profile. Off keeps this device’s current settings separate. Add-ons, library and history sync separately.",
            checked = state.enabled,
            enabled = signedIn && (state.enabled || state.status != SharedPreferencesSyncStatus.Syncing),
            isTablet = isTablet,
            onCheckedChange = { enabled -> scope.launch {
                if (enabled) OmniaPreferencesSync.enable() else OmniaPreferencesSync.disable()
            } },
        )
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(when {
                !signedIn -> "Sign in to share settings."
                else -> when(state.status) {
                    SharedPreferencesSyncStatus.Off -> "Off · This device keeps its own settings."
                    SharedPreferencesSyncStatus.Ready -> "On · Ready to sync."
                    SharedPreferencesSyncStatus.ChooseInitialSettings -> "Choose which settings to use."
                    SharedPreferencesSyncStatus.Syncing -> "Syncing settings…"
                    SharedPreferencesSyncStatus.Synced -> "Settings synced."
                    SharedPreferencesSyncStatus.SignInRequired -> "Sign in to share settings."
                    SharedPreferencesSyncStatus.Error -> "Settings could not sync. Your local preferences are kept. Try again."
                }
            }, style = MaterialTheme.typography.bodyMedium)
            Text("Shares Home catalog order, visibility and names; Continue Watching visibility; hero visibility; unreleased-content filtering; and audio/subtitle language. Device playback tuning stays local. Updates when you open Omnia, change a shared preference, or select Sync now.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (state.enabled && state.status != SharedPreferencesSyncStatus.Syncing) {
                TextButton(onClick = { scope.launch { OmniaPreferencesSync.synchronize() } }) { Text("Sync settings now") }
            }
            if (!state.enabled && state.status == SharedPreferencesSyncStatus.Syncing) {
                TextButton(onClick = { scope.launch { OmniaPreferencesSync.disable() } }) { Text("Cancel enabling sync") }
            }
            if (!state.enabled && state.status == SharedPreferencesSyncStatus.Error) {
                TextButton(onClick = { scope.launch { OmniaPreferencesSync.enable() } }) { Text("Try enabling again") }
            }
        }
    }
    if (state.status == SharedPreferencesSyncStatus.ChooseInitialSettings) {
        AlertDialog(
            onDismissRequest = OmniaPreferencesSync::cancelInitialChoice,
            title = { Text("Which settings should we use?") },
            text = { Text("Saved settings already exist for this profile. Choose the starting settings for this device. Playback tuning, add-ons, library and history are unaffected.") },
            confirmButton = { Column {
                TextButton(onClick = { scope.launch { OmniaPreferencesSync.enable(SharedPreferencesInitialChoice.UseSavedSettings) } }) { Text("Use saved settings") }
                TextButton(onClick = { scope.launch { OmniaPreferencesSync.enable(SharedPreferencesInitialChoice.UseThisDevice) } }) { Text("Use this device’s settings") }
            } },
            dismissButton = { TextButton(onClick = OmniaPreferencesSync::cancelInitialChoice) { Text("Cancel") } },
        )
    }
}

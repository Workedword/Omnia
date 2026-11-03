package com.nuvio.tv.ui.screens.settings

import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Restore
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.tv.R
import com.nuvio.tv.data.local.OmniaPreferenceResetter
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class OmniaResetPreferencesViewModel @Inject constructor(private val resetter: OmniaPreferenceResetter) : ViewModel() {
    private val _state = MutableStateFlow("idle")
    val state = _state.asStateFlow()
    fun reset() {
        if (_state.value == "resetting") return
        _state.value = "resetting"
        viewModelScope.launch {
            try {
                resetter.reset()
                _state.value = "done"
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (_: Exception) { _state.value = "failed" }
        }
    }
}

@Composable
internal fun OmniaResetSettingsControl(initialFocusRequester: FocusRequester? = null, viewModel: OmniaResetPreferencesViewModel = hiltViewModel()) {
    var confirm by rememberSaveable { mutableStateOf(false) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    SettingsGroupCard {
        SettingsActionRow(
            title = stringResource(R.string.omnia_reset_title),
            subtitle = stringResource(when (state) {
                "resetting" -> R.string.omnia_reset_progress
                "done" -> R.string.omnia_reset_done
                "failed" -> R.string.omnia_reset_failed
                else -> R.string.omnia_reset_description
            }),
            leadingIcon = Icons.Default.Restore,
            modifier = if (initialFocusRequester != null) Modifier.focusRequester(initialFocusRequester) else Modifier,
            onClick = { if (state != "resetting") confirm = true },
        )
    }
    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text(stringResource(R.string.omnia_reset_title)) },
            text = { Text(stringResource(R.string.omnia_reset_confirmation)) },
            confirmButton = { TextButton(onClick = { confirm = false; viewModel.reset() }) { Text(stringResource(R.string.omnia_reset_confirm)) } },
            dismissButton = { TextButton(onClick = { confirm = false }) { Text(stringResource(R.string.omnia_reset_cancel)) } },
        )
    }
}

package com.nuvio.app.features.settings

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun OmniaResetSettingsControl(isTablet: Boolean) {
    var confirm by rememberSaveable { mutableStateOf(false) }
    var result by rememberSaveable { mutableStateOf<String?>(null) }
    val done = stringResource(Res.string.omnia_reset_done)
    val failed = stringResource(Res.string.omnia_reset_failed)
    SettingsNavigationRow(
        title = stringResource(Res.string.omnia_reset_title),
        description = result ?: stringResource(Res.string.omnia_reset_description),
        isTablet = isTablet,
        onClick = { confirm = true },
    )
    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text(stringResource(Res.string.omnia_reset_title)) },
            text = { Text(stringResource(Res.string.omnia_reset_confirmation)) },
            confirmButton = {
                TextButton(onClick = {
                    confirm = false
                    result = runCatching { OmniaPreferenceResetter.reset() }.fold({ done }, { failed })
                }) { Text(stringResource(Res.string.omnia_reset_confirm)) }
            },
            dismissButton = { TextButton(onClick = { confirm = false }) { Text(stringResource(Res.string.omnia_reset_cancel)) } },
        )
    }
}

@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)
package com.nuvio.tv.ui.screens.account

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.tv.material3.Button
import androidx.tv.material3.Text
import com.nuvio.tv.ui.theme.NuvioTheme

@Composable
internal fun OmniaTvBrowserSignIn(enabled: Boolean, viewModel: AccountViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val handler = LocalUriHandler.current
    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Or sign in with", color = NuvioTheme.colors.TextSecondary)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(enabled = enabled && !state.isLoading, onClick = { viewModel.startOmniaBrowserSignIn("google") }) { Text("Google") }
            Button(enabled = enabled && !state.isLoading, onClick = { viewModel.startOmniaBrowserSignIn("discord") }) { Text("Discord") }
        }
        state.qrLoginUserCode?.let { code ->
            Text("Your code: " + code.chunked(3).joinToString("-"), color = NuvioTheme.colors.TextPrimary)
            Text("Open ${OmniaAccountPortal.ORIGIN}/discord-account/link in a browser and enter this code. Confirm the device to finish signing in here.", color = NuvioTheme.colors.TextSecondary)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                state.qrLoginUrl?.let { url -> Button(enabled = !state.isLoading, onClick = { runCatching { handler.openUri(url) } }) { Text("Open browser") } }
                Button(enabled = !state.isLoading, onClick = { viewModel.clearQrLoginSession() }) { Text("Cancel") }
            }
        }
    }
}

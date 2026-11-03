package com.nuvio.app.features.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import com.nuvio.app.core.auth.DeviceLinkAuthRepository
import com.nuvio.app.core.auth.DeviceLinkAuthState
import com.nuvio.app.core.network.ServerConfigurationRepository

@Composable
internal fun OmniaAccountPortalLinks(enabled: Boolean) {
    val server by ServerConfigurationRepository.active.collectAsState()
    if (!OmniaAccountPortal.availableFor(server.backendUrl)) return
    val handler = LocalUriHandler.current
    var fallbackUrl by remember { mutableStateOf<String?>(null) }
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            TextButton(enabled = enabled, onClick = { fallbackUrl = if (runCatching { handler.openUri(OmniaAccountPortal.SIGNUP_URL) }.isFailure) OmniaAccountPortal.SIGNUP_URL else null }) { Text("Create account", color = AuthTextPrimary) }
            TextButton(enabled = enabled, onClick = { fallbackUrl = if (runCatching { handler.openUri(OmniaAccountPortal.RECOVERY_URL) }.isFailure) OmniaAccountPortal.RECOVERY_URL else null }) { Text("Forgot password?", color = AuthTextPrimary) }
        }
        if (fallbackUrl != null) Text("Open $fallbackUrl in a browser.", color = AuthTextSecondary)
    }
}

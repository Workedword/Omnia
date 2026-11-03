@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)
package com.nuvio.tv.ui.screens.account

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import androidx.tv.material3.Button
import androidx.tv.material3.Text
import com.nuvio.tv.ui.theme.NuvioTheme

@Composable
internal fun OmniaTvAccountPortalLink(enabled: Boolean) {
    val handler = LocalUriHandler.current
    var fallbackUrl by remember { mutableStateOf<String?>(null) }
    Column(modifier = Modifier.fillMaxWidth().padding(top = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(modifier = Modifier.weight(1f).heightIn(min = 48.dp), enabled = enabled, onClick = { fallbackUrl = if (runCatching { handler.openUri(OmniaAccountPortal.SIGNUP_URL) }.isFailure) OmniaAccountPortal.SIGNUP_URL else null }) { Text("Create account", modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center) }
            Button(modifier = Modifier.weight(1f).heightIn(min = 48.dp), enabled = enabled, onClick = { fallbackUrl = if (runCatching { handler.openUri(OmniaAccountPortal.RECOVERY_URL) }.isFailure) OmniaAccountPortal.RECOVERY_URL else null }) { Text("Forgot password?", modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center) }
        }
        if (fallbackUrl != null) Text("Open $fallbackUrl in a browser.", color = NuvioTheme.colors.TextSecondary)
    }
}

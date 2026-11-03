package com.nuvio.app.features.auth

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import com.nuvio.app.core.auth.DeviceLinkAuthRepository
import com.nuvio.app.core.auth.DeviceLinkAuthState

@Composable
internal fun OmniaBrowserSignIn(enabled: Boolean) {
    val state by DeviceLinkAuthRepository.state.collectAsState()
    val handler = LocalUriHandler.current
    var opened by remember { mutableStateOf<String?>(null) }
    var openFailed by remember { mutableStateOf(false) }
    val waiting = state as? DeviceLinkAuthState.Waiting
    val busy = state is DeviceLinkAuthState.Starting || waiting != null
    fun open(url: String) { openFailed = runCatching { handler.openUri(url) }.isFailure }
    LaunchedEffect(waiting?.verificationUrl) {
        val url = waiting?.verificationUrl
        if (url != null && opened != url && waiting?.isCompleting != true) { opened = url; open(url) }
    }
    DisposableEffect(Unit) { onDispose { DeviceLinkAuthRepository.cancel() } }
    Column(modifier = Modifier.fillMaxWidth()) {
        for ((provider, label) in listOf("google" to "Google", "discord" to "Discord")) {
            OutlinedButton(
                enabled = enabled && !busy,
                modifier = Modifier.fillMaxWidth(),
                onClick = { DeviceLinkAuthRepository.start(provider) },
            ) { Text("Continue with $label", color = AuthTextPrimary) }
        }
        when (state) {
            DeviceLinkAuthState.Starting -> Text("Preparing secure sign-in…", color = AuthTextSecondary)
            is DeviceLinkAuthState.Failed -> Text("Sign-in didn’t finish. Try again or use your Omnia email and password.", color = AuthTextSecondary)
            else -> Unit
        }
        if (waiting != null) {
            Text(if (waiting.isCompleting) "Finishing sign-in…" else "Confirm code ${waiting.code} in your browser, then return to Omnia.", color = AuthTextSecondary)
            if (!waiting.isCompleting) {
                OutlinedButton(onClick = { open(waiting.verificationUrl) }, modifier = Modifier.fillMaxWidth()) { Text(if (openFailed) "Try opening the browser again" else "Open sign-in page", color = AuthTextPrimary) }
                OutlinedButton(onClick = { DeviceLinkAuthRepository.cancel() }, modifier = Modifier.fillMaxWidth()) { Text("Cancel sign-in", color = AuthTextPrimary) }
            }
        }
    }
}

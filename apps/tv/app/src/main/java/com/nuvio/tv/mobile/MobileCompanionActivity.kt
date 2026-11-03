package com.nuvio.tv.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Extension
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.nuvio.tv.BuildConfig
import com.nuvio.tv.domain.model.AuthState
import com.nuvio.tv.domain.model.Addon
import com.nuvio.tv.ui.screens.account.ServerConnectionViewModel
import com.nuvio.tv.updater.UpdateViewModel
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MobileCompanionActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(primary = Color(0xFFFF454F), background = Color(0xFF101014), surface = Color(0xFF1B1B22))) {
                CompanionScreen()
            }
        }
    }
}

@Composable
private fun CompanionScreen(vm: MobileCompanionViewModel = hiltViewModel(), connection: ServerConnectionViewModel = hiltViewModel()) {
    val account by vm.account.collectAsState()
    val busy by vm.busy.collectAsState()
    val ready by vm.ready.collectAsState()
    val message by vm.message.collectAsState()
    val addons by vm.addons.collectAsState()
    val serverState by connection.uiState.collectAsState()
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var email by rememberSaveable { mutableStateOf("") }
    // Credentials intentionally do not enter saved instance state.
    var password by remember { mutableStateOf("") }
    var providerKey by remember { mutableStateOf("") }
    var manifest by rememberSaveable { mutableStateOf("") }
    var serverUrl by rememberSaveable { mutableStateOf("https://omnia.161.97.128.244.sslip.io") }
    var pendingRemoval by remember { mutableStateOf<Addon?>(null) }
    var confirmSignOut by remember { mutableStateOf(false) }
    LaunchedEffect(account) { if (account is AuthState.FullAccount) password = "" }

    Scaffold(
        bottomBar = {
            NavigationBar {
                listOf("Account", "Add-ons", "Providers").forEachIndexed { index, label ->
                    NavigationBarItem(selected = tab == index, onClick = { tab = index }, label = { Text(label) }, icon = {
                        Icon(when(index) { 0 -> Icons.Default.AccountCircle; 1 -> Icons.Default.Extension; else -> Icons.Default.Settings }, contentDescription = label)
                    })
                }
            }
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).imePadding().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("OMNIA", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
            Text("Your TV, set up from your phone", style = MaterialTheme.typography.titleMedium)
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            message?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            when (tab) {
                0 -> {
                    Text("One account. Both devices.", style = MaterialTheme.typography.headlineSmall)
                    if (!vm.canSignIn) {
                        Text("Connect to your private Omnia service before signing in. Use this same address on your Fire Stick.")
                        OutlinedTextField(serverUrl, { serverUrl = it }, label = { Text("Omnia service address") }, singleLine = true, modifier = Modifier.fillMaxWidth(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
                        Button(onClick = { connection.discover(serverUrl) }, enabled = !serverState.isDiscovering && !serverState.isSwitching, modifier = Modifier.fillMaxWidth()) { Text("Check connection") }
                        serverState.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                        serverState.discoveredServer?.let { found ->
                            Text("Connect to ${found.backendUrl}? Omnia will restart with this service.")
                            Button(onClick = connection::connectDiscoveredServer, enabled = found.isSecure && found.capabilities.emailPasswordAuth && !serverState.isSwitching, modifier = Modifier.fillMaxWidth()) { Text("Connect and restart") }
                        }
                    } else if (account is AuthState.FullAccount) {
                        Text((account as AuthState.FullAccount).email, style = MaterialTheme.typography.titleLarge)
                        Text("Managing your primary profile. Sign in with this same email on your Fire Stick to share add-ons and provider settings.")
                        Button(onClick = vm::refresh, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("Refresh account settings") }
                        Text("On Fire Stick: Settings → Account → connect to this Omnia service, then sign in. Return to the app to refresh shared settings.")
                        Text(vm.server.backendUrl, style = MaterialTheme.typography.bodySmall)
                        OutlinedButton(onClick = { confirmSignOut = true }, enabled = !busy) { Text("Sign out") }
                    } else {
                        Text("Sign in to your private account. Public account creation is disabled.")
                        OutlinedTextField(email, { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth(), singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email))
                        OutlinedTextField(password, { password = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password))
                        Button(onClick = { vm.signIn(email, password) }, enabled = !busy && email.isNotBlank() && password.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("Sign in") }
                    }
                    Text("Omnia ${BuildConfig.VERSION_NAME} • Phone companion", style = MaterialTheme.typography.bodySmall)
                    if (BuildConfig.FEATURE_IN_APP_UPDATES_ENABLED) MobileUpdates()
                }
                1 -> {
                    Text("Add-ons", style = MaterialTheme.typography.headlineSmall)
                    if (!ready) Text("Sign in and refresh your account before editing shared add-ons.")
                    OutlinedTextField(manifest, { manifest = it }, label = { Text("HTTPS manifest URL") }, singleLine = true, modifier = Modifier.fillMaxWidth(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
                    Button(onClick = { vm.install(manifest) }, enabled = ready && !busy && manifest.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("Install add-on") }
                    OutlinedButton(onClick = { vm.install("https://opensubtitles-v3.strem.io/manifest.json") }, enabled = ready && !busy, modifier = Modifier.fillMaxWidth()) { Text("Add OpenSubtitles") }
                    addons.forEach { addon ->
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text(addon.displayName, modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                                    Switch(checked = addon.enabled, onCheckedChange = { vm.toggle(addon, it) }, enabled = ready && !busy)
                                }
                                // Configured URLs may contain provider keys; never display them here.
                                Text(addon.description.orEmpty(), maxLines = 3, style = MaterialTheme.typography.bodySmall)
                                TextButton(onClick = { pendingRemoval = addon }, enabled = ready && !busy) { Text("Remove") }
                            }
                        }
                    }
                }
                2 -> {
                    Text("Real-Debrid", style = MaterialTheme.typography.headlineSmall)
                    Text("Save a Real-Debrid API token to your private account so your Fire Stick can use the same provider. Add-ons may also require their own provider configuration.")
                    OutlinedTextField(providerKey, { providerKey = it }, label = { Text("API token") }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password))
                    Button(onClick = { vm.saveRealDebrid(providerKey); providerKey = "" }, enabled = ready && !busy && providerKey.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("Validate and save") }
                    if (!ready) Text("Sign in and load your account settings first.")
                    Text("Tokens are sent over HTTPS to Real-Debrid for validation and to your private Omnia service for sync.", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
    pendingRemoval?.let { addon ->
        AlertDialog(onDismissRequest = { pendingRemoval = null }, title = { Text("Remove ${addon.displayName}?") }, text = { Text("This changes the add-ons shared with your TV.") }, confirmButton = { TextButton(onClick = { vm.remove(addon); pendingRemoval = null }) { Text("Remove") } }, dismissButton = { TextButton(onClick = { pendingRemoval = null }) { Text("Cancel") } })
    }
    if (confirmSignOut) AlertDialog(onDismissRequest = { confirmSignOut = false }, title = { Text("Sign out of this phone?") }, text = { Text("Local account data will be cleared. Your server account and TV login stay available.") }, confirmButton = { TextButton(onClick = { vm.signOut(); confirmSignOut = false }) { Text("Sign out") } }, dismissButton = { TextButton(onClick = { confirmSignOut = false }) { Text("Cancel") } })
}

@Composable
private fun MobileUpdates(updater: UpdateViewModel = hiltViewModel()) {
    val state by updater.uiState.collectAsState()
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("App updates", style = MaterialTheme.typography.titleLarge)
            Text("Download updates from Omnia's GitHub releases. Your account and settings stay on this device.")
            OutlinedButton(
                onClick = { updater.checkForUpdates(force = true, showNoUpdateFeedback = true) },
                enabled = !state.isChecking && !state.isDownloading,
                modifier = Modifier.fillMaxWidth()
            ) { Text(if (state.isChecking) "Checking…" else "Check for updates") }
            state.feedbackMessage?.let { Text(it) }
            state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            if (state.isDownloading) {
                LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(state.downloadProgress?.let { "Downloading ${(it * 100).toInt()}%" } ?: "Downloading…")
            } else if (state.isUpdateAvailable) {
                Button(
                    onClick = {
                        if (state.downloadedApkPath != null) updater.installUpdateOrRequestPermission()
                        else updater.downloadUpdate()
                    },
                    enabled = !state.isChecking,
                    modifier = Modifier.fillMaxWidth()
                ) { Text(if (state.downloadedApkPath != null) "Install update" else "Download and install update") }
            }
            Text("You can also install the latest APK directly. Android may ask you to approve installation.", style = MaterialTheme.typography.bodySmall)
        }
    }
    if (state.showUnknownSourcesDialog) {
        AlertDialog(
            onDismissRequest = updater::dismissUnknownSourcesDialog,
            title = { Text("Allow Omnia updates") },
            text = { Text("Enable ‘Allow from this source’ for Omnia in Android settings, then return and tap Install update.") },
            confirmButton = { TextButton(onClick = updater::openUnknownSourcesSettings) { Text("Open settings") } },
            dismissButton = { TextButton(onClick = updater::dismissUnknownSourcesDialog) { Text("Cancel") } }
        )
    }
}

@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)

package com.nuvio.tv.ui.screens.addon

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Image
import android.view.KeyEvent
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.runtime.*
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.tv.material3.Button
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text
import com.nuvio.tv.core.qr.QrCodeGenerator
import com.nuvio.tv.domain.model.Addon
import com.nuvio.tv.ui.components.NuvioDialog
import com.nuvio.tv.ui.theme.NuvioTheme

@Composable
fun AddonDiscoveryScreen(
    installed: List<Addon>,
    installing: Boolean,
    message: String?,
    onInstall: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: AddonDiscoveryViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    var source by remember { mutableStateOf("All") }
    var category by remember { mutableStateOf("All types") }
    var query by remember { mutableStateOf("") }
    var configuring by remember { mutableStateOf<DiscoverAddon?>(null) }
    val backFocus = remember { FocusRequester() }
    val directoryFiltersFocus = remember { FocusRequester() }
    val keyboardController = LocalSoftwareKeyboardController.current
    val directoryListState = rememberLazyListState()
    LaunchedEffect(Unit) { backFocus.requestFocus() }
    LaunchedEffect(query, source, category) { directoryListState.scrollToItem(0) }
    BackHandler(onBack = onBack)
    // Installed entries belong to Current Add-ons.
    val installedIdentities = remember(installed) { installed.map { DirectoryInstallIdentity(it.id, it.baseUrl) } }
    val visible = remember(state.addons, installedIdentities, source, category, query) {
        state.addons.filter { addon ->
            !OmniaDirectoryPolicy.isInstalled(
                DirectoryCandidate(addon.manifestUrl, addon.setupUrl, addon.matchingIds + addon.id, addon.configurationRequired && addon.setupUrl != null),
                installedIdentities
            ) && (source == "All" || addon.source == source) &&
                (category == "All types" || when (category) {
                    "Subtitles" -> addon.resources.any { it == "subtitles" || it == "subtitle" }
                    "Catalogs" -> "catalog" in addon.resources
                    "Collections" -> "collection" in addon.resources
                    "Live TV & Sports" -> "live" in addon.resources
                    else -> "stream" in addon.resources
                }) && (query.isBlank() || addon.name.contains(query, true) || addon.description.contains(query, true))
        }.sortedWith(compareBy<DiscoverAddon> { it.source != "Omnia Official" }.thenBy { it.name.lowercase() })
    }
    Column(Modifier.fillMaxSize().background(NuvioTheme.colors.Background).padding(28.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Button(onClick = onBack, modifier = Modifier.focusRequester(backFocus)) { Text("Back") }
            Text("Discover add-ons", style = MaterialTheme.typography.headlineMedium, color = NuvioTheme.colors.TextPrimary, modifier = Modifier.weight(1f))
            OutlinedTextField(value = query, onValueChange = { query = it }, singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = {
                    keyboardController?.hide()
                    directoryFiltersFocus.requestFocus()
                }),
                label = { androidx.compose.material3.Text("Search add-ons") }, modifier = Modifier.width(280.dp).onPreviewKeyEvent { event ->
                    if (event.nativeKeyEvent.keyCode == KeyEvent.KEYCODE_DPAD_DOWN) {
                        if (event.nativeKeyEvent.action == KeyEvent.ACTION_DOWN) {
                            keyboardController?.hide()
                            directoryFiltersFocus.requestFocus()
                        }
                        true
                    } else false
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = NuvioTheme.colors.TextPrimary,
                    unfocusedTextColor = NuvioTheme.colors.TextPrimary,
                    focusedBorderColor = NuvioTheme.colors.Primary,
                    unfocusedBorderColor = NuvioTheme.colors.Border,
                    focusedLabelColor = NuvioTheme.colors.Primary,
                    unfocusedLabelColor = NuvioTheme.colors.TextSecondary,
                    cursorColor = NuvioTheme.colors.Primary
                ))
        }
        Text("Subtitles, catalogs and streams from compatible add-ons.", color = NuvioTheme.colors.TextSecondary)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            listOf("All", "Omnia Official", "Community").forEach { option ->
                Button(onClick = { source = option },
                    modifier = if (option == "All") Modifier.focusRequester(directoryFiltersFocus) else Modifier) { Text(if (source == option) "✓ $option" else option) }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            listOf("All types", "Subtitles", "Catalogs", "Collections", "Streams", "Live TV & Sports").forEach { option ->
                Button(onClick = { category = option }) { Text(if (category == option) "✓ $option" else option) }
            }
        }

        Text("${visible.size} available · Installed add-ons stay in Current Add-ons", color = NuvioTheme.colors.TextSecondary)
        Text("Omnia Official: maintained by Omnia. Community: independent developers.", color = NuvioTheme.colors.TextSecondary, style = MaterialTheme.typography.labelMedium)
        if (state.loading) Text("Loading add-on catalogs…", color = NuvioTheme.colors.TextSecondary)
        if (state.failedSources.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Could not load: ${state.failedSources.joinToString()}", color = NuvioTheme.colors.TextSecondary)
                Button(onClick = viewModel::refresh, enabled = !state.loading) { Text("Retry") }
            }
        }
        message?.let { Text(it, color = NuvioTheme.colors.TextSecondary) }
        if (!state.loading && visible.isEmpty()) Text("No matching add-ons. Try another filter or add a manifest URL from the installed add-ons screen.", color = NuvioTheme.colors.TextSecondary)
        LazyColumn(Modifier.weight(1f), state = directoryListState, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items(visible, key = { it.manifestUrl }) { addon ->
                Column(Modifier.fillMaxWidth().background(NuvioTheme.colors.BackgroundCard, RoundedCornerShape(14.dp)).padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(addon.name, style = MaterialTheme.typography.titleLarge, color = NuvioTheme.colors.TextPrimary)
                    Text("${addon.source} · ${addon.resources.joinToString(" · ")}", color = if (addon.source == "Omnia Official") NuvioTheme.colors.Primary else NuvioTheme.colors.TextSecondary)
                    Text(addon.description, maxLines = 2, overflow = TextOverflow.Ellipsis, color = NuvioTheme.colors.TextSecondary)
                    Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                        if (addon.configurable || addon.configurationRequired) Button(onClick = { configuring = addon }) { Text("Set up") }
                        if (!addon.configurationRequired) Button(onClick = { if (!installing) { onInstall(addon.manifestUrl); directoryFiltersFocus.requestFocus() } }, enabled = !installing) {
                            Text(if (installing) "Adding…" else "Add to Omnia")
                        }
                    }
                }
            }
        }
    }
    configuring?.let { addon ->
        val qr = remember(addon.configureUrl) { QrCodeGenerator.generate(addon.configureUrl, 384) }
        NuvioDialog(onDismiss = { configuring = null }, title = "Configure ${addon.name}", subtitle = "Configure this provider in Omnia on your phone.") {
            Text(addon.configureUrl, color = NuvioTheme.colors.TextSecondary)
            Text("In the phone app, open Settings → Catalogs & add-ons and add the configured manifest URL. Use the same Omnia account and profile, then Refresh Add-ons on the TV. You can also open the address above in your phone browser.", color = NuvioTheme.colors.TextSecondary)
            Button(onClick = { configuring = null }) { Text("Done") }
        }
    }
}

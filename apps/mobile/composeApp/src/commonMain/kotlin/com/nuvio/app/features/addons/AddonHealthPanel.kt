package com.nuvio.app.features.addons

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

internal fun addonHealthLabel(addon: ManagedAddon): String = when {
    !addon.enabled -> "Disabled"
    addon.isRefreshing -> "Checking manifest…"
    addon.errorMessage != null && addon.manifest != null -> "Refresh failed · cached manifest available"
    addon.errorMessage != null -> "Unavailable · retry"
    addon.manifest == null -> "Not checked"
    else -> "Manifest ready"
}

@Composable
internal fun AddonHealthPanel(addons: List<ManagedAddon>) {
    key(addons) {
    val scope = rememberCoroutineScope()
    var checking by remember(addons.map { it.manifestUrl }) { mutableStateOf(false) }
    var catalogResults by remember(addons.map { it.manifestUrl }) { mutableStateOf<List<String>>(emptyList()) }
    CompositionLocalProvider(LocalContentColor provides MaterialTheme.colorScheme.onSurface) {
    Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Provider health", style = MaterialTheme.typography.titleMedium)
        Text("Catalogs organize titles. Playback providers supply sources. Subtitles supply text tracks.",
            style = MaterialTheme.typography.bodySmall)
        addons.forEach { addon ->
            val roles = buildList {
                if (addon.manifest?.catalogs?.isNotEmpty() == true) add("Catalogs")
                if (addon.manifest?.resources?.any { it.name == "stream" } == true) add("Playback")
                if (addon.manifest?.resources?.any { it.name == "subtitles" } == true) add("Subtitles")
            }.joinToString(" · ").ifBlank { "Add-on" }
            Text("${addon.displayTitle} — ${addonHealthLabel(addon)}\n$roles",
                style = MaterialTheme.typography.bodyMedium)
        }
        OutlinedButton(onClick = { AddonRepository.refreshAll() }, enabled = addons.none { it.isRefreshing } && addons.isNotEmpty()) {
            Text("Refresh enabled providers")
        }
        OutlinedButton(enabled = !checking, onClick = {
            scope.launch {
                checking = true
                catalogResults = emptyList()
                try {
                    addons.filter { it.enabled }.forEach { addon ->
                        addon.manifest?.catalogs.orEmpty().forEach { catalog ->
                            val result = if (catalog.extra.any { it.isRequired }) "Choose filters in Discover to check this catalog" else {
                                try {
                                    withTimeoutOrNull(10000) {
                                        val payload = fetchAddonResponseText(buildAddonResourceUrl(addon.manifestUrl, "catalog", catalog.type, catalog.id), forceRefresh = true)
                                        val metas = Json.parseToJsonElement(payload).jsonObject["metas"] as? JsonArray
                                        if (metas == null) "Invalid catalog response" else "Responding · ${metas.size} titles"
                                    } ?: "Timed out"
                                } catch (error: CancellationException) { throw error }
                                catch (_: Exception) { "Request failed · retry later" }
                            }
                            catalogResults = catalogResults + "${addon.displayTitle} / ${catalog.name}: $result"
                        }
                    }
                } finally { checking = false }
            }
        }) { Text(if (checking) "Checking catalogs…" else "Check catalog endpoints") }
        catalogResults.forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
        Text("Manifest readiness does not verify playback credentials or every catalog endpoint.",
            style = MaterialTheme.typography.bodySmall)
    }
    }
}
}

@Composable
internal fun OmniaAddonDiagnostics() {
    val state by AddonRepository.uiState.collectAsState()
    LaunchedEffect(Unit) { AddonRepository.initialize() }
    AddonHealthPanel(state.addons)
}

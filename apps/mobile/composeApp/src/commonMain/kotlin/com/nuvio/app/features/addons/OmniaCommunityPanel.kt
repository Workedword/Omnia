package com.nuvio.app.features.addons

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioSurfaceCard
import com.nuvio.app.core.ui.NuvioPrimaryButton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.serialization.json.*

private fun JsonObject.directoryText(key: String) = this[key]?.jsonPrimitive?.contentOrNull.orEmpty()
private fun JsonObject.directoryCandidate() = DirectoryCandidate(
    manifestUrl = directoryText("manifestUrl"),
    setupUrl = directoryText("url"),
    addonIds = (this["addonIds"] as? JsonArray)?.mapNotNull { it.jsonPrimitive.contentOrNull }?.toSet().orEmpty(),
    setupOnly = this["installable"]?.jsonPrimitive?.booleanOrNull != true,
)

@Composable
@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
internal fun OmniaCommunityPanel() {
    val scope = rememberCoroutineScope()
    val uri = LocalUriHandler.current
    val installedState by AddonRepository.uiState.collectAsState()
    val installed = remember(installedState.addons) {
        installedState.addons.map { DirectoryInstallIdentity(it.manifest?.id, it.manifestUrl) }
    }
    var entries by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var status by remember { mutableStateOf("Loading add-ons…") }
    var busy by remember { mutableStateOf(false) }
    var expanded by remember { mutableStateOf(true) }
    var category by remember { mutableStateOf("All") }
    var publisher by remember { mutableStateOf("All sources") }
    var query by remember { mutableStateOf("") }
    var attempt by remember { mutableStateOf(0) }
    LaunchedEffect(attempt) {
        try {
            val payload = fetchAddonResponseText("https://omnia.161.97.128.244.sslip.io/catalogs/community.json")
            entries = Json.parseToJsonElement(payload).jsonObject["entries"]!!.jsonArray.map { it.jsonObject }
            status = "Installed add-ons live in Current Add-ons. Discover something new here."
        } catch (cancelled: CancellationException) { throw cancelled }
        catch (_: Exception) { status = "The directory is unavailable. Try Refresh." }
    }
    val available = remember(entries, installed) {
        entries.filterNot { OmniaDirectoryPolicy.isInstalled(it.directoryCandidate(), installed) }
    }
    val visible = remember(available, category, publisher, query) {
        available.filter { entry ->
            val source = OmniaDirectoryPolicy.publisher(entry.directoryText("publisher"), entry.directoryText("url"))
            (publisher == "All sources" || publisher == source) &&
                (category == "All" || entry.directoryText("category") == category) &&
                (query.isBlank() || entry.directoryText("name").contains(query, true) || entry.directoryText("description").contains(query, true))
        }.sortedWith(compareBy<JsonObject> { OmniaDirectoryPolicy.publisher(it.directoryText("publisher"), it.directoryText("url")) != "Omnia Official" }.thenBy { it.directoryText("name").lowercase() })
    }
    NuvioSurfaceCard {
        Text("DISCOVER ADD-ONS", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text("More for your cinema", style = MaterialTheme.typography.headlineSmall)
        Text("${available.size} available · ${installed.size} installed", style = MaterialTheme.typography.bodyMedium)
        Text(status, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = { expanded = !expanded }) { Text(if (expanded) "Hide directory" else "Browse add-ons") }
            TextButton(onClick = { attempt++ }) { Text("Refresh") }
        }
        if (expanded) {
            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("All sources", "Omnia Official", "Community").forEach { source ->
                    FilterChip(selected = publisher == source, onClick = { publisher = source }, label = { Text(source) })
                }
            }
            Text("Official add-ons are maintained by Omnia. Community add-ons come from independent developers.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedTextField(value = query, onValueChange = { query = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("Search available add-ons") })
            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("All", "Catalogs", "Collections", "Providers", "Live TV & Sports").forEach { type ->
                    FilterChip(selected = category == type, onClick = { category = type }, label = { Text(type) })
                }
            }
            if (visible.isEmpty()) {
                Text("Nothing new in this view", style = MaterialTheme.typography.titleMedium)
                Text("Try another filter. Add-ons you already have stay in Current Add-ons.", style = MaterialTheme.typography.bodySmall)
                if (category != "All" || publisher != "All sources" || query.isNotBlank()) {
                    TextButton(onClick = { category = "All"; publisher = "All sources"; query = "" }) { Text("Clear filters") }
                }
            }
            visible.forEach { entry ->
                val source = OmniaDirectoryPolicy.publisher(entry.directoryText("publisher"), entry.directoryText("url"))
                val manifest = entry.directoryText("manifestUrl")
                val installable = entry["installable"]?.jsonPrimitive?.booleanOrNull == true && manifest.startsWith("https://")
                NuvioSurfaceCard(modifier = Modifier.semantics { contentDescription = "Available add-on: ${entry.directoryText("name")}" }) {
                    Surface(color = if (source == "Omnia Official") MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant, shape = RoundedCornerShape(8.dp)) {
                        Text(source, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), style = MaterialTheme.typography.labelMedium)
                    }
                    Text(entry.directoryText("name"), style = MaterialTheme.typography.titleLarge)
                    Text(entry.directoryText("category") + " · " + if (installable) "Ready to add" else "Setup needed", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                    Text(entry.directoryText("description"), style = MaterialTheme.typography.bodyMedium)
                    val setup = entry.directoryText("url")
                    if (installable) {
                        NuvioPrimaryButton(text = "Add to Omnia", modifier = Modifier.semantics { contentDescription = "Add ${entry.directoryText("name")} to Omnia" }, enabled = !busy, onClick = {
                            busy = true
                            scope.launch {
                                try {
                                    status = when (val result = AddonRepository.addAddon(manifest)) {
                                        is AddAddonResult.Success -> "Added ${result.manifest.name} to Current Add-ons"
                                        is AddAddonResult.Error -> result.message
                                    }
                                } finally { busy = false }
                            }
                        })
                    }
                    TextButton(onClick = { if (setup.startsWith("https://")) runCatching { uri.openUri(setup) } }) { Text(if (installable) "Settings & details" else "Set up") }
                }
                Spacer(Modifier.height(12.dp))
            }
        }
        TextButton(onClick = { runCatching { uri.openUri("https://github.com/Workedword/Omnia/tree/main/addons") } }) { Text("Create an add-on for Omnia") }
    }
}

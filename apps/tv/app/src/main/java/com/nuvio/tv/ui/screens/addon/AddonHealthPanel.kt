package com.nuvio.tv.ui.screens.addon

import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.tv.material3.*
import com.nuvio.tv.core.network.NetworkResult
import com.nuvio.tv.domain.model.Addon
import com.nuvio.tv.domain.repository.AddonRepository
import com.nuvio.tv.domain.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

@HiltViewModel
class AddonHealthViewModel @Inject constructor(private val addons: AddonRepository, private val catalogs: CatalogRepository): ViewModel() {
    val installedAddons = addons.getInstalledAddons()
    suspend fun check(addon: Addon): List<String> {
        if (!addon.enabled) return listOf("${addon.displayName}: Disabled")
        val result = try { withTimeoutOrNull(10000) { addons.fetchAddon(addon.baseUrl) } }
            catch (error: CancellationException) { throw error }
            catch (_: Exception) { null }
        if (result !is NetworkResult.Success) return listOf("${addon.displayName}: Manifest unavailable · retry")
        val fresh = result.data
        return buildList {
            add("${fresh.displayName}: Manifest ready")
            fresh.catalogs.forEach { catalog ->
                val status = if (catalog.extra.any { it.isRequired } || catalog.extraRequired.isNotEmpty()) "Requires filters in Discover" else try {
                    val response = withTimeoutOrNull(10000) {
                        catalogs.getCatalog(fresh.baseUrl, fresh.id, fresh.displayName, catalog.id, catalog.name, catalog.apiType)
                            .first { it !is NetworkResult.Loading }
                    }
                    when (response) {
                        is NetworkResult.Success -> "Loaded · ${response.data.items.size} titles (may be cached)"
                        else -> "Unavailable · retry"
                    }
                } catch (error: CancellationException) { throw error }
                  catch (_: Exception) { "Request failed" }
                add("${catalog.name}: $status")
            }
        }
    }
}

@OptIn(ExperimentalTvMaterial3Api::class)
@Composable
fun AddonHealthPanel(addons: List<Addon>, viewModel: AddonHealthViewModel = hiltViewModel()) {
    key(addons) {
    val scope = rememberCoroutineScope()
    var checking by remember(addons) { mutableStateOf(false) }
    var results by remember(addons) { mutableStateOf<List<String>>(emptyList()) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Provider health", style = MaterialTheme.typography.titleMedium)
        Text("Catalogs organize titles · Playback providers supply sources · Subtitles supply text tracks")
        Button(enabled = !checking && addons.isNotEmpty(), onClick = {
            scope.launch {
                checking = true; results = emptyList()
                try { addons.forEach { results = results + viewModel.check(it) } }
                finally { checking = false }
            }
        }) { Text(if(checking) "Checking providers…" else "Check providers and catalogs") }
        results.forEach { Text(it, style = MaterialTheme.typography.bodyMedium) }
        Text("These checks do not verify playback credentials.", style = MaterialTheme.typography.bodySmall)
    }
}
}

@Composable
fun OmniaAddonDiagnostics(viewModel: AddonHealthViewModel = hiltViewModel()) {
    val addons by viewModel.installedAddons.collectAsState(initial = emptyList())
    AddonHealthPanel(addons, viewModel)
}

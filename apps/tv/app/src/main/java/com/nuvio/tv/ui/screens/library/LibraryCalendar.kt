package com.nuvio.tv.ui.screens.library

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.tv.material3.*
import com.nuvio.tv.core.network.NetworkResult
import com.nuvio.tv.core.util.parseEpisodeReleaseLocalDate
import com.nuvio.tv.domain.model.LibraryEntry
import com.nuvio.tv.domain.repository.MetaRepository
import com.nuvio.tv.ui.components.NuvioDialog
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import java.time.YearMonth
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit

data class OmniaCalendarEpisode(val key: String, val date: String, val title: String, val episode: String, val item: LibraryEntry)

@HiltViewModel
class LibraryCalendarViewModel @Inject constructor(private val metaRepository: MetaRepository): ViewModel() {
    suspend fun load(shows: List<LibraryEntry>): List<List<OmniaCalendarEpisode>?> = coroutineScope {
        val limit = Semaphore(3)
        shows.map { item -> async {
            limit.withPermit {
                try {
                    val result = withTimeoutOrNull(15000) {
                        metaRepository.getMetaFromAllAddons(item.type, item.id).first { it !is NetworkResult.Loading }
                    }
                    (result as? NetworkResult.Success)?.data?.videos?.mapNotNull { video ->
                        val date = parseEpisodeReleaseLocalDate(video.released)?.toString() ?: return@mapNotNull null
                        OmniaCalendarEpisode("${item.type}:${item.id}:${video.id}", date, item.name,
                            "S${video.season ?: "?"} E${video.episode ?: "?"} · ${video.title}", item)
                    }
                } catch (error: CancellationException) { throw error }
                catch (_: Exception) { null }
            }
        } }.awaitAll()
    }
}

@OptIn(ExperimentalTvMaterial3Api::class)
@Composable
fun LibraryCalendarButton(library: List<LibraryEntry>, onOpen: (String, String, String?) -> Unit, viewModel: LibraryCalendarViewModel = hiltViewModel()) {
    var opened by remember { mutableStateOf(false) }
    Button(onClick = { opened = true }) { Text("Episode calendar") }
    if (!opened) return
    var month by remember { mutableStateOf(YearMonth.now()) }
    var refresh by remember { mutableStateOf(0) }
    var loading by remember { mutableStateOf(true) }
    var failures by remember { mutableStateOf(0) }
    var episodes by remember { mutableStateOf<List<OmniaCalendarEpisode>>(emptyList()) }
    val shows = remember(library) { library.filter { it.type.lowercase() in setOf("series","show","tv","anime") }.distinctBy { "${it.type}:${it.id}" } }
    LaunchedEffect(shows, refresh) {
        loading = true; episodes = emptyList(); failures = 0
        val results = viewModel.load(shows)
        failures = results.count { it == null }
        episodes = results.filterNotNull().flatten().distinctBy { it.key }.sortedWith(compareBy<OmniaCalendarEpisode> { it.date }.thenBy { it.title }.thenBy { it.key })
        loading = false
    }
    val visible = episodes.filter { it.date.startsWith(month.toString()) }
    NuvioDialog(onDismiss = { opened = false }, title = "Episode calendar", width = 700.dp) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { month = month.minusMonths(1) }) { Text("Previous") }
            Text(month.toString())
            Button(onClick = { month = month.plusMonths(1) }) { Text("Next") }
            Button(enabled = !loading, onClick = { refresh++ }) { Text("Refresh") }
        }
        Text("Dates from saved shows; schedules may change.")
        if (loading) Text("Loading saved shows…")
        if (failures > 0) Text("Could not load $failures show(s). Results may be incomplete.")
        if (!loading && visible.isEmpty()) Text(if (shows.isEmpty()) "Save a series to see its episode dates." else "No dated episodes found for this month.")
        LazyColumn(Modifier.heightIn(max=280.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(visible, key = { it.key }) { episode ->
                Button(onClick = { opened = false; onOpen(episode.item.id,episode.item.type,episode.item.addonBaseUrl) }) {
                    Column { Text("${episode.date} · ${episode.title}"); Text(episode.episode) }
                }
            }
        }
        Button(onClick = { opened = false }) { Text("Close") }
    }
}

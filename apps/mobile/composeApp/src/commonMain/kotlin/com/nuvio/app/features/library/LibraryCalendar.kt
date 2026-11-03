package com.nuvio.app.features.library

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.time.parseEpisodeReleaseLocalDate
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.watchprogress.CurrentDateProvider
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withTimeoutOrNull

internal data class CalendarEpisode(val key: String, val date: String, val title: String, val episode: String, val item: LibraryItem)

internal fun calendarMonthOffset(month: String, offset: Int): String {
    val parts = month.split('-')
    val total = parts[0].toInt() * 12 + parts[1].toInt() - 1 + offset
    return "${total / 12}-${(total % 12 + 1).toString().padStart(2, '0')}"
}

@Composable
internal fun LibraryCalendarButton(items: List<LibraryItem>, onOpen: ((LibraryItem) -> Unit)?) {
    var opened by rememberSaveable { mutableStateOf(false) }
    OutlinedButton(onClick = { opened = true }) { Text("Episode calendar") }
    if (opened) LibraryCalendarDialog(items, onDismiss = { opened = false }, onOpen = onOpen)
}

@Composable
private fun LibraryCalendarDialog(library: List<LibraryItem>, onDismiss: () -> Unit, onOpen: ((LibraryItem) -> Unit)?) {
    var month by rememberSaveable { mutableStateOf(CurrentDateProvider.todayIsoDate().take(7)) }
    var episodes by remember { mutableStateOf<List<CalendarEpisode>>(emptyList()) }
    var failed by remember { mutableStateOf(0) }
    var loading by remember { mutableStateOf(true) }
    var refresh by remember { mutableStateOf(0) }
    val shows = remember(library) { library.filter { it.type.lowercase() in setOf("series", "show", "tv", "anime") }.distinctBy { "${it.type}:${it.id}" } }
    LaunchedEffect(shows, refresh) {
        loading = true
        failed = 0
        episodes = emptyList()
        val limit = Semaphore(3)
        val results = coroutineScope {
            shows.map { item -> async {
                limit.withPermit {
                    val meta = try {
                        withTimeoutOrNull(15000) { MetaDetailsRepository.fetch(item.type, item.id) }
                    } catch (error: CancellationException) { throw error }
                    catch (_: Exception) { null }
                    if (meta == null) null else meta.videos.mapNotNull { video ->
                        val date = parseEpisodeReleaseLocalDate(video.released) ?: return@mapNotNull null
                        CalendarEpisode("${item.type}:${item.id}:${video.id}", date, item.name,
                            "S${video.season ?: "?"} E${video.episode ?: "?"} · ${video.title}", item)
                    }
                }
            } }.awaitAll()
        }
        failed = results.count { it == null }
        episodes = results.filterNotNull().flatten().distinctBy { it.key }.sortedWith(compareBy<CalendarEpisode> { it.date }.thenBy { it.title }.thenBy { it.key })
        loading = false
    }
    val visible = remember(episodes, month) { episodes.filter { it.date.startsWith(month) } }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Episode calendar") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TextButton(onClick = { month = calendarMonthOffset(month, -1) }) { Text("Previous") }
                    Text(month)
                    TextButton(onClick = { month = calendarMonthOffset(month, 1) }) { Text("Next") }
                }
                Text("Release dates from shows saved in your library. Dates may change.")
                if (loading) { LinearProgressIndicator(Modifier.fillMaxWidth()); Text("Loading saved shows…") }
                if (failed > 0) Text("Could not load $failed show(s). Results may be incomplete.")
                if (!loading && visible.isEmpty()) Text(if (shows.isEmpty()) "Save a series to your library to see its episode dates." else "No dated episodes found for this month.")
                LazyColumn(Modifier.heightIn(max = 340.dp)) {
                    items(visible, key = { it.key }) { episode ->
                        TextButton(enabled = onOpen != null, onClick = { onDismiss(); onOpen?.invoke(episode.item) }) {
                            Column(Modifier.fillMaxWidth()) {
                                Text("${episode.date} · ${episode.title}")
                                Text(episode.episode, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } },
        dismissButton = { TextButton(enabled = !loading, onClick = { refresh++ }) { Text("Refresh") } },
    )
}

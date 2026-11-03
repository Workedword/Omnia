package com.nuvio.app.features.library

import com.nuvio.app.features.watched.WatchedItem
import com.nuvio.app.features.watched.normalizeWatchedMarkedAtEpochMs
import com.nuvio.app.features.watchprogress.WatchProgressEntry

internal fun withLibraryActivity(
    sections: List<LibrarySection>,
    watched: List<WatchedItem>,
    progress: List<WatchProgressEntry>,
): List<LibrarySection> {
    fun key(type: String, id: String) = "${type.trim().lowercase()}:$id"
    val latest = mutableMapOf<String, Long>()
    val episodes = mutableMapOf<String, MutableSet<String>>()
    watched.forEach { item ->
        val k = key(item.type, item.id)
        latest[k] = maxOf(latest[k] ?: 0, normalizeWatchedMarkedAtEpochMs(item.markedAtEpochMs))
        if (item.season != null && item.episode != null) {
            episodes.getOrPut(k) { mutableSetOf() }.add("${item.season}:${item.episode}")
        }
    }
    progress.filter { it.lastPositionMs > 0 || it.isEffectivelyCompleted }.forEach { item ->
        val k = key(item.parentMetaType, item.parentMetaId)
        latest[k] = maxOf(latest[k] ?: 0, item.lastUpdatedEpochMs)
        if (item.isEffectivelyCompleted && item.seasonNumber != null && item.episodeNumber != null) {
            episodes.getOrPut(k) { mutableSetOf() }.add("${item.seasonNumber}:${item.episodeNumber}")
        }
    }
    return sections.map { section -> section.copy(items = section.items.map { item ->
        val k = key(item.type, item.id)
        item.copy(lastWatchedEpochMs = latest[k] ?: 0, watchedEpisodeCount = episodes[k]?.size ?: 0)
    }) }
}

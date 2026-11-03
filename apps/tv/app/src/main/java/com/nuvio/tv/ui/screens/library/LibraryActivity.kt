package com.nuvio.tv.ui.screens.library

import com.nuvio.tv.domain.model.WatchProgress
import com.nuvio.tv.domain.model.WatchedItem

internal fun libraryActivity(progress: List<WatchProgress>, watched: List<WatchedItem>): Pair<Map<String,Long>,Map<String,Int>> {
    val last = mutableMapOf<String, Long>()
    val episodes = mutableMapOf<String, MutableSet<Pair<Int,Int>>>()
    progress.filter { it.position > 0 || it.isCompleted() }.forEach { item ->
        val key = "${item.contentType}:${item.contentId}"
        last[key] = maxOf(last[key] ?: 0, item.lastWatched)
        if (item.isCompleted() && item.season != null && item.episode != null)
            episodes.getOrPut(key) { mutableSetOf() }.add(item.season to item.episode)
    }
    watched.forEach { item ->
        val key = "${item.contentType}:${item.contentId}"
        last[key] = maxOf(last[key] ?: 0, item.watchedAt)
        if (item.season != null && item.episode != null)
            episodes.getOrPut(key) { mutableSetOf() }.add(item.season to item.episode)
    }
    return last to episodes.mapValues { it.value.size }
}

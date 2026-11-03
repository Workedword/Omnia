package com.nuvio.app.features.library

import com.nuvio.app.features.watched.WatchedItem
import kotlin.test.Test
import kotlin.test.assertEquals

class OmniaLibraryFeaturesTest {
    @Test fun calendarCrossesYearBoundaries() {
        assertEquals("2027-01", calendarMonthOffset("2026-12", 1))
        assertEquals("2025-12", calendarMonthOffset("2026-01", -1))
    }
    @Test fun episodeCountsDeduplicateAndRecencyDoesNotUseLibrarySaveTime() {
        val a = LibraryItem("tt1", "series", "A", savedAtEpochMs = 999)
        val b = LibraryItem("tt2", "series", "B", savedAtEpochMs = 1)
        val watched = listOf(
            WatchedItem("tt1", "series", "A", season=1, episode=1, markedAtEpochMs=10),
            WatchedItem("tt1", "series", "A", season=1, episode=1, markedAtEpochMs=20),
            WatchedItem("tt2", "series", "B", season=1, episode=2, markedAtEpochMs=30),
        )
        val items = withLibraryActivity(listOf(LibrarySection("series", "Series", listOf(a,b))), watched, emptyList()).single().items
        assertEquals(1, items.first().watchedEpisodeCount)
        assertEquals(listOf("tt2","tt1"), sortLibraryItems(items, LibrarySortOption.RECENTLY_WATCHED, LibrarySourceMode.LOCAL).map { it.id })
    }
    @Test fun transientActivityDoesNotPolluteSyncedLibraryPayload() {
        val item = LibraryItem("tt1", "series", "A", savedAtEpochMs=1, lastWatchedEpochMs=42, watchedEpisodeCount=3)
        val text = kotlinx.serialization.json.Json.encodeToString(LibraryItem.serializer(), item)
        assertEquals(false, text.contains("lastWatchedEpochMs"))
        assertEquals(false, text.contains("watchedEpisodeCount"))
    }
}

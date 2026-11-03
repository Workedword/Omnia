package com.nuvio.tv.ui.screens.library
import com.nuvio.tv.domain.model.WatchedItem
import org.junit.Test
import org.junit.Assert.assertEquals
class OmniaLibraryActivityTest {
    @Test fun countsDistinctEpisodesAndKeepsLatestWatchTime() {
        val (times,counts) = libraryActivity(emptyList(), listOf(
            WatchedItem("tt1","series","A",1,1,100),
            WatchedItem("tt1","series","A",1,1,200),
            WatchedItem("tt1","series","A",1,2,300),
            WatchedItem("tt2","movie","B",watchedAt=400)
        ))
        assertEquals(300L,times["series:tt1"])
        assertEquals(2,counts["series:tt1"])
        assertEquals(null,counts["movie:tt2"])
        assertEquals(emptyMap<String,Long>(),libraryActivity(emptyList(),emptyList()).first)
    }
}

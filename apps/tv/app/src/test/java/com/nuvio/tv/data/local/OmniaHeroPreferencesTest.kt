package com.nuvio.tv.data.local

import androidx.datastore.preferences.core.booleanPreferencesKey
import com.nuvio.tv.TestPreferencesStore
import com.nuvio.tv.core.profile.ProfileManager
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class OmniaHeroPreferencesTest {
    private fun preferences(): Pair<LayoutPreferenceDataStore, TestPreferencesStore> {
        val store = TestPreferencesStore()
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns MutableStateFlow(1)
        every { profiles.profiles } returns MutableStateFlow(emptyList())
        val factory = mockk<ProfileDataStoreFactory>()
        every { factory.get(1, "layout_settings") } returns store
        return LayoutPreferenceDataStore(factory, profiles) to store
    }
    @Test fun freshProfilePlaysHeroTrailersWithAudio() = runBlocking {
        val (prefs, _) = preferences()
        assertTrue(prefs.focusedPosterBackdropTrailerEnabled.first())
        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())
    }
    @Test fun disablingAndReenablingTrailersKeepsAnAudibleChoice() = runBlocking {
        val (prefs, store) = preferences()
        prefs.setFocusedPosterBackdropTrailerMuted(false)
        prefs.setFocusedPosterBackdropTrailerEnabled(false)
        prefs.setFocusedPosterBackdropTrailerEnabled(true)
        assertTrue(prefs.focusedPosterBackdropTrailerEnabled.first())
        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())
        assertFalse(store.value[booleanPreferencesKey("focused_poster_backdrop_trailer_muted")]!!)
    }
    @Test fun explicitMuteSurvivesTrailerAndExpansionToggles() = runBlocking {
        val (prefs, _) = preferences()
        prefs.setFocusedPosterBackdropTrailerMuted(true)
        prefs.setFocusedPosterBackdropTrailerEnabled(false)
        prefs.setFocusedPosterBackdropTrailerEnabled(true)
        prefs.setFocusedPosterBackdropExpandEnabled(false)
        prefs.setFocusedPosterBackdropExpandEnabled(true)
        assertTrue(prefs.focusedPosterBackdropTrailerMuted.first())
    }
    @Test fun disablingExpansionDoesNotOverwriteAnAudibleChoice() = runBlocking {
        val (prefs, _) = preferences()
        prefs.setFocusedPosterBackdropTrailerMuted(false)
        prefs.setFocusedPosterBackdropExpandEnabled(false)
        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())
    }
}

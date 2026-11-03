package com.nuvio.tv.data.local

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.preferencesOf
import androidx.datastore.preferences.core.stringPreferencesKey
import com.nuvio.tv.core.profile.ProfileManager
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class OmniaPreferenceResetterTest {
    private class MemoryStore : DataStore<Preferences> {
        override val data = MutableStateFlow<Preferences>(preferencesOf(stringPreferencesKey("sentinel") to "keep"))
        override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
            transform(data.value).also { data.value = it }
    }

    @Test fun resetsOnlyAppearancePlayerAndHomeOfSelectedProfile() = runBlocking {
        val profile = MutableStateFlow(2)
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns profile
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = omniaResetPreferenceFeatures.associateWith { MemoryStore() }
        every { factory.get(2, any()) } answers { stores.getValue(secondArg()) }
        val protectedAccount = MemoryStore()
        val resetter = OmniaPreferenceResetter(factory, profiles)
        resetter.reset()
        assertEquals(setOf(booleanPreferencesKey("has_chosen_layout")), stores.getValue("layout_settings").data.value.asMap().keys)
        assertTrue(stores.getValue("layout_settings").data.value[booleanPreferencesKey("has_chosen_layout")] == true)
        assertTrue(stores.getValue("player_settings").data.value.asMap().isEmpty())
        assertTrue(stores.getValue("theme_settings").data.value.asMap().isEmpty())
        assertEquals("keep", protectedAccount.data.value[stringPreferencesKey("sentinel")])
        verify(exactly = 3) { factory.get(2, any()) }
        listOf("addons", "collections", "auth", "watch_progress", "library", "debrid_settings").forEach { feature ->
            verify(exactly = 0) { factory.get(any(), feature) }
        }
    }

    @Test fun profileSwitchCannotRedirectAnInFlightReset() = runBlocking {
        val profile = MutableStateFlow(2)
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns profile
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = omniaResetPreferenceFeatures.associateWith { MemoryStore() }
        every { factory.get(2, any()) } answers { profile.value = 3; stores.getValue(secondArg()) }
        OmniaPreferenceResetter(factory, profiles).reset()
        verify(exactly = 3) { factory.get(2, any()) }
        verify(exactly = 0) { factory.get(3, any()) }
        assertTrue(stores.getValue("player_settings").data.value.asMap().isEmpty())
    }

    @Test fun repeatedResetKeepsTheDeviceOnboarded() = runBlocking {
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns MutableStateFlow(1)
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = omniaResetPreferenceFeatures.associateWith { MemoryStore() }
        every { factory.get(1, any()) } answers { stores.getValue(secondArg()) }
        val resetter = OmniaPreferenceResetter(factory, profiles)
        resetter.reset();val snapshot = stores.mapValues { it.value.data.value }
        resetter.reset()
        assertEquals(snapshot, stores.mapValues { it.value.data.value })
    }
}

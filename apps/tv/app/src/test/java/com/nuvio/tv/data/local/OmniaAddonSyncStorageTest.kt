package com.nuvio.tv.data.local

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.core.sync.*
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class OmniaAddonSyncStorageTest {
    private class MemoryStore : DataStore<Preferences> {
        override val data = MutableStateFlow<Preferences>(emptyPreferences())
        override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
            transform(data.value).also { data.value = it }
    }
    private fun fixture(): AddonPreferences {
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns MutableStateFlow(1)
        every { profiles.profiles } returns MutableStateFlow(emptyList())
        every { profiles.activeProfile } returns null
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = mutableMapOf<Int, MemoryStore>()
        every { factory.get(any(), "addon_preferences") } answers { stores.getOrPut(firstArg()) { MemoryStore() } }
        return AddonPreferences(factory, profiles)
    }
    private fun snapshot(vararg rows: OmniaSyncAddon) = OmniaAddonSnapshot("f".repeat(64), rows.toList())
    @Test fun acknowledgedMetadataAndExplicitEmptyListAreAppliedAtomically() = runBlocking {
        val preferences = fixture()
        val remote = snapshot(OmniaSyncAddon("https://a?key=AbC/", "Named", false))
        preferences.acceptSyncSnapshot("owner", 1, remote, null)
        assertEquals(remote, preferences.readSyncState("owner", 1).second)
        assertEquals(remote.addons, preferences.readSyncState("owner", 1).first)
        preferences.acceptSyncSnapshot("owner", 1, snapshot(), remote.addons)
        assertTrue(preferences.readSyncState("owner", 1).first.isEmpty())
    }
    @Test fun localMutationDuringNetworkRequestRemainsPending() = runBlocking {
        val preferences = fixture()
        val original = snapshot(OmniaSyncAddon("https://a"))
        preferences.acceptSyncSnapshot("owner", 1, original, null)
        preferences.addAddon("https://b/manifest.json")
        val accepted = snapshot(OmniaSyncAddon("https://a"), OmniaSyncAddon("https://c", sortOrder=1))
        preferences.acceptSyncSnapshot("owner", 1, accepted, original.addons)
        val state = preferences.readSyncState("owner", 1)
        assertEquals(listOf("https://a", "https://c", "https://b"), state.first.map { it.url })
        assertEquals(accepted, state.second)
    }
    @Test fun acknowledgementCannotLeakAcrossOwnersOrProfiles() = runBlocking {
        val preferences = fixture()
        preferences.acceptSyncSnapshot("first", 1, snapshot(OmniaSyncAddon("https://a")), null)
        assertNull(preferences.readSyncState("second", 1).second)
        assertNull(preferences.readSyncState("first", 2).second)
    }
    @Test fun configuredUrlsWithDifferentCaseAreSeparateInstallations() = runBlocking {
        val preferences = fixture()
        preferences.acceptSyncSnapshot("owner", 1, snapshot(), null)
        assertTrue(preferences.addAddon("https://a/manifest.json?key=AbC/"))
        assertTrue(preferences.addAddon("https://a/manifest.json?key=abc/"))
        assertTrue(preferences.removeAddon("https://a/manifest.json?key=AbC/"))
        assertEquals(listOf("https://a?key=abc/"), preferences.readSyncState("owner", 1).first.map { it.url })
    }
    @Test fun reorderingAnOlderUiListCannotDropNewlySyncedRows() = runBlocking {
        val preferences = fixture()
        preferences.acceptSyncSnapshot("owner", 1, snapshot(OmniaSyncAddon("https://a"), OmniaSyncAddon("https://b",sortOrder=1), OmniaSyncAddon("https://c",sortOrder=2)), null)
        preferences.setAddonOrder(listOf("https://b", "https://a"))
        assertEquals(listOf("https://b", "https://a", "https://c"), preferences.readSyncState("owner", 1).first.map { it.url })
    }
}

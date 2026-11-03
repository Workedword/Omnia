package com.nuvio.tv.domain.model

import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import com.google.gson.Gson
import com.nuvio.tv.data.local.CollectionsDataStore
import io.mockk.mockk

class HiddenCollectionCatalogsTest {
    private fun collection(hidden: Boolean = true, addon: String = "a", type: String = "movie", catalog: String = "c"): Collection {
        val source = AddonCatalogCollectionSource(addonId = addon, type = type, catalogId = catalog)
        return Collection("one", "First", hideSourceRows = hidden, folders = listOf(CollectionFolder("folder", "Titles", sources = listOf(source))))
    }
    @Test fun optInOnly() {
        assertTrue(hiddenCollectionCatalogKeys(listOf(collection(false)), emptySet()).isEmpty())
        assertEquals(setOf(catalogRowLegacyKey("a", "movie", "c")), hiddenCollectionCatalogKeys(listOf(collection()), emptySet()))
    }
    @Test fun disabledCollectionDoesNotHideHomeCatalogs() {
        assertTrue(hiddenCollectionCatalogKeys(listOf(collection()), setOf("one")).isEmpty())
    }
    @Test fun disablingOrDeletingRestoresRows() {
        val original = collection()
        assertTrue(hiddenCollectionCatalogKeys(listOf(original.copy(hideSourceRows = false)), emptySet()).isEmpty())
        assertTrue(hiddenCollectionCatalogKeys(emptyList(), emptySet()).isEmpty())
        assertEquals(1, original.folders.single().sources.size)
    }
    @Test fun profileInputDoesNotLeakToAnotherProfile() {
        val first = hiddenCollectionCatalogKeys(listOf(collection()), emptySet())
        val second = hiddenCollectionCatalogKeys(listOf(collection(false)), emptySet())
        assertEquals(1, first.size)
        assertTrue(second.isEmpty())
    }
    @Test fun catalogIdentityKeepsOtherTypesAndProvidersDistinct() {
        val keys = hiddenCollectionCatalogKeys(listOf(collection(), collection(addon = "b"), collection(type = "series")), emptySet())
        assertEquals(3, keys.size)
    }
    @Test fun duplicatesDoNotMutateSourcesOrCatalogPreferences() {
        val value = collection()
        assertEquals(1, hiddenCollectionCatalogKeys(listOf(value, value.copy(id = "two")), emptySet()).size)
        assertEquals(1, value.folders.single().sources.size)
        assertTrue(value.hideSourceRows)
    }
    @Test fun persistenceRetainsFlagAndSources() {
        val value = collection()
        val payload = CollectionsDataStore(mockk(relaxed = true), mockk(relaxed = true), mockk(relaxed = true)).exportToJson(listOf(value))
        val decoded = CollectionsDataStore(mockk(relaxed = true), mockk(relaxed = true), mockk(relaxed = true)).importFromJson(payload).single()
        assertTrue(decoded.hideSourceRows)
        assertEquals(value.folders, decoded.folders)
        assertFalse(Collection("old", "Legacy").hideSourceRows)
    }

}

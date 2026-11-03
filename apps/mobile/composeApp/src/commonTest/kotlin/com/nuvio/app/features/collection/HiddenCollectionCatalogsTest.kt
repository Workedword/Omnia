package com.nuvio.app.features.collection

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.serialization.json.Json
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString

class HiddenCollectionCatalogsTest {
    private fun collection(hidden: Boolean = true, addon: String = "a", type: String = "movie", catalog: String = "c"): Collection {
        val source = CollectionSource(addonId = addon, type = type, catalogId = catalog)
        return Collection("one", "First", hideSourceRows = hidden, folders = listOf(CollectionFolder("folder", "Titles", sources = listOf(source))))
    }
    @Test fun optInOnly() {
        assertTrue(hiddenCollectionCatalogKeys(listOf(collection(false)), emptySet()).isEmpty())
        assertEquals(setOf("a:movie:c"), hiddenCollectionCatalogKeys(listOf(collection()), emptySet()))
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
        val payload = Json.encodeToString(value)
        val decoded = Json.decodeFromString<Collection>(payload)
        assertTrue(decoded.hideSourceRows)
        assertEquals(value.folders, decoded.folders)
        assertFalse(Collection("old", "Legacy").hideSourceRows)
    }

    @Test fun legacyCatalogSourcesAlsoHide() {
        val value = Collection("one", "First", hideSourceRows = true, folders = listOf(
            CollectionFolder("f", "Legacy", catalogSources = listOf(CollectionCatalogSource("a", "movie", "c")))
        ))
        assertEquals(setOf("a:movie:c"), hiddenCollectionCatalogKeys(listOf(value), emptySet()))
    }

}

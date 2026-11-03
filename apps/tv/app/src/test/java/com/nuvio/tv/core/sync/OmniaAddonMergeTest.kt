package com.nuvio.tv.core.sync
import org.junit.Test
import org.junit.Assert.assertEquals
import kotlinx.serialization.encodeToString

class OmniaAddonMergeTest {
    private fun rows(vararg names: String) = names.mapIndexed { i, s -> OmniaSyncAddon("https://$s", sortOrder = i) }
    private fun keys(rows: List<OmniaSyncAddon>) = rows.map { it.url.substringAfter("https://") }
    @Test fun staleDeviceCannotEraseRemoteAddition() {
        assertEquals(listOf("a", "b"), keys(omniaMergeAddons(rows("a"), rows("a"), rows("a", "b"))))
    }
    @Test fun explicitRemovalKeepsUnknownRemoteAddition() {
        assertEquals(listOf("b", "c"), keys(omniaMergeAddons(rows("a", "b"), rows("b"), rows("a", "b", "c"))))
    }
    @Test fun remoteDeletionIsNotResurrectedByStaleEnableEdit() {
        assertEquals(emptyList<String>(), keys(omniaMergeAddons(rows("a"), rows("a").map { it.copy(enabled = false) }, emptyList())))
    }
    @Test fun independentNameAndEnableEditsAreMerged() {
        val before = rows("a")
        val result = omniaMergeAddons(before, before.map { it.copy(enabled = false) }, before.map { it.copy(name = "Remote") }).single()
        assertEquals("Remote", result.name)
        assertEquals(false, result.enabled)
    }
    @Test fun bothDevicesCanAddWithoutLosingEither() {
        assertEquals(listOf("a", "c", "b"), keys(omniaMergeAddons(rows("a"), rows("a", "b"), rows("a", "c"))))
    }
    @Test fun noLocalReorderRetainsRemoteReorder() {
        assertEquals(listOf("b", "a"), keys(omniaMergeAddons(rows("a", "b"), rows("a", "b"), rows("b", "a"))))
    }
    @Test fun explicitLocalReorderKeepsRemoteUnknownItems() {
        assertEquals(listOf("b", "a", "c"), keys(omniaMergeAddons(rows("a", "b"), rows("b", "a"), rows("a", "b", "c"))))
    }
    @Test fun firstContactDoesNotDeleteOrReaddUnknownOldLocalState() {
        assertEquals(listOf("b"), keys(omniaMergeAddons(null, rows("a"), rows("b"))))
    }
    @Test fun explicitEmptyListIsADeletion() {
        assertEquals(listOf("b"), keys(omniaMergeAddons(rows("a"), emptyList(), rows("a", "b"))))
    }
    @Test fun queryCaseAndTrailingSlashArePreserved() {
        val value = "https://a/manifest.json?key=AbC/"
        assertEquals("https://a?key=AbC/", omniaAddonKey(value))
        assertEquals(value, omniaManifestUrl(value))
        assertEquals(2, omniaNormalizeAddons(rows("a?key=AbC/", "a?key=abc/")).size)
    }
    @Test fun aliasesDeduplicateAndReindexWithoutMutatingInputs() {
        val input = listOf(OmniaSyncAddon("https://a/manifest.json", sortOrder = 7), OmniaSyncAddon("https://a", sortOrder = 8))
        assertEquals(listOf(OmniaSyncAddon("https://a")), omniaNormalizeAddons(input))
        assertEquals(7, input.first().sortOrder)
    }
    @Test fun secondMergeRetainsNewerLocalMutationDuringRequest() {
        val sent = rows("a", "b")
        val accepted = rows("a", "c", "b")
        assertEquals(listOf("c", "b"), keys(omniaMergeAddons(sent, rows("b"), accepted)))
    }
    @Test fun acknowledgedStateRoundTripsWithoutChangingQueries() {
        val envelope = OmniaAddonEnvelope(OmniaAddonSnapshot("f".repeat(64), rows("a?key=AbC/")), rows("a?key=AbC/", "b"))
        assertEquals(envelope, kotlinx.serialization.json.Json.decodeFromString<OmniaAddonEnvelope>(kotlinx.serialization.json.Json.encodeToString(envelope)))
    }
}

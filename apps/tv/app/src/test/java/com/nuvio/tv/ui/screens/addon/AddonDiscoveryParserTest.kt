package com.nuvio.tv.ui.screens.addon

import org.junit.Assert.*
import org.junit.Test

class AddonDiscoveryParserTest {
    @Test fun `supports subtitle resource objects and required configuration`() {
        val entries = AddonDiscoveryParser.parse("""[{"transportUrl":"https://example.com/manifest.json","manifest":{"id":"sub","name":"Subtitles","resources":[{"name":"subtitles","types":["movie"]}],"behaviorHints":{"configurationRequired":true}}}]""", "Community")
        assertEquals(setOf("subtitles"), entries.single().resources)
        assertTrue(entries.single().configurationRequired)
        assertEquals("https://example.com/configure", entries.single().configureUrl)
    }
    @Test fun `skips invalid rows without losing valid entries and deduplicates`() {
        val good = """{"transportUrl":"https://example.com/manifest.json","manifest":{"id":"x","name":"X","resources":["catalog"]}}"""
        assertEquals(1, AddonDiscoveryParser.parse("[null,{},$good,$good]", "Official").size)
    }
    @Test fun `public catalog excludes embedded credentials local and insecure URLs`() {
        listOf("http://example.com/manifest.json", "https://secret@example.com/manifest.json", "https://localhost/manifest.json", "https://example.com/manifest.json?token=secret").forEach { url ->
            assertTrue(AddonDiscoveryParser.parse("""[{"transportUrl":"$url","manifest":{"id":"x","name":"X","resources":["stream"]}}]""", "Community").isEmpty())
        }
    }

    @Test fun `sports setup remains visible without pretending it is installed`() {
        val entries=AddonDiscoveryParser.parse("""{"entries":[{"name":"IPTV","category":"Live TV & Sports","url":"https://example.com/configure","installable":false}]}""", "Omnia Community")
        val entry=entries.single()
        assertEquals("IPTV",entry.name)
        assertTrue("live" in entry.resources)
        assertTrue(entry.configurationRequired)
        assertEquals("https://example.com/configure",entry.configureUrl)
    }
    @Test fun `directory requires a real manifest before direct installation`() {
        val entries=AddonDiscoveryParser.parse("""{"entries":[{"name":"Sports","category":"Live TV & Sports","url":"https://example.com/configure","manifestUrl":"https://example.com/configure","installable":true}]}""", "Omnia Community")
        assertTrue(entries.isEmpty())
    }
}

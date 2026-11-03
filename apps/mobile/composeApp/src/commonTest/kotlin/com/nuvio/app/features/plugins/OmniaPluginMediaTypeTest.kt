package com.nuvio.app.features.plugins

import kotlin.test.Test
import kotlin.test.assertEquals

class OmniaPluginMediaTypeTest {
    @Test
    fun `declared series provider receives episodic series`() {
        assertEquals("series", jsPluginMediaType("series", listOf("movie", "series"), 2, 5))
        assertEquals("series", jsPluginMediaType("tv", listOf("movie", "series"), 2, 5))
    }

    @Test
    fun `ordinary tv providers retain their existing contract`() {
        assertEquals("tv", jsPluginMediaType("series", listOf("movie", "tv"), 2, 5))
    }

    @Test
    fun `movie requests never become episodic requests`() {
        assertEquals("movie", jsPluginMediaType("movie", listOf("movie", "series"), null, null))
        assertEquals("movie", jsPluginMediaType("movie", listOf("movie", "series"), 1, 1))
    }

    @Test
    fun `both episode indices are required for the episodic adapter`() {
        assertEquals("tv", jsPluginMediaType("series", listOf("series"), null, 1))
        assertEquals("tv", jsPluginMediaType("series", listOf("series"), 1, null))
    }

    @Test
    fun `case variants and season zero specials keep the declared contract`() {
        assertEquals("series", jsPluginMediaType("TV", listOf("movie", "SERIES"), 0, 1))
    }

    @Test
    fun `unknown content types are not coerced into television`() {
        assertEquals("custom", jsPluginMediaType("custom", listOf("series"), 1, 1))
    }
}

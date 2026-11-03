package com.nuvio.app.features.details

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class OmniaHeroAudioStateTest {
    @Test fun defaultIsAudibleAndExplicitMuteCanBeToggledBack() {
        assertFalse(HeroTrailerAudioState.muted.value)
        HeroTrailerAudioState.toggleMuted()
        try { assertTrue(HeroTrailerAudioState.muted.value) }
        finally { HeroTrailerAudioState.toggleMuted() }
        assertFalse(HeroTrailerAudioState.muted.value)
    }
}

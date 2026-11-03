package com.nuvio.app.features.details

import android.app.Application
import android.content.Context
import org.junit.Before
import org.junit.After
import org.junit.Test
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], application = Application::class)
class OmniaHeroDefaultsTest {
    @Before fun initialize() {
        val context = RuntimeEnvironment.getApplication()
        context.getSharedPreferences("nuvio_meta_screen_settings", Context.MODE_PRIVATE).edit().clear().commit()
        MetaScreenSettingsStorage.initialize(context)
        MetaScreenSettingsRepository.clearLocalState()
    }
    @After fun finish() { MetaScreenSettingsRepository.clearLocalState() }

    @Test fun freshProfileEnablesTrailers() {
        MetaScreenSettingsRepository.ensureLoaded()
        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)
        assertTrue(MetaScreenSettingsStorage.loadPayload()!!.contains("\"hero_trailer_playback\":true"))
    }
    @Test fun olderPayloadWithoutTrailerSettingUsesDefaultAndKeepsOtherChoices() {
        MetaScreenSettingsStorage.savePayload("""{"blur_unwatched_episodes":true}""")
        MetaScreenSettingsRepository.onProfileChanged()
        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)
        assertTrue(MetaScreenSettingsRepository.uiState.value.blurUnwatchedEpisodes)
    }
    @Test fun explicitOffSurvivesProfileReloadAndUnrelatedChanges() {
        MetaScreenSettingsRepository.setHeroTrailerPlayback(false)
        MetaScreenSettingsRepository.setShowOverallRatings(false)
        MetaScreenSettingsRepository.onProfileChanged()
        assertFalse(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)
        assertFalse(MetaScreenSettingsRepository.uiState.value.showOverallRatings)
    }
    @Test fun resetRestoresDefaultButDoesNotChangeRetainedPayload() {
        MetaScreenSettingsRepository.setHeroTrailerPlayback(false)
        val before = MetaScreenSettingsStorage.loadPayload()!!
        MetaScreenSettingsRepository.resetToDefaults()
        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)
        MetaScreenSettingsStorage.savePayload(before)
        MetaScreenSettingsRepository.onProfileChanged()
        assertFalse(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)
    }
}

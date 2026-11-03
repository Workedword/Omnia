package com.nuvio.app.features.settings

import com.nuvio.app.features.player.PlayerSettingsStorage
import com.nuvio.app.features.player.PlayerSettingsRepository
import com.nuvio.app.features.home.HomeCatalogSettingsRepository
import com.nuvio.app.features.details.MetaScreenSettingsRepository
import com.nuvio.app.core.ui.PosterCardStyleRepository
import com.nuvio.app.core.ui.CardDepthStyleRepository
import com.nuvio.app.features.watchprogress.ContinueWatchingPreferencesRepository
import com.nuvio.app.features.watchprogress.ContinueWatchingSectionStyle
import com.nuvio.app.features.watchprogress.ContinueWatchingSortMode

/** No account, add-on, collection, library, history or provider storage is cleared. */
internal object OmniaPreferenceResetter {
    fun reset() {
        PlayerSettingsStorage.resetProfilePreferences()
        ThemeSettingsStorage.resetProfilePreferences()
        PlayerSettingsRepository.onProfileChanged()
        ThemeSettingsRepository.onProfileChanged()
        HomeCatalogSettingsRepository.resetToDefaults()
        MetaScreenSettingsRepository.resetToDefaults()
        PosterCardStyleRepository.resetToDefaults()
        CardDepthStyleRepository.resetToDefaults()
        ContinueWatchingPreferencesRepository.setVisible(true)
        ContinueWatchingPreferencesRepository.setStyle(ContinueWatchingSectionStyle.Card)
        ContinueWatchingPreferencesRepository.setUpNextFromFurthestEpisode(true)
        ContinueWatchingPreferencesRepository.setUseEpisodeThumbnails(true)
        ContinueWatchingPreferencesRepository.setShowUnairedNextUp(true)
        ContinueWatchingPreferencesRepository.setBlurNextUp(false)
        ContinueWatchingPreferencesRepository.setShowResumePromptOnLaunch(true)
        ContinueWatchingPreferencesRepository.setSortMode(ContinueWatchingSortMode.DEFAULT)
    }
}

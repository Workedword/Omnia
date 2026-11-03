package com.nuvio.tv.data.local

import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import com.nuvio.tv.core.profile.ProfileManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

internal val omniaResetPreferenceFeatures = listOf("layout_settings", "player_settings", "theme_settings")

@Singleton
class OmniaPreferenceResetter @Inject constructor(
    private val factory: ProfileDataStoreFactory,
    private val profiles: ProfileManager,
) {
    suspend fun reset() = withContext(Dispatchers.IO) {
        // Capture once: a profile switch cannot redirect a later write.
        val profileId = profiles.activeProfileId.value
        omniaResetPreferenceFeatures.forEach { feature ->
            factory.get(profileId, feature).edit { prefs ->
                prefs.clear()
                if (feature == "layout_settings") prefs[booleanPreferencesKey("has_chosen_layout")] = true
            }
        }
    }
}

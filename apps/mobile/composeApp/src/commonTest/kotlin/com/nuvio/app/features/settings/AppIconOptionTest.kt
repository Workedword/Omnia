package com.nuvio.app.features.settings

import com.nuvio.app.core.ui.AppTheme
import kotlin.test.Test
import kotlin.test.assertEquals
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.omnia_wordmark

class AppIconOptionTest {
    @Test
    fun primaryIconUsesPlatformDefault() {
        assertEquals(null, AppIconOption.ORIGINAL.platformName)
        assertEquals(AppIconOption.ORIGINAL, AppIconOption.fromPlatformName(null))
    }

    @Test
    fun alternateIconNamesRoundTrip() {
        AppIconOption.entries.drop(1).forEach { icon ->
            assertEquals(icon, AppIconOption.fromPlatformName(icon.platformName))
        }
    }

    @Test
    fun shortlistedCatalogueContainsSixIcons() {
        assertEquals(6, AppIconOption.entries.size)
    }

    @Test
    fun unknownIconFallsBackToOriginal() {
        assertEquals(AppIconOption.ORIGINAL, AppIconOption.fromPlatformName("UnknownIcon"))
    }

    @Test
    fun goldThemeUsesOmniaWordmark() {
        assertEquals(
            Res.drawable.omnia_wordmark,
            AppTheme.GOLD.wordmarkResource(AppIconOption.COPPER),
        )
    }
}

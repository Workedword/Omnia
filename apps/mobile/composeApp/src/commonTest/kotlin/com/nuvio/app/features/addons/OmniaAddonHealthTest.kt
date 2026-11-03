package com.nuvio.app.features.addons
import com.nuvio.app.features.settings.filterHomeCatalogs
import com.nuvio.app.features.home.HomeCatalogSettingsItem
import kotlin.test.Test
import kotlin.test.assertEquals
class OmniaAddonHealthTest {
    @Test fun disabledAndFailedProvidersAreNotReportedReady() {
        assertEquals("Disabled", addonHealthLabel(ManagedAddon("https://example.invalid", enabled=false)))
        assertEquals("Unavailable · retry", addonHealthLabel(ManagedAddon("https://example.invalid", errorMessage="offline")))
        assertEquals("Checking manifest…", addonHealthLabel(ManagedAddon("https://example.invalid", isRefreshing=true)))
        assertEquals("Not checked", addonHealthLabel(ManagedAddon("https://example.invalid")))
    }
    @Test fun catalogSearchCombinesProviderAndVisibilityAndKeepsStableKeys() {
        val first = HomeCatalogSettingsItem("a", "Popular movies", "Cinemeta")
        val hidden = first.copy(key = "b", customTitle = "My shows", enabled = false)
        val other = first.copy(key = "c", addonName = "Other")
        val items = listOf(first, hidden, other)
        assertEquals(listOf(first, hidden), filterHomeCatalogs(items, "  CINEMETA ", "All"))
        assertEquals(listOf(hidden), filterHomeCatalogs(items, "my shows", "Hidden"))
        assertEquals(listOf(first, other), filterHomeCatalogs(items, "", "Shown"))
        assertEquals(emptyList<HomeCatalogSettingsItem>(), filterHomeCatalogs(items, "missing", "All"))
        assertEquals(items, filterHomeCatalogs(items, "", "All"))
    }
}

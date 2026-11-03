package com.nuvio.app.features.settings

import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.ui.Modifier
import com.nuvio.app.core.build.AppFeaturePolicy
import com.nuvio.app.features.addons.AddonsSettingsPageContent
import com.nuvio.app.features.addons.OmniaAddonSection

internal fun LazyListScope.addonsSettingsContent(
    onPageClick: (SettingsPage) -> Unit,
    isTablet: Boolean = false,
) {
    item {
        SettingsGroup(isTablet = isTablet) {
            SettingsNavigationRow(title = "Current Add-ons", description = "Manage your installed add-ons and custom URLs.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.CurrentAddons) })
            SettingsGroupDivider(isTablet = isTablet)
            SettingsNavigationRow(title = "Discover Add-ons", description = "Find official and community add-ons that are not already installed.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.DiscoverAddons) })
            SettingsGroupDivider(isTablet = isTablet)
            SettingsNavigationRow(title = "Sync Add-ons", description = "Sync this profile's add-ons with your Omnia account.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.SyncAddons) })
            if (AppFeaturePolicy.pluginsEnabled) {
                SettingsGroupDivider(isTablet = isTablet)
                SettingsNavigationRow(title = "Script Providers", description = "Manage script-based sources, including Omnia India Providers.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.Plugins) })
            }
        }
    }
}

internal fun LazyListScope.addonSectionContent(section: OmniaAddonSection) {
    item { AddonsSettingsPageContent(modifier = Modifier.fillMaxWidth(), section = section) }
}

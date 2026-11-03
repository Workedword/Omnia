@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)
package com.nuvio.tv.ui.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Extension
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import com.nuvio.tv.ui.theme.NuvioTheme

@Composable
internal fun OmniaAddonsSettingsContent(onNavigateToAddons: (String) -> Unit, onNavigateToPlugins: () -> Unit, showPlugins: Boolean, initialFocusRequester: FocusRequester?) {
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.md)) {
        SettingsDetailHeader(title = "Add-ons", subtitle = "Manage your sources in one place.")
        SettingsGroupCard(modifier = Modifier.fillMaxWidth()) {
            SettingsActionRow(
                title = "Current Add-ons",
                subtitle = "Manage installed add-ons and custom URLs.",
                leadingIcon = Icons.Default.Extension,
                onClick = { onNavigateToAddons("current") },
                modifier = if (initialFocusRequester != null) Modifier.focusRequester(initialFocusRequester) else Modifier
            )
            SettingsActionRow(title = "Discover Add-ons", subtitle = "Find official and community add-ons that are not already installed.", leadingIcon = Icons.Default.Extension, onClick = { onNavigateToAddons("discover") })
            SettingsActionRow(title = "Sync Add-ons", subtitle = "Sync this profile's add-ons with your Omnia account.", leadingIcon = Icons.Default.Extension, onClick = { onNavigateToAddons("sync") })
            if (showPlugins) {
                SettingsActionRow(
                    title = "Script Providers",
                    subtitle = "Manage script-based sources, including Omnia India Providers.",
                    leadingIcon = Icons.Default.Extension,
                    onClick = onNavigateToPlugins,
                )
            }
        }
    }
}

package com.nuvio.tv.ui.screens.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SettingsCatalogTest {
    @Test
    fun `restore defaults is available exactly once in essentials and advanced`() {
        allCombinations().forEach { categories ->
            assertEquals(1, categories.count { it == SettingsCategory.RESTORE_DEFAULTS })
            assertEquals(SettingsRailGroup.SYSTEM, SettingsCategory.RESTORE_DEFAULTS.group)
        }
    }


    @Test
    fun `primary profile in advanced debug build sees product categories in group order`() {
        val categories = visibleSettingsCategories(
            isPrimaryProfile = true,
            isEssentialMode = false,
            isDebugBuild = true
        )

        assertEquals(
            listOf(
                SettingsCategory.ACCOUNT,
                SettingsCategory.APPEARANCE,
                SettingsCategory.LAYOUT,
                SettingsCategory.ADDONS,
                SettingsCategory.CONTENT_DISCOVERY,
                SettingsCategory.PLAYBACK,
                SettingsCategory.INTEGRATION,
                SettingsCategory.TRACKING,
                SettingsCategory.ADVANCED,
                SettingsCategory.RESTORE_DEFAULTS,
                SettingsCategory.ABOUT
            ),
            categories
        )
    }

    @Test
    fun `secondary profile does not see account or profiles`() {
        val categories = visibleSettingsCategories(
            isPrimaryProfile = false,
            isEssentialMode = false,
            isDebugBuild = false
        )

        assertFalse(SettingsCategory.ACCOUNT in categories)
        assertFalse(SettingsCategory.PROFILES in categories)
        assertEquals(SettingsCategory.APPEARANCE, categories.first())
    }

    @Test
    fun `debug is never exposed in user settings`() {
        allCombinations().forEach { assertFalse(SettingsCategory.DEBUG in it) }
        assertFalse(SettingsCategory.DEBUG in visibleSettingsCategories(true, isEssentialMode = false, isDebugBuild = false))
        assertFalse(SettingsCategory.DEBUG in visibleSettingsCategories(true, isEssentialMode = true, isDebugBuild = true))
    }

    @Test
    fun `experience never appears in the rail`() {
        allCombinations().forEach { categories ->
            assertFalse(SettingsCategory.EXPERIENCE in categories)
        }
    }

    @Test
    fun `about is the last regular category`() {
        allCombinations().forEach { categories ->
            val withoutDebug = categories - SettingsCategory.DEBUG
            assertEquals(SettingsCategory.ABOUT, withoutDebug.last())
        }
    }

    @Test
    fun `each group is contiguous in every configuration`() {
        allCombinations().forEach { categories ->
            val groupRuns = categories.map { it.group }.fold(mutableListOf<SettingsRailGroup>()) { runs, group ->
                if (runs.lastOrNull() != group) runs.add(group)
                runs
            }
            assertEquals(groupRuns.distinct(), groupRuns)
        }
    }

    @Test
    fun `dividers are placed only where the group changes`() {
        val categories = visibleSettingsCategories(
            isPrimaryProfile = true,
            isEssentialMode = false,
            isDebugBuild = true
        )
        val dividerBefore = categories.indices.filter { categories.startsNewGroup(it) }.map { categories[it] }

        assertEquals(
            listOf(
                SettingsCategory.APPEARANCE,
                SettingsCategory.ADDONS,
                SettingsCategory.INTEGRATION,
                SettingsCategory.ADVANCED
            ),
            dividerBefore
        )
        assertFalse(categories.startsNewGroup(0))
    }

    @Test
    fun `secondary profile rail starts without a divider`() {
        val categories = visibleSettingsCategories(
            isPrimaryProfile = false,
            isEssentialMode = true,
            isDebugBuild = false
        )
        assertFalse(categories.startsNewGroup(0))
        assertTrue(categories.startsNewGroup(categories.indexOf(SettingsCategory.ADDONS)))
    }

    @Test
    fun `watch party shows for every profile only while available`() {
        listOf(true, false).forEach { primary ->
            val available = visibleSettingsCategories(primary, isEssentialMode = false, isDebugBuild = false, isWatchPartyAvailable = true)
            val unavailable = visibleSettingsCategories(primary, isEssentialMode = false, isDebugBuild = false, isWatchPartyAvailable = false)
            assertTrue(SettingsCategory.WATCH_PARTY in available)
            assertFalse(SettingsCategory.WATCH_PARTY in unavailable)
        }
        assertEquals(
            listOf(SettingsCategory.ACCOUNT, SettingsCategory.WATCH_PARTY),
            visibleSettingsCategories(true, isEssentialMode = false, isDebugBuild = false, isWatchPartyAvailable = true).take(2)
        )
    }

    private fun allCombinations(): List<List<SettingsCategory>> =
        listOf(true, false).flatMap { primary ->
            listOf(true, false).flatMap { essential ->
                listOf(true, false).flatMap { debug ->
                    listOf(true, false).map { watchParty ->
                        visibleSettingsCategories(primary, essential, debug, watchParty)
                    }
                }
            }
        }
}

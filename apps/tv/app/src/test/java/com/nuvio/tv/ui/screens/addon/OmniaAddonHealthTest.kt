package com.nuvio.tv.ui.screens.addon
import com.nuvio.tv.domain.model.*
import com.nuvio.tv.domain.repository.*
import com.nuvio.tv.core.network.NetworkResult
import io.mockk.*
import kotlinx.coroutines.test.runTest
import org.junit.Test
import org.junit.Assert.assertEquals
class OmniaAddonHealthTest {
    private fun addon() = Addon(id="test",name="Test",version="1",description=null,logo=null,baseUrl="https://example.invalid",catalogs=emptyList(),types=emptyList(),resources=emptyList())
    @Test fun disabledProvidersAreNeverRequested() = runTest {
        val repo=mockk<AddonRepository>()
        every { repo.getInstalledAddons() } returns kotlinx.coroutines.flow.flowOf(emptyList())
        val catalogs=mockk<CatalogRepository>()
        assertEquals(listOf("Test: Disabled"),AddonHealthViewModel(repo,catalogs).check(addon().copy(enabled=false)))
        coVerify(exactly=0) { repo.fetchAddon(any()) }
    }
    @Test fun requiredFilterCatalogsAreNotMarkedUnavailable() = runTest {
        val repo=mockk<AddonRepository>()
        every { repo.getInstalledAddons() } returns kotlinx.coroutines.flow.flowOf(emptyList())
        val catalogs=mockk<CatalogRepository>()
        val source=addon().copy(catalogs=listOf(CatalogDescriptor(ContentType.MOVIE,id="filtered",name="Filtered",extraRequired=listOf("search"))))
        coEvery { repo.fetchAddon(any()) } returns NetworkResult.Success(source)
        assertEquals(listOf("Test: Manifest ready","Filtered: Requires filters in Discover"),AddonHealthViewModel(repo,catalogs).check(source))
    }
    @Test fun catalogFiltersCombineSearchAndVisibilityWithoutChangingOrder() {
        val first = CatalogOrderItem("a", "a", "Popular movies", "Cinemeta", "movie", false, false, true)
        val hidden = first.copy(key = "b", catalogName = "Popular series", isDisabled = true)
        val other = first.copy(key = "c", addonName = "Other")
        val items = listOf(first, hidden, other)
        assertEquals(listOf(first, hidden), filterHomeCatalogs(items, "  CINEMETA ", "All"))
        assertEquals(listOf(hidden), filterHomeCatalogs(items, "popular", "Hidden"))
        assertEquals(listOf(first, other), filterHomeCatalogs(items, "", "Shown"))
        assertEquals(emptyList<CatalogOrderItem>(), filterHomeCatalogs(items, "missing", "All"))
        assertEquals(listOf(first, hidden, other), filterHomeCatalogs(items, "", "All"))
    }
}

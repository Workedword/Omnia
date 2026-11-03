package com.nuvio.app.core.deeplink
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
class OmniaUrlTest {
    @Test fun omniaLinksAndCompatibilityLinksOpenTheSameTitle() {
        val expected = AppDeepLink.Meta("movie", "omniaqa:test")
        assertEquals(expected, parseAppDeepLink("omnia://detail/movie/omniaqa%3Atest"))
        assertEquals(expected, parseAppDeepLink("nuvio://detail/movie/omniaqa%3Atest"))
        assertNull(parseAppDeepLink("other://detail/movie/omniaqa%3Atest"))
    }
    @Test fun omniaAddonLinksPreserveConfiguredQueryParameters() {
        assertEquals(AppDeepLink.AddonInstall("https://example.com/u/demo/manifest.json?language=hi"), parseAppDeepLink("omnia://example.com/u/demo/manifest.json?language=hi"))
        assertNull(parseAppDeepLink("omnia://auth/trakt?code=example"))
    }
    @Test fun generatedLinksUseOmniaScheme() {
        assertEquals("omnia://meta?type=movie&id=omniaqa%3Atest", buildMetaDeepLinkUrl("movie", "omniaqa:test"))
        assertEquals("omnia://downloads", buildDownloadsDeepLinkUrl())
    }
}

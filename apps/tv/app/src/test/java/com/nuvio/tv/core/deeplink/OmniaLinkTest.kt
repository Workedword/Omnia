package com.nuvio.tv.core.deeplink
import com.nuvio.tv.domain.deeplink.AppDeepLink
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
class OmniaLinkTest {
    @Test fun omniaAndCompatibilityLinksOpenTheSameTitle() {
        val expected = AppDeepLink.Meta("movie", "omniaqa:test")
        assertEquals(expected, DeepLinkParser.parse("omnia://detail/movie/omniaqa%3Atest"))
        assertEquals(expected, DeepLinkParser.parse("nuvio://detail/movie/omniaqa%3Atest"))
        assertNull(DeepLinkParser.parse("other://detail/movie/omniaqa%3Atest"))
    }
    @Test fun omniaAddonLinksPreserveConfiguration() {
        assertEquals(AppDeepLink.AddonInstall("https://example.com/u/demo/manifest.json?language=hi"), DeepLinkParser.parse("omnia://example.com/u/demo/manifest.json?language=hi"))
        assertNull(DeepLinkParser.parse("omnia://auth/trakt?code=example"))
    }
}

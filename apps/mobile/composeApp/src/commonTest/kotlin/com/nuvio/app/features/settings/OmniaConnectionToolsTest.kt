package com.nuvio.app.features.settings

import com.nuvio.app.features.addons.RawHttpResponse
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.test.runTest
import kotlin.test.*

class OmniaConnectionToolsTest {
    private fun response(status: Int, body: String = "") = RawHttpResponse(status,"test","https://example.test",body,emptyMap())
    @Test fun validInternetAndCatalogResponsesPass() = runTest {
        val urls=mutableListOf<String>()
        val results=checkOmniaConnections { url -> urls+=url; if(url.endsWith("generate_204")) response(204) else response(200,"""{"catalogs":[]}""") }
        assertEquals(2,results.size);assertTrue(results.all { it.passed });assertTrue(urls.all { it.startsWith("https://") })
    }
    @Test fun captivePortalOrBrokenCatalogIsNotShownAsConnected() = runTest {
        val results=checkOmniaConnections { response(200,"<html>Sign in to Wi-Fi</html>") }
        assertTrue(results.none { it.passed });assertTrue(results.all { it.detail.contains("Unexpected response") })
    }
    @Test fun serverErrorIsReportedWithoutEchoingItsPrivateResponse() = runTest {
        val results=checkOmniaConnections { response(503,"private diagnostic token") }
        assertTrue(results.all { !it.passed && it.detail.contains("503") && !it.detail.contains("private") })
    }
    @Test fun cancellationStopsTheCheckRatherThanBecomingAConnectionError() = runTest {
        var calls=0
        assertFailsWith<CancellationException> { checkOmniaConnections { calls++;throw CancellationException("stop") } }
        assertEquals(1,calls)
    }
}

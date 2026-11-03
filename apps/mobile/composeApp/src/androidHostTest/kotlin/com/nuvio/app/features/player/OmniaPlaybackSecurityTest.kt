package com.nuvio.app.features.player

import com.nuvio.app.core.network.OmniaHttpSecurity
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException
import java.util.concurrent.TimeUnit
import javax.net.ssl.HttpsURLConnection

/** Uses real sockets, handshakes and redirects, with dummy provider headers only. */
class OmniaPlaybackSecurityTest {
    private val secrets = mapOf(
        "Authorization" to "Bearer test-only", "Cookie" to "test=session",
        "Proxy-Authorization" to "Basic test-only", "X-Api-Key" to "test-key",
        "X-Unusual-Provider-Credential" to "test-private", "Referer" to "https://example.test/?token=test",
        "Origin" to "https://example.test"
    )
    private val ca = HeldCertificate.Builder().certificateAuthority(0).commonName("Omnia test CA").build()
    private val trusted = HandshakeCertificates.Builder().addTrustedCertificate(ca.certificate).build()
    private fun leaf(wrongHost: Boolean = false, expired: Boolean = false): HeldCertificate =
        HeldCertificate.Builder().commonName("media fixture")
            .addSubjectAlternativeName(if (wrongHost) "wrong.invalid" else "localhost")
            .apply { if (expired) validityInterval(1_000L, 2_000L) }
            .signedBy(ca).build()

    private fun server(certificate: HeldCertificate? = null): MockWebServer = MockWebServer().apply {
        if (certificate != null) useHttps(
            HandshakeCertificates.Builder().heldCertificate(certificate, ca.certificate).build().sslSocketFactory(), false,
        )
        start()
    }
    private fun client(url: String, headers: Map<String, String> = secrets, trustFixture: Boolean = false): OkHttpClient =
        PlayerPlaybackNetworking.createHttpClient(headers, sourceUrl = url).newBuilder()
            .apply { if (trustFixture) sslSocketFactory(trusted.sslSocketFactory(), trusted.trustManager) }
            .callTimeout(5, TimeUnit.SECONDS).build()

    private fun RecordedRequest.assertNoSecrets() {
        secrets.keys.forEach { assertNull("Leaked $it", getHeader(it)) }
    }
    private fun get(client: OkHttpClient, url: String, head: Boolean = false) {
        client.newCall(Request.Builder().url(url).apply { if (head) head() }.header("Range", "bytes=0-3").build())
            .execute().use { assertEquals(200, it.code); if (!head) assertEquals("data", it.body!!.string()) }
    }

    @Test fun systemTrustRejectsAnUntrustedServerWithoutRetry() {
        server(leaf()).use { s ->
            s.enqueue(MockResponse().setBody("data"))
            assertThrows(IOException::class.java) { get(client(s.url("/").toString()), s.url("/").toString()) }
            assertEquals(0, s.requestCount)
        }
    }
    @Test fun trustedCertificateAndSameOriginCredentialsWork() {
        server(leaf()).use { s ->
            s.enqueue(MockResponse().setBody("data"))
            get(client(s.url("/").toString(), trustFixture = true), s.url("/").toString())
            val request=s.takeRequest(); secrets.forEach { (k,v) -> assertEquals(v, request.getHeader(k)) }
            assertEquals("bytes=0-3", request.getHeader("Range"))
        }
    }
    @Test fun aTrustedCaDoesNotPermitAWrongHostname() {
        server(leaf(wrongHost=true)).use { s ->
            s.enqueue(MockResponse().setBody("data"))
            assertThrows(IOException::class.java) { get(client(s.url("/").toString(), trustFixture=true), s.url("/").toString()) }
            assertEquals(0, s.requestCount)
        }
    }
    @Test fun aTrustedCaDoesNotPermitAnExpiredLeaf() {
        server(leaf(expired=true)).use { s ->
            s.enqueue(MockResponse().setBody("data"))
            assertThrows(IOException::class.java) { get(client(s.url("/").toString(), trustFixture=true), s.url("/").toString()) }
            assertEquals(0, s.requestCount)
        }
    }
    @Test fun sameOriginGetAndHeadRedirectsRetainHeadersAndRanges() {
        for (code in listOf(301,302,303,307,308)) for (head in listOf(false,true)) server().use { s ->
            s.enqueue(MockResponse().setResponseCode(code).addHeader("Location", "/final"))
            s.enqueue(MockResponse().setBody(if (head) "" else "data"))
            get(client(s.url("/").toString()), s.url("/").toString(), head)
            repeat(2) {
                val r=s.takeRequest(); secrets.forEach { (k,v) -> assertEquals(v,r.getHeader(k)) }
                assertEquals("bytes=0-3",r.getHeader("Range"));assertEquals(if(head) "HEAD" else "GET",r.method)
            }
        }
    }
    @Test fun crossHostAndCrossPortRedirectsStripAllProviderHeaders() {
        for (code in listOf(301,302,303,307,308)) for (otherHost in listOf(false,true)) server().use { a -> server().use { b ->
            val target=b.url("/final").newBuilder().apply { if(otherHost) host("127.0.0.1") }.build()
            a.enqueue(MockResponse().setResponseCode(code).addHeader("Location",target))
            b.enqueue(MockResponse().setBody("data"))
            get(client(a.url("/").toString()),a.url("/").toString())
            assertEquals("Bearer test-only",a.takeRequest().getHeader("Authorization"))
            val final=b.takeRequest();final.assertNoSecrets();assertEquals("bytes=0-3",final.getHeader("Range"))
        } }
    }
    @Test fun redirectAwayAndBackDoesNotRestoreStrippedSecrets() {
        server().use { a -> server().use { b ->
            a.enqueue(MockResponse().setResponseCode(302).addHeader("Location",b.url("/middle")))
            b.enqueue(MockResponse().setResponseCode(302).addHeader("Location",a.url("/final")))
            a.enqueue(MockResponse().setBody("data"))
            val scoped = client(a.url("/").toString())
            get(scoped,a.url("/").toString())
            a.takeRequest();b.takeRequest().assertNoSecrets();a.takeRequest().assertNoSecrets()
            // The completed redirect chain must not strip a later independent same-origin call.
            a.enqueue(MockResponse().setBody("data"));get(scoped,a.url("/new-call").toString())
            val independent = a.takeRequest()
            secrets.forEach { (key,value) -> assertEquals(value,independent.getHeader(key)) }
        } }
    }
    @Test fun directAdaptiveChildrenCannotInheritTheManifestCredentialsOnAnotherOrigin() {
        server().use { a -> server().use { b ->
            val scoped=client(a.url("/manifest.m3u8").toString())
            for(path in listOf("/segment.ts","/video.m4s","/subtitles.vtt")) {
                b.enqueue(MockResponse().setBody("data"));get(scoped,b.url(path).toString())
                b.takeRequest().assertNoSecrets()
            }
            a.enqueue(MockResponse().setBody("data"));get(scoped,a.url("/local-segment.ts").toString())
            assertEquals("Bearer test-only",a.takeRequest().getHeader("Authorization"))
        } }
    }
    @Test fun explicitSubtitleCredentialsBelongOnlyToThatResourceOrigin() {
        server().use { a -> server().use { b -> server().use { c ->
            val sub=b.url("/subtitle.vtt")
            val scoped=OmniaHttpSecurity.scope(PlayerPlaybackNetworking.playbackHttpClient.newBuilder(),a.url("/video").toString(),secrets,
                mapOf(sub.toString() to mapOf("X-Subtitle-Key" to "subtitle-test"))).build()
            b.enqueue(MockResponse().setResponseCode(302).addHeader("Location",c.url("/final")))
            c.enqueue(MockResponse().setBody("data"));get(scoped,sub.toString())
            val first=b.takeRequest();first.assertNoSecrets();assertEquals("subtitle-test",first.getHeader("X-Subtitle-Key"))
            val final=c.takeRequest();final.assertNoSecrets();assertNull(final.getHeader("X-Subtitle-Key"))
        } } }
    }
    @Test fun httpsDowngradeMakesNoRequestToTheHttpTarget() {
        server(leaf()).use { a -> server().use { b ->
            a.enqueue(MockResponse().setResponseCode(302).addHeader("Location",b.url("/insecure")))
            b.enqueue(MockResponse().setBody("data"))
            assertThrows(IOException::class.java) { get(client(a.url("/").toString(),trustFixture=true),a.url("/").toString()) }
            assertEquals(1,a.requestCount);assertEquals(0,b.requestCount)
        } }
    }
    @Test fun directHttpChildOfHttpsManifestIsRejected() {
        server(leaf()).use { a -> server().use { b ->
            b.enqueue(MockResponse().setBody("data"))
            assertThrows(IOException::class.java) { get(client(a.url("/manifest.mpd").toString(),trustFixture=true),b.url("/segment").toString()) }
            assertEquals(0,b.requestCount)
        } }
    }
    @Test fun credentialHeadersRequireAnExplicitSourceOrigin() {
        assertThrows(IllegalArgumentException::class.java) { PlayerPlaybackNetworking.createHttpClient(secrets) }
    }
    @Test fun rawBaseClientAlsoProtectsRedirectHeaders() {
        server().use { a -> server().use { b ->
            a.enqueue(MockResponse().setResponseCode(302).addHeader("Location",b.url("/final")))
            b.enqueue(MockResponse().setBody("data"))
            val request=Request.Builder().url(a.url("/")).apply { secrets.forEach { (k,v)->header(k,v) } }.build()
            PlayerPlaybackNetworking.playbackHttpClient.newCall(request).execute().use { assertEquals(200,it.code) }
            b.takeRequest().assertNoSecrets()
        } }
    }
    @Test fun urlConnectionSameOriginHeadAndCrossOriginGetAreScoped() {
        server().use { a -> server().use { b ->
            a.enqueue(MockResponse().setResponseCode(307).addHeader("Location","/head"));a.enqueue(MockResponse())
            PlayerPlaybackNetworking.openConnection(a.url("/").toString(),secrets,"HEAD",3000,3000,"bytes=0-3").disconnect()
            repeat(2) { val r=a.takeRequest();assertEquals("HEAD",r.method);assertEquals("Bearer test-only",r.getHeader("Authorization")) }
            a.enqueue(MockResponse().setResponseCode(308).addHeader("Location",b.url("/final")));b.enqueue(MockResponse().setBody("data"))
            val connection=PlayerPlaybackNetworking.openConnection(a.url("/").toString(),secrets,"GET",3000,3000,"bytes=0-3")
            try { assertEquals("data",connection.inputStream.bufferedReader().readText()) } finally { connection.disconnect() }
            val final=b.takeRequest();final.assertNoSecrets();assertEquals("bytes=0-3",final.getHeader("Range"))
        } }
    }
    @Test fun urlConnectionRejectsUntrustedTls() {
        server(leaf()).use { s ->
            s.enqueue(MockResponse())
            assertThrows(IOException::class.java) { PlayerPlaybackNetworking.openConnection(s.url("/").toString(),secrets,"GET",3000,3000) }
            assertEquals(0,s.requestCount)
        }
    }
    @Test fun urlConnectionValidatesCertificateAndRejectsDowngrade() {
        val previous=HttpsURLConnection.getDefaultSSLSocketFactory()
        try {
            HttpsURLConnection.setDefaultSSLSocketFactory(trusted.sslSocketFactory())
            for(certificate in listOf(leaf(wrongHost=true),leaf(expired=true))) server(certificate).use { s ->
                s.enqueue(MockResponse())
                assertThrows(IOException::class.java) { PlayerPlaybackNetworking.openConnection(s.url("/").toString(),secrets,"HEAD",3000,3000) }
                assertEquals(0,s.requestCount)
            }
            server(leaf()).use { a -> server().use { b ->
                a.enqueue(MockResponse());PlayerPlaybackNetworking.openConnection(a.url("/valid").toString(),secrets,"HEAD",3000,3000).disconnect()
                assertEquals("Bearer test-only",a.takeRequest().getHeader("Authorization"))
                a.enqueue(MockResponse().setResponseCode(302).addHeader("Location",b.url("/insecure")));b.enqueue(MockResponse())
                assertThrows(IOException::class.java) { PlayerPlaybackNetworking.openConnection(a.url("/").toString(),secrets,"GET",3000,3000) }
                assertEquals(0,b.requestCount)
            } }
        } finally { HttpsURLConnection.setDefaultSSLSocketFactory(previous) }
    }
}

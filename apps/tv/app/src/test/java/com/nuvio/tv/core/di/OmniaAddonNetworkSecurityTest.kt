package com.nuvio.tv.core.di

import android.content.Context
import io.mockk.every
import io.mockk.mockk
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException
import java.nio.file.Files

class OmniaAddonNetworkSecurityTest {
    @Test fun addonClientRejectsUntrustedTlsAndOnlyRetiresThePermissiveCache() {
        val directory=Files.createTempDirectory("omnia-addon-cache-test").toFile()
        val context=mockk<Context>();every { context.cacheDir } returns directory
        directory.resolve("addon_http_cache").mkdir()
        directory.resolve("addon_http_cache/old-response").writeText("unvalidated fixture")
        directory.resolve("account-preserved").writeText("fixture")
        val client=NetworkModule.provideAddonValidatedOkHttpClient(context,OkHttpClient())
        try {
            assertFalse(directory.resolve("addon_http_cache").exists())
            assertEquals("fixture",directory.resolve("account-preserved").readText())
            assertEquals("addon_http_cache_validated_v1",client.cache!!.directory.name)
            val leaf=HeldCertificate.Builder().commonName("localhost").addSubjectAlternativeName("localhost").build()
            MockWebServer().use { s ->
                s.useHttps(HandshakeCertificates.Builder().heldCertificate(leaf).build().sslSocketFactory(),false);s.start()
                s.enqueue(MockResponse().setBody("{\"id\":\"test\"}"))
                assertThrows(IOException::class.java) { client.newCall(Request.Builder().url(s.url("/manifest.json")).build()).execute().close() }
                assertEquals(0,s.requestCount)
            }
        } finally { client.cache!!.close();directory.deleteRecursively() }
    }
}

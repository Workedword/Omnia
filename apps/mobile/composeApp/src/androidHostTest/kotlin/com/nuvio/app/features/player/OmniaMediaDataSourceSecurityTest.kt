package com.nuvio.app.features.player

import android.net.Uri
import androidx.media3.datasource.DataSpec
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class OmniaMediaDataSourceSecurityTest {
    @Test fun actualMedia3FactoryDoesNotForwardManifestHeadersToIndependentCdnChildren() {
        MockWebServer().use { origin -> MockWebServer().use { cdn ->
            origin.start();cdn.start()
            val factory=PlayerPlaybackNetworking.createHttpDataSourceFactory(
                mapOf("Authorization" to "Bearer test", "Cookie" to "test=private", "X-Custom-Key" to "test"),
                sourceUrl=origin.url("/manifest.mpd").toString(),
            )
            for(path in listOf("/segment.m4s", "/subtitle.vtt")) {
                cdn.enqueue(MockResponse().setBody("fixture"))
                val ds=factory.createDataSource()
                try {
                    ds.open(DataSpec.Builder().setUri(Uri.parse(cdn.url(path).toString())).build())
                    assertTrue(ds.read(ByteArray(64),0,64)>0)
                } finally { ds.close() }
                val request=cdn.takeRequest()
                for(header in listOf("Authorization","Cookie","X-Custom-Key")) assertNull(request.getHeader(header))
            }
            origin.enqueue(MockResponse().setResponseCode(206).addHeader("Content-Range","bytes 1-3/7").setBody("ixt"))
            val ds=factory.createDataSource()
            try { ds.open(DataSpec.Builder().setUri(Uri.parse(origin.url("/local.m4s").toString())).setPosition(1).setLength(3).build())
                val buffer=ByteArray(3);assertEquals(3,ds.read(buffer,0,3));assertEquals("ixt",String(buffer))
            } finally { ds.close() }
            val local=origin.takeRequest();assertEquals("bytes=1-3",local.getHeader("Range"));assertEquals("Bearer test",local.getHeader("Authorization"))
        } }
    }

    @Test fun separateSubtitleCredentialsReplaceStreamDefaultsInTheRealFactory() {
        MockWebServer().use { origin -> MockWebServer().use { subtitles ->
            origin.start();subtitles.start()
            val subtitleUrl=subtitles.url("/own.vtt").toString()
            val factory=PlayerPlaybackNetworking.createHttpDataSourceFactory(
                mapOf("Authorization" to "Bearer stream-test", "X-Stream-Key" to "stream-test"),
                sourceUrl=origin.url("/video").toString(),
                resourceHeaders=mapOf(subtitleUrl to mapOf("Authorization" to "Bearer subtitle-test")),
            )
            subtitles.enqueue(MockResponse().setBody("WEBVTT"))
            val ds=factory.createDataSource()
            try { ds.open(DataSpec(Uri.parse(subtitleUrl)));assertTrue(ds.read(ByteArray(64),0,64)>0) } finally { ds.close() }
            val request=subtitles.takeRequest();assertEquals("Bearer subtitle-test",request.getHeader("Authorization"));assertNull(request.getHeader("X-Stream-Key"))
        } }
    }
}

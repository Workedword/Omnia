package com.nuvio.tv.ui.screens.player

import okhttp3.OkHttpClient
import org.junit.Assert.*
import org.junit.Test

class PlaybackNetworkingSslVerificationTest {
    @Test fun playbackUsesThePlatformHostnameVerifierAndTrustManager() {
        val normal=OkHttpClient()
        val playback=PlayerPlaybackNetworking.playbackHttpClient
        assertSame(normal.hostnameVerifier, playback.hostnameVerifier)
        assertNotNull(normal.x509TrustManager)
        assertNotNull(playback.x509TrustManager)
        assertEquals(normal.x509TrustManager!!::class.java,playback.x509TrustManager!!::class.java)
        assertEquals(15000,playback.connectTimeoutMillis)
        assertEquals(15000,playback.readTimeoutMillis)
        assertTrue(playback.retryOnConnectionFailure)
    }
}

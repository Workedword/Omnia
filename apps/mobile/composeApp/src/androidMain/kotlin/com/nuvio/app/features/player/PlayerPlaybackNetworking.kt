package com.nuvio.app.features.player

import android.content.Context
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import com.nuvio.app.core.diagnostics.SentryNetworkBreadcrumbInterceptor
import com.nuvio.app.core.network.IPv4FirstDns
import com.nuvio.app.core.network.OmniaHttpSecurity
import okhttp3.OkHttpClient
import java.net.HttpURLConnection
import java.util.concurrent.TimeUnit

internal object PlayerPlaybackNetworking {
    internal const val DEFAULT_USER_AGENT =
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

    private val DEFAULT_STREAM_HEADERS = mapOf(
        "User-Agent" to DEFAULT_USER_AGENT,
    )

    internal val playbackHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .dns(IPv4FirstDns())
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .followRedirects(true)
            .followSslRedirects(true)
            .retryOnConnectionFailure(true)
            .addInterceptor(SentryNetworkBreadcrumbInterceptor())
            .let(OmniaHttpSecurity::protect)
            .build()
    }

    private val loopbackPlaybackHttpClient: OkHttpClient by lazy {
        playbackHttpClient.newBuilder()
            .addInterceptor { chain ->
                val request = chain.request()
                val requestChain = if (isLoopbackHost(request.url.host)) {
                    chain.withReadTimeout(65, TimeUnit.SECONDS)
                } else {
                    chain
                }
                requestChain.proceed(request)
            }
            .build()
    }

    fun createHttpClient(
        defaultHeaders: Map<String, String> = emptyMap(),
        useLongReadTimeout: Boolean = false,
        sourceUrl: String? = null,
        resourceHeaders: Map<String, Map<String, String>> = emptyMap(),
    ): OkHttpClient {
        val base = if (useLongReadTimeout) loopbackPlaybackHttpClient else playbackHttpClient
        return OmniaHttpSecurity.scope(base.newBuilder(), sourceUrl, sanitizeHeaders(defaultHeaders), resourceHeaders).build()
    }

    fun createHttpDataSourceFactory(
        defaultHeaders: Map<String, String> = emptyMap(),
        useLongReadTimeout: Boolean = false,
        sourceUrl: String? = null,
        resourceHeaders: Map<String, Map<String, String>> = emptyMap(),
    ): DataSource.Factory {
        val requestHeaders = sanitizeHeaders(defaultHeaders)
        val client = createHttpClient(requestHeaders, useLongReadTimeout, sourceUrl, resourceHeaders)

        return OkHttpDataSource.Factory(client).apply {
            setDefaultRequestProperties(requestHeaders)
            if (requestHeaders.headerValue("User-Agent") == null) {
                setUserAgent(DEFAULT_USER_AGENT)
            }
        }
    }

    fun createDataSourceFactory(
        context: Context,
        defaultHeaders: Map<String, String> = emptyMap(),
        useLongReadTimeout: Boolean = false,
        sourceUrl: String? = null,
        resourceHeaders: Map<String, Map<String, String>> = emptyMap(),
    ): DataSource.Factory {
        return DefaultDataSource.Factory(
            context,
            createHttpDataSourceFactory(defaultHeaders, useLongReadTimeout, sourceUrl, resourceHeaders),
        )
    }

    fun openConnection(
        url: String,
        headers: Map<String, String>,
        method: String,
        connectTimeoutMs: Int,
        readTimeoutMs: Int,
        range: String? = null,
    ): HttpURLConnection {
        val merged = headers.toMutableMap()
        if (merged.keys.none { it.equals("User-Agent", true) }) merged["User-Agent"] = DEFAULT_USER_AGENT
        return OmniaHttpSecurity.openConnection(url, merged, method, connectTimeoutMs, readTimeoutMs, range)
    }

    private fun sanitizeHeaders(headers: Map<String, String>): Map<String, String> =
        headers.mapNotNull { (rawKey, rawValue) ->
            val key = rawKey.trim()
            val value = rawValue.trim()
            if (key.isBlank() || value.isBlank() || key.equals("Range", ignoreCase = true)) {
                null
            } else {
                key to value
            }
        }.toMap()

    private fun isLoopbackHost(host: String): Boolean = when (host.lowercase()) {
        "127.0.0.1", "localhost", "::1" -> true
        else -> false
    }

    private fun withDefaultUserAgent(headers: Map<String, String>): Map<String, String> {
        val sanitized = sanitizeHeaders(headers)
        if (sanitized.headerValue("User-Agent") != null) return sanitized
        return DEFAULT_STREAM_HEADERS + sanitized
    }

    private fun Map<String, String>.headerValue(name: String): String? =
        entries.firstOrNull { (key, _) -> key.equals(name, ignoreCase = true) }?.value
}

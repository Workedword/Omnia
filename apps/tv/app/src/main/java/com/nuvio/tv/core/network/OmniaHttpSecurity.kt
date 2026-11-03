package com.nuvio.tv.core.network

import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.HttpURLConnection
import java.net.ProtocolException
import java.net.URL
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean

/** Each call owns its scope; redirects and adaptive-media children never acquire another scope. */
internal object OmniaHttpSecurity {
    private class Scope(val origin: HttpUrl) {
        // OkHttp builds follow-ups from its earlier request, not the network interceptor's
        // stripped copy. Remember crossing an origin for the lifetime of this call.
        val crossedOrigin = AtomicBoolean(false)
    }

    // Provider credentials may use arbitrary names. Only transport headers can cross origins.
    private val transportHeaders = setOf(
        "host", "user-agent", "accept", "accept-encoding", "accept-language", "range",
        "connection", "content-length", "content-type", "if-range", "icy-metadata"
    )

    fun sameOrigin(a: HttpUrl, b: HttpUrl): Boolean =
        a.scheme == b.scheme && a.host == b.host && a.port == b.port

    private fun checkDowngrade(from: HttpUrl, to: HttpUrl) {
        if (from.isHttps && !to.isHttps) {
            // Do not include provider URLs or tokens in the exception or diagnostic logs.
            throw ProtocolException("An HTTPS media request cannot redirect to HTTP")
        }
    }

    private fun Request.withTransportHeadersOnly(): Request = newBuilder().apply {
        headers.names().filter { it.lowercase(Locale.ROOT) !in transportHeaders }
            .forEach(::removeHeader)
    }.build()

    /** Install once on the base client, including callers that construct requests directly. */
    fun protect(builder: OkHttpClient.Builder): OkHttpClient.Builder = builder
        .addInterceptor { chain ->
            val request = chain.request()
            // A cloned/reused Request must not share mutable scope with another call.
            val scoped = request.newBuilder().tag(Scope::class.java, Scope(request.url)).build()
            chain.proceed(scoped)
        }
        .addNetworkInterceptor { chain ->
            val request = chain.request()
            val scope = request.tag(Scope::class.java)
                ?: throw ProtocolException("Missing media request origin")
            checkDowngrade(scope.origin, request.url)
            if (!sameOrigin(scope.origin, request.url)) scope.crossedOrigin.set(true)
            val outgoing = if (scope.crossedOrigin.get()) request.withTransportHeadersOnly() else request
            val response = chain.proceed(outgoing)
            if (response.isRedirect) {
                val target = response.header("Location")?.let(request.url::resolve)
                try {
                    if (target != null) checkDowngrade(request.url, target)
                } catch (error: ProtocolException) {
                    response.close()
                    throw error
                }
            }
            response
        }

    /**
     * Use the configured stream URL, not the URL of each HLS/DASH child, as the credential origin.
     * A separately configured subtitle may have its own headers. Match its complete initial URL
     * and discard stream headers before adding those credentials; never authorize an entire CDN.
     */
    fun scope(
        builder: OkHttpClient.Builder,
        sourceUrl: String?,
        headers: Map<String, String>,
        resourceHeaders: Map<String, Map<String, String>> = emptyMap(),
    ): OkHttpClient.Builder {
        require(sourceUrl != null || headers.isEmpty()) { "Media headers require a source URL" }
        val origin = sourceUrl?.toHttpUrlOrNull()
        require(origin != null || headers.isEmpty()) { "Media headers require an HTTP source URL" }
        val resources = resourceHeaders.mapKeys { it.key.toHttpUrl() }
        return builder.addInterceptor { chain ->
            val request = chain.request()
            val own = resources[request.url]
            val requestOrigin = if (own != null) request.url else origin ?: request.url
            checkDowngrade(requestOrigin, request.url)
            val selectedHeaders = own ?: headers
            val initial = if (own != null || !sameOrigin(requestOrigin, request.url)) {
                request.withTransportHeadersOnly()
            } else request
            val outgoing = initial.newBuilder().tag(Scope::class.java, Scope(requestOrigin)).apply {
                if (sameOrigin(requestOrigin, request.url)) selectedHeaders.forEach { (key, value) ->
                    if (key.lowercase(Locale.ROOT) !in setOf("range", "host", "connection", "content-length", "transfer-encoding")) header(key, value)
                }
            }.build()
            chain.proceed(outgoing)
        }
    }

    /** GET/HEAD probe helper; returns the connected final response with platform TLS validation. */
    fun openConnection(
        url: String,
        headers: Map<String, String>,
        method: String,
        connectTimeoutMs: Int,
        readTimeoutMs: Int,
        range: String?,
    ): HttpURLConnection {
        require(method == "GET" || method == "HEAD") { "Media probes support GET or HEAD" }
        val origin = url.toHttpUrl()
        var target = origin
        var forwarded = headers
        repeat(11) { hop ->
            checkDowngrade(origin, target)
            if (!sameOrigin(origin, target)) {
                forwarded = forwarded.filterKeys { it.lowercase(Locale.ROOT) in transportHeaders }
            }
            val connection = URL(target.toString()).openConnection() as HttpURLConnection
            try {
                connection.instanceFollowRedirects = false
                connection.connectTimeout = connectTimeoutMs
                connection.readTimeout = readTimeoutMs
                connection.requestMethod = method
                forwarded.forEach { (key, value) ->
                    if (!key.equals("Range", true)) connection.setRequestProperty(key, value)
                }
                range?.let { connection.setRequestProperty("Range", it) }
                val code = connection.responseCode
                val location = connection.getHeaderField("Location")
                if (code !in setOf(301, 302, 303, 307, 308) || location == null) return connection
                if (hop == 10) throw ProtocolException("Too many media redirects")
                val next = target.resolve(location) ?: throw ProtocolException("Invalid media redirect")
                checkDowngrade(target, next)
                connection.disconnect()
                target = next
            } catch (error: Exception) {
                connection.disconnect()
                throw error
            }
        }
        throw ProtocolException("Too many media redirects")
    }
}

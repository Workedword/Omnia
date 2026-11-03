package com.nuvio.app.features.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import coil3.SingletonImageLoader
import coil3.compose.LocalPlatformContext
import com.nuvio.app.features.addons.RawHttpResponse
import com.nuvio.app.features.addons.httpRequestRaw
import com.nuvio.app.features.addons.omniaDefaultAddonUrls
import com.nuvio.app.features.streams.BadgeImageLoader
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.jsonObject
import kotlin.time.TimeSource

internal data class OmniaConnectionResult(val name: String, val passed: Boolean, val detail: String)

/** Small, anonymous requests only; no stream URLs, login tokens or speed-test downloads. */
internal suspend fun checkOmniaConnections(
    request: suspend (String) -> RawHttpResponse = { url ->
        httpRequestRaw("GET", url, mapOf("Cache-Control" to "no-cache"), "",
            followRedirects = false, maxResponseBodyBytes = 64 * 1024)
    },
): List<OmniaConnectionResult> = listOf(
    "Internet connection" to "https://www.gstatic.com/generate_204",
    "Omnia Catalog" to omniaDefaultAddonUrls.first(),
).mapIndexed { index, (name, url) ->
    val started = TimeSource.Monotonic.markNow()
    try {
        val response = withTimeoutOrNull(6_000) { request(url) }
        val valid = response != null && if (index == 0) response.status == 204 else
            response.status == 200 && runCatching {
                Json.parseToJsonElement(response.body).jsonObject["catalogs"] is JsonArray
            }.getOrDefault(false)
        val detail = when {
            response == null -> "Timed out — try again"
            valid -> "Connected · ${started.elapsedNow().inWholeMilliseconds} ms"
            response.status in 300..399 -> "Redirected — check Wi-Fi sign-in or VPN"
            response.status !in 200..299 -> "Server returned HTTP ${response.status}"
            else -> "Unexpected response — check Wi-Fi sign-in or provider status"
        }
        OmniaConnectionResult(name, valid, detail)
    } catch (error: CancellationException) {
        throw error
    } catch (_: Exception) {
        OmniaConnectionResult(name, false, "Could not connect securely — check your connection and try again")
    }
}

@Composable
internal fun OmniaConnectionTools(isTablet: Boolean) {
    val scope = rememberCoroutineScope()
    var checking by remember { mutableStateOf(false) }
    var results by remember { mutableStateOf<List<OmniaConnectionResult>>(emptyList()) }
    SettingsSection(title = "Connection checks", isTablet = isTablet) {
        SettingsGroup(isTablet = isTablet) {
            SettingsNavigationRow(
                title = if (checking) "Checking connections…" else "Check connection",
                description = "Check internet and catalog response time using small requests. Runs only when selected.",
                enabled = !checking, isTablet = isTablet,
                onClick = {
                    scope.launch {
                        checking = true
                        results = emptyList()
                        try { results = checkOmniaConnections() } finally { checking = false }
                    }
                },
            )
            if (results.isNotEmpty()) Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                results.forEach {
                    Text(it.name, style = MaterialTheme.typography.titleSmall)
                    Text(it.detail, style = MaterialTheme.typography.bodySmall,
                        color = if (it.passed) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.error)
                }
                Text("These checks do not measure maximum download speed or test playback-provider credentials.",
                    style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
internal fun OmniaArtworkCacheAction(isTablet: Boolean) {
    val context = LocalPlatformContext.current
    val scope = rememberCoroutineScope()
    var confirm by remember { mutableStateOf(false) }
    var clearing by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<String?>(null) }
    SettingsNavigationRow(
        title = if (clearing) "Clearing artwork cache…" else "Clear artwork cache",
        description = result ?: "Remove cached posters, backdrops and badges. Your account, settings and watch history stay saved.",
        enabled = !clearing, isTablet = isTablet, onClick = { confirm = true },
    )
    if (confirm) AlertDialog(
        onDismissRequest = { confirm = false },
        title = { Text("Clear artwork cache?") },
        text = { Text("Artwork downloads again when needed. This keeps your login, add-ons, settings, downloads and watch history.") },
        dismissButton = { TextButton(onClick = { confirm = false }) { Text("Cancel") } },
        confirmButton = { TextButton(onClick = {
            confirm = false
            scope.launch {
                clearing = true
                try {
                    val loader = SingletonImageLoader.get(context)
                    loader.memoryCache?.clear()
                    BadgeImageLoader.get(context).memoryCache?.clear()
                    withContext(Dispatchers.Default) { loader.diskCache?.clear() }
                    result = "Artwork cache cleared. New images may begin caching as you browse."
                } catch (error: CancellationException) { throw error }
                catch (_: Exception) { result = "Could not clear every cached image. Try again when playback has stopped." }
                finally { clearing = false }
            }
        }) { Text("Clear cache") } },
    )
}

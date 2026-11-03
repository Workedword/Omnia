package com.nuvio.tv.ui.screens.addon

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import javax.inject.Inject

data class DiscoverAddon(
    val id: String,
    val name: String,
    val description: String,
    val manifestUrl: String,
    val source: String,
    val resources: Set<String>,
    val configurable: Boolean,
    val configurationRequired: Boolean,
    val setupUrl: String? = null,
    val matchingIds: Set<String> = emptySet()
) {
    val baseUrl: String get() = manifestUrl.removeSuffix("/manifest.json")
    val configureUrl: String get() = setupUrl ?: "$baseUrl/configure"
}

object AddonDiscoveryParser {
    fun parse(json: String, source: String): List<DiscoverAddon> {
        val root = JsonParser.parseString(json)
        if (root.isJsonObject && root.asJsonObject.has("entries")) {
            return root.asJsonObject.getAsJsonArray("entries").mapNotNull { element ->
                runCatching {
                    val item=element.asJsonObject
                    val setup=item.text("url").toHttpUrlOrNull() ?: return@runCatching null
                    if (!setup.isHttps || setup.username.isNotEmpty() || setup.password.isNotEmpty()) return@runCatching null
                    val installable=item.get("installable")?.asBoolean==true
                    val manifest=item.text("manifestUrl").toHttpUrlOrNull()
                    if (installable && (manifest==null || !manifest.isHttps || manifest.username.isNotEmpty() || manifest.password.isNotEmpty() || manifest.query!=null || !manifest.encodedPath.endsWith("/manifest.json"))) return@runCatching null
                    val category=item.text("category")
                    DiscoverAddon("omnia-directory:"+item.text("name"),item.text("name"),item.text("description"),
                        if(installable) manifest.toString() else setup.toString(),OmniaDirectoryPolicy.publisher(item.text("publisher"),setup.toString()),
                        setOf(when(category){"Catalogs"->"catalog";"Collections"->"collection";"Live TV & Sports"->"live";else->"stream"}),true,!installable,setup.toString(),item.getAsJsonArray("addonIds")?.mapNotNull { it.takeIf { value -> value.isJsonPrimitive }?.asString }?.toSet().orEmpty())
                }.getOrNull()
            }
        }
        val entries = if (root.isJsonArray) root.asJsonArray else root.asJsonObject.getAsJsonArray("addons")
        return entries.mapNotNull { element ->
            runCatching {
                val entry = element.asJsonObject
                val manifest = entry.getAsJsonObject("manifest") ?: return@runCatching null
                val url = entry.text("transportUrl").toHttpUrlOrNull() ?: return@runCatching null
                // Catalog entries are public HTTPS services; local URLs stay available through manual install.
                if (!url.isHttps || url.username.isNotEmpty() || url.password.isNotEmpty() ||
                    url.query != null || url.fragment != null || !url.encodedPath.endsWith("/manifest.json") ||
                    url.host in setOf("localhost", "127.0.0.1", "::1")) return@runCatching null
                val id = manifest.text("id").takeIf { it.isNotBlank() } ?: return@runCatching null
                val name = manifest.text("name").takeIf { it.isNotBlank() } ?: return@runCatching null
                val hints = manifest.getAsJsonObject("behaviorHints")
                val resources = manifest.getAsJsonArray("resources")?.mapNotNull {
                    when {
                        it.isJsonPrimitive && it.asJsonPrimitive.isString -> it.asString.lowercase()
                        it.isJsonObject -> it.asJsonObject.text("name").lowercase()
                        else -> null
                    }
                }?.toSet().orEmpty()
                if (resources.intersect(setOf("catalog", "meta", "stream", "subtitle", "subtitles")).isEmpty()) return@runCatching null
                DiscoverAddon(id, name, manifest.text("description"), url.toString(), source, resources,
                    hints?.get("configurable")?.asBoolean == true,
                    hints?.get("configurationRequired")?.asBoolean == true)
            }.getOrNull()
        }.distinctBy { it.manifestUrl }
    }

    private fun JsonObject.text(key: String): String = get(key)?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
}

data class AddonDiscoveryState(
    val addons: List<DiscoverAddon> = emptyList(),
    val loading: Boolean = false,
    val failedSources: List<String> = emptyList()
)

@HiltViewModel
class AddonDiscoveryViewModel @Inject constructor(client: OkHttpClient) : ViewModel() {
    private val client = client.newBuilder().callTimeout(25, TimeUnit.SECONDS).build()
    private val _state = MutableStateFlow(AddonDiscoveryState())
    val state = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        if (_state.value.loading) return
        _state.value = _state.value.copy(loading = true, failedSources = emptyList())
        viewModelScope.launch {
            val results = coroutineScope {
                listOf(
                    "Omnia Community" to "https://omnia.161.97.128.244.sslip.io/catalogs/community.json",
                    "Community" to "https://raw.githubusercontent.com/Stremio/stremio-official-addons/master/index.json",
                    "Community" to "https://api.strem.io/addonscollection.json"
                ).map { (name, url) ->
                    async { name to load(url, name) }
                }.map { it.await() }
            }
            _state.value = AddonDiscoveryState(
                addons = results.flatMap { it.second.orEmpty() }.distinctBy { it.manifestUrl },
                failedSources = results.filter { it.second == null }.map { it.first }
            )
        }
    }

    private suspend fun load(url: String, source: String): List<DiscoverAddon>? = withContext(Dispatchers.IO) {
        try {
            client.newCall(Request.Builder().url(url).build()).execute().use { response ->
                if (!response.isSuccessful) return@withContext null
                val body = response.body ?: return@withContext null
                val limit = 8L * 1024 * 1024
                if (body.contentLength() > limit) return@withContext null
                val stream = body.source()
                stream.request(limit + 1)
                if (stream.buffer.size > limit) return@withContext null
                AddonDiscoveryParser.parse(stream.readUtf8(), source)
            }
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) { null }
    }
}

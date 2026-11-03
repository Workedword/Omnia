"""Apply Omnia catalog defaults and community discovery after prepare_omnia.py."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
ORIGIN='https://omnia.161.97.128.244.sslip.io'
DEFAULT='https://catalog.nuvio.tv/manifest.json'

# These two generated screens are owned by the overlay pipeline. Rebuild their
# baseline before applying ordered changes so repeated preparation is stable.
if not (ROOT/'composeApp').exists():
    import ast
    module=ast.parse((ROOT/'prepare_omnia.py').read_text(encoding='utf-8'))
    assignment=next(node for node in module.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sources' for t in node.targets))
    generated=ast.literal_eval(assignment.value)
    for relative in ('app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonDiscoveryScreen.kt',):
        (ROOT/relative).write_text(generated[relative],encoding='utf-8')

if not (ROOT/'composeApp').exists():
    (ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonDiscovery.kt').write_text('package com.nuvio.tv.ui.screens.addon\n\nimport androidx.lifecycle.ViewModel\nimport androidx.lifecycle.viewModelScope\nimport com.google.gson.JsonObject\nimport com.google.gson.JsonParser\nimport dagger.hilt.android.lifecycle.HiltViewModel\nimport kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.async\nimport kotlinx.coroutines.coroutineScope\nimport kotlinx.coroutines.flow.MutableStateFlow\nimport kotlinx.coroutines.flow.asStateFlow\nimport kotlinx.coroutines.launch\nimport kotlinx.coroutines.withContext\nimport okhttp3.HttpUrl.Companion.toHttpUrlOrNull\nimport okhttp3.OkHttpClient\nimport okhttp3.Request\nimport java.util.concurrent.TimeUnit\nimport javax.inject.Inject\n\ndata class DiscoverAddon(\n    val id: String,\n    val name: String,\n    val description: String,\n    val manifestUrl: String,\n    val source: String,\n    val resources: Set<String>,\n    val configurable: Boolean,\n    val configurationRequired: Boolean\n) {\n    val baseUrl: String get() = manifestUrl.removeSuffix("/manifest.json")\n    val configureUrl: String get() = "$baseUrl/configure"\n}\n\nobject AddonDiscoveryParser {\n    fun parse(json: String, source: String): List<DiscoverAddon> {\n        val root = JsonParser.parseString(json)\n        val entries = if (root.isJsonArray) root.asJsonArray else root.asJsonObject.getAsJsonArray("addons")\n        return entries.mapNotNull { element ->\n            runCatching {\n                val entry = element.asJsonObject\n                val manifest = entry.getAsJsonObject("manifest") ?: return@runCatching null\n                val url = entry.text("transportUrl").toHttpUrlOrNull() ?: return@runCatching null\n                // Catalog entries are public HTTPS services; local URLs stay available through manual install.\n                if (!url.isHttps || url.username.isNotEmpty() || url.password.isNotEmpty() ||\n                    url.query != null || url.fragment != null || !url.encodedPath.endsWith("/manifest.json") ||\n                    url.host in setOf("localhost", "127.0.0.1", "::1")) return@runCatching null\n                val id = manifest.text("id").takeIf { it.isNotBlank() } ?: return@runCatching null\n                val name = manifest.text("name").takeIf { it.isNotBlank() } ?: return@runCatching null\n                val hints = manifest.getAsJsonObject("behaviorHints")\n                val resources = manifest.getAsJsonArray("resources")?.mapNotNull {\n                    when {\n                        it.isJsonPrimitive && it.asJsonPrimitive.isString -> it.asString.lowercase()\n                        it.isJsonObject -> it.asJsonObject.text("name").lowercase()\n                        else -> null\n                    }\n                }?.toSet().orEmpty()\n                if (resources.intersect(setOf("catalog", "meta", "stream", "subtitle", "subtitles")).isEmpty()) return@runCatching null\n                DiscoverAddon(id, name, manifest.text("description"), url.toString(), source, resources,\n                    hints?.get("configurable")?.asBoolean == true,\n                    hints?.get("configurationRequired")?.asBoolean == true)\n            }.getOrNull()\n        }.distinctBy { it.manifestUrl }\n    }\n\n    private fun JsonObject.text(key: String): String = get(key)?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()\n}\n\ndata class AddonDiscoveryState(\n    val addons: List<DiscoverAddon> = emptyList(),\n    val loading: Boolean = false,\n    val failedSources: List<String> = emptyList()\n)\n\n@HiltViewModel\nclass AddonDiscoveryViewModel @Inject constructor(client: OkHttpClient) : ViewModel() {\n    private val client = client.newBuilder().callTimeout(25, TimeUnit.SECONDS).build()\n    private val _state = MutableStateFlow(AddonDiscoveryState())\n    val state = _state.asStateFlow()\n\n    init { refresh() }\n\n    fun refresh() {\n        if (_state.value.loading) return\n        _state.value = _state.value.copy(loading = true, failedSources = emptyList())\n        viewModelScope.launch {\n            val results = coroutineScope {\n                listOf(\n                    "Official" to "https://raw.githubusercontent.com/Stremio/stremio-official-addons/master/index.json",\n                    "Community" to "https://api.strem.io/addonscollection.json"\n                ).map { (name, url) ->\n                    async { name to load(url, name) }\n                }.map { it.await() }\n            }\n            _state.value = AddonDiscoveryState(\n                addons = results.flatMap { it.second.orEmpty() }.distinctBy { it.manifestUrl },\n                failedSources = results.filter { it.second == null }.map { it.first }\n            )\n        }\n    }\n\n    private suspend fun load(url: String, source: String): List<DiscoverAddon>? = withContext(Dispatchers.IO) {\n        try {\n            client.newCall(Request.Builder().url(url).build()).execute().use { response ->\n                if (!response.isSuccessful) return@withContext null\n                val body = response.body ?: return@withContext null\n                val limit = 8L * 1024 * 1024\n                if (body.contentLength() > limit) return@withContext null\n                val stream = body.source()\n                stream.request(limit + 1)\n                if (stream.buffer.size > limit) return@withContext null\n                AddonDiscoveryParser.parse(stream.readUtf8(), source)\n            }\n        } catch (cancelled: CancellationException) {\n            throw cancelled\n        } catch (_: Exception) { null }\n    }\n}\n',encoding='utf-8')


for relative,old,new in [
    ('app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonDiscoveryScreen.kt',
     'listOf("All types", "Subtitles", "Catalogs", "Collections", "Streams")',
     'listOf("All types", "Subtitles", "Catalogs", "Collections", "Streams", "Live TV & Sports")'),
    ('app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonDiscoveryScreen.kt',
     '"Collections" -> "collection" in addon.resources\n                    else',
     '"Collections" -> "collection" in addon.resources\n                    "Live TV & Sports" -> "live" in addon.resources\n                    else'),
    ('app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonDiscovery.kt',
     '"Collections"->"collection";else->"stream"',
     '"Collections"->"collection";"Live TV & Sports"->"live";else->"stream"'),
]:
    path=ROOT/relative
    if path.exists(): path.write_text(path.read_text(encoding='utf-8').replace(old,new),encoding='utf-8')

# Upgrade checkouts that already have the previous default overlay applied.
for relative in [
    'composeApp/src/androidMain/kotlin/com/nuvio/app/features/addons/AddonPlatform.android.kt',
    'composeApp/src/iosMain/kotlin/com/nuvio/app/features/addons/AddonPlatform.ios.kt',
    'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/AddonRepository.kt',
    'app/src/main/java/com/nuvio/tv/data/local/AddonPreferences.kt',
]:
    path=ROOT/relative
    if path.exists():
        text=path.read_text(encoding='utf-8')
        text=text.replace(ORIGIN+'/catalogs/manifest.json',DEFAULT)
        text=text.replace('"'+ORIGIN+'/catalogs"','"https://catalog.nuvio.tv"')
        text=text.replace('name = "Omnia Catalogs"','name = "Nuvio Catalog Addon"')
        path.write_text(text,encoding='utf-8')

def edit(relative,old,new):
    path=ROOT/relative
    text=path.read_text(encoding='utf-8')
    if new in text: return
    if relative.endswith("/AddonPreferences.kt") and old == '"https://v3-cinemeta.strem.io",' and '"https://omnia.161.97.128.244.sslip.io/catalogs/core/manifest.json",' in text: return
    if relative.endswith('/AddonRepository.kt') and 'private val syncMutex' in text and old == '            val urls = rowsByUrl.keys.toList()': return
    if old not in text: raise RuntimeError('Source changed: '+relative+' / '+old[:60])
    path.write_text(text.replace(old,new),encoding='utf-8')

if (ROOT/'composeApp').exists():
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=19\nMARKETING_VERSION=0.4.11\n',encoding='utf-8')
    base='composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/'
    path=ROOT/base/'AddonsScreen.kt'
    text=path.read_text(encoding='utf-8')
    if '        OmniaCommunityPanel()' not in text:
        if '        AddonHealthPanel(uiState.addons)' not in text: raise RuntimeError('Missing add-on overview insertion point')
        text=text.replace('        AddonHealthPanel(uiState.addons)','        OmniaCommunityPanel()')
    else:
        text=text.replace('        AddonHealthPanel(uiState.addons)\n','')
    path.write_text(text,encoding='utf-8')
    for target in ['android','ios']:
        path=f'composeApp/src/{target}Main/kotlin/com/nuvio/app/features/addons/AddonPlatform.{target}.kt'
        old='?.getString("${addonUrlsKey}_$profileId", null)' if target=='android' else '.stringForKey("${addonUrlsKey}_$profileId")'
        edit(path,old,old+'\n            ?: "'+DEFAULT+'"')
        # Parenthesize fallback so the existing lineSequence pipeline applies to either value.
        text=(ROOT/path).read_text(encoding='utf-8')
        start='actual fun loadInstalledAddonUrls(profileId: Int): List<String> =\n        '
        if start+'(' not in text:
            text=text.replace(start,start+'(',1).replace('?: "'+DEFAULT+'"','?: "'+DEFAULT+'")',1)
            (ROOT/path).write_text(text,encoding='utf-8')
    # Seed a genuinely new server profile, but preserve an explicitly empty saved list.
    edit(base+'AddonRepository.kt','            val urls = rowsByUrl.keys.toList()',
         '            if (rowsByUrl.isEmpty() && AddonStorage.loadInstalledAddonUrls(currentProfileId) == listOf("'+DEFAULT+'")) {\n                rowsByUrl["'+DEFAULT+'"] = AddonRow(url = "'+DEFAULT+'", name = "Nuvio Catalog Addon")\n            }\n            val urls = rowsByUrl.keys.toList()')
    (ROOT/base/'OmniaCommunityPanel.kt').write_text(r'''package com.nuvio.app.features.addons

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioSurfaceCard
import com.nuvio.app.core.ui.NuvioPrimaryButton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.serialization.json.*

@Composable
internal fun OmniaCommunityPanel() {
    val scope=rememberCoroutineScope()
    val uri=LocalUriHandler.current
    var entries by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var status by remember { mutableStateOf("Loading community add-ons…") }
    var busy by remember { mutableStateOf(false) }
    var expanded by remember { mutableStateOf(true) }
    var category by remember { mutableStateOf("All") }
    var attempt by remember { mutableStateOf(0) }
    LaunchedEffect(attempt) {
        try {
            val payload=fetchAddonResponseText("https://omnia.161.97.128.244.sslip.io/catalogs/community.json")
            entries=Json.parseToJsonElement(payload).jsonObject["entries"]!!.jsonArray.map { it.jsonObject }
            status="Choose an optional add-on. Configuration and platform support vary."
        } catch (cancelled:CancellationException) { throw cancelled }
        catch (_:Exception) { status="Community directory unavailable. Try again." }
    }
    fun JsonObject.text(key:String)=this[key]?.jsonPrimitive?.contentOrNull.orEmpty()
    NuvioSurfaceCard {
        Text("Community Add-ons",style=MaterialTheme.typography.titleLarge)
        Text(status)
        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            TextButton(onClick={expanded=!expanded}) { Text(if(expanded) "Hide directory" else "Browse add-ons") }
            TextButton(onClick={attempt++}) { Text("Refresh") }
        }
        if(expanded) {
            Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                TextButton(onClick={category=when(category){"All"->"Catalogs";"Catalogs"->"Collections";"Collections"->"Providers";"Providers"->"Live TV & Sports";else->"All"}}) { Text("Category: $category") }
            }
            entries.filter { category=="All" || it.text("category")==category }.forEach { entry ->
                HorizontalDivider()
                Text(entry.text("name"),style=MaterialTheme.typography.titleMedium)
                Text(entry.text("description"))
                Text(entry.text("status"),style=MaterialTheme.typography.bodySmall)
                val setup=entry.text("url")
                TextButton(onClick={if(setup.startsWith("https://")) runCatching { uri.openUri(setup) }}) { Text("Setup & details") }
                val manifest=entry.text("manifestUrl")
                if(entry["installable"]?.jsonPrimitive?.booleanOrNull==true && manifest.startsWith("https://")) {
                    NuvioPrimaryButton(text="Install ${entry.text("name")}",enabled=!busy,onClick={
                        busy=true
                        scope.launch {
                            try {
                                status=when(val result=AddonRepository.addAddon(manifest)) {
                                    is AddAddonResult.Success -> "Installed ${result.manifest.name}"
                                    is AddAddonResult.Error -> result.message
                                }
                            } finally { busy=false }
                        }
                    })
                }
                Spacer(Modifier.height(12.dp))
            }
        }
        TextButton(onClick={runCatching { uri.openUri("https://github.com/Workedword/Omnia/tree/main/addons") }}) { Text("Developer submissions") }
    }
}
''',encoding='utf-8')
else:
    version_path=ROOT/'app/build.gradle.kts'
    version_text=version_path.read_text(encoding='utf-8')
    version_text=re.sub(r'(?m)^(\s*versionCode\s*=\s*)\d+',r'\g<1>19',version_text,count=1)
    version_text=re.sub(r'(?m)^(\s*versionName\s*=\s*)"[^"]+"',r'\g<1>"0.3.13"',version_text,count=1)
    version_path.write_text(version_text,encoding='utf-8')
    base='app/src/main/java/com/nuvio/tv/'
    edit(base+'data/local/AddonPreferences.kt','"https://v3-cinemeta.strem.io",','"https://catalog.nuvio.tv",')
    path=base+'ui/screens/addon/AddonDiscovery.kt'
    edit(path,'    val configurationRequired: Boolean\n','    val configurationRequired: Boolean,\n    val setupUrl: String? = null\n')
    edit(path,'val configureUrl: String get() = "$baseUrl/configure"','val configureUrl: String get() = setupUrl ?: "$baseUrl/configure"')
    edit(path,'        val entries = if (root.isJsonArray)',r'''        if (root.isJsonObject && root.asJsonObject.has("entries")) {
            return root.asJsonObject.getAsJsonArray("entries").mapNotNull { element ->
                runCatching {
                    val item=element.asJsonObject
                    val setup=item.text("url").toHttpUrlOrNull() ?: return@runCatching null
                    if (!setup.isHttps || setup.username.isNotEmpty() || setup.password.isNotEmpty()) return@runCatching null
                    val installable=item.get("installable")?.asBoolean==true
                    val manifest=item.text("manifestUrl").toHttpUrlOrNull()
                    if (installable && (manifest==null || !manifest.isHttps || manifest.username.isNotEmpty() || manifest.password.isNotEmpty() || manifest.query!=null || !manifest.encodedPath.endsWith("/manifest.json"))) return@runCatching null
                    val category=item.text("category")
                    DiscoverAddon("omnia-directory:"+item.text("name"),item.text("name"),item.text("description")+" · "+item.text("status"),
                        if(installable) manifest.toString() else setup.toString(),"Community",
                        setOf(when(category){"Catalogs"->"catalog";"Collections"->"collection";"Live TV & Sports"->"live";else->"stream"}),true,!installable,setup.toString())
                }.getOrNull()
            }
        }
        val entries = if (root.isJsonArray)''')
    edit(path,'                    "Official" to ', '                    "Omnia Community" to "'+ORIGIN+'/catalogs/community.json",\n                    "Official" to ')
    screen=base+'ui/screens/addon/AddonDiscoveryScreen.kt'
    edit(screen,'"Catalogs" -> "catalog" in addon.resources','"Catalogs" -> "catalog" in addon.resources\n                    "Collections" -> "collection" in addon.resources\n                    "Live TV & Sports" -> "live" in addon.resources')
    edit(screen,'listOf("All types", "Subtitles", "Catalogs", "Streams")','listOf("All types", "Subtitles", "Catalogs", "Collections", "Streams", "Live TV & Sports")')
    edit(base+'ui/screens/addon/AddonManagerScreen.kt',
         '            if (!viewModel.isReadOnly && !isEssential && hasHomeVisibleCatalogs) {\n                item {\n                    CatalogOrderEntryCard(onClick = onNavigateToCatalogOrder)\n                }\n            }',
         '            // Home row selection is available only through Choose Home Catalogs.')
    test=ROOT/'app/src/test/java/com/nuvio/tv/ui/screens/addon/AddonDiscoveryParserTest.kt'
    text=test.read_text(encoding='utf-8')
    if 'sports setup remains visible without pretending it is installed' not in text:
        text=text.rstrip()[:-1]+r'''
    @Test fun `sports setup remains visible without pretending it is installed`() {
        val entries=AddonDiscoveryParser.parse("""{"entries":[{"name":"IPTV","category":"Live TV & Sports","url":"https://example.com/configure","installable":false}]}""", "Omnia Community")
        val entry=entries.single()
        assertEquals("IPTV",entry.name)
        assertTrue("live" in entry.resources)
        assertTrue(entry.configurationRequired)
        assertEquals("https://example.com/configure",entry.configureUrl)
    }
    @Test fun `directory requires a real manifest before direct installation`() {
        val entries=AddonDiscoveryParser.parse("""{"entries":[{"name":"Sports","category":"Live TV & Sports","url":"https://example.com/configure","manifestUrl":"https://example.com/configure","installable":true}]}""", "Omnia Community")
        assertTrue(entries.isEmpty())
    }
}
'''
        test.write_text(text,encoding='utf-8')
if (ROOT/'composeApp').exists():
    health=ROOT/'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/AddonHealthPanel.kt'
    text=health.read_text(encoding='utf-8')
    if 'internal fun OmniaAddonDiagnostics()' not in text:
        text+='''
@Composable
internal fun OmniaAddonDiagnostics() {
    val state by AddonRepository.uiState.collectAsState()
    LaunchedEffect(Unit) { AddonRepository.initialize() }
    AddonHealthPanel(state.addons)
}
'''
        health.write_text(text,encoding='utf-8')
    advanced='composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/AdvancedSettingsPage.kt'
    edit(advanced,') {\n    item {', ''') {
    item {
        SettingsSection(title = "Add-on diagnostics", isTablet = isTablet) {
            com.nuvio.app.features.addons.OmniaAddonDiagnostics()
        }
    }
    item {''')
    tests=ROOT/'prepare_omnia_ios_tests.py'
    text=tests.read_text(encoding='utf-8')
    marker='    @available(iOS 16.4, *)\n    func testAddonDeepLinksAndPlayback()'
    if 'func testCommunityDirectoryIsVisible()' not in text:
        if marker not in text: raise RuntimeError('iOS test insertion point changed')
        text=text.replace(marker,'''    func testCommunityDirectoryIsVisible() {
        enterGuest()
        openSettings()
        tap("Content & Discovery", scroll: true)
        tap("Catalogs & add-ons", scroll: true)
        XCTAssertTrue(item("Community Add-ons").waitForExistence(timeout: 20))
        XCTAssertTrue(item("Hide directory").exists)
        XCTAssertFalse(item("Check catalog endpoints").exists)
        tap("Category: All", scroll: true)
        tap("Category: Catalogs", scroll: true)
        tap("Category: Collections", scroll: true)
        tap("Category: Providers", scroll: true)
        XCTAssertTrue(item("IPTV").waitForExistence(timeout: 20))
        XCTAssertTrue(item("Sports Streams").exists)
        capture("community-live-tv-and-sports")
    }
''' + marker)
        tests.write_text(text,encoding='utf-8')
else:
    base='app/src/main/java/com/nuvio/tv/'
    edit(base+'ui/screens/addon/AddonManagerScreen.kt',
         '            item { AddonHealthPanel(uiState.installedAddons) }',
         '            // Provider diagnostics live in Advanced settings.')
    health=ROOT/base/'ui/screens/addon/AddonHealthPanel.kt'
    text=health.read_text(encoding='utf-8')
    text=text.replace('): ViewModel() {\n    suspend fun check', '): ViewModel() {\n    val installedAddons = addons.getInstalledAddons()\n    suspend fun check')
    if 'fun OmniaAddonDiagnostics(' not in text:
        text+='''
@Composable
fun OmniaAddonDiagnostics(viewModel: AddonHealthViewModel = hiltViewModel()) {
    val addons by viewModel.installedAddons.collectAsState(initial = emptyList())
    AddonHealthPanel(addons, viewModel)
}
'''
    health.write_text(text,encoding='utf-8')
    test=ROOT/'app/src/test/java/com/nuvio/tv/ui/screens/addon/OmniaAddonHealthTest.kt'
    text=test.read_text(encoding='utf-8')
    fixture='        val repo=mockk<AddonRepository>()'
    if 'every { repo.getInstalledAddons() }' not in text:
        text=text.replace(fixture,fixture+'\n        every { repo.getInstalledAddons() } returns kotlinx.coroutines.flow.flowOf(emptyList())')
        test.write_text(text,encoding='utf-8')
    edit(base+'ui/screens/settings/NetworkSettingsScreen.kt',
         '        item(key = "experience_mode_settings") {',
         '''        item(key = "addon_diagnostics") {
            com.nuvio.tv.ui.screens.addon.OmniaAddonDiagnostics()
        }
        item(key = "experience_mode_settings") {''')
if (ROOT/'app').exists():
    discovery='app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonDiscoveryScreen.kt'
    edit(discovery,'import androidx.compose.foundation.background', '''import android.view.KeyEvent
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.foundation.background''')
    edit(discovery,'    val backFocus = remember { FocusRequester() }', '''    val backFocus = remember { FocusRequester() }
    val directoryFiltersFocus = remember { FocusRequester() }
    val keyboardController = LocalSoftwareKeyboardController.current''')
    edit(discovery,'onValueChange = { query = it }, singleLine = true,', '''onValueChange = { query = it }, singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = {
                    keyboardController?.hide()
                    directoryFiltersFocus.requestFocus()
                }),''')
    edit(discovery,'modifier = Modifier.width(280.dp),', '''modifier = Modifier.width(280.dp).onPreviewKeyEvent { event ->
                    if (event.nativeKeyEvent.keyCode == KeyEvent.KEYCODE_DPAD_DOWN) {
                        if (event.nativeKeyEvent.action == KeyEvent.ACTION_DOWN) {
                            keyboardController?.hide()
                            directoryFiltersFocus.requestFocus()
                        }
                        true
                    } else false
                },''')
    edit(discovery,'Button(onClick = { source = option })', '''Button(onClick = { source = option },
                    modifier = if (option == "All") Modifier.focusRequester(directoryFiltersFocus) else Modifier)''')
    edit(discovery,'import androidx.compose.foundation.lazy.items', '''import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState''')
    edit(discovery,'    val keyboardController = LocalSoftwareKeyboardController.current', '''    val keyboardController = LocalSoftwareKeyboardController.current
    val directoryListState = rememberLazyListState()''')
    edit(discovery,'    LaunchedEffect(Unit) { backFocus.requestFocus() }', '''    LaunchedEffect(Unit) { backFocus.requestFocus() }
    LaunchedEffect(query, source, category) { directoryListState.scrollToItem(0) }''')
    edit(discovery,'LazyColumn(Modifier.weight(1f), verticalArrangement',
         'LazyColumn(Modifier.weight(1f), state = directoryListState, verticalArrangement')
if (ROOT/'app').exists():
    # Remove obsolete setup cards without changing installed add-ons or their defaults.
    manager=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonManagerScreen.kt'
    text=manager.read_text(encoding='utf-8')
    if '// Omnia compact add-on setup.' not in text:
        start=text.index('            if (!viewModel.isReadOnly) {\n                item(key = "omnia_subtitle_provider")')
        end=text.index('            // Home row selection is available only through Choose Home Catalogs.',start)
        text=text[:start]+'            // Omnia compact add-on setup. Installed subtitle add-ons remain below.\n\n'+text[end:]
        start=text.index('@OptIn(ExperimentalTvMaterial3Api::class)\n@Composable\nprivate fun ManageFromPhoneCard(')
        end=text.index('@OptIn(ExperimentalTvMaterial3Api::class)\n@Composable\nprivate fun CatalogOrderEntryCard(',start)
        text=text[:start]+text[end:]
        text=text.replace('    val manageFromPhoneFocusRequester = remember { FocusRequester() }\n','')
        text=text.replace('    var restoreManageFromPhoneFocus by remember { mutableStateOf(false) }\n','')
        start=text.index('    val manageFromPhoneSubtitle = if (webConfigMode')
        end=text.index('    val qrInstruction = if (webConfigMode',start)
        text=text[:start]+text[end:]
        start=text.index('    val requestManageFromPhoneFocus = {')
        end=text.index('    LaunchedEffect(uiState.isQrModeActive',start)
        text=text[:start]+text[end:]
        text=text.replace('        if (uiState.isQrModeActive) {\n            restoreManageFromPhoneFocus = true\n        }\n','')
        text,count=re.subn(r'(?m)^( +)if \(restoreManageFromPhoneFocus\) \{\n *requestManageFromPhoneFocus\(\)\n *\} else \{\n *requestInputBarFocus\(\)\n *\}',r'\1requestInputBarFocus()',text)
        if count!=2: raise RuntimeError('Unexpected add-on focus restoration structure')
        if 'ManageFromPhone' in text: raise RuntimeError('Removed focus target still referenced')
        manager.write_text(text,encoding='utf-8')
    plugin=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/plugin/PluginScreen.kt'
    text=plugin.read_text(encoding='utf-8')
    if 'private fun ManageFromPhoneCard(' in text:
        old='''                // Manage from phone card
                item {
                    ManageFromPhoneCard(onClick = { viewModel.onEvent(PluginUiEvent.StartQrMode) })
                }
'''
        if old not in text: raise RuntimeError('Plugin phone card structure changed')
        text=text.replace(old,'')
        start=text.index('@Composable\nprivate fun ManageFromPhoneCard(')
        end=text.index('@Composable\nprivate fun QrCodeOverlay(',start)
        text=text[:start]+text[end:]
        plugin.write_text(text,encoding='utf-8')
    essential=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/addon/EssentialAddonSetupScreen.kt'
    text=essential.read_text(encoding='utf-8')
    if 'R.string.addon_manage_from_phone_title' in text:
        row=text.index('            Row(')
        first=text.index('                Card(',row)
        start=text.index('                Card(',first+1)
        end=text.index('            }\n            Spacer(modifier = Modifier.height(NuvioTheme.spacing.xl))',start)
        text=text[:start]+text[end:]
        essential.write_text(text,encoding='utf-8')
if (ROOT/'app').exists():
    catalogs=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/addon/CatalogOrderScreen.kt'
    text=catalogs.read_text(encoding='utf-8')
    if '// Omnia deliberate catalog search.' not in text:
        text=text.replace('import androidx.compose.runtime.Composable\n','import androidx.compose.runtime.Composable\nimport androidx.compose.runtime.LaunchedEffect\n')
        text=text.replace('    val catalogControlsFocus = remember { FocusRequester() }','''    val catalogControlsFocus = remember { FocusRequester() }
    val catalogSearchFieldFocus = remember { FocusRequester() }
    var catalogSearchEditing by rememberSaveable { mutableStateOf(false) }''')
        text=text.replace('    BackHandler { onBackPress() }','''    // Omnia deliberate catalog search. Catalog controls are usable before opening the keyboard.
    LaunchedEffect(Unit) {
        repeat(2) { withFrameNanos { } }
        keyboardController?.hide()
        catalogControlsFocus.requestFocus()
    }
    LaunchedEffect(catalogSearchEditing) {
        if (catalogSearchEditing) {
            repeat(2) { withFrameNanos { } }
            catalogSearchFieldFocus.requestFocus()
            keyboardController?.show()
        }
    }
    BackHandler {
        if (catalogSearchEditing) {
            catalogSearchEditing = false
            keyboardController?.hide()
            catalogControlsFocus.requestFocus()
        } else onBackPress()
    }''')
        start=text.index('                    OutlinedTextField(')
        end=text.index('                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp))',start)
        field=text[start:end]
        field=field.replace('modifier = Modifier.fillMaxWidth().onPreviewKeyEvent',
                            'modifier = Modifier.fillMaxWidth().focusRequester(catalogSearchFieldFocus).onPreviewKeyEvent')
        field=re.sub(r'(?m)^( *)keyboardController\?\.hide\(\)',r'\1catalogSearchEditing = false\n\1keyboardController?.hide()',field)
        field=''.join('    '+line if line.strip() else line for line in field.splitlines(keepends=True))
        button='''                    } else {
                        Button(
                            onClick = { catalogSearchEditing = true },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.colors(
                                containerColor = NuvioTheme.colors.BackgroundCard,
                                contentColor = NuvioTheme.colors.TextPrimary,
                                focusedContainerColor = NuvioTheme.colors.FocusBackground,
                                focusedContentColor = NuvioTheme.colors.Primary
                            )
                        ) {
                            Column(modifier = Modifier.fillMaxWidth()) {
                                Text("Search catalogs or providers")
                                if (catalogQuery.isNotBlank()) Text(catalogQuery, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
'''
        text=text[:start]+'                    if (catalogSearchEditing) {\n'+field+button+text[end:]
        catalogs.write_text(text,encoding='utf-8')
if (ROOT/'composeApp').exists():
    details=ROOT/'composeApp/src/commonMain/kotlin/com/nuvio/app/features/details'
    (details/'OmniaCastPreview.kt').write_text('''package com.nuvio.app.features.details

internal fun MetaDetails.principalCastNames(): List<String> = cast.asSequence()
    .filter { it.role.orEmpty().trim().lowercase() !in listOf("director", "writer", "creator") }
    .map { it.name.trim() }
    .filter { it.isNotBlank() }
    .distinctBy { it.lowercase() }
    .take(6)
    .toList()
''',encoding='utf-8')
    for filename in ['DetailMetaInfo.kt','TabletDetailHero.kt']:
        relative='composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/'+filename
        edit(relative,'import com.nuvio.app.features.details.MetaDetails\n',
             'import com.nuvio.app.features.details.MetaDetails\nimport com.nuvio.app.features.details.principalCastNames\n')
    edit('composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailMetaInfo.kt',
         '        if (meta.writer.isNotEmpty()) {', '''        val principalCast = remember(meta.cast) { meta.principalCastNames() }
        if (principalCast.isNotEmpty()) {
            MetaLabelValueRow(
                label = stringResource(Res.string.settings_meta_cast),
                value = principalCast.joinToString(", "),
            )
        }

        if (meta.writer.isNotEmpty()) {''')
    tablet='composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/TabletDetailHero.kt'
    edit(tablet,'import nuvio.composeapp.generated.resources.details_director\n',
         'import nuvio.composeapp.generated.resources.details_director\nimport nuvio.composeapp.generated.resources.settings_meta_cast\n')
    edit(tablet,'            meta.description?.takeIf { showOverview && it.isNotBlank() }?.let { synopsis ->', '''            val principalCast = remember(meta.cast) { meta.principalCastNames() }
            if (showOverview && principalCast.isNotEmpty()) {
                Spacer(modifier = Modifier.height(space.s8))
                MetaLabelValueRow(
                    label = stringResource(Res.string.settings_meta_cast),
                    value = principalCast.joinToString(", "),
                )
            }
            meta.description?.takeIf { showOverview && it.isNotBlank() }?.let { synopsis ->''')
    tests=ROOT/'prepare_omnia_ios_tests.py'
    text=tests.read_text(encoding='utf-8')
    if 'capture("inline-cast-credits")' not in text:
        marker='        capture("playback-details")\n        tap("Play")'
        if marker not in text: raise RuntimeError('iOS credit assertion insertion point changed')
        text=text.replace(marker,'''        capture("playback-details")
        let castCredit = item("Omnia QA Actor One, Omnia QA Actor Two")
        for _ in 0..<8 {
            if castCredit.exists && castCredit.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(castCredit.waitForExistence(timeout: 15), "Inline actor names are missing")
        let directorCredit = item("Omnia QA Director")
        XCTAssertTrue(directorCredit.exists, "Director credit is missing")
        XCTAssertGreaterThan(castCredit.frame.minY, directorCredit.frame.minY, "Actor names must appear below the director")
        capture("inline-cast-credits")
        for _ in 0..<6 { app.swipeDown() }
        tap("Play")''',1)
        tests.write_text(text,encoding='utf-8')
else:
    details=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/detail'
    (details/'OmniaCastPreview.kt').write_text('''package com.nuvio.tv.ui.screens.detail

import com.nuvio.tv.domain.model.Meta

internal fun Meta.principalCastNames(): List<String> {
    val principal = castMembers
        .filter { it.character.orEmpty().trim().lowercase() !in listOf("director", "writer", "creator") }
        .map { it.name }
    return (principal.ifEmpty { cast }).asSequence()
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinctBy { it.lowercase() }
        .take(6)
        .toList()
}
''',encoding='utf-8')
    hero='app/src/main/java/com/nuvio/tv/ui/screens/detail/HeroSection.kt'
    edit(hero,'    // Animate logo properties for trailer mode', '''    val principalCast = remember(meta.cast, meta.castMembers) { meta.principalCastNames() }

    // Animate logo properties for trailer mode''')
    edit(hero,'                    if (mdbListRatings?.isEmpty() == false) {', '''                    if (principalCast.isNotEmpty()) {
                        Text(
                            text = stringResource(R.string.pause_cast_label) + ": " + principalCast.joinToString(", "),
                            style = MaterialTheme.typography.labelLarge,
                            color = NuvioTheme.extendedColors.textSecondary,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.fillMaxWidth(0.6f)
                        )
                        Spacer(modifier = Modifier.height(NuvioTheme.spacing.md))
                    }

                    if (mdbListRatings?.isEmpty() == false) {''')
    search=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/search/SearchScreen.kt'
    text=search.read_text(encoding='utf-8')
    if '// Omnia labelled discovery action.' not in text:
        text=text.replace('import androidx.compose.foundation.layout.width\n','import androidx.compose.foundation.layout.width\nimport androidx.compose.foundation.layout.widthIn\n')
        start=text.index('        if (showDiscoverButton) {')
        end=text.index('        if (showVoiceSearch) {',start)
        block=text[start:end]
        block=block.replace('            IconButton(','            // Omnia labelled discovery action.\n            Button(',1)
        block=block.replace('.size(NuvioTheme.spacing.huge)', '.height(NuvioTheme.spacing.huge)\n                    .widthIn(min = 160.dp)',1)
        block=block.replace('                modifier = Modifier', '''                colors = ButtonDefaults.colors(
                    containerColor = NuvioTheme.colors.BackgroundCard,
                    contentColor = NuvioTheme.colors.TextPrimary,
                    focusedContainerColor = NuvioTheme.colors.FocusBackground,
                    focusedContentColor = NuvioTheme.colors.Primary
                ),
                shape = ButtonDefaults.shape(RoundedCornerShape(NuvioTheme.radii.md)),
                modifier = Modifier''',1)
        block=block.replace('contentDescription = stringResource(R.string.cd_open_discover)', 'contentDescription = null',1)
        block=block.replace('tint = NuvioTheme.colors.TextPrimary', 'tint = if (isDiscoverButtonFocused) NuvioTheme.colors.Primary else NuvioTheme.colors.TextPrimary',1)
        old='''                )
            }

            Spacer'''
        new='''                )
                Spacer(modifier = Modifier.width(12.dp))
                Text(stringResource(R.string.discover_title), maxLines = 1)
            }

            Spacer'''
        if old not in block: raise RuntimeError('Discovery action structure changed')
        block=block.replace(old,new,1)
        text=text[:start]+block+text[end:]
        search.write_text(text,encoding='utf-8')
print('Applied Omnia catalog navigation, labelled discovery and cast-credit improvements to '+('mobile/iOS' if (ROOT/'composeApp').exists() else 'TV'))


# Omnia links, accurate update failures, integration explanations and URL privacy.
from xml.sax.saxutils import escape
def resource_value(relative,key,value):
    path=ROOT/relative
    text=path.read_text(encoding='utf-8')
    pattern=r'(<string name="'+re.escape(key)+r'">).*?(</string>)'
    replacement=escape(value).replace("'","\\'")
    text,count=re.subn(pattern,lambda m:m[1]+replacement+m[2],text,flags=re.S)
    if count!=1: raise RuntimeError('Expected one resource '+key)
    path.write_text(text,encoding='utf-8')

if (ROOT/'composeApp').exists():
    prefix='composeApp/src/commonMain/kotlin/com/nuvio/app/'
    edit('androidApp/src/main/AndroidManifest.xml','<data android:scheme="nuvio" />','<data android:scheme="nuvio" />\n                <data android:scheme="omnia" />')
    bridge=prefix+'core/deeplink/AppUrlBridge.kt'
    edit(bridge,'if (scheme != "nuvio") return null','if (scheme != "nuvio" && scheme != "omnia") return null')
    edit(bridge,'append("nuvio://meta?type=")','append("omnia://meta?type=")')
    edit(bridge,'fun buildDownloadsDeepLinkUrl(): String = "nuvio://downloads"','fun buildDownloadsDeepLinkUrl(): String = "omnia://downloads"')
    updater=prefix+'features/updater/'
    edit(updater+'AppUpdaterRepository.kt','repos/Workedword/Omnia-Releases/','repos/Workedword/Omnia/')
    path=ROOT/(updater+'AppUpdaterRepository.kt')
    text=path.read_text(encoding="utf-8").replace('        if (response.status == 404) throw NoChannelReleaseException()\n','')
    path.write_text(text,encoding='utf-8')
    controller=ROOT/(updater+'AppUpdater.kt')
    text=controller.read_text(encoding='utf-8')
    if '// Omnia update failures never mean current.' not in text:
        text=text.replace('            }.onFailure { error ->\n                _uiState.update { state ->','''            }.onFailure { error ->
                // Omnia update failures never mean current.
                val failureMessage = if (error is NoChannelReleaseException) {
                    getString(Res.string.updates_no_channel_release)
                } else {
                    error.message ?: getString(Res.string.updates_check_failed)
                }
                _uiState.update { state ->''',1)
        text=text.replace('showDialog = force && error !is NoChannelReleaseException,','showDialog = force,',1)
        text=text.replace('errorMessage = if (force && error !is NoChannelReleaseException) {\n                            error.message ?: getString(Res.string.updates_check_failed)','errorMessage = if (force) {\n                            failureMessage',1)
        text=text.replace('''                        if (error is NoChannelReleaseException) noUpdateMessage(channel)
                        else error.message ?: getString(Res.string.updates_check_failed),''','''                        failureMessage,''',1)
        assert 'error is NoChannelReleaseException) noUpdateMessage' not in text
        controller.write_text(text,encoding='utf-8')
    resources='composeApp/src/commonMain/composeResources/values/strings.xml'
    resource_value(resources,'updates_no_channel_release','No compatible update is available on this channel. Please try again later.')
    resource_value(resources,'settings_tracking_services','Watch tracking')
    hint=ROOT/'composeApp/src/commonMain/composeResources/values/omnia_tracking.xml'
    hint.write_text('<resources><string name="omnia_tracking_sync_hint">Connect Trakt or Simkl for watch tracking. Your Omnia history and settings sync through Account &amp; Profiles.</string></resources>\n',encoding='utf-8')
    tracking=prefix+'features/settings/TrackingSettingsPage.kt'
    edit(tracking,'import nuvio.composeapp.generated.resources.Res\n','import nuvio.composeapp.generated.resources.Res\nimport nuvio.composeapp.generated.resources.omnia_tracking_sync_hint\n')
    edit(tracking,'            TrackingProviderCards(','            Text(\n                text = stringResource(Res.string.omnia_tracking_sync_hint),\n                style = MaterialTheme.typography.bodyMedium,\n                color = MaterialTheme.colorScheme.onSurfaceVariant,\n                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),\n            )\n            TrackingProviderCards(')
    path=ROOT/(prefix+'features/addons/AddonRepository.kt')
    text=path.read_text(encoding='utf-8')
    text=text.replace('            urls.forEachIndexed { i, u -> log.d { "  server[$i]: $u" } }\n','')
    text=text.replace('log.i { "addAddon() — rawUrl=$rawUrl" }','log.i { "addAddon() — install requested" }')
    text=text.replace('log.i { "removeAddon() — $manifestUrl" }','log.i { "removeAddon() — removal requested" }')
    text=text.replace('log.e(e) { "pullFromServer() — FAILED" }','log.e { "pullFromServer() — FAILED (${e::class.simpleName})" }')
    text=text.replace('log.e(error) { "pushToServer() — FAILED" }','log.e { "pushToServer() — FAILED (${error::class.simpleName})" }')
    path.write_text(text,encoding='utf-8')
    test=ROOT/'composeApp/src/commonTest/kotlin/com/nuvio/app/core/deeplink/OmniaUrlTest.kt'
    test.write_text('''package com.nuvio.app.core.deeplink
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
class OmniaUrlTest {
    @Test fun omniaLinksAndCompatibilityLinksOpenTheSameTitle() {
        val expected = AppDeepLink.Meta("movie", "omniaqa:test")
        assertEquals(expected, parseAppDeepLink("omnia://detail/movie/omniaqa%3Atest"))
        assertEquals(expected, parseAppDeepLink("nuvio://detail/movie/omniaqa%3Atest"))
        assertNull(parseAppDeepLink("other://detail/movie/omniaqa%3Atest"))
    }
    @Test fun omniaAddonLinksPreserveConfiguredQueryParameters() {
        assertEquals(AppDeepLink.AddonInstall("https://example.com/u/demo/manifest.json?language=hi"), parseAppDeepLink("omnia://example.com/u/demo/manifest.json?language=hi"))
        assertNull(parseAppDeepLink("omnia://auth/trakt?code=example"))
    }
    @Test fun generatedLinksUseOmniaScheme() {
        assertEquals("omnia://meta?type=movie&id=omniaqa%3Atest", buildMetaDeepLinkUrl("movie", "omniaqa:test"))
        assertEquals("omnia://downloads", buildDownloadsDeepLinkUrl())
    }
}
''',encoding='utf-8')
    footer=prefix+'features/settings/AboutSettingsPage.kt'
    edit(footer,'''            Text(
                text = stringResource(Res.string.compose_about_made_with),
                modifier = Modifier.fillMaxWidth(),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )''','''            // Omnia footer: retain the wordmark and version only.''')
    path=ROOT/footer
    path.write_text(path.read_text(encoding='utf-8').replace('import nuvio.composeapp.generated.resources.compose_about_made_with\n',''),encoding='utf-8')
    screen=ROOT/(prefix+'features/search/SearchScreen.kt')
    text=screen.read_text(encoding='utf-8')
    text=text.replace('''    val discoverInFocus by remember(query, listState) {
        derivedStateOf {
            query.isBlank() && listState.firstVisibleItemIndex > 0
        }
    }
''','')
    text=text.replace('''        val headerTitle = when {
            query.isNotBlank() -> stringResource(Res.string.compose_nav_search)
            discoverInFocus -> stringResource(Res.string.compose_search_discover_title)
            else -> stringResource(Res.string.compose_nav_search)
        }''','''        // One stable Discover heading; typing changes it to Search.
        val headerTitle = if (query.isBlank()) {
            stringResource(Res.string.compose_search_discover_title)
        } else {
            stringResource(Res.string.compose_nav_search)
        }''')
    text=text.replace('import androidx.compose.runtime.derivedStateOf\n','')
    screen.write_text(text,encoding='utf-8')
    content=prefix+'features/search/SearchDiscoverContent.kt'
    edit(content,'''    item {
        DiscoverSectionHeader(modifier = Modifier.padding(horizontal = 16.dp))
    }
''','''    // The sticky screen header owns the single Discover title.
''')
    path=ROOT/content
    text=path.read_text(encoding='utf-8')
    text=text.replace('''@Composable
private fun DiscoverSectionHeader(modifier: Modifier = Modifier) {
    Text(
        text = stringResource(Res.string.compose_search_discover_title),
        modifier = modifier,
        style = MaterialTheme.typography.displaySmall,
        color = MaterialTheme.colorScheme.onBackground,
    )
}

''','')
    path.write_text(text,encoding='utf-8')
    tests=ROOT/'prepare_omnia_ios_tests.py'
    edit('prepare_omnia_ios_tests.py','''        tap("Discover")
        capture("search")''','''        tap("Discover")
        let discoverHeading = app.staticTexts.matching(NSPredicate(format: "label == %@", "Discover"))
        XCTAssertTrue(discoverHeading.firstMatch.waitForExistence(timeout: 10))
        let visibleHeadings = discoverHeading.allElementsBoundByIndex.filter { $0.frame.minY < app.frame.height * 0.7 && $0.frame.height > 0 }
        XCTAssertEqual(visibleHeadings.count, 1, "Discover heading must appear once above the filters")
        capture("search")''')
    for path in (ROOT/'composeApp/src/commonMain/composeResources').glob('values*/*.xml'):
        text=path.read_text(encoding='utf-8')
        text=re.sub(r'\s*<string name="compose_about_made_with">.*?</string>','',text,flags=re.S)
        path.write_text(text,encoding='utf-8')
else:
    edit('app/src/main/AndroidManifest.xml','<data android:scheme="nuvio" />','<data android:scheme="nuvio" />\n                <data android:scheme="omnia" />')
    edit('app/src/main/java/com/nuvio/tv/core/deeplink/DeepLinkParser.kt','if (scheme != "nuvio") return null','if (scheme != "nuvio" && scheme != "omnia") return null')
    path=ROOT/'app/build.gradle.kts'
    path.write_text(path.read_text(encoding='utf-8').replace('Omnia-Releases','Omnia'),encoding='utf-8')
    vm='app/src/full/java/com/nuvio/tv/updater/UpdateViewModel.kt'
    edit(vm,'if (error is NoEligibleUpdateException) {\n                                    noUpdateFeedback(channel)','if (error is NoEligibleUpdateException) {\n                                    context.getString(R.string.omnia_no_compatible_update)')
    resources='app/src/main/res/values/strings.xml'
    resource_value(resources,'tracking_accounts_title','Watch tracking')
    resource_value(resources,'tracking_accounts_subtitle','Trakt and Simkl watch tracking. Omnia history and settings sync through Account & Profiles.')
    (ROOT/'app/src/main/res/values/omnia_update_errors.xml').write_text('<resources><string name="omnia_no_compatible_update">No compatible update is available on this channel. Please try again later.</string></resources>\n',encoding='utf-8')
    path=ROOT/'app/src/main/java/com/nuvio/tv/core/sync/AddonSyncService.kt'
    text=path.read_text(encoding='utf-8')
    text=text.replace('Log.e(TAG, "Failed to push addons to remote", e)','Log.e(TAG, "Failed to push addons to remote (${e.javaClass.simpleName})")')
    text=text.replace('Log.e(TAG, "Failed to get remote addon URLs", e)','Log.e(TAG, "Failed to get remote addon URLs (${e.javaClass.simpleName})")')
    path.write_text(text,encoding='utf-8')
    (ROOT/'app/src/test/java/com/nuvio/tv/core/deeplink/OmniaLinkTest.kt').write_text('''package com.nuvio.tv.core.deeplink
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
''',encoding='utf-8')
    edit('app/src/main/java/com/nuvio/tv/ui/screens/settings/AboutScreen.kt','''                            Text(
                                text = stringResource(R.string.about_made_with_love),
                                style = MaterialTheme.typography.labelSmall,
                                color = NuvioTheme.colors.TextSecondary,
                                textAlign = TextAlign.Center
                            )''','''                            // Omnia About: retain the wordmark and version only.''')
    edit('app/src/main/java/com/nuvio/tv/ui/screens/search/SearchDiscoverSection.kt','''        Text(
            text = stringResource(R.string.discover_title),
            style = MaterialTheme.typography.headlineMedium,
            color = if (showBuiltInHeader) NuvioTheme.colors.TextPrimary else Color.Transparent
        )''','''        if (showBuiltInHeader) {
            Text(
                text = stringResource(R.string.discover_title),
                style = MaterialTheme.typography.headlineMedium,
                color = NuvioTheme.colors.TextPrimary
            )
        }''')
    for path in (ROOT/'app/src/main/res').glob('values*/*.xml'):
        text=path.read_text(encoding='utf-8')
        text=re.sub(r'\s*<string name="about_made_with_love">.*?</string>','',text,flags=re.S)
        path.write_text(text,encoding='utf-8')
print('Applied Omnia update and account-clarity batch')

# Omnia available-addons directory.
DIRECTORY_POLICY = 'package OMNIA_DIRECTORY_PACKAGE\n\ninternal data class DirectoryInstallIdentity(val id: String?, val url: String)\ninternal data class DirectoryCandidate(\n    val manifestUrl: String,\n    val setupUrl: String?,\n    val addonIds: Set<String> = emptySet(),\n    val setupOnly: Boolean = false,\n)\n\ninternal object OmniaDirectoryPolicy {\n    private data class ServiceKey(val origin: String, val path: String, val query: String)\n    private val address = Regex("^(https?)://(\\\\[[^\\\\]]+\\\\]|[^/?#:@]+)(?::(\\\\d+))?([^?#]*)(?:\\\\?([^#]*))?(?:#.*)?$", RegexOption.IGNORE_CASE)\n    private fun key(value: String?): ServiceKey? {\n        val m = address.matchEntire(value?.trim().orEmpty()) ?: return null\n        val scheme = m.groupValues[1].lowercase()\n        val host = m.groupValues[2].lowercase()\n        val port = m.groupValues[3].ifBlank { if (scheme == "https") "443" else "80" }\n        val portNumber = port.toIntOrNull() ?: return null\n        if (portNumber !in 1..65535) return null\n        return ServiceKey("$scheme://$host:$port", m.groupValues[4].trimEnd(\'/\').removeSuffix("/manifest.json"), m.groupValues[5])\n    }\n\n    fun isInstalled(candidate: DirectoryCandidate, installed: List<DirectoryInstallIdentity>): Boolean {\n        val manifest = key(candidate.manifestUrl)\n        val setup = if (candidate.setupOnly) key(candidate.setupUrl) else null\n        val setupPath = setup?.path?.removeSuffix("/configure")?.trimEnd(\'/\')\n        return installed.any { addon ->\n            if (!addon.id.isNullOrBlank() && addon.id in candidate.addonIds) return@any true\n            val current = key(addon.url) ?: return@any false\n            if (manifest != null && manifest == current) return@any true\n            setup != null && setup.origin == current.origin && setupPath != null &&\n                (setupPath.isEmpty() || current.path == setupPath || current.path.startsWith("$setupPath/"))\n        }\n    }\n\n    fun publisher(declaredPublisher: String, setupUrl: String): String =\n        if (declaredPublisher == "Omnia Official" && key(setupUrl)?.origin == "https://omnia.161.97.128.244.sslip.io:443") "Omnia Official" else "Community"\n}\n'
DIRECTORY_TEST = 'package OMNIA_DIRECTORY_PACKAGE\n\nTEST_IMPORTS\n\nclass OmniaDirectoryPolicyTest {\n    @Test fun configuredIdentityIsHiddenAndRemovalMakesItAvailableAgain() {\n        val entry = DirectoryCandidate("https://example.com/manifest.json", null, setOf("demo.catalog"))\n        val installed = listOf(DirectoryInstallIdentity("demo.catalog", "https://other.example/u/private-demo/manifest.json"))\n        assertTrue(OmniaDirectoryPolicy.isInstalled(entry, installed))\n        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, emptyList()))\n    }\n    @Test fun setupServicesMatchConfiguredPathsButNotLookalikeHosts() {\n        val entry = DirectoryCandidate("", "https://example.com/provider/configure", setupOnly = true)\n        assertTrue(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/provider/config-demo/manifest.json"))))\n        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/provider-two/manifest.json"))))\n        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com.evil.test/provider/manifest.json"))))\n    }\n    @Test fun distinctCatalogsOnTheSameServerRemainAvailable() {\n        val entry = DirectoryCandidate("https://example.com/catalogs/india/manifest.json", "https://example.com/catalogs/india/configure", setOf("india"))\n        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity("other", "https://example.com/catalogs/manifest.json"))))\n    }\n    @Test fun exactUrlsNormalizePortsAndSuffixesWithoutDiscardingQueryIdentity() {\n        val entry = DirectoryCandidate("https://EXAMPLE.com:443/catalog/manifest.json?edition=one", null)\n        assertTrue(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/catalog?edition=one#ignored"))))\n        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/catalog?edition=two"))))\n    }\n    @Test fun officialLabelRequiresFirstPartyPublicationAndHost() {\n        assertEquals("Omnia Official", OmniaDirectoryPolicy.publisher("Omnia Official", "https://omnia.161.97.128.244.sslip.io/catalogs/configure"))\n        assertEquals("Community", OmniaDirectoryPolicy.publisher("Omnia Official", "https://example.com/configure"))\n        assertEquals("Community", OmniaDirectoryPolicy.publisher("Community", "https://omnia.161.97.128.244.sslip.io/catalogs/configure"))\n    }\n}\n'
if (ROOT/'composeApp').exists():
    package='com.nuvio.app.features.addons'
    path=ROOT/'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons'
    (path/'OmniaDirectoryPolicy.kt').write_text(DIRECTORY_POLICY.replace('OMNIA_DIRECTORY_PACKAGE',package),encoding='utf-8')
    test=ROOT/'composeApp/src/commonTest/kotlin/com/nuvio/app/features/addons/OmniaDirectoryPolicyTest.kt'
    test.parent.mkdir(parents=True,exist_ok=True)
    test.write_text(DIRECTORY_TEST.replace('OMNIA_DIRECTORY_PACKAGE',package).replace('TEST_IMPORTS','import kotlin.test.Test\nimport kotlin.test.assertTrue\nimport kotlin.test.assertFalse\nimport kotlin.test.assertEquals'),encoding='utf-8')
    (path/'OmniaCommunityPanel.kt').write_text('package com.nuvio.app.features.addons\n\nimport androidx.compose.foundation.layout.*\nimport androidx.compose.foundation.shape.RoundedCornerShape\nimport androidx.compose.material3.*\nimport androidx.compose.runtime.*\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.platform.LocalUriHandler\nimport androidx.compose.ui.semantics.contentDescription\nimport androidx.compose.ui.semantics.semantics\nimport androidx.compose.ui.unit.dp\nimport com.nuvio.app.core.ui.NuvioSurfaceCard\nimport com.nuvio.app.core.ui.NuvioPrimaryButton\nimport kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.launch\nimport kotlinx.serialization.json.*\n\nprivate fun JsonObject.directoryText(key: String) = this[key]?.jsonPrimitive?.contentOrNull.orEmpty()\nprivate fun JsonObject.directoryCandidate() = DirectoryCandidate(\n    manifestUrl = directoryText("manifestUrl"),\n    setupUrl = directoryText("url"),\n    addonIds = (this["addonIds"] as? JsonArray)?.mapNotNull { it.jsonPrimitive.contentOrNull }?.toSet().orEmpty(),\n    setupOnly = this["installable"]?.jsonPrimitive?.booleanOrNull != true,\n)\n\n@Composable\n@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)\ninternal fun OmniaCommunityPanel() {\n    val scope = rememberCoroutineScope()\n    val uri = LocalUriHandler.current\n    val installedState by AddonRepository.uiState.collectAsState()\n    val installed = remember(installedState.addons) {\n        installedState.addons.map { DirectoryInstallIdentity(it.manifest?.id, it.manifestUrl) }\n    }\n    var entries by remember { mutableStateOf<List<JsonObject>>(emptyList()) }\n    var status by remember { mutableStateOf("Loading add-ons…") }\n    var busy by remember { mutableStateOf(false) }\n    var expanded by remember { mutableStateOf(true) }\n    var category by remember { mutableStateOf("All") }\n    var publisher by remember { mutableStateOf("All sources") }\n    var query by remember { mutableStateOf("") }\n    var attempt by remember { mutableStateOf(0) }\n    LaunchedEffect(attempt) {\n        try {\n            val payload = fetchAddonResponseText("https://omnia.161.97.128.244.sslip.io/catalogs/community.json")\n            entries = Json.parseToJsonElement(payload).jsonObject["entries"]!!.jsonArray.map { it.jsonObject }\n            status = "Installed add-ons live in Current Add-ons. Discover something new here."\n        } catch (cancelled: CancellationException) { throw cancelled }\n        catch (_: Exception) { status = "The directory is unavailable. Try Refresh." }\n    }\n    val available = remember(entries, installed) {\n        entries.filterNot { OmniaDirectoryPolicy.isInstalled(it.directoryCandidate(), installed) }\n    }\n    val visible = remember(available, category, publisher, query) {\n        available.filter { entry ->\n            val source = OmniaDirectoryPolicy.publisher(entry.directoryText("publisher"), entry.directoryText("url"))\n            (publisher == "All sources" || publisher == source) &&\n                (category == "All" || entry.directoryText("category") == category) &&\n                (query.isBlank() || entry.directoryText("name").contains(query, true) || entry.directoryText("description").contains(query, true))\n        }.sortedWith(compareBy<JsonObject> { OmniaDirectoryPolicy.publisher(it.directoryText("publisher"), it.directoryText("url")) != "Omnia Official" }.thenBy { it.directoryText("name").lowercase() })\n    }\n    NuvioSurfaceCard {\n        Text("DISCOVER ADD-ONS", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)\n        Text("More for your cinema", style = MaterialTheme.typography.headlineSmall)\n        Text("${available.size} available · ${installed.size} installed", style = MaterialTheme.typography.bodyMedium)\n        Text(status, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)\n        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {\n            TextButton(onClick = { expanded = !expanded }) { Text(if (expanded) "Hide directory" else "Browse add-ons") }\n            TextButton(onClick = { attempt++ }) { Text("Refresh") }\n        }\n        if (expanded) {\n            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {\n                listOf("All sources", "Omnia Official", "Community").forEach { source ->\n                    FilterChip(selected = publisher == source, onClick = { publisher = source }, label = { Text(source) })\n                }\n            }\n            Text("Official add-ons are maintained by Omnia. Community add-ons come from independent developers.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)\n            OutlinedTextField(value = query, onValueChange = { query = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("Search available add-ons") })\n            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {\n                listOf("All", "Catalogs", "Collections", "Providers", "Live TV & Sports").forEach { type ->\n                    FilterChip(selected = category == type, onClick = { category = type }, label = { Text(type) })\n                }\n            }\n            if (visible.isEmpty()) {\n                Text("Nothing new in this view", style = MaterialTheme.typography.titleMedium)\n                Text("Try another filter. Add-ons you already have stay in Current Add-ons.", style = MaterialTheme.typography.bodySmall)\n                if (category != "All" || publisher != "All sources" || query.isNotBlank()) {\n                    TextButton(onClick = { category = "All"; publisher = "All sources"; query = "" }) { Text("Clear filters") }\n                }\n            }\n            visible.forEach { entry ->\n                val source = OmniaDirectoryPolicy.publisher(entry.directoryText("publisher"), entry.directoryText("url"))\n                val manifest = entry.directoryText("manifestUrl")\n                val installable = entry["installable"]?.jsonPrimitive?.booleanOrNull == true && manifest.startsWith("https://")\n                NuvioSurfaceCard(modifier = Modifier.semantics { contentDescription = "Available add-on: ${entry.directoryText("name")}" }) {\n                    Surface(color = if (source == "Omnia Official") MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant, shape = RoundedCornerShape(8.dp)) {\n                        Text(source, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), style = MaterialTheme.typography.labelMedium)\n                    }\n                    Text(entry.directoryText("name"), style = MaterialTheme.typography.titleLarge)\n                    Text(entry.directoryText("category") + " · " + if (installable) "Ready to add" else "Setup needed", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)\n                    Text(entry.directoryText("description"), style = MaterialTheme.typography.bodyMedium)\n                    val setup = entry.directoryText("url")\n                    if (installable) {\n                        NuvioPrimaryButton(text = "Add to Omnia", modifier = Modifier.semantics { contentDescription = "Add ${entry.directoryText("name")} to Omnia" }, enabled = !busy, onClick = {\n                            busy = true\n                            scope.launch {\n                                try {\n                                    status = when (val result = AddonRepository.addAddon(manifest)) {\n                                        is AddAddonResult.Success -> "Added ${result.manifest.name} to Current Add-ons"\n                                        is AddAddonResult.Error -> result.message\n                                    }\n                                } finally { busy = false }\n                            }\n                        })\n                    }\n                    TextButton(onClick = { if (setup.startsWith("https://")) runCatching { uri.openUri(setup) } }) { Text(if (installable) "Settings & details" else "Set up") }\n                }\n                Spacer(Modifier.height(12.dp))\n            }\n        }\n        TextButton(onClick = { runCatching { uri.openUri("https://github.com/Workedword/Omnia/tree/main/addons") } }) { Text("Create an add-on for Omnia") }\n    }\n}\n',encoding='utf-8')
    resource_value('composeApp/src/commonMain/composeResources/values/strings.xml','addons_section_installed','Current Add-ons')
    page=ROOT/'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/AddonsScreen.kt'
    text=page.read_text(encoding='utf-8')
    if '// Omnia separates installed controls from discovery.' not in text:
        text=text.replace('import androidx.compose.material3.Text\n','import androidx.compose.material3.Text\nimport androidx.compose.material3.FilterChip\n',1)
        text=text.replace('    val overview = remember(uiState.addons)', '    var showDiscover by rememberSaveable { mutableStateOf(false) }\n    val overview = remember(uiState.addons)',1)
        text=text.replace('        OmniaCommunityPanel()','        // Omnia separates installed controls from discovery.\n        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {\n            FilterChip(selected = !showDiscover, onClick = { showDiscover = false }, label = { Text("Current Add-ons") })\n            FilterChip(selected = showDiscover, onClick = { showDiscover = true }, label = { Text("Discover add-ons") })\n        }\n        if (showDiscover) {\n            OmniaCommunityPanel()\n        } else {',1)
        text=text.replace('    }\n\n    val pendingDeletionUrl = addonPendingDeletionUrl','        } // Current Add-ons\n    }\n\n    val pendingDeletionUrl = addonPendingDeletionUrl',1)
        page.write_text(text,encoding='utf-8')
    tests=ROOT/'prepare_omnia_ios_tests.py'
    text=tests.read_text(encoding='utf-8')
    text=text.replace('item("Community Add-ons")','item("DISCOVER ADD-ONS")')
    text=text.replace('        tap("Catalogs & add-ons", scroll: true)\n        XCTAssertTrue(item("DISCOVER ADD-ONS")','        tap("Catalogs & add-ons", scroll: true)\n        tap("Discover add-ons", scroll: true)\n        XCTAssertTrue(item("DISCOVER ADD-ONS")',1)
    text=text.replace('            // Manifest deep links install directly;','            if item("Current Add-ons").exists && item("Current Add-ons").isHittable { tap("Current Add-ons") }\n            // Manifest deep links install directly;',1)
    text=text.replace('tap("Category: All", scroll: true)','tap("Catalogs", scroll: true)')
    text=text.replace('tap("Category: Catalogs", scroll: true)','tap("Collections", scroll: true)')
    text=text.replace('tap("Category: Collections", scroll: true)','tap("Providers", scroll: true)')
    text=text.replace('tap("Category: Providers", scroll: true)','tap("Live TV & Sports", scroll: true)')
    if 'func testSettingsFooterBranding()' not in text:
        text=text.replace('    func testCatalogSettings() {','    func testSettingsFooterBranding() {\n        enterGuest()\n        openSettings()\n        let footer = item("Version 0.4.11 (19)")\n        for _ in 0..<14 {\n            if footer.exists && footer.isHittable { break }\n            app.swipeUp()\n        }\n        XCTAssertTrue(footer.exists && footer.isHittable, "Settings footer was not reached")\n        XCTAssertEqual(app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS[c] %@", "Tapframe")).count, 0)\n        capture("omnia-settings-footer")\n    }\n    func testCatalogSettings() {',1)
        text=text.replace('        XCTAssertTrue(item("Hide directory").exists)\n        XCTAssertFalse(item("Check catalog endpoints").exists)','        XCTAssertTrue(item("Hide directory").exists)\n        XCTAssertFalse(item("Check catalog endpoints").exists)\n        tap("Omnia Official", scroll: true)\n        let availableCard = item("Available add-on: Omnia Catalogs")\n        XCTAssertTrue(availableCard.waitForExistence(timeout: 15))\n        tap("Add Omnia Catalogs to Omnia", scroll: true)\n        for _ in 0..<15 {\n            if !availableCard.exists { break }\n            Thread.sleep(forTimeInterval: 1)\n        }\n        XCTAssertFalse(availableCard.exists, "Installed add-on must leave the available directory")\n        capture("installed-addon-hidden-from-directory")\n        for _ in 0..<8 { app.swipeDown() }\n        tap("Community", scroll: true)',1)
    tests.write_text(text,encoding='utf-8')
else:
    package='com.nuvio.tv.ui.screens.addon'
    path=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/addon'
    (path/'OmniaDirectoryPolicy.kt').write_text(DIRECTORY_POLICY.replace('OMNIA_DIRECTORY_PACKAGE',package),encoding='utf-8')
    test=ROOT/'app/src/test/java/com/nuvio/tv/ui/screens/addon/OmniaDirectoryPolicyTest.kt'
    test.write_text(DIRECTORY_TEST.replace('OMNIA_DIRECTORY_PACKAGE',package).replace('TEST_IMPORTS','import org.junit.Test\nimport org.junit.Assert.assertTrue\nimport org.junit.Assert.assertFalse\nimport org.junit.Assert.assertEquals'),encoding='utf-8')
    (ROOT/'app/src/main/res/values/omnia_directory.xml').write_text('<resources><string name="omnia_current_addons">Current Add-ons</string></resources>\n',encoding='utf-8')
    manager=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonManagerScreen.kt'
    manager.write_text(manager.read_text(encoding='utf-8').replace('text = stringResource(R.string.addon_title),','text = stringResource(R.string.omnia_current_addons),',1),encoding='utf-8')
    source=path/'AddonDiscovery.kt'
    text=source.read_text(encoding='utf-8')
    if 'val matchingIds:' not in text:
        text=text.replace('val setupUrl: String? = null\n','val setupUrl: String? = null,\n    val matchingIds: Set<String> = emptySet()\n',1)
        text=text.replace('item.text("description")+" · "+item.text("status")','item.text("description")',1)
        text=text.replace('if(installable) manifest.toString() else setup.toString(),"Community",','if(installable) manifest.toString() else setup.toString(),OmniaDirectoryPolicy.publisher(item.text("publisher"),setup.toString()),',1)
        text=text.replace('true,!installable,setup.toString())','true,!installable,setup.toString(),item.getAsJsonArray("addonIds")?.mapNotNull { it.takeIf { value -> value.isJsonPrimitive }?.asString }?.toSet().orEmpty())',1)
        text=text.replace('"Official" to "https://raw.githubusercontent.com/Stremio/stremio-official-addons/master/index.json"','"Community" to "https://raw.githubusercontent.com/Stremio/stremio-official-addons/master/index.json"',1)
        source.write_text(text,encoding='utf-8')
    screen=path/'AddonDiscoveryScreen.kt'
    text=screen.read_text(encoding='utf-8')
    if '// Installed entries belong to Current Add-ons.' not in text:
        text=text.replace('    val visible = remember(state.addons, source, category, query) {','    // Installed entries belong to Current Add-ons.\n    val installedIdentities = remember(installed) { installed.map { DirectoryInstallIdentity(it.id, it.baseUrl) } }\n    val visible = remember(state.addons, installedIdentities, source, category, query) {',1)
        text=text.replace('(source == "All" || addon.source == source) &&','!OmniaDirectoryPolicy.isInstalled(\n                DirectoryCandidate(addon.manifestUrl, addon.setupUrl, addon.matchingIds + addon.id, addon.configurationRequired && addon.setupUrl != null),\n                installedIdentities\n            ) && (source == "All" || addon.source == source) &&',1)
        text=text.replace('}.sortedBy { it.name.lowercase() }','}.sortedWith(compareBy<DiscoverAddon> { it.source != "Omnia Official" }.thenBy { it.name.lowercase() })',1)
        text=text.replace('listOf("All", "Official", "Community")','listOf("All", "Omnia Official", "Community")',1)
        text=text.replace('        if (state.loading) Text(','        Text("${visible.size} available · Installed add-ons stay in Current Add-ons", color = NuvioTheme.colors.TextSecondary)\n        Text("Omnia Official: maintained by Omnia. Community: independent developers.", color = NuvioTheme.colors.TextSecondary, style = MaterialTheme.typography.labelMedium)\n        if (state.loading) Text(',1)
        text=text.replace("                val isInstalled = installed.any { it.id == addon.id || it.baseUrl.trimEnd('/') == addon.baseUrl }\n",'')
        text=text.replace('Text("${addon.source}${if (isInstalled) " · Installed" else ""} · ${addon.resources.joinToString(" · ")}", color = NuvioTheme.colors.TextSecondary)','Text("${addon.source} · ${addon.resources.joinToString(" · ")}", color = if (addon.source == "Omnia Official") NuvioTheme.colors.Primary else NuvioTheme.colors.TextSecondary)',1)
        text=text.replace('Text("Configure on phone")','Text("Set up")')
        text=text.replace('Button(onClick = { if (!isInstalled && !installing) onInstall(addon.manifestUrl) }, enabled = true)', 'Button(onClick = { if (!installing) { onInstall(addon.manifestUrl); directoryFiltersFocus.requestFocus() } }, enabled = !installing)',1)
        text=text.replace('Text(if (isInstalled) "Installed" else if (installing) "Installing…" else "Install")','Text(if (installing) "Adding…" else "Add to Omnia")',1)
        screen.write_text(text,encoding='utf-8')
print('Applied Omnia source-directory design and installed-addon filtering')

# Omnia top-level Add-ons settings (next release batch).
"""Prepare the next settings navigation change on both private app layouts."""
from pathlib import Path
import sys

root=ROOT
def change(relative,old,new):
    p=root/relative
    s=p.read_text(encoding='utf-8')
    if new in s:return
    assert old in s,(relative,old[:70])
    p.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')

if (root/'composeApp').exists():
    prefix='composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/'
    change(prefix+'SettingsModels.kt', '''    Addons(
        titleRes = Res.string.compose_settings_page_addons,
        category = SettingsCategory.Watch,
        parentPage = ContentDiscovery,
''','''    Addons(
        titleRes = Res.string.compose_settings_page_addons,
        category = SettingsCategory.Watch,
        parentPage = Root,
''')
    change(prefix+'SettingsRootPage.kt', '''                    SettingsCategory.Watch -> {
                        SettingsPageRow(
                            page = SettingsPage.ContentDiscovery,''','''                    SettingsCategory.Watch -> {
                        SettingsPageRow(
                            page = SettingsPage.Addons,
                            description = Res.string.settings_content_discovery_addons_description,
                            isTablet = isTablet,
                            onPageClick = onPageClick,
                        )
                        SettingsGroupDivider(isTablet = isTablet)
                        SettingsPageRow(
                            page = SettingsPage.ContentDiscovery,''')
    p=root/prefix/'ContentDiscoverySettingsPage.kt'
    s=p.read_text(encoding="utf-8")
    start=s.find('                SettingsNavigationRow(\n                    title = stringResource(Res.string.compose_settings_page_addons),')
    end=s.find('                SettingsNavigationRow(\n                    title = stringResource(Res.string.compose_settings_page_media_servers),',start)
    if start!=-1:
        assert end>start
        p.write_text(s[:start]+s[end:],encoding='utf-8',newline='\n')
    import re
    p=root/'composeApp/src/commonMain/composeResources/values/strings.xml'
    s=p.read_text(encoding="utf-8")
    for key,value in [('compose_settings_page_addons','Add-ons'),('settings_content_discovery_addons_description','Manage installed add-ons and discover new catalogs and playback sources.')]:
        s,n=re.subn(r'(<string name="'+key+r'">).*?(</string>)',lambda m:m[1]+value+m[2],s,count=1,flags=re.S)
        assert n==1,key
    p.write_text(s,encoding='utf-8',newline='\n')
else:
    prefix='app/src/main/java/com/nuvio/tv/ui/screens/settings/'
    change(prefix+'SettingsCatalog.kt','    CONTENT_DISCOVERY(SettingsRailGroup.WATCH),','    ADDONS(SettingsRailGroup.WATCH),\n    CONTENT_DISCOVERY(SettingsRailGroup.WATCH),')
    p=root/prefix/'SettingsScreen.kt'
    s=p.read_text(encoding="utf-8")
    if 'SettingsCategory.ADDONS ->' not in s:
        s=s.replace('import androidx.compose.material.icons.filled.Explore','import androidx.compose.material.icons.filled.Extension\nimport androidx.compose.material.icons.filled.Explore',1)
        line='    SettingsCategory.CONTENT_DISCOVERY -> SettingsSectionSpec('
        i=s.index(line)
        s=s[:i]+'    SettingsCategory.ADDONS -> SettingsSectionSpec(category, "Add-ons", Icons.Default.Extension, destination = SettingsSectionDestination.Inline)\n'+s[i:]
        s=s.replace('            SettingsCategory.CONTENT_DISCOVERY to FocusRequester(),','            SettingsCategory.ADDONS to FocusRequester(),\n            SettingsCategory.CONTENT_DISCOVERY to FocusRequester(),',1)
        i=s.index('        SettingsCategory.CONTENT_DISCOVERY -> ContentDiscoverySettingsContent(')
        case='''        SettingsCategory.ADDONS -> OmniaAddonsSettingsContent(
            onNavigateToAddons = onNavigateToAddons,
            initialFocusRequester = if (allowDetailAutofocus) contentFocusRequesters[SettingsCategory.ADDONS] else null
        )
'''
        s=s[:i]+case+s[i:]
        p.write_text(s,encoding='utf-8',newline='\n')
    p=root/prefix/'ContentDiscoverySettingsContent.kt'
    s=p.read_text(encoding="utf-8")
    start=s.find('            SettingsActionRow(\n                title = stringResource(R.string.addon_title),')
    end=s.find('            SettingsActionRow(\n                title = stringResource(R.string.catalog_order_title),',start)
    if start!=-1:
        assert end>start
        s=s[:start]+s[end:]
        s=s.replace('mutableStateOf("addons")','mutableStateOf("catalogs")',1)
        p.write_text(s,encoding='utf-8',newline='\n')
    (root/prefix/'OmniaAddonsSettingsContent.kt').write_text('''@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)
package com.nuvio.tv.ui.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Extension
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import com.nuvio.tv.ui.theme.NuvioTheme

@Composable
internal fun OmniaAddonsSettingsContent(onNavigateToAddons: () -> Unit, initialFocusRequester: FocusRequester?) {
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.md)) {
        SettingsDetailHeader(title = "Add-ons", subtitle = "Manage your sources in one place.")
        SettingsGroupCard(modifier = Modifier.fillMaxWidth()) {
            SettingsActionRow(
                title = "Current & Discover Add-ons",
                subtitle = "Manage installed add-ons or find new catalogs, subtitles and playback sources.",
                leadingIcon = Icons.Default.Extension,
                onClick = onNavigateToAddons,
                modifier = if (initialFocusRequester != null) Modifier.focusRequester(initialFocusRequester) else Modifier
            )
        }
    }
}
''',encoding='utf-8',newline='\n')
    p=root/'app/src/test/java/com/nuvio/tv/ui/screens/settings/SettingsCatalogTest.kt'
    s=p.read_text(encoding="utf-8")
    # The first Watch-group category is now Add-ons, including its group divider.
    if 'SettingsCategory.ADDONS,\n                SettingsCategory.CONTENT_DISCOVERY,' not in s:
        s=s.replace('SettingsCategory.CONTENT_DISCOVERY,\n                SettingsCategory.PLAYBACK,','SettingsCategory.ADDONS,\n                SettingsCategory.CONTENT_DISCOVERY,\n                SettingsCategory.PLAYBACK,',1)
    s=s.replace('SettingsCategory.APPEARANCE,\n                SettingsCategory.CONTENT_DISCOVERY,\n                SettingsCategory.INTEGRATION,','SettingsCategory.APPEARANCE,\n                SettingsCategory.ADDONS,\n                SettingsCategory.INTEGRATION,',1)
    s=s.replace('categories.startsNewGroup(categories.indexOf(SettingsCategory.CONTENT_DISCOVERY))','categories.startsNewGroup(categories.indexOf(SettingsCategory.ADDONS))')
    p.write_text(s,encoding='utf-8',newline='\n')
print('Prepared top-level Add-ons navigation on',root.name)

if (ROOT/'composeApp').exists():
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=20\nMARKETING_VERSION=0.4.12\n',encoding='utf-8')
    resource_value('composeApp/src/commonMain/composeResources/values/strings.xml','compose_settings_page_content_discovery','Content')
    resource_value('composeApp/src/commonMain/composeResources/values/strings.xml','compose_settings_root_content_discovery_description','Catalogs, media servers and search preferences.')
    p=ROOT/'composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt'
    s=p.read_text(encoding="utf-8")
    start=s.index('                    is AppDeepLink.AddonInstall -> {')
    end=s.index('                    AppDeepLink.Downloads -> {',start)
    block=s[start:end]
    navigation='                        activateTab(AppScreenTab.Settings)\n                        navController.navigate(AddonsSettingsRoute(addonsSettingsTitle)) {\n                            launchSingleTop = true\n                        }\n'
    marker='                        // Open management after installation has settled.\n'
    if marker not in block:
        assert navigation in block
        block=block.replace(navigation,'',1)
        block=block.replace('                        AppDeepLinkRepository.markConsumed(deepLink)',marker+navigation+'                        AppDeepLinkRepository.markConsumed(deepLink)',1)
        s=s[:start]+block+s[end:]
        p.write_text(s,encoding='utf-8')
    p=ROOT/'prepare_omnia_ios_tests.py'
    s=p.read_text(encoding="utf-8")
    s=s.replace('Version 0.4.11 (19)','Version 0.4.12 (20)')
    s=s.replace('        tap("Content & Discovery", scroll: true)\n        tap("Catalogs & add-ons", scroll: true)','        tap("Add-ons", scroll: true)')
    s=s.replace('tap("Content & Discovery", scroll: true)','tap("Content", scroll: true)')
    s=s.replace('tap("Add Omnia Catalogs to Omnia", scroll: true)','tap("Add Omnia Catalogs to Omnia, Add to Omnia", scroll: true)')
    marker='        tap("Discover add-ons", scroll: true)'
    reset='        for _ in 0..<12 { app.swipeDown() }\n'+marker
    if reset not in s: s=s.replace(marker,reset,1)
    p.write_text(s,encoding='utf-8')
else:
    resource_value('app/src/main/res/values/strings.xml','settings_content_discovery','Content')
    resource_value('app/src/main/res/values/strings.xml','settings_content_discovery_subtitle','Catalogs, media servers and discovery preferences.')
    p=ROOT/'app/build.gradle.kts'
    s=p.read_text(encoding="utf-8")
    s=re.sub(r'(?m)^(\s*versionCode\s*=\s*)\d+',r'\g<1>20',s,count=1)
    s=re.sub(r'(?m)^(\s*versionName\s*=\s*)"[^"]+"',r'\g<1>"0.3.14"',s,count=1)
    p.write_text(s,encoding='utf-8')

# Corrections found during the completion audit.
"""Apply fixes found by the completion audit; preserve prior candidate artifacts."""
from pathlib import Path
import re

root=ROOT
if (root/'composeApp').exists():
    (root/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=21\nMARKETING_VERSION=0.4.13\n',encoding='utf-8')
    prefix='composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/'
    (root/prefix/'OmniaAddonDefaults.kt').write_text('''package com.nuvio.app.features.addons

// Used only when a profile has no saved local preferences. An explicitly saved
// empty list remains empty; do not reinstall sources the user has removed.
internal val omniaDefaultAddonUrls = listOf(
    "https://catalog.nuvio.tv/manifest.json",
    "https://opensubtitles-v3.strem.io/manifest.json",
)
''',encoding='utf-8')
    for platform in ['android','ios']:
        p=root/f'composeApp/src/{platform}Main/kotlin/com/nuvio/app/features/addons/AddonPlatform.{platform}.kt'
        s=p.read_text(encoding='utf-8')
        old='?: "https://catalog.nuvio.tv/manifest.json")'
        new='?: omniaDefaultAddonUrls.joinToString(separator = "\\n"))'
        if new in s:
            # The legacy overlay reinserts its one-catalog Elvis fallback when
            # its old literal no longer appears. Remove that extra link before
            # it can shadow the shared two-source defaults on a repeated run.
            s=s.replace('            ?: "https://catalog.nuvio.tv/manifest.json"\n','')
        else:
            assert old in s,p
            s=s.replace(old,new,1)
        p.write_text(s,encoding='utf-8')
    p=root/prefix/'AddonRepository.kt'
    s=p.read_text(encoding='utf-8')
    # A successfully loaded empty server list is a real user choice. Initial
    # authenticated account defaults are supplied by the server's auth trigger.
    old='''            if (rowsByUrl.isEmpty() && AddonStorage.loadInstalledAddonUrls(currentProfileId) == listOf("https://catalog.nuvio.tv/manifest.json")) {
                rowsByUrl["https://catalog.nuvio.tv/manifest.json"] = AddonRow(url = "https://catalog.nuvio.tv/manifest.json", name = "Nuvio Catalog Addon")
            }
'''
    s=s.replace(old,'')
    p.write_text(s,encoding='utf-8')
    resource_value('composeApp/src/commonMain/composeResources/values/strings_servers.xml','library_servers_empty_message','Choose which libraries to show in Settings, under Content, then Media servers.')
    p=root/'prepare_omnia_ios_tests.py'
    p.write_text(p.read_text(encoding='utf-8').replace('Version 0.4.12 (20)','Version 0.4.13 (21)'),encoding='utf-8')
else:
    prefix='app/src/main/java/com/nuvio/tv/ui/screens/search/'
    (root/prefix/'OmniaSearchFocusPolicy.kt').write_text('''package com.nuvio.tv.ui.screens.search

import android.view.KeyEvent

/** Empty search must allow a remote to reach its leading controls. */
internal fun shouldFocusLeadingSearchControl(query: String, isRtl: Boolean, keyCode: Int, discoverVisible: Boolean): Boolean =
    discoverVisible && query.isEmpty() && keyCode == if (isRtl) KeyEvent.KEYCODE_DPAD_RIGHT else KeyEvent.KEYCODE_DPAD_LEFT
''',encoding='utf-8')
    p=root/prefix/'SearchScreen.kt'
    s=p.read_text(encoding='utf-8')
    marker='''                .onPreviewKeyEvent { keyEvent ->
                    when (keyEvent.nativeKeyEvent.keyCode) {'''
    replacement='''                .onPreviewKeyEvent { keyEvent ->
                    if (shouldFocusLeadingSearchControl(query, isRtl, keyEvent.nativeKeyEvent.keyCode, showDiscoverButton)) {
                        if (keyEvent.nativeKeyEvent.action == KeyEvent.ACTION_DOWN) {
                            keyboardController?.hide()
                            val leadingControl = if (showVoiceSearch) voiceFocusRequester ?: discoverFocusRequester else discoverFocusRequester
                            leadingControl?.let { runCatching { it.requestFocus() } }
                        }
                        return@onPreviewKeyEvent true
                    }
                    when (keyEvent.nativeKeyEvent.keyCode) {'''
    if replacement not in s and replacement.replace("showDiscoverButton))", "showDiscoverButton || showVoiceSearch))") not in s:
        assert s.count(marker)==1,s.count(marker)
        p.write_text(s.replace(marker,replacement,1),encoding='utf-8')
    p=root/'app/src/test/java/com/nuvio/tv/ui/screens/search/OmniaSearchFocusPolicyTest.kt'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('''package com.nuvio.tv.ui.screens.search

import android.view.KeyEvent
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OmniaSearchFocusPolicyTest {
    @Test fun emptyFieldReachesLeadingControlsInLtr() {
        assertTrue(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_LEFT, true))
        assertFalse(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_RIGHT, true))
    }
    @Test fun emptyFieldReachesLeadingControlsInRtl() {
        assertTrue(shouldFocusLeadingSearchControl("", true, KeyEvent.KEYCODE_DPAD_RIGHT, true))
        assertFalse(shouldFocusLeadingSearchControl("", true, KeyEvent.KEYCODE_DPAD_LEFT, true))
    }
    @Test fun typedQueriesKeepCaretNavigation() {
        for (query in listOf("Movie", " ", "Hindi series")) {
            assertFalse(shouldFocusLeadingSearchControl(query, false, KeyEvent.KEYCODE_DPAD_LEFT, true))
            assertFalse(shouldFocusLeadingSearchControl(query, true, KeyEvent.KEYCODE_DPAD_RIGHT, true))
        }
    }
    @Test fun hiddenDiscoverAndOtherDirectionsDoNotCaptureFocus() {
        assertFalse(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_LEFT, false))
        assertFalse(shouldFocusLeadingSearchControl("", true, KeyEvent.KEYCODE_DPAD_RIGHT, false))
        assertFalse(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_DOWN, true))
    }
}
''',encoding='utf-8')
    p=root/'app/build.gradle.kts'
    s=p.read_text(encoding='utf-8')
    s=re.sub(r'(?m)^(\s*versionCode\s*=\s*)\d+',r'\g<1>21',s,count=1)
    s=re.sub(r'(?m)^(\s*versionName\s*=\s*)"[^"]+"',r'\g<1>"0.3.15"',s,count=1)
    p.write_text(s,encoding='utf-8')
print('Prepared completion-audit corrections on',root.name)


# Omnia preferences and Collections batch.

from pathlib import Path
import re,sys

def apply_finish_batch(root):
    root=Path(root)
    mobile=(root/'composeApp').exists()
    def edit(rel,old,new,count=1):
        p=root/rel;s=p.read_text(encoding='utf-8')
        if new in s:return
        assert s.count(old)==count,(rel,s.count(old),old[:100])
        p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')
    def write(rel,s):
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8',newline='\n')
    prefix='composeApp/src/commonMain/kotlin/com/nuvio/app/' if mobile else 'app/src/main/java/com/nuvio/tv/'
    model=prefix+('features/collection/CollectionModels.kt' if mobile else 'domain/model/Collection.kt')
    edit(model,'    val showAllTab: Boolean = true,','    val showAllTab: Boolean = true,\n    val hideSourceRows: Boolean = false,')
    editor=prefix+('features/collection/CollectionEditorRepository.kt' if mobile else 'ui/screens/collection/CollectionEditorViewModel.kt')
    edit(editor,'    val showAllTab: Boolean = true,','    val showAllTab: Boolean = true,\n    val hideSourceRows: Boolean = false,')
    # Apply each field wherever its corresponding existing show-All field is copied.
    p=root/editor;s=p.read_text(encoding='utf-8')
    for expr in ['existing.showAllTab','state.showAllTab']:
        pattern=r'(?m)^(\s*)showAllTab = '+re.escape(expr)+r',\n(?!\s*hideSourceRows)'
        s=re.sub(pattern,lambda m:m.group(0)+m.group(1)+'hideSourceRows = '+expr.replace('showAllTab','hideSourceRows')+',\n',s)
    setter=('    fun setHideSourceRows(hidden: Boolean) {\n        _uiState.value = _uiState.value.copy(hideSourceRows = hidden)\n    }\n\n' if mobile else '    fun setHideSourceRows(hidden: Boolean) {\n        _uiState.update { it.copy(hideSourceRows = hidden) }\n    }\n\n')
    if setter not in s:
        marker='    fun setShowAllTab(show: Boolean) {';assert marker in s;s=s.replace(marker,setter+marker,1)
    p.write_text(s,encoding='utf-8',newline='\n')
    if not mobile:
        store=prefix+'data/local/CollectionsDataStore.kt'
        edit(store,'        val showAllTab: Boolean = true,','        val showAllTab: Boolean = true,\n        val hideSourceRows: Boolean = false,')
        edit(store,'        showAllTab = showAllTab,','        showAllTab = showAllTab,\n        hideSourceRows = hideSourceRows,',count=2)
    screen=prefix+('features/collection/CollectionEditorScreen.kt' if mobile else 'ui/screens/collection/CollectionEditorScreen.kt')
    p=root/screen;s=p.read_text(encoding='utf-8')
    if 'collections_editor_hide_source_rows' not in s:
        if mobile:
            start=s.index('            // Show All Tab')
            end=s.index('            // Folders Section Header',start)
            block=s[start:end]
        else:
            start=s.index('        if (uiState.viewMode == FolderViewMode.TABBED_GRID) {')
            end=s.index('        item(key = "folders_header")',start)
            block=s[start:end].replace('if (uiState.viewMode == FolderViewMode.TABBED_GRID) {','run {',1)
        block=block.replace('// Show All Tab','// Hide standalone source rows while retaining Collection sources')
        block=block.replace('show_all_tab','hide_source_rows').replace('showAllTab','hideSourceRows').replace('setShowAllTab','setHideSourceRows')
        s=s[:start]+block+s[start:]
        p.write_text(s,encoding='utf-8',newline='\n')
    package='com.nuvio.app.features.collection' if mobile else 'com.nuvio.tv.domain.model'
    source_expr='folder.resolvedCatalogSources' if mobile else 'folder.catalogSources'
    key_expr='"${source.addonId}:${source.type}:${source.catalogId}"' if mobile else 'catalogRowLegacyKey(source.addonId, source.type, source.catalogId)'
    write(prefix+('features/collection/' if mobile else 'domain/model/')+'HiddenCollectionCatalogs.kt',f'''package {package}

/** Derived from the active profile; never mutates catalog preferences or sources. */
internal fun hiddenCollectionCatalogKeys(collections: List<Collection>, disabledCollectionIds: Set<String>): Set<String> =
    collections.asSequence()
        .filter {{ it.hideSourceRows && it.id !in disabledCollectionIds }}
        .flatMap {{ it.folders.asSequence() }}
        .flatMap {{ folder -> {source_expr}.asSequence() }}
        .map {{ source -> {key_expr} }}
        .toSet()
''')
    if mobile:
        home=prefix+'features/home/HomeRepository.kt'
        edit(home,'import com.nuvio.app.features.collection.CollectionRepository','import com.nuvio.app.features.collection.CollectionRepository\nimport com.nuvio.app.features.collection.hiddenCollectionCatalogKeys')
        edit(home,'        val sections = currentDefinitions','''        val hiddenSourceKeys = hiddenCollectionCatalogKeys(
            CollectionRepository.collections.value,
            CollectionRepository.collections.value.filter { preferences["collection_${it.id}"]?.enabled == false }.mapTo(mutableSetOf()) { it.id },
        )
        val sections = currentDefinitions''')
        edit(home,'                if (preference?.enabled == false) return@mapNotNull null','                if (preference?.enabled == false || definition.key in hiddenSourceKeys) return@mapNotNull null')
        # Explicit light system-bar icons match Omnia's dark application surface.
        edit('composeApp/src/androidMain/kotlin/com/nuvio/app/MainActivity.kt','        enableEdgeToEdge(\n            navigationBarStyle','        enableEdgeToEdge(\n            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),\n            navigationBarStyle')
    else:
        home=prefix+'ui/screens/home/HomeViewModelCatalogPipeline.kt'
        edit(home,'import com.nuvio.tv.domain.model.Collection\n','import com.nuvio.tv.domain.model.Collection\nimport com.nuvio.tv.domain.model.hiddenCollectionCatalogKeys\n')
        edit(home,'    val collectionsSnapshot = collectionsCache.associateBy { "collection_${it.id}" }','''    val collectionsSnapshot = collectionsCache.associateBy { "collection_${it.id}" }
    val hiddenSourceKeys = hiddenCollectionCatalogKeys(
        collectionsCache,
        collectionsCache.filter { "collection_${it.id}" in disabledHomeCatalogKeys }.mapTo(mutableSetOf()) { it.id },
    )''')
        edit(home,'        val computedDisplayRows = orderedRows.map { row ->','        val computedDisplayRows = orderedRows.filterNot { it.legacyKey() in hiddenSourceKeys }.map { row ->')
        edit(home,'            if (key in disabledHomeCatalogKeys) continue','            if (key in disabledHomeCatalogKeys || key in hiddenSourceKeys) continue')
    resource=('composeApp/src/commonMain/composeResources/values/' if mobile else 'app/src/main/res/values/')+'omnia_finish.xml'
    write(resource,'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="collections_editor_hide_source_rows">Hide source catalog rows from Home</string>
    <string name="collections_editor_hide_source_rows_desc">Keep these catalogs inside this Collection and hide their separate Home rows. Turn this off, hide or delete the Collection to restore those rows. Your catalog visibility choices are kept.</string>
</resources>
''')



from pathlib import Path
import sys

def apply_finish_tests(root):
    root=Path(root);mobile=(root/'composeApp').exists()
    if mobile:
        package='com.nuvio.app.features.collection'
        source='CollectionSource(addonId = addon, type = type, catalogId = catalog)'
        expected='"a:movie:c"'
        main='Collection("one", "First", hideSourceRows = hidden, folders = listOf(CollectionFolder("folder", "Titles", sources = listOf(source))))'
        imports='import kotlin.test.Test\nimport kotlin.test.assertEquals\nimport kotlin.test.assertFalse\nimport kotlin.test.assertTrue\nimport kotlinx.serialization.json.Json\nimport kotlinx.serialization.decodeFromString\nimport kotlinx.serialization.encodeToString'
        encode='Json.encodeToString(value)';decode='Json.decodeFromString<Collection>(payload)'
        extra='''
    @Test fun legacyCatalogSourcesAlsoHide() {
        val value = Collection("one", "First", hideSourceRows = true, folders = listOf(
            CollectionFolder("f", "Legacy", catalogSources = listOf(CollectionCatalogSource("a", "movie", "c")))
        ))
        assertEquals(setOf("a:movie:c"), hiddenCollectionCatalogKeys(listOf(value), emptySet()))
    }
'''
        target='composeApp/src/commonTest/kotlin/com/nuvio/app/features/collection/HiddenCollectionCatalogsTest.kt'
    else:
        package='com.nuvio.tv.domain.model'
        source='AddonCatalogCollectionSource(addonId = addon, type = type, catalogId = catalog)'
        expected='catalogRowLegacyKey("a", "movie", "c")'
        main='Collection("one", "First", hideSourceRows = hidden, folders = listOf(CollectionFolder("folder", "Titles", sources = listOf(source))))'
        imports='import org.junit.Test\nimport org.junit.Assert.assertEquals\nimport org.junit.Assert.assertFalse\nimport org.junit.Assert.assertTrue\nimport com.google.gson.Gson'
        # Exercise the actual persistence codec, including source polymorphism.
        imports+='\nimport com.nuvio.tv.data.local.CollectionsDataStore\nimport io.mockk.mockk'
        encode='CollectionsDataStore(mockk(relaxed = true), mockk(relaxed = true), mockk(relaxed = true)).exportToJson(listOf(value))'
        decode='CollectionsDataStore(mockk(relaxed = true), mockk(relaxed = true), mockk(relaxed = true)).importFromJson(payload).single()'
        extra=''
        target='app/src/test/java/com/nuvio/tv/domain/model/HiddenCollectionCatalogsTest.kt'
    code=f'''package {package}

{imports}

class HiddenCollectionCatalogsTest {{
    private fun collection(hidden: Boolean = true, addon: String = "a", type: String = "movie", catalog: String = "c"): Collection {{
        val source = {source}
        return {main}
    }}
    @Test fun optInOnly() {{
        assertTrue(hiddenCollectionCatalogKeys(listOf(collection(false)), emptySet()).isEmpty())
        assertEquals(setOf({expected}), hiddenCollectionCatalogKeys(listOf(collection()), emptySet()))
    }}
    @Test fun disabledCollectionDoesNotHideHomeCatalogs() {{
        assertTrue(hiddenCollectionCatalogKeys(listOf(collection()), setOf("one")).isEmpty())
    }}
    @Test fun disablingOrDeletingRestoresRows() {{
        val original = collection()
        assertTrue(hiddenCollectionCatalogKeys(listOf(original.copy(hideSourceRows = false)), emptySet()).isEmpty())
        assertTrue(hiddenCollectionCatalogKeys(emptyList(), emptySet()).isEmpty())
        assertEquals(1, original.folders.single().sources.size)
    }}
    @Test fun profileInputDoesNotLeakToAnotherProfile() {{
        val first = hiddenCollectionCatalogKeys(listOf(collection()), emptySet())
        val second = hiddenCollectionCatalogKeys(listOf(collection(false)), emptySet())
        assertEquals(1, first.size)
        assertTrue(second.isEmpty())
    }}
    @Test fun catalogIdentityKeepsOtherTypesAndProvidersDistinct() {{
        val keys = hiddenCollectionCatalogKeys(listOf(collection(), collection(addon = "b"), collection(type = "series")), emptySet())
        assertEquals(3, keys.size)
    }}
    @Test fun duplicatesDoNotMutateSourcesOrCatalogPreferences() {{
        val value = collection()
        assertEquals(1, hiddenCollectionCatalogKeys(listOf(value, value.copy(id = "two")), emptySet()).size)
        assertEquals(1, value.folders.single().sources.size)
        assertTrue(value.hideSourceRows)
    }}
    @Test fun persistenceRetainsFlagAndSources() {{
        val value = collection()
        val payload = {encode}
        val decoded = {decode}
        assertTrue(decoded.hideSourceRows)
        assertEquals(value.folders, decoded.folders)
        assertFalse(Collection("old", "Legacy").hideSourceRows)
    }}
{extra}
}}
'''
    p=root/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(code,encoding='utf-8',newline='\n')



from pathlib import Path
import re,sys

def apply_reset_batch(root):
    root=Path(root);mobile=(root/'composeApp').exists()
    def edit(rel,old,new):
        p=root/rel;s=p.read_text(encoding='utf-8')
        if new in s:return
        assert s.count(old)==1,(rel,s.count(old),old[:80])
        p.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
    def write(rel,text):
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')
    if mobile:
        common='composeApp/src/commonMain/kotlin/com/nuvio/app/'
        for category,obj in [('player','PlayerSettingsStorage'),('settings','ThemeSettingsStorage')]:
            edit(common+f'features/{category}/{obj}.kt',f'internal expect object {obj} {{',f'internal expect object {obj} {{\n    fun resetProfilePreferences()')
            for platform in ['android','ios']:
                rel=f'composeApp/src/{platform}Main/kotlin/com/nuvio/app/features/{category}/{obj}.{platform}.kt'
                p=root/rel;s=p.read_text(encoding='utf-8')
                if 'actual fun resetProfilePreferences()' in s:continue
                constants=re.findall(r'private const val (\w+) = "([^"\n]+)"',s)
                # Remove only declared preference keys for this profile, retaining
                # credentials, pending external playback and device brightness.
                keys=[name for name,value in constants if name!='preferencesName' and name not in {'pendingExternalPlaybackKey','playbackBrightnessKey','selectedAppLanguageKey'} and not re.search(r'(api_key|client_id|token|password|secret)',value,re.I)]
                assert len(keys)>50 if category=='player' else len(keys)>=6
                values=', '.join(keys)
                if platform=='android':
                    body=f'''    actual fun resetProfilePreferences() {{
        val editor = requireNotNull(preferences) {{ "Preferences are not initialized" }}.edit()
        listOf({values}).forEach {{ editor.remove(ProfileScopedKey.of(it)) }}
        check(editor.commit()) {{ "Unable to save reset preferences" }}
    }}

'''
                else:
                    body=f'''    actual fun resetProfilePreferences() {{
        val defaults = NSUserDefaults.standardUserDefaults
        listOf({values}).forEach {{ defaults.removeObjectForKey(ProfileScopedKey.of(it)) }}
    }}

'''
                marker=f'actual object {obj} {{';assert marker in s
                s=s.replace(marker,marker+'\n'+body,1);p.write_text(s,encoding='utf-8',newline='\n')
        write(common+'features/settings/OmniaPreferenceResetter.kt','''package com.nuvio.app.features.settings

import com.nuvio.app.features.player.PlayerSettingsStorage
import com.nuvio.app.features.player.PlayerSettingsRepository
import com.nuvio.app.features.home.HomeCatalogSettingsRepository
import com.nuvio.app.features.details.MetaScreenSettingsRepository
import com.nuvio.app.core.ui.PosterCardStyleRepository
import com.nuvio.app.core.ui.CardDepthStyleRepository
import com.nuvio.app.features.watchprogress.ContinueWatchingPreferencesRepository
import com.nuvio.app.features.watchprogress.ContinueWatchingSectionStyle
import com.nuvio.app.features.watchprogress.ContinueWatchingSortMode

/** No account, add-on, collection, library, history or provider storage is cleared. */
internal object OmniaPreferenceResetter {
    fun reset() {
        PlayerSettingsStorage.resetProfilePreferences()
        ThemeSettingsStorage.resetProfilePreferences()
        PlayerSettingsRepository.onProfileChanged()
        ThemeSettingsRepository.onProfileChanged()
        HomeCatalogSettingsRepository.resetToDefaults()
        MetaScreenSettingsRepository.resetToDefaults()
        PosterCardStyleRepository.resetToDefaults()
        CardDepthStyleRepository.resetToDefaults()
        ContinueWatchingPreferencesRepository.setVisible(true)
        ContinueWatchingPreferencesRepository.setStyle(ContinueWatchingSectionStyle.Card)
        ContinueWatchingPreferencesRepository.setUpNextFromFurthestEpisode(true)
        ContinueWatchingPreferencesRepository.setUseEpisodeThumbnails(true)
        ContinueWatchingPreferencesRepository.setShowUnairedNextUp(true)
        ContinueWatchingPreferencesRepository.setBlurNextUp(false)
        ContinueWatchingPreferencesRepository.setShowResumePromptOnLaunch(true)
        ContinueWatchingPreferencesRepository.setSortMode(ContinueWatchingSortMode.DEFAULT)
    }
}
''')
        write(common+'features/settings/OmniaResetSettingsControl.kt','''package com.nuvio.app.features.settings

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun OmniaResetSettingsControl(isTablet: Boolean) {
    var confirm by rememberSaveable { mutableStateOf(false) }
    var result by rememberSaveable { mutableStateOf<String?>(null) }
    val done = stringResource(Res.string.omnia_reset_done)
    val failed = stringResource(Res.string.omnia_reset_failed)
    SettingsNavigationRow(
        title = stringResource(Res.string.omnia_reset_title),
        description = result ?: stringResource(Res.string.omnia_reset_description),
        isTablet = isTablet,
        onClick = { confirm = true },
    )
    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text(stringResource(Res.string.omnia_reset_title)) },
            text = { Text(stringResource(Res.string.omnia_reset_confirmation)) },
            confirmButton = {
                TextButton(onClick = {
                    confirm = false
                    result = runCatching { OmniaPreferenceResetter.reset() }.fold({ done }, { failed })
                }) { Text(stringResource(Res.string.omnia_reset_confirm)) }
            },
            dismissButton = { TextButton(onClick = { confirm = false }) { Text(stringResource(Res.string.omnia_reset_cancel)) } },
        )
    }
}
''')
        edit(common+'features/settings/AdvancedSettingsPage.kt','    item {\n        SettingsSection(title = "Add-on diagnostics"','    item { OmniaResetSettingsControl(isTablet) }\n    item {\n        SettingsSection(title = "Add-on diagnostics"')
    else:
        prefix='app/src/main/java/com/nuvio/tv/'
        write(prefix+'data/local/OmniaPreferenceResetter.kt','''package com.nuvio.tv.data.local

import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import com.nuvio.tv.core.profile.ProfileManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

internal val omniaResetPreferenceFeatures = listOf("layout_settings", "player_settings", "theme_settings")

@Singleton
class OmniaPreferenceResetter @Inject constructor(
    private val factory: ProfileDataStoreFactory,
    private val profiles: ProfileManager,
) {
    suspend fun reset() = withContext(Dispatchers.IO) {
        // Capture once: a profile switch cannot redirect a later write.
        val profileId = profiles.activeProfileId.value
        omniaResetPreferenceFeatures.forEach { feature ->
            factory.get(profileId, feature).edit { prefs ->
                prefs.clear()
                if (feature == "layout_settings") prefs[booleanPreferencesKey("has_chosen_layout")] = true
            }
        }
    }
}
''')
        write(prefix+'ui/screens/settings/OmniaResetSettingsControl.kt','''package com.nuvio.tv.ui.screens.settings

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Restore
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.tv.R
import com.nuvio.tv.data.local.OmniaPreferenceResetter
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class OmniaResetPreferencesViewModel @Inject constructor(private val resetter: OmniaPreferenceResetter) : ViewModel() {
    private val _state = MutableStateFlow("idle")
    val state = _state.asStateFlow()
    fun reset() {
        if (_state.value == "resetting") return
        _state.value = "resetting"
        viewModelScope.launch {
            try {
                resetter.reset()
                _state.value = "done"
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (_: Exception) { _state.value = "failed" }
        }
    }
}

@Composable
internal fun OmniaResetSettingsControl(viewModel: OmniaResetPreferencesViewModel = hiltViewModel()) {
    var confirm by rememberSaveable { mutableStateOf(false) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    SettingsGroupCard {
        SettingsActionRow(
            title = stringResource(R.string.omnia_reset_title),
            subtitle = stringResource(when (state) {
                "resetting" -> R.string.omnia_reset_progress
                "done" -> R.string.omnia_reset_done
                "failed" -> R.string.omnia_reset_failed
                else -> R.string.omnia_reset_description
            }),
            leadingIcon = Icons.Default.Restore,
            onClick = { if (state != "resetting") confirm = true },
        )
    }
    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text(stringResource(R.string.omnia_reset_title)) },
            text = { Text(stringResource(R.string.omnia_reset_confirmation)) },
            confirmButton = { TextButton(onClick = { confirm = false; viewModel.reset() }) { Text(stringResource(R.string.omnia_reset_confirm)) } },
            dismissButton = { TextButton(onClick = { confirm = false }) { Text(stringResource(R.string.omnia_reset_cancel)) } },
        )
    }
}
''')
        edit(prefix+'ui/screens/settings/NetworkSettingsScreen.kt','        item(key = "addon_diagnostics") {','        item(key = "reset_preferences") { OmniaResetSettingsControl() }\n        item(key = "addon_diagnostics") {')
    resource=('composeApp/src/commonMain/composeResources/values/' if mobile else 'app/src/main/res/values/')+'omnia_finish.xml'
    p=root/resource;s=p.read_text(encoding='utf-8')
    if 'name="omnia_reset_title"' not in s:
        s=s.replace('</resources>','''    <string name="omnia_reset_title">Reset settings</string>
    <string name="omnia_reset_description">Restore this profile’s display, playback and Home preferences.</string>
    <string name="omnia_reset_confirmation">Reset this profile’s display, playback and Home preferences to their defaults? Your login, profiles, watch history, library, add-ons, Collections and service credentials will be kept. Language and other profiles’ preferences will be kept.</string>
    <string name="omnia_reset_confirm">Reset preferences</string>
    <string name="omnia_reset_cancel">Cancel</string>
    <string name="omnia_reset_progress">Resetting preferences…</string>
    <string name="omnia_reset_done">Preferences reset. Your account and media data were kept.</string>
    <string name="omnia_reset_failed">Some preferences could not be reset. Please retry.</string>
</resources>''')
        p.write_text(s,encoding='utf-8',newline='\n')



from pathlib import Path
import sys

def apply_reset_tests(root):
    root=Path(root)
    if (root/'composeApp').exists():return
    p=root/'app/src/test/java/com/nuvio/tv/data/local/OmniaPreferenceResetterTest.kt'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('''package com.nuvio.tv.data.local

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.preferencesOf
import androidx.datastore.preferences.core.stringPreferencesKey
import com.nuvio.tv.core.profile.ProfileManager
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class OmniaPreferenceResetterTest {
    private class MemoryStore : DataStore<Preferences> {
        override val data = MutableStateFlow<Preferences>(preferencesOf(stringPreferencesKey("sentinel") to "keep"))
        override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
            transform(data.value).also { data.value = it }
    }

    @Test fun resetsOnlyAppearancePlayerAndHomeOfSelectedProfile() = runBlocking {
        val profile = MutableStateFlow(2)
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns profile
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = omniaResetPreferenceFeatures.associateWith { MemoryStore() }
        every { factory.get(2, any()) } answers { stores.getValue(secondArg()) }
        val protectedAccount = MemoryStore()
        val resetter = OmniaPreferenceResetter(factory, profiles)
        resetter.reset()
        assertEquals(setOf(booleanPreferencesKey("has_chosen_layout")), stores.getValue("layout_settings").data.value.asMap().keys)
        assertTrue(stores.getValue("layout_settings").data.value[booleanPreferencesKey("has_chosen_layout")] == true)
        assertTrue(stores.getValue("player_settings").data.value.asMap().isEmpty())
        assertTrue(stores.getValue("theme_settings").data.value.asMap().isEmpty())
        assertEquals("keep", protectedAccount.data.value[stringPreferencesKey("sentinel")])
        verify(exactly = 3) { factory.get(2, any()) }
        listOf("addons", "collections", "auth", "watch_progress", "library", "debrid_settings").forEach { feature ->
            verify(exactly = 0) { factory.get(any(), feature) }
        }
    }

    @Test fun profileSwitchCannotRedirectAnInFlightReset() = runBlocking {
        val profile = MutableStateFlow(2)
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns profile
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = omniaResetPreferenceFeatures.associateWith { MemoryStore() }
        every { factory.get(2, any()) } answers { profile.value = 3; stores.getValue(secondArg()) }
        OmniaPreferenceResetter(factory, profiles).reset()
        verify(exactly = 3) { factory.get(2, any()) }
        verify(exactly = 0) { factory.get(3, any()) }
        assertTrue(stores.getValue("player_settings").data.value.asMap().isEmpty())
    }

    @Test fun repeatedResetKeepsTheDeviceOnboarded() = runBlocking {
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns MutableStateFlow(1)
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = omniaResetPreferenceFeatures.associateWith { MemoryStore() }
        every { factory.get(1, any()) } answers { stores.getValue(secondArg()) }
        val resetter = OmniaPreferenceResetter(factory, profiles)
        resetter.reset();val snapshot = stores.mapValues { it.value.data.value }
        resetter.reset()
        assertEquals(snapshot, stores.mapValues { it.value.data.value })
    }
}
''',encoding='utf-8',newline='\n')



from pathlib import Path
import re,sys

def apply_provider_navigation(root):
    root=Path(root);mobile=(root/'composeApp').exists()
    def edit(rel,old,new,count=1):
        p=root/rel;s=p.read_text(encoding='utf-8')
        if new in s:return
        assert s.count(old)==count,(rel,s.count(old),old[:80])
        p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')
    if mobile:
        base='composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/'
        edit(base+'SettingsModels.kt','''    Plugins(
        titleRes = Res.string.compose_settings_page_plugins,
        category = SettingsCategory.Watch,
        parentPage = ContentDiscovery,''','''    Plugins(
        titleRes = Res.string.compose_settings_page_plugins,
        category = SettingsCategory.Watch,
        parentPage = Addons,''')
        edit(base+'SettingsScreen.kt','showPluginsEntry = AppFeaturePolicy.pluginsEnabled,','showPluginsEntry = false,',count=2)
        p=root/base/'SettingsScreen.kt';s=p.read_text(encoding='utf-8')
        needle='SettingsPage.Addons -> addonsSettingsContent()'
        if needle in s:
            assert s.count(needle)==2
            s=s.replace(needle,'SettingsPage.Addons -> addonsSettingsContent(onPluginsClick = onPluginsClick)',1)
            s=s.replace(needle,'SettingsPage.Addons -> addonsSettingsContent(onPluginsClick = { openInlinePage(SettingsPage.Plugins) }, isTablet = true)',1)
            p.write_text(s,encoding='utf-8',newline='\n')
        p=root/base/'AddonsSettingsPage.kt';s=p.read_text(encoding='utf-8')
        if 'onPluginsClick: () -> Unit' not in s:
            s=s.replace('internal fun LazyListScope.addonsSettingsContent() {','''internal fun LazyListScope.addonsSettingsContent(onPluginsClick: () -> Unit = {}, isTablet: Boolean = false) {
    if (com.nuvio.app.core.build.AppFeaturePolicy.pluginsEnabled) {
        item {
            SettingsNavigationRow(
                title = "Script providers",
                description = "Manage script-based sources, including Omnia India Providers.",
                isTablet = isTablet,
                onClick = onPluginsClick,
            )
        }
    }''',1)
            p.write_text(s,encoding='utf-8',newline='\n')
        # Upgrade a source tree already prepared by the first local iteration.
        p=root/base/'AddonsSettingsPage.kt';s=p.read_text(encoding='utf-8')
        s=s.replace('addonsSettingsContent(onPluginsClick: () -> Unit = {})','addonsSettingsContent(onPluginsClick: () -> Unit = {}, isTablet: Boolean = false)').replace('isTablet = false,','isTablet = isTablet,')
        p.write_text(s,encoding='utf-8',newline='\n')
        p=root/base/'SettingsScreen.kt';s=p.read_text(encoding='utf-8')
        s=s.replace('addonsSettingsContent(onPluginsClick = { openInlinePage(SettingsPage.Plugins) })','addonsSettingsContent(onPluginsClick = { openInlinePage(SettingsPage.Plugins) }, isTablet = true)')
        p.write_text(s,encoding='utf-8',newline='\n')
        resource=root/'composeApp/src/commonMain/composeResources/values/strings.xml'
        if not resource.exists():
            files=list((root/'composeApp/src/commonMain/composeResources/values').glob('*.xml'))
        else:files=[resource]+[p for p in resource.parent.glob('*.xml') if p!=resource]
        for p in files:
            s=p.read_text(encoding='utf-8');n=re.sub(r'(<string name="(?:compose_settings_page_plugins|plugin_title)">).*?(</string>)',r'\g<1>Script providers\2',s)
            if s!=n:p.write_text(n,encoding='utf-8',newline='\n')
    else:
        base='app/src/main/java/com/nuvio/tv/ui/screens/settings/'
        edit(base+'SettingsScreen.kt','showPlugins = AppFeaturePolicy.pluginsEnabled && !isEssentialMode,','showPlugins = false,')
        edit(base+'SettingsScreen.kt','''SettingsCategory.ADDONS -> OmniaAddonsSettingsContent(
            onNavigateToAddons = onNavigateToAddons,''','''SettingsCategory.ADDONS -> OmniaAddonsSettingsContent(
            onNavigateToAddons = onNavigateToAddons,
            onNavigateToPlugins = onNavigateToPlugins,
            showPlugins = AppFeaturePolicy.pluginsEnabled && !isEssentialMode,''')
        p=root/base/'OmniaAddonsSettingsContent.kt';s=p.read_text(encoding='utf-8')
        s=s.replace('onNavigateToAddons: () -> Unit, initialFocusRequester: FocusRequester?','onNavigateToAddons: () -> Unit, onNavigateToPlugins: () -> Unit, showPlugins: Boolean, initialFocusRequester: FocusRequester?')
        if 'Manage script-based sources' not in s:
            marker='''            )
        }
    }
}'''
            assert marker in s
            s=s.replace(marker,'''            )
            if (showPlugins) {
                SettingsActionRow(
                    title = "Script providers",
                    subtitle = "Manage script-based sources, including Omnia India Providers.",
                    leadingIcon = Icons.Default.Extension,
                    onClick = onNavigateToPlugins,
                )
            }
        }
    }
}''',1)
        p.write_text(s,encoding='utf-8',newline='\n')
        p=root/'app/src/main/res/values/strings.xml';s=p.read_text(encoding='utf-8')
        s=re.sub(r'(<string name="plugin_title">).*?(</string>)',r'\g<1>Script providers\2',s)
        p.write_text(s,encoding='utf-8',newline='\n')



apply_finish_batch(ROOT)
apply_finish_tests(ROOT)
apply_reset_batch(ROOT)
apply_reset_tests(ROOT)
apply_provider_navigation(ROOT)
if (ROOT/'composeApp').exists():
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=22\nMARKETING_VERSION=0.4.14\n',encoding='utf-8')
    p=ROOT/'prepare_omnia_ios_tests.py'
    p.write_text(p.read_text(encoding='utf-8').replace('Version 0.4.13 (21)','Version 0.4.14 (22)'),encoding='utf-8')
else:
    p=ROOT/'app/build.gradle.kts'
    s=p.read_text(encoding='utf-8')
    s=re.sub(r'(?m)^(\s*versionCode\s*=\s*)\d+',r'\g<1>22',s,count=1)
    s=re.sub(r'(?m)^(\s*versionName\s*=\s*)"[^"]+"',r'\g<1>"0.3.16"',s,count=1)
    p.write_text(s,encoding='utf-8')
print('Prepared Omnia scoped settings and Collection visibility batch')


# Omnia revision-based add-on synchronization.
from pathlib import Path

MODEL = '''
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OmniaSyncAddon(
    val url: String,
    val name: String = "",
    val enabled: Boolean = true,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
data class OmniaAddonSnapshot(val revision: String, val addons: List<OmniaSyncAddon>)

@Serializable
data class OmniaAddonWriteResult(val conflict: Boolean, val snapshot: OmniaAddonSnapshot)

@Serializable
data class OmniaAddonEnvelope(val acknowledged: OmniaAddonSnapshot, val local: List<OmniaSyncAddon>)

enum class OmniaAddonSyncStatus { Idle, Syncing, Success, Error, SignIn }

/** Configuration paths and query values are case-sensitive and must stay byte-for-byte intact. */
fun omniaAddonKey(url: String): String {
    val value = url.trim()
    val queryAt = value.indexOf('?')
    val path = (if (queryAt < 0) value else value.substring(0, queryAt)).trimEnd('/')
    val query = if (queryAt < 0) "" else value.substring(queryAt)
    return (if (path.endsWith("/manifest.json", ignoreCase = true)) path.dropLast(14).trimEnd('/') else path) + query
}

fun omniaManifestUrl(url: String): String {
    val key = omniaAddonKey(url)
    val queryAt = key.indexOf('?')
    return if (queryAt < 0) "$key/manifest.json" else key.substring(0, queryAt) + "/manifest.json" + key.substring(queryAt)
}

fun omniaNormalizeAddons(rows: List<OmniaSyncAddon>): List<OmniaSyncAddon> = rows
    .distinctBy { omniaAddonKey(it.url) }
    .mapIndexed { index, row -> row.copy(url = omniaAddonKey(row.url), sortOrder = index) }

/** Three-way merge: only explicit edits since this device's last acknowledgement are sent.
 * Unknown remote additions survive. Remote deletion wins over a stale local edit.
 * First contact is authoritative remote state, never a guessed deletion from an old local list.
 */
fun omniaMergeAddons(
    base: List<OmniaSyncAddon>?, local: List<OmniaSyncAddon>, remote: List<OmniaSyncAddon>,
): List<OmniaSyncAddon> {
    val r = omniaNormalizeAddons(remote)
    if (base == null) return r
    val b = omniaNormalizeAddons(base)
    val l = omniaNormalizeAddons(local)
    val bm = b.associateBy { it.url }
    val lm = l.associateBy { it.url }
    val merged = linkedMapOf<String, OmniaSyncAddon>()
    r.forEach { row ->
        val before = bm[row.url]
        val after = lm[row.url]
        if (before != null && after == null) return@forEach // explicit local removal
        merged[row.url] = if (before != null && after != null) row.copy(
            name = if (after.name != before.name) after.name else row.name,
            enabled = if (after.enabled != before.enabled) after.enabled else row.enabled,
        ) else row
    }
    l.filter { it.url !in bm && it.url !in merged }.forEach { merged[it.url] = it }
    val survivingBase = b.map { it.url }.filter { it in lm && it in merged }
    val localBaseOrder = l.map { it.url }.filter { it in bm && it in merged }
    val keys = if (survivingBase != localBaseOrder) {
        l.map { it.url }.filter { it in merged } + merged.keys.filter { it !in lm }
    } else merged.keys.toList()
    return keys.mapIndexed { index, key -> merged.getValue(key).copy(sortOrder = index) }
}
'''

TESTS = '''
class OmniaAddonMergeTest {
    private fun rows(vararg names: String) = names.mapIndexed { i, s -> OmniaSyncAddon("https://$s", sortOrder = i) }
    private fun keys(rows: List<OmniaSyncAddon>) = rows.map { it.url.substringAfter("https://") }
    @Test fun staleDeviceCannotEraseRemoteAddition() {
        assertEquals(listOf("a", "b"), keys(omniaMergeAddons(rows("a"), rows("a"), rows("a", "b"))))
    }
    @Test fun explicitRemovalKeepsUnknownRemoteAddition() {
        assertEquals(listOf("b", "c"), keys(omniaMergeAddons(rows("a", "b"), rows("b"), rows("a", "b", "c"))))
    }
    @Test fun remoteDeletionIsNotResurrectedByStaleEnableEdit() {
        assertEquals(emptyList<String>(), keys(omniaMergeAddons(rows("a"), rows("a").map { it.copy(enabled = false) }, emptyList())))
    }
    @Test fun independentNameAndEnableEditsAreMerged() {
        val before = rows("a")
        val result = omniaMergeAddons(before, before.map { it.copy(enabled = false) }, before.map { it.copy(name = "Remote") }).single()
        assertEquals("Remote", result.name)
        assertEquals(false, result.enabled)
    }
    @Test fun bothDevicesCanAddWithoutLosingEither() {
        assertEquals(listOf("a", "c", "b"), keys(omniaMergeAddons(rows("a"), rows("a", "b"), rows("a", "c"))))
    }
    @Test fun noLocalReorderRetainsRemoteReorder() {
        assertEquals(listOf("b", "a"), keys(omniaMergeAddons(rows("a", "b"), rows("a", "b"), rows("b", "a"))))
    }
    @Test fun explicitLocalReorderKeepsRemoteUnknownItems() {
        assertEquals(listOf("b", "a", "c"), keys(omniaMergeAddons(rows("a", "b"), rows("b", "a"), rows("a", "b", "c"))))
    }
    @Test fun firstContactDoesNotDeleteOrReaddUnknownOldLocalState() {
        assertEquals(listOf("b"), keys(omniaMergeAddons(null, rows("a"), rows("b"))))
    }
    @Test fun explicitEmptyListIsADeletion() {
        assertEquals(listOf("b"), keys(omniaMergeAddons(rows("a"), emptyList(), rows("a", "b"))))
    }
    @Test fun queryCaseAndTrailingSlashArePreserved() {
        val value = "https://a/manifest.json?key=AbC/"
        assertEquals("https://a?key=AbC/", omniaAddonKey(value))
        assertEquals(value, omniaManifestUrl(value))
        assertEquals(2, omniaNormalizeAddons(rows("a?key=AbC/", "a?key=abc/")).size)
    }
    @Test fun aliasesDeduplicateAndReindexWithoutMutatingInputs() {
        val input = listOf(OmniaSyncAddon("https://a/manifest.json", sortOrder = 7), OmniaSyncAddon("https://a", sortOrder = 8))
        assertEquals(listOf(OmniaSyncAddon("https://a")), omniaNormalizeAddons(input))
        assertEquals(7, input.first().sortOrder)
    }
    @Test fun secondMergeRetainsNewerLocalMutationDuringRequest() {
        val sent = rows("a", "b")
        val accepted = rows("a", "c", "b")
        assertEquals(listOf("c", "b"), keys(omniaMergeAddons(sent, rows("b"), accepted))))
    }
    @Test fun acknowledgedStateRoundTripsWithoutChangingQueries() {
        val envelope = OmniaAddonEnvelope(OmniaAddonSnapshot("f".repeat(64), rows("a?key=AbC/")), rows("a?key=AbC/", "b"))
        assertEquals(envelope, kotlinx.serialization.json.Json.decodeFromString<OmniaAddonEnvelope>(kotlinx.serialization.json.Json.encodeToString(envelope)))
    }
}
'''.replace('accepted))))', 'accepted)))')

TV_STORE_TESTS = '''package com.nuvio.tv.data.local

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.core.sync.*
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class OmniaAddonSyncStorageTest {
    private class MemoryStore : DataStore<Preferences> {
        override val data = MutableStateFlow<Preferences>(emptyPreferences())
        override suspend fun updateData(transform: suspend (Preferences) -> Preferences): Preferences =
            transform(data.value).also { data.value = it }
    }
    private fun fixture(): AddonPreferences {
        val profiles = mockk<ProfileManager>()
        every { profiles.activeProfileId } returns MutableStateFlow(1)
        every { profiles.profiles } returns MutableStateFlow(emptyList())
        every { profiles.activeProfile } returns null
        val factory = mockk<ProfileDataStoreFactory>()
        val stores = mutableMapOf<Int, MemoryStore>()
        every { factory.get(any(), "addon_preferences") } answers { stores.getOrPut(firstArg()) { MemoryStore() } }
        return AddonPreferences(factory, profiles)
    }
    private fun snapshot(vararg rows: OmniaSyncAddon) = OmniaAddonSnapshot("f".repeat(64), rows.toList())
    @Test fun acknowledgedMetadataAndExplicitEmptyListAreAppliedAtomically() = runBlocking {
        val preferences = fixture()
        val remote = snapshot(OmniaSyncAddon("https://a?key=AbC/", "Named", false))
        preferences.acceptSyncSnapshot("owner", 1, remote, null)
        assertEquals(remote, preferences.readSyncState("owner", 1).second)
        assertEquals(remote.addons, preferences.readSyncState("owner", 1).first)
        preferences.acceptSyncSnapshot("owner", 1, snapshot(), remote.addons)
        assertTrue(preferences.readSyncState("owner", 1).first.isEmpty())
    }
    @Test fun localMutationDuringNetworkRequestRemainsPending() = runBlocking {
        val preferences = fixture()
        val original = snapshot(OmniaSyncAddon("https://a"))
        preferences.acceptSyncSnapshot("owner", 1, original, null)
        preferences.addAddon("https://b/manifest.json")
        val accepted = snapshot(OmniaSyncAddon("https://a"), OmniaSyncAddon("https://c", sortOrder=1))
        preferences.acceptSyncSnapshot("owner", 1, accepted, original.addons)
        val state = preferences.readSyncState("owner", 1)
        assertEquals(listOf("https://a", "https://c", "https://b"), state.first.map { it.url })
        assertEquals(accepted, state.second)
    }
    @Test fun acknowledgementCannotLeakAcrossOwnersOrProfiles() = runBlocking {
        val preferences = fixture()
        preferences.acceptSyncSnapshot("first", 1, snapshot(OmniaSyncAddon("https://a")), null)
        assertNull(preferences.readSyncState("second", 1).second)
        assertNull(preferences.readSyncState("first", 2).second)
    }
    @Test fun configuredUrlsWithDifferentCaseAreSeparateInstallations() = runBlocking {
        val preferences = fixture()
        preferences.acceptSyncSnapshot("owner", 1, snapshot(), null)
        assertTrue(preferences.addAddon("https://a/manifest.json?key=AbC/"))
        assertTrue(preferences.addAddon("https://a/manifest.json?key=abc/"))
        assertTrue(preferences.removeAddon("https://a/manifest.json?key=AbC/"))
        assertEquals(listOf("https://a?key=abc/"), preferences.readSyncState("owner", 1).first.map { it.url })
    }
    @Test fun reorderingAnOlderUiListCannotDropNewlySyncedRows() = runBlocking {
        val preferences = fixture()
        preferences.acceptSyncSnapshot("owner", 1, snapshot(OmniaSyncAddon("https://a"), OmniaSyncAddon("https://b",sortOrder=1), OmniaSyncAddon("https://c",sortOrder=2)), null)
        preferences.setAddonOrder(listOf("https://b", "https://a"))
        assertEquals(listOf("https://b", "https://a", "https://c"), preferences.readSyncState("owner", 1).first.map { it.url })
    }
}
'''

def replace_once(text, old, new):
    if new in text:
        return text
    assert old in text, old[:160]
    return text.replace(old, new, 1)

def apply_sync_models(root, tv):
    root = Path(root)
    package = 'com.nuvio.tv.core.sync' if tv else 'com.nuvio.app.features.addons'
    folder = root / ('app/src/main/java/com/nuvio/tv/core/sync' if tv else 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons')
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'OmniaAddonSyncPolicy.kt').write_text('package '+package+'\n'+MODEL, encoding='utf-8')
    tests = root / ('app/src/test/java/com/nuvio/tv/core/sync' if tv else 'composeApp/src/commonTest/kotlin/com/nuvio/app/features/addons')
    tests.mkdir(parents=True, exist_ok=True)
    imports = 'import org.junit.Test\nimport org.junit.Assert.assertEquals\n' if tv else 'import kotlin.test.Test\nimport kotlin.test.assertEquals\n'
    (tests/'OmniaAddonMergeTest.kt').write_text('package '+package+'\n'+imports+'import kotlinx.serialization.encodeToString\n'+TESTS, encoding='utf-8')
    if tv:
        test = root/'app/src/test/java/com/nuvio/tv/data/local/OmniaAddonSyncStorageTest.kt'
        test.write_text(TV_STORE_TESTS,encoding='utf-8')

TV_SERVICE = '''package com.nuvio.tv.core.sync

import com.nuvio.tv.core.auth.AuthManager
import com.nuvio.tv.core.profile.ProfileManager
import com.nuvio.tv.data.local.AddonPreferences
import com.nuvio.tv.domain.model.AuthState
import io.github.jan.supabase.postgrest.Postgrest
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AddonSyncService @Inject constructor(
    private val postgrest: Postgrest,
    private val authManager: AuthManager,
    private val addonPreferences: AddonPreferences,
    private val profileManager: ProfileManager,
    private val syncClientIdentity: SyncClientIdentity,
) {
    private val syncMutex = Mutex()
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    private data class Scope(val owner: String, val selected: Int, val profile: Int, val readOnly: Boolean)
    private fun captureScope(): Scope {
        val owner = (authManager.authState.value as? AuthState.FullAccount)?.userId
            ?: error("Sign in to sync add-ons")
        val selected = profileManager.activeProfileId.value
        val active = profileManager.activeProfile
        val readOnly = active != null && !active.isPrimary && active.usesPrimaryAddons
        return Scope(owner, selected, if (readOnly) 1 else selected, readOnly)
    }
    private fun checkScope(expected: Scope) {
        check(captureScope() == expected) { "Account or profile changed; sync again" }
    }
    private suspend fun <T> request(expected: Scope, block: suspend () -> T): T {
        checkScope(expected)
        return try { block() } catch (error: CancellationException) { throw error }
        catch (error: Exception) {
            checkScope(expected)
            if (!authManager.refreshSessionIfJwtExpired(error)) throw error
            checkScope(expected)
            block()
        }.also { checkScope(expected) }
    }

    /** Establish a server baseline before the first signed-in edit. Offline edits after that
     * baseline remain local and are merged on the next successful sync. */
    suspend fun ensureReadyForEdit() {
        if (authManager.authState.value !is AuthState.FullAccount) return
        val expected = captureScope()
        if (expected.readOnly) return
        if (addonPreferences.readSyncState(expected.owner, expected.profile).second == null) {
            synchronize().getOrThrow()
        }
    }

    suspend fun pushToRemote(): Result<Unit> = synchronize().map { Unit }
    suspend fun getRemoteAddonUrls(): Result<List<String>> = synchronize()

    private suspend fun synchronize(): Result<List<String>> = withContext(Dispatchers.IO) {
        try {
            Result.success(syncMutex.withLock {
                val expected = captureScope()
                val (local, acknowledged) = addonPreferences.readSyncState(expected.owner, expected.profile)
                var remote = request(expected) {
                    postgrest.rpc("sync_pull_addons_v2", buildJsonObject { put("p_profile_id", expected.profile); put("p_expected_owner", expected.owner) })
                        .decodeAs<OmniaAddonSnapshot>()
                }
                val base = acknowledged?.addons
                val desired = omniaMergeAddons(base, local, remote.addons)
                if (expected.readOnly || desired == omniaNormalizeAddons(remote.addons)) {
                    checkScope(expected)
                    return@withLock addonPreferences.acceptSyncSnapshot(expected.owner, expected.profile, remote, base)
                }
                repeat(4) {
                    checkScope(expected)
                    val merged = omniaMergeAddons(base, local, remote.addons)
                    val response = request(expected) {
                        postgrest.rpc("sync_push_addons_v2", buildJsonObject {
                            put("p_profile_id", expected.profile)
                            put("p_expected_owner", expected.owner)
                            put("p_expected_revision", remote.revision)
                            put("p_addons", json.encodeToJsonElement(merged))
                            putSyncOriginClientId(syncClientIdentity)
                        }).decodeAs<OmniaAddonWriteResult>()
                    }
                    if (!response.conflict) {
                        checkScope(expected)
                        // Preserve edits made locally while this request was in flight.
                        return@withLock addonPreferences.acceptSyncSnapshot(expected.owner, expected.profile, response.snapshot, local)
                    }
                    remote = response.snapshot
                }
                error("Add-ons changed on another device; sync again")
            })
        } catch (error: CancellationException) { throw error }
        catch (error: Exception) { Result.failure(error) }
    }
}
'''

TV_STORAGE = '''
    private val syncJson = kotlinx.serialization.json.Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private fun syncKey(owner: String) = stringPreferencesKey("omnia_addon_sync_$owner")

    private fun syncRows(preferences: Preferences): List<com.nuvio.tv.core.sync.OmniaSyncAddon> {
        val names = preferences[userSetNamesKey]?.let(::parseNameMap).orEmpty()
        val enabled = getCurrentEnabledStates(preferences)
        return getCurrentList(preferences).mapIndexed { index, url ->
            val key = com.nuvio.tv.core.sync.omniaAddonKey(url)
            com.nuvio.tv.core.sync.OmniaSyncAddon(key, names[key].orEmpty(), enabled[key] ?: true, index)
        }
    }

    suspend fun readSyncState(owner: String, profileId: Int): Pair<List<com.nuvio.tv.core.sync.OmniaSyncAddon>, com.nuvio.tv.core.sync.OmniaAddonSnapshot?> {
        val preferences = store(profileId).data.first()
        val acknowledged = preferences[syncKey(owner)]?.let {
            syncJson.decodeFromString<com.nuvio.tv.core.sync.OmniaAddonSnapshot>(it)
        }
        return syncRows(preferences) to acknowledged
    }

    suspend fun acceptSyncSnapshot(owner: String, profileId: Int, snapshot: com.nuvio.tv.core.sync.OmniaAddonSnapshot, beforeRequest: List<com.nuvio.tv.core.sync.OmniaSyncAddon>?): List<String> {
        var urls = emptyList<String>()
        store(profileId).edit { preferences ->
            val merged = com.nuvio.tv.core.sync.omniaMergeAddons(beforeRequest, syncRows(preferences), snapshot.addons)
            urls = merged.map { it.url }
            preferences[orderedUrlsKey] = gson.toJson(urls)
            preferences[addonEnabledStatesKey] = gson.toJson(merged.associate { it.url to it.enabled })
            preferences[userSetNamesKey] = gson.toJson(merged.filter { it.name.isNotBlank() }.associate { it.url to it.name })
            preferences[syncKey(owner)] = syncJson.encodeToString(com.nuvio.tv.core.sync.OmniaAddonSnapshot.serializer(), snapshot)
            preferences.remove(legacyUrlsKey)
        }
        return urls
    }
'''

def apply_tv_sync(root):
    root = Path(root)
    base = root/'app/src/main/java/com/nuvio/tv'
    (base/'core/sync/AddonSyncService.kt').write_text(TV_SERVICE, encoding='utf-8')
    path = base/'data/local/AddonPreferences.kt'
    text = path.read_text(encoding='utf-8')
    if 'private val syncJson' not in text:
        text = text.replace('    private fun getDefaultAddons()', TV_STORAGE+'\n    private fun getDefaultAddons()',1)
    text = text.replace("url.trim().trimEnd('/')", 'url.trim()')
    text = text.replace('canonicalizeUrl(it).equals(normalizedUrl, ignoreCase = true)', 'canonicalizeUrl(it) == normalizedUrl')
    path.write_text(text, encoding='utf-8')

    path = base/'data/repository/AddonRepositoryImpl.kt'
    text = path.read_text(encoding='utf-8')
    text = text.replace("url.trim().trimEnd('/')", 'url.trim()').replace('canonicalizeUrl(url).lowercase()', 'canonicalizeUrl(url)')
    if '        if (isSyncingFromRemote) {' in text:
        start = text.index('        if (isSyncingFromRemote) {', text.index('private fun triggerRemoteSync'))
        end = text.index('        if (!authManager.isAuthenticated)', start)
        text = text[:start]+text[end:]
    # Do not log server exception messages: they may contain configured manifest URLs.
    text = text.replace('${result.exceptionOrNull()?.message ?: ""}', '${result.exceptionOrNull()?.javaClass?.simpleName ?: ""}')
    for signature in ['override suspend fun addAddon(url: String)', 'override suspend fun removeAddon(url: String)', 'override suspend fun setAddonOrder(urls: List<String>)', 'override suspend fun setAddonEnabled(url: String, enabled: Boolean)']:
        old = signature+' {'
        text = replace_once(text, old, old+'\n        addonSyncService.ensureReadyForEdit()')
    path.write_text(text, encoding='utf-8')
    # Sync service now atomically applies the snapshot and metadata. Reapplying a captured URL
    # list here would race a new local edit and also mishandle an explicitly empty server list.
    path = base/'core/sync/StartupSyncService.kt'
    text = path.read_text(encoding='utf-8')
    import re
    text, count = re.subn(r'\s*addonRepository.reconcileWithRemoteAddonUrls\(\s*remoteUrls = remoteAddonUrls,\s*removeMissingLocal = (?:true|!initialAccountLink)\s*\)', '\n                // AddonSyncService applies the acknowledged snapshot atomically.\n', text)
    assert count == 3 or 'AddonSyncService applies the acknowledged snapshot atomically.' in text, count
    path.write_text(text, encoding='utf-8')


def span(text, start, end, replacement):
    a = text.index(start)
    b = text.index(end, a)
    return text[:a].rstrip('\n')+'\n\n'+replacement.strip('\n')+'\n\n'+text[b:]

SHARED_SYNC = '''
    private val syncMutex = kotlinx.coroutines.sync.Mutex()
    private val _syncStatus = MutableStateFlow(OmniaAddonSyncStatus.Idle)
    val syncStatus: StateFlow<OmniaAddonSyncStatus> = _syncStatus.asStateFlow()
    private data class SyncScope(val owner: String?, val selected: Int, val profile: Int, val readOnly: Boolean)
    private fun captureScope(): SyncScope {
        val auth = com.nuvio.app.core.auth.AuthRepository.state.value as? com.nuvio.app.core.auth.AuthState.Authenticated
        val selected = ProfileRepository.activeProfileId
        return SyncScope(auth?.takeUnless { it.isAnonymous }?.userId, selected, resolveEffectiveProfileId(selected), isUsingPrimaryAddonsFromSecondaryProfile())
    }
    private fun checkScope(expected: SyncScope) {
        check(captureScope() == expected && currentProfileId == expected.profile) { "Account or profile changed; sync again" }
    }
    private fun readEnvelope(expected: SyncScope): OmniaAddonEnvelope? = expected.owner?.let { owner ->
        AddonStorage.loadSyncEnvelope(owner, expected.profile)?.let { json.decodeFromString<OmniaAddonEnvelope>(it) }
    }
    private fun localSyncRows(): List<OmniaSyncAddon> = _uiState.value.addons.mapIndexed { i, addon ->
        OmniaSyncAddon(omniaAddonKey(addon.manifestUrl), addon.userSetName.orEmpty(), addon.enabled, i)
    }
    private fun applySnapshot(expected: SyncScope, snapshot: OmniaAddonSnapshot, beforeRequest: List<OmniaSyncAddon>?) {
        checkScope(expected)
        val rows = omniaMergeAddons(beforeRequest, localSyncRows(), snapshot.addons)
        // One durable envelope holds BOTH acknowledged state and unsent local changes. URL/name
        // values stay private in the app sandbox. Owner and profile are part of the storage key.
        AddonStorage.saveSyncEnvelope(expected.owner!!, expected.profile, json.encodeToString(OmniaAddonEnvelope.serializer(), OmniaAddonEnvelope(snapshot, rows)))
        val existing = _uiState.value.addons.associateBy { omniaAddonKey(it.manifestUrl) }
        _uiState.value = _uiState.value.copy(addons = rows.map { row ->
            existing[row.url].toPendingAddon(omniaManifestUrl(row.url), row.name, row.enabled)
        })
        persist(expected)
        initialized = true
        refreshAll()
    }
    private suspend fun syncLocked(expected: SyncScope) {
        checkScope(expected)
        check(expected.owner != null) { "Sign in to sync add-ons" }
        val envelope = readEnvelope(expected)
        val local = localSyncRows()
        val base = envelope?.acknowledged?.addons
        var remote = SupabaseProvider.client.postgrest.rpc("sync_pull_addons_v2", buildJsonObject {
            put("p_profile_id", expected.profile)
            put("p_expected_owner", expected.owner)
        }).decodeAs<OmniaAddonSnapshot>()
        checkScope(expected)
        if (expected.readOnly || omniaMergeAddons(base, local, remote.addons) == omniaNormalizeAddons(remote.addons)) {
            applySnapshot(expected, remote, base)
            return
        }
        repeat(4) {
            checkScope(expected)
            val merged = omniaMergeAddons(base, local, remote.addons)
            val response = SupabaseProvider.client.postgrest.rpc("sync_push_addons_v2", buildJsonObject {
                put("p_profile_id", expected.profile)
                put("p_expected_owner", expected.owner)
                put("p_expected_revision", remote.revision)
                put("p_addons", json.encodeToJsonElement(merged))
                putSyncOriginClientId()
            }).decodeAs<OmniaAddonWriteResult>()
            checkScope(expected)
            if (!response.conflict) {
                applySnapshot(expected, response.snapshot, local)
                return
            }
            remote = response.snapshot
        }
        error("Add-ons changed on another device; sync again")
    }
    private suspend fun ensureReadyForEdit(expected: SyncScope) {
        checkScope(expected)
        if (expected.owner != null && readEnvelope(expected) == null) syncLocked(expected)
    }
    private suspend fun synchronize() {
        syncMutex.withLock {
            initialize()
            val expected = captureScope()
            if (expected.owner == null) { _syncStatus.value = OmniaAddonSyncStatus.SignIn; return@withLock }
            _syncStatus.value = OmniaAddonSyncStatus.Syncing
            try {
                syncLocked(expected)
                _syncStatus.value = OmniaAddonSyncStatus.Success
            } catch (error: CancellationException) { _syncStatus.value = OmniaAddonSyncStatus.Idle; throw error }
            catch (error: Exception) {
                _syncStatus.value = OmniaAddonSyncStatus.Error
                log.e { "Add-on sync failed (${error::class.simpleName})" }
                throw error
            }
        }
    }
    fun syncAddonsNow() {
        if (_syncStatus.value == OmniaAddonSyncStatus.Syncing) return
        scope.launch {
            try { synchronize() } catch (error: CancellationException) { throw error }
            catch (_: Exception) { /* status contains the user-visible retry state */ }
        }
    }
    suspend fun pullFromServer(profileId: Int) {
        if (ProfileRepository.activeProfileId != profileId) return
        try { synchronize() } catch (error: CancellationException) { throw error }
        catch (_: Exception) { /* retain local data and report the failed sync */ }
    }
    private fun launchMutation(change: () -> Unit) {
        val expected = captureScope()
        if (expected.readOnly) return
        scope.launch {
            try {
                syncMutex.withLock {
                    ensureReadyForEdit(expected)
                    checkScope(expected)
                    change()
                    persist(expected)
                    pushToServer()
                }
            } catch (error: CancellationException) { throw error }
            catch (_: Exception) { _syncStatus.value = OmniaAddonSyncStatus.Error }
        }
    }
'''

SHARED_MUTATIONS = '''    fun removeAddon(manifestUrl: String) = launchMutation {
        _uiState.update { current -> current.copy(addons = current.addons.filterNot { omniaAddonKey(it.manifestUrl) == omniaAddonKey(manifestUrl) }) }
    }

    fun moveAddon(fromIndex: Int, toIndex: Int) {
        val rows = _uiState.value.addons
        val moving = rows.getOrNull(fromIndex)?.manifestUrl ?: return
        val anchor = rows.getOrNull(toIndex)?.manifestUrl ?: return
        if (fromIndex == toIndex) return
        launchMutation {
            _uiState.update { current ->
                val addons = current.addons.toMutableList()
                val from = addons.indexOfFirst { it.manifestUrl == moving }
                if (from < 0 || addons.none { it.manifestUrl == anchor }) return@update current
                val item = addons.removeAt(from)
                val target = addons.indexOfFirst { it.manifestUrl == anchor }
                addons.add(target + if (fromIndex < toIndex) 1 else 0, item)
                current.copy(addons = addons)
            }
        }
    }

    fun setAddonEnabled(manifestUrl: String, enabled: Boolean) = launchMutation {
        _uiState.update { current -> current.copy(addons = current.addons.map {
            if (omniaAddonKey(it.manifestUrl) == omniaAddonKey(manifestUrl)) it.copy(enabled = enabled) else it
        }) }
        if (enabled) refreshAddon(manifestUrl)
    }
'''

SHARED_PUSH = '''    private fun pushToServer() {
        val expected = captureScope()
        if (expected.readOnly || expected.owner == null) return
        pushJobsByProfile[expected.profile]?.cancel()
        var pushJob: Job? = null
        pushJob = scope.launch {
            try {
                delay(ADDON_PUSH_DEBOUNCE_MS)
                checkScope(expected)
                synchronize()
            } catch (error: CancellationException) { throw error }
            catch (_: Exception) { _syncStatus.value = OmniaAddonSyncStatus.Error }
            finally {
                if (pushJobsByProfile[expected.profile] === pushJob) pushJobsByProfile.remove(expected.profile)
            }
        }
        pushJobsByProfile[expected.profile] = pushJob
    }
'''

def apply_shared_sync(root):
    root = Path(root)
    base = root/'composeApp/src'
    path = base/'commonMain/kotlin/com/nuvio/app/features/addons/AddonRepository.kt'
    text = path.read_text(encoding='utf-8')
    if 'private val syncMutex' not in text:
        text = text.replace('import kotlinx.coroutines.sync.withLock\n', '')
        text = text.replace('import kotlinx.coroutines.launch\n', 'import kotlinx.coroutines.launch\nimport kotlinx.coroutines.sync.withLock\n')
        text = span(text, '    suspend fun pullFromServer(profileId: Int)', '    suspend fun awaitManifestsLoaded()', SHARED_SYNC)
        text = span(text, '    fun removeAddon(manifestUrl: String)', '    fun refreshAll()', SHARED_MUTATIONS)
        text = span(text, '    private fun pushToServer()', '    private fun markRefreshing(', SHARED_PUSH)
        text = text.replace('        val storedUrls = dedupeManifestUrls(AddonStorage.loadInstalledAddonUrls(currentProfileId))', '''        val envelope = readEnvelope(captureScope())
        val storedUrls = dedupeManifestUrls(envelope?.local?.map { it.url } ?: AddonStorage.loadInstalledAddonUrls(currentProfileId))''')
        text = text.replace('        val enabledByUrl = loadLocalEnabledStates()', '''        val enabledByUrl = envelope?.local?.associate { omniaManifestUrl(it.url) to it.enabled } ?: loadLocalEnabledStates()''',1)
        text = text.replace('                    manifestUrl = manifestUrl,\n                    enabled = enabledByUrl[manifestUrl],', '''                    manifestUrl = manifestUrl,
                    userSetName = envelope?.local?.firstOrNull { omniaManifestUrl(it.url) == manifestUrl }?.name,
                    enabled = enabledByUrl[manifestUrl],''',1)
        # Capture the account before manifest I/O, then recheck it after I/O and baseline loading.
        text = text.replace('        log.i { "addAddon() — install requested" }', '        val installScope = captureScope()\n        log.i { "addAddon() — install requested" }',1)
        start = text.index('        _uiState.update { current ->', text.index('suspend fun addAddon'))
        end = text.index('        return AddAddonResult.Success(manifest)', start)
        original = text[start:end]
        text = text[:start]+'''        return try {
            syncMutex.withLock {
                ensureReadyForEdit(installScope)
                checkScope(installScope)
'''+original+'''                AddAddonResult.Success(manifest)
            }
        } catch (error: CancellationException) { throw error }
        catch (_: Exception) { AddAddonResult.Error("Could not sync add-ons. Check your connection and try again.") }
'''+text[end+len('        return AddAddonResult.Success(manifest)\n'):]
        text = text.replace('        } catch (error: Throwable) {\n            return AddAddonResult.Error', '        } catch (error: CancellationException) { throw error }\n        catch (error: Throwable) {\n            return AddAddonResult.Error',1)
        # Persist the acknowledgement and pending edits together, even while offline.
        text = text.replace('        val addons = _uiState.value.addons\n        AddonStorage.saveInstalledAddonUrls(', '''        val addons = _uiState.value.addons
        val expected = captureScope()
        readEnvelope(expected)?.let { envelope ->
            AddonStorage.saveSyncEnvelope(expected.owner!!, expected.profile, json.encodeToString(OmniaAddonEnvelope.serializer(), envelope.copy(local = localSyncRows())))
        }
        AddonStorage.saveInstalledAddonUrls(''',1)
        text = text.replace('        cancelActiveRefreshes()\n        currentProfileId = effectiveProfileId', '''        cancelActiveRefreshes()
        pushJobsByProfile.values.forEach(Job::cancel)
        pushJobsByProfile.clear()
        _syncStatus.value = OmniaAddonSyncStatus.Idle
        currentProfileId = effectiveProfileId''',1)
        text = text.replace('        currentProfileId = 1\n        initialized = false', '        _syncStatus.value = OmniaAddonSyncStatus.Idle\n        currentProfileId = 1\n        initialized = false',1)
        text = span(text, 'private fun ensureManifestSuffix(url: String)', 'private fun normalizeManifestUrl(rawUrl: String)', 'private fun ensureManifestSuffix(url: String): String = omniaManifestUrl(url)')
    # Rebuild owned protocol functions on a source tree already prepared by an earlier v23
    # iteration, so tightening the server contract does not leave stale request parameters.
    text = span(text, '    private val syncMutex', '    suspend fun awaitManifestsLoaded()', SHARED_SYNC)
    text = span(text, '    private fun pushToServer()', '    private fun markRefreshing(', SHARED_PUSH)
    text = text.replace('    private fun persist() {\n        val addons = _uiState.value.addons\n        val expected = captureScope()', '    private fun persist(expected: SyncScope = captureScope()) {\n        checkScope(expected)\n        val addons = _uiState.value.addons')
    a=text.index('    suspend fun addAddon(');b=text.index('    fun removeAddon(',a)
    text=text[:a]+text[a:b].replace('        persist()','        persist(installScope)')+text[b:]
    path.write_text(text, encoding='utf-8')

    path = base/'commonMain/kotlin/com/nuvio/app/features/addons/AddonPlatform.kt'
    text = path.read_text(encoding='utf-8')
    text = replace_once(text, 'internal expect object AddonStorage {', '''internal expect object AddonStorage {
    fun loadSyncEnvelope(owner: String, profileId: Int): String?
    fun saveSyncEnvelope(owner: String, profileId: Int, payload: String)''')
    path.write_text(text, encoding='utf-8')
    for platform in ['android', 'ios']:
        path = base/f'{platform}Main/kotlin/com/nuvio/app/features/addons/AddonPlatform.{platform}.kt'
        text = path.read_text(encoding='utf-8')
        methods = '''    actual fun loadSyncEnvelope(owner: String, profileId: Int): String? =
        preferences?.getString("omnia_addon_sync_${owner}_$profileId", null)
    actual fun saveSyncEnvelope(owner: String, profileId: Int, payload: String) {
        check(preferences?.edit()?.putString("omnia_addon_sync_${owner}_$profileId", payload)?.commit() == true) { "Could not save add-on changes" }
    }
''' if platform == 'android' else '''    actual fun loadSyncEnvelope(owner: String, profileId: Int): String? =
        NSUserDefaults.standardUserDefaults.stringForKey("omnia_addon_sync_${owner}_$profileId")
    actual fun saveSyncEnvelope(owner: String, profileId: Int, payload: String) {
        NSUserDefaults.standardUserDefaults.setObject(payload, forKey = "omnia_addon_sync_${owner}_$profileId")
    }
'''
        text = replace_once(text, 'actual object AddonStorage {', 'actual object AddonStorage {\n'+methods)
        path.write_text(text, encoding='utf-8')
    path = base/'iosMain/kotlin/com/nuvio/app/core/storage/PlatformLocalAccountDataCleaner.ios.kt'
    text = path.read_text(encoding='utf-8')
    text = replace_once(text, '        "installed_manifest_urls_",', '        "installed_manifest_urls_",\n        "installed_manifest_enabled_states_",')
    text = replace_once(text, 'keyString.startsWith("stream_link_") ||', 'keyString.startsWith("omnia_addon_sync_") ||\n                keyString.startsWith("stream_link_") ||')
    path.write_text(text, encoding='utf-8')
    # The older diagnostics overlay looks for its insertion as a contiguous prefix.
    # Inserting Reset ahead of it made a repeated preparation insert a second copy.
    path = base/'commonMain/kotlin/com/nuvio/app/features/settings/AdvancedSettingsPage.kt'
    text = path.read_text(encoding='utf-8')
    block = '''    item {
        SettingsSection(title = "Add-on diagnostics", isTablet = isTablet) {
            com.nuvio.app.features.addons.OmniaAddonDiagnostics()
        }
    }
'''
    assert block in text
    text = text.replace(block, '')
    marker = '    item { OmniaResetSettingsControl(isTablet) }\n'
    assert marker in text
    path.write_text(text.replace(marker, marker+block, 1), encoding='utf-8')

def apply_sync_ui(root, tv):
    root = Path(root)
    screen = root/('app/src/main/java/com/nuvio/tv/ui/screens/addon/AddonManagerScreen.kt' if tv else 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/AddonsScreen.kt')
    if 'val addonSyncStatus by' in screen.read_text(encoding='utf-8'):
        return
    resources = {
        'omnia_addon_sync_action': 'Sync add-ons',
        'omnia_addon_sync_idle': 'Sync installed add-ons and their order for this profile.',
        'omnia_addon_sync_busy': 'Syncing add-ons…',
        'omnia_addon_sync_done': 'Add-ons synced successfully.',
        'omnia_addon_sync_error': 'Could not sync add-ons. Your saved list is kept. Check your connection and try again.',
        'omnia_addon_sync_signin': 'Sign in to sync add-ons across your devices.',
    }
    from xml.sax.saxutils import escape
    values = root/('app/src/main/res/values' if tv else 'composeApp/src/commonMain/composeResources/values')
    (values/'omnia_sync.xml').write_text('<resources>\n'+''.join(f'    <string name="{key}">{escape(value)}</string>\n' for key,value in resources.items())+'</resources>\n', encoding='utf-8')
    if tv:
        base = root/'app/src/main/java/com/nuvio/tv'
        path = base/'core/sync/StartupSyncService.kt'
        text = path.read_text(encoding='utf-8')
        text = span(text, '    fun requestAddonSyncNow()', '    fun requestRealtimeSurfacePull(', '''    private val _manualAddonSyncStatus = kotlinx.coroutines.flow.MutableStateFlow(OmniaAddonSyncStatus.Idle)
    val manualAddonSyncStatus: kotlinx.coroutines.flow.StateFlow<OmniaAddonSyncStatus> = _manualAddonSyncStatus

    fun requestAddonSyncNow() {
        if (_manualAddonSyncStatus.value == OmniaAddonSyncStatus.Syncing) return
        if (!authManager.isAuthenticated) {
            _manualAddonSyncStatus.value = OmniaAddonSyncStatus.SignIn
            return
        }
        _manualAddonSyncStatus.value = OmniaAddonSyncStatus.Syncing
        scope.launch {
            try {
                addonSyncService.getRemoteAddonUrls().getOrThrow()
                _manualAddonSyncStatus.value = OmniaAddonSyncStatus.Success
                _manualAddonRefreshes.tryEmit(Unit)
            } catch (error: kotlinx.coroutines.CancellationException) {
                _manualAddonSyncStatus.value = OmniaAddonSyncStatus.Idle
                throw error
            } catch (error: Exception) {
                _manualAddonSyncStatus.value = OmniaAddonSyncStatus.Error
                Log.e(TAG, "Manual add-on sync failed (${error.javaClass.simpleName})")
            }
        }
    }''')
        # Server responses can include configured URLs; log classes only for add-on failures.
        text = text.replace('Log.e(TAG, "Failed to pull addons from remote, keeping local cache", e)', 'Log.e(TAG, "Failed to pull add-ons (${e.javaClass.simpleName}), keeping local cache")')
        path.write_text(text, encoding='utf-8')
        path = base/'ui/screens/addon/AddonManagerViewModel.kt'
        text = path.read_text(encoding='utf-8')
        text = replace_once(text, '    fun requestAddonSyncNow()', '    val addonSyncStatus = startupSyncService.manualAddonSyncStatus\n\n    fun requestAddonSyncNow()')
        path.write_text(text, encoding='utf-8')
        path = base/'ui/screens/addon/AddonManagerScreen.kt'
        text = path.read_text(encoding='utf-8')
        text = span(text, '    val defaultRefreshAddonsSubtitle', '    // When isEditing changes', '''    val addonSyncStatus by viewModel.addonSyncStatus.collectAsState()
    val refreshAddonsSubtitle = stringResource(when (addonSyncStatus) {
        com.nuvio.tv.core.sync.OmniaAddonSyncStatus.Idle -> R.string.omnia_addon_sync_idle
        com.nuvio.tv.core.sync.OmniaAddonSyncStatus.Syncing -> R.string.omnia_addon_sync_busy
        com.nuvio.tv.core.sync.OmniaAddonSyncStatus.Success -> R.string.omnia_addon_sync_done
        com.nuvio.tv.core.sync.OmniaAddonSyncStatus.Error -> R.string.omnia_addon_sync_error
        com.nuvio.tv.core.sync.OmniaAddonSyncStatus.SignIn -> R.string.omnia_addon_sync_signin
    })''')
        text = text.replace('                        refreshAddonsSubtitle = refreshedAddonsSubtitle\n', '')
        text = text.replace('                    subtitle = refreshAddonsSubtitle,', '                    subtitle = refreshAddonsSubtitle,\n                    enabled = addonSyncStatus != com.nuvio.tv.core.sync.OmniaAddonSyncStatus.Syncing,',1)
        text = text.replace('private fun RefreshAddonsEntryCard(\n    subtitle: String,', 'private fun RefreshAddonsEntryCard(\n    subtitle: String,\n    enabled: Boolean,',1)
        start = text.index('private fun RefreshAddonsEntryCard(')
        body = text[start:].replace('        onClick = onClick,', '        onClick = onClick,\n        enabled = enabled,',1).replace('R.string.addon_refresh_action', 'R.string.omnia_addon_sync_action',1)
        text = text[:start]+body
        path.write_text(text, encoding='utf-8')
        path = base/'data/local/AddonPreferences.kt'
        text = path.read_text(encoding='utf-8')
        text = text.replace('            val orderedUrls = urls.map(::canonicalizeUrl)\n            val currentUrls', '''            val requested = urls.map(::canonicalizeUrl).distinct()
            // Reorder is not removal: a stale UI must retain newly synced additions.
            val orderedUrls = requested + getCurrentList(preferences).map(::canonicalizeUrl).filter { it !in requested }
            val currentUrls''',1)
        path.write_text(text, encoding='utf-8')
    else:
        path = root/'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/AddonsScreen.kt'
        text = path.read_text(encoding='utf-8')
        text = replace_once(text, '    val uiState by AddonRepository.uiState.collectAsStateWithLifecycle()', '    val uiState by AddonRepository.uiState.collectAsStateWithLifecycle()\n    val addonSyncStatus by AddonRepository.syncStatus.collectAsStateWithLifecycle()')
        text = replace_once(text, '        OverviewCard(overview = overview)', '''        OverviewCard(overview = overview)
        NuvioPrimaryButton(
            text = stringResource(if (addonSyncStatus == OmniaAddonSyncStatus.Syncing) Res.string.omnia_addon_sync_busy else Res.string.omnia_addon_sync_action),
            enabled = addonSyncStatus != OmniaAddonSyncStatus.Syncing,
            onClick = { AddonRepository.syncAddonsNow() },
        )
        Text(text = stringResource(when (addonSyncStatus) {
            OmniaAddonSyncStatus.Idle -> Res.string.omnia_addon_sync_idle
            OmniaAddonSyncStatus.Syncing -> Res.string.omnia_addon_sync_busy
            OmniaAddonSyncStatus.Success -> Res.string.omnia_addon_sync_done
            OmniaAddonSyncStatus.Error -> Res.string.omnia_addon_sync_error
            OmniaAddonSyncStatus.SignIn -> Res.string.omnia_addon_sync_signin
        }), style = MaterialTheme.typography.bodyMedium)''')
        path.write_text(text, encoding='utf-8')

from pathlib import Path

def apply_ios_audio_queue(root):
    path=Path(root)/'iosApp/iosApp/Player/PlayerAudioSessionController.swift'
    if not path.exists(): return
    path.write_text('''import AVFoundation
import CallKit

/// Call observation/UI callbacks stay on main. Potentially blocking audio-session IPC
/// runs in order on its own serial queue, including deactivation after a player closes.
final class PlayerAudioSessionController: NSObject, CXCallObserverDelegate {
    private let callObserver = CXCallObserver()
    private let audioQueue = DispatchQueue(label: "io.omnia.audio-session", qos: .userInitiated)
    private var isActive = false
    private var generation: UInt64 = 0
    private var interruptionObserver: NSObjectProtocol?
    var onConfigurationChanged: (() -> Void)?

    func activate() {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.activate() }
            return
        }
        if !isActive {
            isActive = true
            callObserver.setDelegate(self, queue: .main)
            interruptionObserver = NotificationCenter.default.addObserver(
                forName: AVAudioSession.interruptionNotification,
                object: AVAudioSession.sharedInstance(), queue: .main
            ) { [weak self] notification in
                guard let self, self.isActive,
                      let value = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                      AVAudioSession.InterruptionType(rawValue: value) == .ended else { return }
                self.configure()
            }
        }
        configure()
    }

    func deactivate() {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.deactivate() }
            return
        }
        isActive = false
        generation &+= 1
        callObserver.setDelegate(nil, queue: nil)
        if let interruptionObserver {
            NotificationCenter.default.removeObserver(interruptionObserver)
            self.interruptionObserver = nil
        }
        audioQueue.async {
            do {
                try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            } catch {
                print("[NowPlaying] Could not deactivate audio session")
            }
        }
    }

    func callObserver(_ callObserver: CXCallObserver, callChanged call: CXCall) {
        guard isActive else { return }
        let hasCall = !call.hasEnded || callObserver.calls.contains {
            $0.uuid != call.uuid && !$0.hasEnded
        }
        configure(hasCall: hasCall)
    }

    private func configure(hasCall: Bool? = nil) {
        guard isActive else { return }
        generation &+= 1
        let requestGeneration = generation
        let mixing = hasCall ?? callObserver.calls.contains { !$0.hasEnded }
        let options: AVAudioSession.CategoryOptions = mixing ? [.mixWithOthers] : []
        audioQueue.async { [weak self] in
            let session = AVAudioSession.sharedInstance()
            do {
                if session.category != .playback || session.mode != .moviePlayback || session.categoryOptions != options {
                    try session.setCategory(.playback, mode: .moviePlayback, options: options)
                }
                try session.setActive(true)
                DispatchQueue.main.async { [weak self] in
                    guard let self, self.isActive, self.generation == requestGeneration else { return }
                    self.onConfigurationChanged?()
                }
            } catch {
                print("[NowPlaying] Could not activate audio session")
            }
        }
    }

    deinit {
        if let interruptionObserver { NotificationCenter.default.removeObserver(interruptionObserver) }
    }
}
''', encoding='utf-8')


is_tv = not (ROOT/'composeApp').exists()
apply_sync_models(ROOT, is_tv)
if is_tv:
    apply_tv_sync(ROOT)
else:
    apply_shared_sync(ROOT)
    apply_ios_audio_queue(ROOT)
apply_sync_ui(ROOT, is_tv)
if is_tv:
    p=ROOT/'app/build.gradle.kts'
    s=p.read_text(encoding='utf-8')
    s=re.sub(r'(?m)^(\s*versionCode\s*=\s*)\d+',r'\g<1>23',s,count=1)
    s=re.sub(r'(?m)^(\s*versionName\s*=\s*)"[^"]+"',r'\g<1>"0.3.17"',s,count=1)
    p.write_text(s,encoding='utf-8')
else:
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=23\nMARKETING_VERSION=0.4.15\n',encoding='utf-8')
    p=ROOT/'prepare_omnia_ios_tests.py'
    p.write_text(p.read_text(encoding='utf-8').replace('Version 0.4.14 (22)','Version 0.4.15 (23)'),encoding='utf-8')
print('Prepared Omnia safe add-on sync batch')

SHARED_ADDONS_BASELINE='package com.nuvio.app.features.addons\n\nimport androidx.compose.foundation.background\nimport androidx.compose.foundation.layout.Arrangement\nimport androidx.compose.foundation.layout.Box\nimport androidx.compose.foundation.layout.Column\nimport androidx.compose.foundation.layout.FlowRow\nimport androidx.compose.foundation.layout.Row\nimport androidx.compose.foundation.layout.Spacer\nimport androidx.compose.foundation.layout.fillMaxWidth\nimport androidx.compose.foundation.layout.height\nimport androidx.compose.foundation.layout.padding\nimport androidx.compose.foundation.layout.size\nimport androidx.compose.foundation.layout.width\nimport androidx.compose.foundation.shape.RoundedCornerShape\nimport androidx.compose.material.icons.Icons\nimport androidx.compose.material.icons.rounded.ArrowDownward\nimport androidx.compose.material.icons.rounded.ArrowUpward\nimport androidx.compose.material.icons.rounded.Delete\nimport androidx.compose.material.icons.rounded.Extension\nimport androidx.compose.material.icons.rounded.Refresh\nimport androidx.compose.material.icons.rounded.Settings\nimport androidx.compose.material3.HorizontalDivider\nimport androidx.compose.material3.Icon\nimport androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.Switch\nimport androidx.compose.material3.SwitchDefaults\nimport androidx.compose.material3.Text\nimport androidx.compose.material3.FilterChip\nimport androidx.compose.runtime.Composable\nimport androidx.compose.runtime.LaunchedEffect\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.rememberCoroutineScope\nimport androidx.compose.runtime.saveable.rememberSaveable\nimport androidx.compose.runtime.setValue\nimport androidx.compose.ui.Alignment\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.draw.clip\nimport androidx.compose.ui.graphics.Color\nimport androidx.compose.ui.graphics.vector.ImageVector\nimport androidx.compose.ui.layout.ContentScale\nimport androidx.compose.ui.platform.LocalUriHandler\nimport androidx.compose.ui.text.style.TextOverflow\nimport androidx.compose.ui.unit.dp\nimport androidx.lifecycle.compose.collectAsStateWithLifecycle\nimport com.nuvio.app.core.build.AppFeaturePolicy\nimport coil3.compose.AsyncImage\nimport com.nuvio.app.core.ui.NuvioIconActionButton\nimport com.nuvio.app.core.ui.NuvioInfoBadge\nimport com.nuvio.app.core.ui.NuvioInputField\nimport com.nuvio.app.core.ui.NuvioPrimaryButton\nimport com.nuvio.app.core.ui.NuvioScreen\nimport com.nuvio.app.core.ui.NuvioScreenHeader\nimport com.nuvio.app.core.ui.NuvioSectionLabel\nimport com.nuvio.app.core.ui.NuvioStatusModal\nimport com.nuvio.app.core.ui.NuvioSurfaceCard\nimport kotlinx.coroutines.launch\nimport nuvio.composeapp.generated.resources.*\nimport org.jetbrains.compose.resources.stringResource\n\n@Composable\nfun AddonsScreen(\n    modifier: Modifier = Modifier,\n    title: String? = null,\n    onBack: (() -> Unit)? = null,\n) {\n    NuvioScreen(modifier = modifier) {\n        stickyHeader {\n            NuvioScreenHeader(\n                title = title ?: stringResource(Res.string.addon_title),\n                onBack = onBack,\n            ) {\n            }\n        }\n        item {\n            AddonsSettingsPageContent()\n        }\n    }\n}\n\n@Composable\ninternal fun AddonsSettingsPageContent(\n    modifier: Modifier = Modifier,\n) {\n    LaunchedEffect(Unit) {\n        AddonRepository.initialize()\n    }\n\n    val uiState by AddonRepository.uiState.collectAsStateWithLifecycle()\n    val addonSyncStatus by AddonRepository.syncStatus.collectAsStateWithLifecycle()\n    val uriHandler = LocalUriHandler.current\n    val coroutineScope = rememberCoroutineScope()\n    var addonUrl by rememberSaveable { mutableStateOf("") }\n    var formMessage by rememberSaveable { mutableStateOf<String?>(null) }\n    var installModalState by remember { mutableStateOf<AddonInstallModalState?>(null) }\n    var addonPendingDeletionUrl by rememberSaveable { mutableStateOf<String?>(null) }\n    val enterAddonUrlMessage = stringResource(Res.string.addons_error_enter_url)\n    val usePersonalMediaCopy = AppFeaturePolicy.personalMediaAddonCopyEnabled\n\n    var showDiscover by rememberSaveable { mutableStateOf(false) }\n    val overview = remember(uiState.addons) { uiState.addons.toOverview() }\n\n    Column(\n        modifier = modifier,\n        verticalArrangement = Arrangement.spacedBy(12.dp),\n    ) {\n        SectionHeader(stringResource(Res.string.addons_section_overview))\n        OverviewCard(overview = overview)\n        NuvioPrimaryButton(\n            text = stringResource(if (addonSyncStatus == OmniaAddonSyncStatus.Syncing) Res.string.omnia_addon_sync_busy else Res.string.omnia_addon_sync_action),\n            enabled = addonSyncStatus != OmniaAddonSyncStatus.Syncing,\n            onClick = { AddonRepository.syncAddonsNow() },\n        )\n        Text(text = stringResource(when (addonSyncStatus) {\n            OmniaAddonSyncStatus.Idle -> Res.string.omnia_addon_sync_idle\n            OmniaAddonSyncStatus.Syncing -> Res.string.omnia_addon_sync_busy\n            OmniaAddonSyncStatus.Success -> Res.string.omnia_addon_sync_done\n            OmniaAddonSyncStatus.Error -> Res.string.omnia_addon_sync_error\n            OmniaAddonSyncStatus.SignIn -> Res.string.omnia_addon_sync_signin\n        }), style = MaterialTheme.typography.bodyMedium)\n        // Omnia separates installed controls from discovery.\n        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {\n            FilterChip(selected = !showDiscover, onClick = { showDiscover = false }, label = { Text("Current Add-ons") })\n            FilterChip(selected = showDiscover, onClick = { showDiscover = true }, label = { Text("Discover add-ons") })\n        }\n        if (showDiscover) {\n            OmniaCommunityPanel()\n        } else {\n\n        SectionHeader(stringResource(Res.string.addons_section_add_addon))\n        AddAddonCard(\n            addonUrl = addonUrl,\n            formMessage = formMessage,\n            usePersonalMediaCopy = usePersonalMediaCopy,\n            onAddonUrlChange = {\n                addonUrl = it\n                formMessage = null\n            },\n            onAddClick = {\n                val requestedUrl = addonUrl.trim()\n                if (requestedUrl.isBlank()) {\n                    formMessage = enterAddonUrlMessage\n                    return@AddAddonCard\n                }\n\n                formMessage = null\n                installModalState = AddonInstallModalState.Checking\n                coroutineScope.launch {\n                    val result = AddonRepository.addAddon(requestedUrl)\n                    installModalState = when (result) {\n                        is AddAddonResult.Success -> {\n                            addonUrl = ""\n                            AddonInstallModalState.Success(result.manifest.name)\n                        }\n\n                        is AddAddonResult.Error -> {\n                            AddonInstallModalState.Error(result.message)\n                        }\n                    }\n                }\n            },\n        )\n\n        SectionHeader(stringResource(Res.string.addons_section_installed))\n        if (uiState.addons.isEmpty()) {\n            EmptyStateCard(usePersonalMediaCopy = usePersonalMediaCopy)\n        } else {\n            val lastIndex = uiState.addons.lastIndex\n            uiState.addons.forEachIndexed { index, addon ->\n                val manifest = addon.manifest\n                val behaviorHints = manifest?.behaviorHints\n                val showConfigureAction = behaviorHints?.configurable == true || behaviorHints?.configurationRequired == true\n                val configureUrl = addon.manifestUrl.toConfigureUrl()\n                InstalledAddonCard(\n                    addon = addon,\n                    onMoveUpClick = if (index > 0) {\n                        { AddonRepository.moveAddon(index, index - 1) }\n                    } else {\n                        null\n                    },\n                    onMoveDownClick = if (index < lastIndex) {\n                        { AddonRepository.moveAddon(index, index + 1) }\n                    } else {\n                        null\n                    },\n                    onRefreshClick = {\n                        AddonRepository.refreshAddon(\n                            manifestUrl = addon.manifestUrl,\n                            forceRefresh = true,\n                        )\n                    },\n                    onEnabledChange = { enabled ->\n                        AddonRepository.setAddonEnabled(addon.manifestUrl, enabled)\n                    },\n                    onConfigureClick = if (showConfigureAction && !configureUrl.isNullOrBlank()) {\n                        {\n                            runCatching {\n                                uriHandler.openUri(configureUrl)\n                            }\n                        }\n                    } else {\n                        null\n                    },\n                    onDeleteClick = { addonPendingDeletionUrl = addon.manifestUrl },\n                )\n            }\n        }\n        } // Current Add-ons\n    }\n\n    val pendingDeletionUrl = addonPendingDeletionUrl\n    if (pendingDeletionUrl != null) {\n        NuvioStatusModal(\n            title = stringResource(Res.string.addons_delete_confirm_title),\n            message = stringResource(Res.string.action_delete_confirm_message),\n            isVisible = true,\n            destructive = true,\n            confirmText = stringResource(Res.string.action_yes),\n            dismissText = stringResource(Res.string.action_no),\n            onConfirm = {\n                AddonRepository.removeAddon(pendingDeletionUrl)\n                addonPendingDeletionUrl = null\n            },\n            onDismiss = { addonPendingDeletionUrl = null },\n        )\n    }\n\n    val modalState = installModalState\n    if (modalState != null) {\n        val modalTitle = when (modalState) {\n            AddonInstallModalState.Checking -> stringResource(Res.string.addons_modal_checking_title)\n            is AddonInstallModalState.Success -> stringResource(Res.string.addons_modal_success_title)\n            is AddonInstallModalState.Error -> stringResource(Res.string.addons_modal_failure_title)\n        }\n        val modalMessage = when (modalState) {\n            AddonInstallModalState.Checking -> stringResource(Res.string.addons_modal_checking_message)\n            is AddonInstallModalState.Success -> stringResource(\n                Res.string.addons_modal_success_message,\n                modalState.addonName,\n            )\n            is AddonInstallModalState.Error -> modalState.reason\n        }\n        val modalConfirmText = when (modalState) {\n            AddonInstallModalState.Checking -> stringResource(Res.string.addon_installing)\n            is AddonInstallModalState.Success -> stringResource(Res.string.action_done)\n            is AddonInstallModalState.Error -> stringResource(Res.string.action_close)\n        }\n        NuvioStatusModal(\n            title = modalTitle,\n            message = modalMessage,\n            isVisible = true,\n            isBusy = modalState.isBusy,\n            confirmText = modalConfirmText,\n            onConfirm = {\n                if (!modalState.isBusy) {\n                    installModalState = null\n                }\n            },\n        )\n    }\n}\n\n@Composable\nprivate fun SectionHeader(text: String) {\n    NuvioSectionLabel(text = text)\n}\n\n@Composable\nprivate fun OverviewCard(overview: AddonOverview) {\n    NuvioSurfaceCard {\n        Row(\n            modifier = Modifier.fillMaxWidth(),\n            verticalAlignment = Alignment.CenterVertically,\n        ) {\n            OverviewStat(\n                value = overview.totalAddons.toString(),\n                label = stringResource(Res.string.addons_overview_addons),\n                modifier = Modifier.weight(1f),\n            )\n            VerticalSeparator()\n            OverviewStat(\n                value = overview.activeAddons.toString(),\n                label = stringResource(Res.string.addons_overview_active),\n                modifier = Modifier.weight(1f),\n            )\n            VerticalSeparator()\n            OverviewStat(\n                value = overview.totalCatalogs.toString(),\n                label = stringResource(Res.string.addons_overview_catalogs),\n                modifier = Modifier.weight(1f),\n            )\n        }\n    }\n}\n\n@Composable\nprivate fun OverviewStat(\n    value: String,\n    label: String,\n    modifier: Modifier = Modifier,\n) {\n    Column(\n        modifier = modifier,\n        horizontalAlignment = Alignment.CenterHorizontally,\n    ) {\n        Text(\n            text = value,\n            style = MaterialTheme.typography.headlineLarge,\n            color = MaterialTheme.colorScheme.onSurface,\n        )\n        Text(\n            text = label,\n            style = MaterialTheme.typography.bodyLarge,\n            color = MaterialTheme.colorScheme.onSurfaceVariant,\n        )\n    }\n}\n\n@Composable\nprivate fun VerticalSeparator() {\n    Box(\n        modifier = Modifier\n            .padding(horizontal = 10.dp)\n            .width(1.dp)\n            .height(64.dp)\n            .background(MaterialTheme.colorScheme.outline),\n    )\n}\n\n@Composable\nprivate fun AddAddonCard(\n    addonUrl: String,\n    formMessage: String?,\n    usePersonalMediaCopy: Boolean,\n    onAddonUrlChange: (String) -> Unit,\n    onAddClick: () -> Unit,\n) {\n    NuvioSurfaceCard {\n        NuvioInputField(\n            value = addonUrl,\n            onValueChange = onAddonUrlChange,\n            placeholder = stringResource(\n                if (usePersonalMediaCopy) {\n                    Res.string.addons_appstore_input_placeholder\n                } else {\n                    Res.string.addons_input_placeholder\n                },\n            ),\n        )\n        Spacer(modifier = Modifier.height(18.dp))\n        NuvioPrimaryButton(\n            text = stringResource(\n                if (usePersonalMediaCopy) {\n                    Res.string.addons_appstore_install_button\n                } else {\n                    Res.string.addons_install_button\n                },\n            ),\n            enabled = addonUrl.isNotBlank(),\n            onClick = onAddClick,\n        )\n        if (usePersonalMediaCopy) {\n            Spacer(modifier = Modifier.height(14.dp))\n            Text(\n                text = stringResource(Res.string.addons_appstore_add_description),\n                style = MaterialTheme.typography.bodyLarge,\n                color = MaterialTheme.colorScheme.onSurfaceVariant,\n            )\n        }\n        formMessage?.let { message ->\n            Spacer(modifier = Modifier.height(14.dp))\n            Text(\n                text = message,\n                style = MaterialTheme.typography.bodyMedium,\n                color = MaterialTheme.colorScheme.error,\n            )\n        }\n    }\n}\n\nprivate sealed interface AddonInstallModalState {\n    val isBusy: Boolean\n\n    data object Checking : AddonInstallModalState {\n        override val isBusy: Boolean = true\n    }\n\n    data class Success(\n        val addonName: String,\n    ) : AddonInstallModalState {\n        override val isBusy: Boolean = false\n    }\n\n    data class Error(\n        val reason: String,\n    ) : AddonInstallModalState {\n        override val isBusy: Boolean = false\n    }\n}\n\n@Composable\nprivate fun EmptyStateCard(\n    usePersonalMediaCopy: Boolean,\n) {\n    NuvioSurfaceCard {\n        Text(\n            text = stringResource(\n                if (usePersonalMediaCopy) {\n                    Res.string.addons_appstore_empty_title\n                } else {\n                    Res.string.addons_empty_title\n                },\n            ),\n            style = MaterialTheme.typography.titleLarge,\n            color = MaterialTheme.colorScheme.onSurface,\n        )\n        Spacer(modifier = Modifier.height(8.dp))\n        Text(\n            text = stringResource(\n                if (usePersonalMediaCopy) {\n                    Res.string.addons_appstore_empty_subtitle\n                } else {\n                    Res.string.addons_empty_subtitle\n                },\n            ),\n            style = MaterialTheme.typography.bodyLarge,\n            color = MaterialTheme.colorScheme.onSurfaceVariant,\n        )\n    }\n}\n\n@Composable\nprivate fun InstalledAddonCard(\n    addon: ManagedAddon,\n    onMoveUpClick: (() -> Unit)?,\n    onMoveDownClick: (() -> Unit)?,\n    onRefreshClick: () -> Unit,\n    onEnabledChange: (Boolean) -> Unit,\n    onConfigureClick: (() -> Unit)?,\n    onDeleteClick: () -> Unit,\n) {\n    val manifest = addon.manifest\n\n    NuvioSurfaceCard {\n        Row(\n            modifier = Modifier.fillMaxWidth(),\n            verticalAlignment = Alignment.Top,\n        ) {\n            AddonIconBadge(\n                imageUrl = manifest?.logoUrl,\n                icon = Icons.Rounded.Extension,\n                tint = if (manifest != null) Color(0xFF71BDE8) else MaterialTheme.colorScheme.onSurfaceVariant,\n            )\n            Spacer(modifier = Modifier.width(16.dp))\n            Column(modifier = Modifier.weight(1f)) {\n                Text(\n                    text = addon.displayTitle,\n                    style = MaterialTheme.typography.headlineLarge,\n                    color = MaterialTheme.colorScheme.onSurface,\n                    maxLines = 2,\n                    overflow = TextOverflow.Ellipsis,\n                )\n                manifest?.version?.let { version ->\n                    Spacer(modifier = Modifier.height(8.dp))\n                    Text(\n                        text = stringResource(Res.string.addons_version_format, version),\n                        style = MaterialTheme.typography.bodyLarge,\n                        color = MaterialTheme.colorScheme.onSurfaceVariant,\n                    )\n                }\n            }\n            Spacer(modifier = Modifier.width(12.dp))\n            Switch(\n                checked = addon.enabled,\n                onCheckedChange = onEnabledChange,\n                colors = SwitchDefaults.colors(\n                    checkedThumbColor = MaterialTheme.colorScheme.onPrimary,\n                    checkedTrackColor = MaterialTheme.colorScheme.primary,\n                    uncheckedThumbColor = MaterialTheme.colorScheme.onSurfaceVariant,\n                    uncheckedTrackColor = MaterialTheme.colorScheme.outlineVariant,\n                ),\n            )\n        }\n\n        Spacer(modifier = Modifier.height(12.dp))\n\n        Row(\n            modifier = Modifier.fillMaxWidth(),\n            horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End),\n            verticalAlignment = Alignment.CenterVertically,\n        ) {\n            onMoveUpClick?.let { onMoveUp ->\n                NuvioIconActionButton(\n                    icon = Icons.Rounded.ArrowUpward,\n                    contentDescription = stringResource(Res.string.addons_move_up),\n                    tint = MaterialTheme.colorScheme.onSurfaceVariant,\n                    onClick = onMoveUp,\n                )\n            }\n            onMoveDownClick?.let { onMoveDown ->\n                NuvioIconActionButton(\n                    icon = Icons.Rounded.ArrowDownward,\n                    contentDescription = stringResource(Res.string.addons_move_down),\n                    tint = MaterialTheme.colorScheme.onSurfaceVariant,\n                    onClick = onMoveDown,\n                )\n            }\n            NuvioIconActionButton(\n                icon = Icons.Rounded.Refresh,\n                contentDescription = stringResource(Res.string.addons_refresh),\n                tint = MaterialTheme.colorScheme.primary,\n                onClick = onRefreshClick,\n            )\n            onConfigureClick?.let { onConfigure ->\n                NuvioIconActionButton(\n                    icon = Icons.Rounded.Settings,\n                    contentDescription = stringResource(Res.string.addons_configure),\n                    tint = MaterialTheme.colorScheme.tertiary,\n                    onClick = onConfigure,\n                )\n            }\n            NuvioIconActionButton(\n                icon = Icons.Rounded.Delete,\n                contentDescription = stringResource(Res.string.addons_delete),\n                tint = MaterialTheme.colorScheme.error,\n                onClick = onDeleteClick,\n            )\n        }\n\n        Spacer(modifier = Modifier.height(12.dp))\n        HorizontalDivider(color = MaterialTheme.colorScheme.outline)\n        Spacer(modifier = Modifier.height(18.dp))\n\n        FlowRow(\n            modifier = Modifier.fillMaxWidth(),\n            horizontalArrangement = Arrangement.spacedBy(10.dp),\n            verticalArrangement = Arrangement.spacedBy(10.dp),\n        ) {\n            NuvioInfoBadge(\n                text = when {\n                    !addon.enabled -> stringResource(Res.string.addons_badge_disabled)\n                    addon.isRefreshing -> stringResource(Res.string.addons_badge_refreshing)\n                    manifest != null -> stringResource(Res.string.addons_badge_active)\n                    else -> stringResource(Res.string.addons_badge_unavailable)\n                },\n            )\n            manifest?.let {\n                NuvioInfoBadge(text = stringResource(Res.string.addons_badge_resources, it.resources.size))\n                NuvioInfoBadge(text = stringResource(Res.string.addons_badge_catalogs, it.catalogs.size))\n                if (it.behaviorHints.configurable) {\n                    NuvioInfoBadge(text = stringResource(Res.string.addons_badge_configurable))\n                }\n            }\n        }\n\n        when {\n            addon.isRefreshing -> {\n                Spacer(modifier = Modifier.height(16.dp))\n                Text(\n                    text = stringResource(Res.string.addons_loading_manifest_details),\n                    style = MaterialTheme.typography.bodyLarge,\n                    color = MaterialTheme.colorScheme.onSurfaceVariant,\n                )\n            }\n\n            addon.errorMessage != null && manifest == null -> {\n                Spacer(modifier = Modifier.height(16.dp))\n                Text(\n                    text = addon.errorMessage,\n                    style = MaterialTheme.typography.bodyLarge,\n                    color = MaterialTheme.colorScheme.error,\n                )\n            }\n\n            manifest != null -> {\n                Spacer(modifier = Modifier.height(16.dp))\n                manifest.description.takeIf { it.isNotBlank() }?.let { description ->\n                    Text(\n                        text = description,\n                        style = MaterialTheme.typography.bodyLarge,\n                        color = MaterialTheme.colorScheme.onSurfaceVariant,\n                    )\n\n                    Spacer(modifier = Modifier.height(14.dp))\n                }\n\n                Text(\n                    text = manifestSummary(manifest),\n                    style = MaterialTheme.typography.bodyMedium,\n                    color = MaterialTheme.colorScheme.onSurfaceVariant,\n                )\n\n                addon.errorMessage?.let { staleError ->\n                    Spacer(modifier = Modifier.height(14.dp))\n                    Text(\n                        text = staleError,\n                        style = MaterialTheme.typography.bodyMedium,\n                        color = MaterialTheme.colorScheme.error,\n                    )\n                }\n            }\n        }\n    }\n}\n\n@Composable\nprivate fun AddonIconBadge(\n    imageUrl: String?,\n    icon: ImageVector,\n    tint: Color,\n) {\n    Box(\n        modifier = Modifier\n            .size(64.dp)\n            .clip(RoundedCornerShape(20.dp))\n            .background(MaterialTheme.colorScheme.surfaceVariant),\n        contentAlignment = Alignment.Center,\n    ) {\n        if (!imageUrl.isNullOrBlank()) {\n            AsyncImage(\n                model = imageUrl,\n                contentDescription = null,\n                modifier = Modifier.matchParentSize(),\n                contentScale = ContentScale.Crop,\n            )\n        } else {\n            Icon(\n                imageVector = icon,\n                contentDescription = null,\n                tint = tint,\n                modifier = Modifier.size(34.dp),\n            )\n        }\n    }\n}\n\n@Composable\nprivate fun manifestSummary(manifest: AddonManifest): String {\n    val resources = manifest.resources.joinToString(separator = ", ") { it.name }\n    val types = manifest.types.joinToString(separator = " / ") { it.replaceFirstChar(Char::uppercase) }\n    return buildString {\n        append(types)\n        append(" • ")\n        append(resources)\n        if (manifest.idPrefixes.isNotEmpty()) {\n            append(" • ")\n            append(stringResource(Res.string.addons_summary_id_rules, manifest.idPrefixes.size))\n        }\n        if (manifest.behaviorHints.p2p) {\n            append(" • P2P")\n        }\n    }\n}\n\nprivate fun String.toConfigureUrl(): String {\n    val base = substringBefore("?").trimEnd(\'/\')\n    return if (base.endsWith("/manifest.json")) {\n        base.removeSuffix("/manifest.json") + "/configure"\n    } else {\n        "$base/configure"\n    }\n}\n'
"""Final settings refinement; appended to the pinned preparation helper per client."""
from pathlib import Path
import re

def refine(path, old, new):
    path = ROOT / path
    code = path.read_text(encoding='utf8')
    if old in code:
        code = code.replace(old, new)
    else:
        assert new in code, f'Missing settings refinement anchor: {path.name}: {old[:100]}'
    path.write_text(code, encoding='utf8', newline='\n')

def save(path, code):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code.lstrip(), encoding='utf8', newline='\n')

if (ROOT/'composeApp').exists():
    shared = 'composeApp/src/commonMain/kotlin/com/nuvio/app/'
    settings = shared+'features/settings/'
    addons = shared+'features/addons/'
    refine(settings+'SettingsModels.kt', '    Plugins(\n', '''    CurrentAddons(
        titleRes = Res.string.omnia_current_addons,
        category = SettingsCategory.Watch,
        parentPage = Addons,
    ),
    DiscoverAddons(
        titleRes = Res.string.omnia_discover_addons,
        category = SettingsCategory.Watch,
        parentPage = Addons,
    ),
    SyncAddons(
        titleRes = Res.string.omnia_sync_addons,
        category = SettingsCategory.Watch,
        parentPage = Addons,
    ),
    Plugins(
''') if '    CurrentAddons(' not in (ROOT/(settings+'SettingsModels.kt')).read_text() else None
    refine(settings+'SettingsModels.kt', '    Notifications(\n', '''    RestoreDefaults(
        titleRes = Res.string.omnia_reset_title,
        category = SettingsCategory.System,
        parentPage = Root,
    ),
    Notifications(
''') if '    RestoreDefaults(' not in (ROOT/(settings+'SettingsModels.kt')).read_text() else None
    refine(settings+'SettingsModels.kt', '        SettingsPage.Addons -> Icons.Default.Extension', '''        SettingsPage.CurrentAddons -> Icons.Default.Extension
        SettingsPage.DiscoverAddons -> Icons.Default.Explore
        SettingsPage.SyncAddons -> Icons.Default.Sync
        SettingsPage.RestoreDefaults -> Icons.Default.Build
        SettingsPage.Addons -> Icons.Default.Extension''') if 'SettingsPage.CurrentAddons ->' not in (ROOT/(settings+'SettingsModels.kt')).read_text() else None
    save('composeApp/src/commonMain/composeResources/values/omnia_settings_navigation.xml', '''
<resources>
    <string name="omnia_current_addons">Current Add-ons</string>
    <string name="omnia_discover_addons">Discover Add-ons</string>
    <string name="omnia_sync_addons">Sync Add-ons</string>
</resources>
''')
    save(settings+'AddonsSettingsPage.kt', '''
package com.nuvio.app.features.settings

import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.ui.Modifier
import com.nuvio.app.core.build.AppFeaturePolicy
import com.nuvio.app.features.addons.AddonsSettingsPageContent
import com.nuvio.app.features.addons.OmniaAddonSection

internal fun LazyListScope.addonsSettingsContent(
    onPageClick: (SettingsPage) -> Unit = {},
    isTablet: Boolean = false,
) {
    item {
        SettingsGroup(isTablet = isTablet) {
            SettingsNavigationRow(title = "Current Add-ons", description = "Manage your installed add-ons and custom URLs.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.CurrentAddons) })
            SettingsGroupDivider(isTablet = isTablet)
            SettingsNavigationRow(title = "Discover Add-ons", description = "Find official and community add-ons that are not already installed.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.DiscoverAddons) })
            SettingsGroupDivider(isTablet = isTablet)
            SettingsNavigationRow(title = "Sync Add-ons", description = "Sync this profile's add-ons with your Omnia account.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.SyncAddons) })
            if (AppFeaturePolicy.pluginsEnabled) {
                SettingsGroupDivider(isTablet = isTablet)
                SettingsNavigationRow(title = "Script Providers", description = "Manage script-based sources, including Omnia India Providers.", isTablet = isTablet, onClick = { onPageClick(SettingsPage.Plugins) })
            }
        }
    }
}

internal fun LazyListScope.addonSectionContent(section: OmniaAddonSection) {
    item { AddonsSettingsPageContent(modifier = Modifier.fillMaxWidth(), section = section) }
}
''')
    ap=ROOT/(addons+'AddonsScreen.kt')
    code=SHARED_ADDONS_BASELINE
    if 'enum class OmniaAddonSection' not in code:
        code=code.replace('@Composable\ninternal fun AddonsSettingsPageContent(', 'internal enum class OmniaAddonSection { Current, Discover, Sync }\n\n@Composable\ninternal fun AddonsSettingsPageContent(')
        code=code.replace('internal fun AddonsSettingsPageContent(\n    modifier: Modifier = Modifier,', 'internal fun AddonsSettingsPageContent(\n    modifier: Modifier = Modifier,\n    section: OmniaAddonSection = OmniaAddonSection.Current,')
        code=code.replace('    var showDiscover by rememberSaveable { mutableStateOf(false) }\n','')
        start=code.index('        NuvioPrimaryButton(\n            text = stringResource(if (addonSyncStatus')
        end=code.index('        // Omnia separates installed controls from discovery.',start)
        sync=code[start:end]
        code=code[:start]+code[end:]
        start=code.index('        // Omnia separates installed controls from discovery.')
        end=code.index('        SectionHeader(stringResource(Res.string.addons_section_add_addon))', start)
        code=code[:start]+code[end:]
        code=code.replace('        } // Current Add-ons\n','')
        anchor='    val overview = remember(uiState.addons) { uiState.addons.toOverview() }\n'
        code=code.replace(anchor,anchor+'''
    if (section == OmniaAddonSection.Discover) {
        OmniaCommunityPanel()
        return
    }
    if (section == OmniaAddonSection.Sync) {
        Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
'''+sync+'''        }
        return
    }
''')
        ap.write_text(code,encoding='utf8',newline='\n')
    # Dedicated page and one entry, independent of advanced/essential feature gating.
    refine(settings+'AdvancedSettingsPage.kt', '    item { OmniaResetSettingsControl(isTablet) }\n', '') if 'item { OmniaResetSettingsControl' in (ROOT/(settings+'AdvancedSettingsPage.kt')).read_text() else None
    screen=ROOT/(settings+'SettingsScreen.kt');code=screen.read_text()
    code=code.replace('SettingsPage.Addons -> addonsSettingsContent(onPluginsClick = onPluginsClick)', 'SettingsPage.Addons -> addonsSettingsContent(onPageClick = onPageChange)')
    code=code.replace('SettingsPage.Addons -> addonsSettingsContent(onPluginsClick = { openInlinePage(SettingsPage.Plugins) }, isTablet = true)', 'SettingsPage.Addons -> addonsSettingsContent(onPageClick = { openInlinePage(it) }, isTablet = true)')
    for indent,tablet in [('                ',False),('                    ',True)]:
        marker=indent+'SettingsPage.Addons -> addonsSettingsContent('
        if indent+'SettingsPage.CurrentAddons ->' not in code:
            pos=code.index(marker)
            code=code[:pos]+''.join(indent+'SettingsPage.'+page+' -> addonSectionContent(com.nuvio.app.features.addons.OmniaAddonSection.'+section+')\n' for page,section in [('CurrentAddons','Current'),('DiscoverAddons','Discover'),('SyncAddons','Sync')])+indent+'SettingsPage.RestoreDefaults -> item { SettingsGroup(isTablet = '+str(tablet).lower()+') { OmniaResetSettingsControl(isTablet = '+str(tablet).lower()+') } }\n'+code[pos:]
    code=code.replace('                    onCatalogsClick = onHomescreenClick,', '                    onCatalogsClick = onHomescreenClick,\n                    onCollectionsClick = onCollectionsClick,')
    code=code.replace('                        onCatalogsClick = { openInlinePage(SettingsPage.Homescreen) },', '                        onCatalogsClick = { openInlinePage(SettingsPage.Homescreen) },\n                        onCollectionsClick = onCollectionsClick,')
    # Avoid repeated callback insertion on idempotent application.
    code=re.sub(r'(\s+onCollectionsClick = onCollectionsClick,\n)\s+onCollectionsClick = onCollectionsClick,\n',r'\1',code)
    screen.write_text(code,encoding='utf8',newline='\n')
    root=ROOT/(settings+'SettingsRootPage.kt');code=root.read_text()
    if 'page = SettingsPage.RestoreDefaults,' not in code:
        marker='''                        SettingsPageRow(
                            page = SettingsPage.About,'''
        code=code.replace(marker,'''                        SettingsPageRow(
                            page = SettingsPage.RestoreDefaults,
                            description = Res.string.omnia_reset_description,
                            isTablet = isTablet,
                            onPageClick = onPageClick,
                        )
                        SettingsGroupDivider(isTablet = isTablet)
'''+marker)
    root.write_text(code,encoding='utf8',newline='\n')
    cp=ROOT/(settings+'ContentDiscoverySettingsPage.kt');code=cp.read_text()
    code=code.replace('    onCatalogsClick: () -> Unit,','    onCatalogsClick: () -> Unit,\n    onCollectionsClick: () -> Unit,') if '    onCollectionsClick: () -> Unit,' not in code else code
    if 'onClick = onCollectionsClick,' not in code:
        marker='''                SettingsNavigationRow(
                    title = stringResource(Res.string.compose_settings_page_media_servers),'''
        code=code.replace(marker,'''                SettingsNavigationRow(
                    title = "Collections",
                    description = "Combine catalogs into collections and control duplicate Home rows.",
                    isTablet = isTablet,
                    onClick = onCollectionsClick,
                )
'''+marker)
    cp.write_text(code,encoding='utf8',newline='\n')
    lp=ROOT/(settings+'LayoutSettingsPage.kt');code=lp.read_text()
    code=re.sub(r'                SettingsNavigationRow\(\n                    title = stringResource\(Res.string.collections_header\),.*?                \)\n                SettingsGroupDivider\(isTablet = isTablet\)\n','',code,flags=re.S)
    lp.write_text(code,encoding='utf8',newline='\n')
    # Settings search follows the same destinations, not a stale second location.
    sp=ROOT/(settings+'SettingsSearch.kt');code=sp.read_text()
    if 'key = "restore-defaults"' not in code:
        marker='''    addPage(
        page = SettingsPage.Addons,'''
        entries=''
        for page,key,title,description in [('RestoreDefaults','restore-defaults','Restore default settings','Restore profile preferences while keeping your account and saved content.'),('CurrentAddons','current-addons','Current Add-ons','Manage installed add-ons.'),('DiscoverAddons','discover-addons','Discover Add-ons','Find official and community add-ons.'),('SyncAddons','sync-addons','Sync Add-ons','Sync add-ons with your Omnia account.')]:
            entries+=f'    addPage(page = SettingsPage.{page}, key = "{key}", title = "{title}", description = "{description}")\n'
        code=code.replace(marker,entries+marker)
    pattern=r'(key = "collections",.*?page = )layoutPage(,\n        section = )stringResource\(Res.string.settings_appearance_section_home\)'
    code=re.sub(pattern,r'\1contentDiscoveryPage\2stringResource(Res.string.settings_content_discovery_section_sources)',code,flags=re.S)
    sp.write_text(code,encoding='utf8',newline='\n')
    resource=ROOT/'composeApp/src/commonMain/composeResources/values/omnia_finish.xml'
    refine(resource.relative_to(ROOT), '<string name="omnia_reset_title">Reset settings</string>', '<string name="omnia_reset_title">Restore default settings</string>')
    tests=ROOT/'composeApp/src/commonTest/kotlin/com/nuvio/app/features/settings/SettingsNavigationTest.kt'
    code=tests.read_text()
    if 'fun addOnSectionsReturnToTheirHub()' not in code:
        code=code.replace('class SettingsNavigationTest {','''class SettingsNavigationTest {
    @Test
    fun addOnSectionsReturnToTheirHub() {
        listOf(SettingsPage.CurrentAddons, SettingsPage.DiscoverAddons, SettingsPage.SyncAddons, SettingsPage.Plugins).forEach { page ->
            assertEquals(SettingsPage.Addons, page.previousPage())
            assertEquals(SettingsCategory.Watch, page.category)
        }
    }

    @Test
    fun restoreDefaultsHasItsOwnSystemEntry() {
        assertEquals(SettingsPage.Root, SettingsPage.RestoreDefaults.previousPage())
        assertEquals(SettingsCategory.System, SettingsPage.RestoreDefaults.category)
    }
''')
    tests.write_text(code,encoding='utf8',newline='\n')
else:
    tv='app/src/main/java/com/nuvio/tv/'
    settings=tv+'ui/screens/settings/'
    addons=tv+'ui/screens/addon/'
    refine(settings+'SettingsCatalog.kt','    ADVANCED(SettingsRailGroup.SYSTEM),','    ADVANCED(SettingsRailGroup.SYSTEM),\n    RESTORE_DEFAULTS(SettingsRailGroup.SYSTEM),') if 'RESTORE_DEFAULTS(' not in (ROOT/(settings+'SettingsCatalog.kt')).read_text() else None
    screen=ROOT/(settings+'SettingsScreen.kt');code=screen.read_text()
    code=code.replace('onNavigateToAddons: () -> Unit', 'onNavigateToAddons: (String) -> Unit')
    code=code.replace('onNavigateToAddons: (String) -> Unit = {},','onNavigateToAddons: (String) -> Unit = {},')
    code=code.replace('    onNavigateToCatalogs: () -> Unit', '    onNavigateToCollections: () -> Unit'+('' )+',\n    onNavigateToCatalogs: () -> Unit') if '    onNavigateToCollections: () -> Unit' not in code else code
    # public SettingsScreen and private detail signatures need different defaults.
    code=code.replace('    onNavigateToCollections: () -> Unit,\n    onNavigateToCatalogs: () -> Unit = {},','    onNavigateToCollections: () -> Unit = {},\n    onNavigateToCatalogs: () -> Unit = {},')
    code=code.replace('onNavigateToCatalogs = onNavigateToCatalogs,', 'onNavigateToCatalogs = onNavigateToCatalogs,\n                                onNavigateToCollections = onNavigateToCollections,') if 'onNavigateToCollections = onNavigateToCollections,' not in code else code
    if 'SettingsCategory.RESTORE_DEFAULTS -> SettingsSectionSpec' not in code:
        marker='    SettingsCategory.ADVANCED -> SettingsSectionSpec'
        pos=code.index(marker)
        code=code[:pos]+'    SettingsCategory.RESTORE_DEFAULTS -> SettingsSectionSpec(category, stringResource(R.string.omnia_reset_title), Icons.Default.Build, destination = SettingsSectionDestination.Inline)\n'+code[pos:]
    code=code.replace('            SettingsCategory.ADVANCED to FocusRequester(),','            SettingsCategory.ADVANCED to FocusRequester(),\n            SettingsCategory.RESTORE_DEFAULTS to FocusRequester(),') if 'SettingsCategory.RESTORE_DEFAULTS to' not in code else code
    if 'SettingsCategory.RESTORE_DEFAULTS -> Column' not in code:
        marker='        SettingsCategory.ADVANCED -> if (isEssentialMode) {'
        code=code.replace(marker,'''        SettingsCategory.RESTORE_DEFAULTS -> Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.md)
        ) {
            SettingsDetailHeader(title = stringResource(R.string.omnia_reset_title), subtitle = stringResource(R.string.omnia_reset_description))
            OmniaResetSettingsControl(initialFocusRequester = if (allowDetailAutofocus) contentFocusRequesters[SettingsCategory.RESTORE_DEFAULTS] else null)
        }
'''+marker)
    # Content's obsolete unused add-on callback retains the old zero-arg type.
    code=code.replace('''SettingsCategory.CONTENT_DISCOVERY -> ContentDiscoverySettingsContent(
            onNavigateToAddons = onNavigateToAddons,''','''SettingsCategory.CONTENT_DISCOVERY -> ContentDiscoverySettingsContent(
            onNavigateToAddons = { onNavigateToAddons("current") },''')
    code=code.replace('showPlugins = AppFeaturePolicy.pluginsEnabled && !isEssentialMode,','showPlugins = AppFeaturePolicy.pluginsEnabled,')
    code=re.sub(r'        SettingsCategory.ADDONS -> OmniaAddonsSettingsContent\(.*?(?=        SettingsCategory.CONTENT_DISCOVERY)', '''        SettingsCategory.ADDONS -> OmniaAddonsSettingsContent(
            onNavigateToAddons = onNavigateToAddons,
            onNavigateToPlugins = onNavigateToPlugins,
            showPlugins = AppFeaturePolicy.pluginsEnabled,
            initialFocusRequester = if (allowDetailAutofocus) contentFocusRequesters[SettingsCategory.ADDONS] else null
        )
''',code,flags=re.S)
    screen.write_text(code,encoding='utf8',newline='\n')
    # One hub, four destinations. No installed list, discovery or sync controls duplicated here.
    hub=(ROOT/(settings+'OmniaAddonsSettingsContent.kt')).read_text()
    hub=hub.replace('onNavigateToAddons: () -> Unit','onNavigateToAddons: (String) -> Unit')
    hub=hub.replace('title = "Current & Discover Add-ons",','title = "Current Add-ons",').replace('subtitle = "Manage installed add-ons or find new catalogs, subtitles and playback sources.",','subtitle = "Manage installed add-ons and custom URLs.",').replace('onClick = onNavigateToAddons,','onClick = { onNavigateToAddons("current") },')
    if 'title = "Discover Add-ons"' not in hub:
        marker='            if (showPlugins) {'
        hub=hub.replace(marker,'''            SettingsActionRow(title = "Discover Add-ons", subtitle = "Find official and community add-ons that are not already installed.", leadingIcon = Icons.Default.Extension, onClick = { onNavigateToAddons("discover") })
            SettingsActionRow(title = "Sync Add-ons", subtitle = "Sync this profile's add-ons with your Omnia account.", leadingIcon = Icons.Default.Extension, onClick = { onNavigateToAddons("sync") })
'''+marker)
    hub=hub.replace('title = "Script providers",','title = "Script Providers",')
    save(settings+'OmniaAddonsSettingsContent.kt',hub)
    content=ROOT/(settings+'ContentDiscoverySettingsContent.kt');code=content.read_text()
    code=code.replace('    onNavigateToCatalogs: () -> Unit,','    onNavigateToCollections: () -> Unit,\n    onNavigateToCatalogs: () -> Unit,') if '    onNavigateToCollections: () -> Unit,' not in code else code
    code=code.replace('            onNavigateToServers = { serverPage = SERVERS_PAGE },','            onNavigateToServers = { serverPage = SERVERS_PAGE },\n            onNavigateToCollections = onNavigateToCollections,') if 'onNavigateToCollections = onNavigateToCollections,' not in code else code
    if 'title = "Collections",' not in code:
        marker='''            SettingsActionRow(
                title = stringResource(R.string.settings_media_servers),'''
        code=code.replace(marker,'''            SettingsActionRow(
                title = "Collections",
                subtitle = "Combine catalogs and control duplicate Home rows.",
                onClick = onNavigateToCollections,
                leadingIcon = Icons.Default.Extension,
            )
'''+marker)
    content.write_text(code,encoding='utf8',newline='\n')
    manager=ROOT/(addons+'AddonManagerScreen.kt');code=manager.read_text()
    if 'section: String = "current"' not in code:
        code=code.replace('    showBuiltInHeader: Boolean = true,','    showBuiltInHeader: Boolean = true,\n    section: String = "current",',1)
        code=code.replace('    var showDiscovery by remember { mutableStateOf(false) }\n    if (showDiscovery && !viewModel.isReadOnly) {','    if (section == "discover" && !viewModel.isReadOnly) {').replace('onBack = { showDiscovery = false }','onBack = onBackPress')
        code=re.sub(r'                item\(key = "omnia_discover_addons"\) \{.*?\n                \}\n','',code,flags=re.S)
        start=code.index('            if (!isEssential) {\n                item {\n                    CollectionsEntryCard')
        end=code.index('            item {\n                Row(',start)
        code=code[:start]+code[end:]
        marker='    // When isEditing changes to true, focus the text field and show keyboard'
        code=code.replace(marker,'''    if (section == "sync") {
        Column(Modifier.fillMaxSize().background(NuvioTheme.colors.Background).padding(28.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Sync Add-ons", style = MaterialTheme.typography.headlineMedium, color = NuvioTheme.colors.TextPrimary)
            Text(refreshAddonsSubtitle, style = MaterialTheme.typography.bodyLarge, color = NuvioTheme.colors.TextSecondary)
            Button(onClick = { viewModel.requestAddonSyncNow() }, enabled = addonSyncStatus != com.nuvio.tv.core.sync.OmniaAddonSyncStatus.Syncing, modifier = Modifier.focusRequester(surfaceFocusRequester)) { Text(stringResource(R.string.omnia_addon_sync_action)) }
            Button(onClick = onBackPress) { Text("Back") }
        }
        LaunchedEffect(Unit) { surfaceFocusRequester.requestFocus() }
        return
    }

'''+marker)
        manager.write_text(code,encoding='utf8',newline='\n')
    nav=ROOT/(tv+'ui/navigation/NuvioNavHost.kt');code=nav.read_text()
    code=code.replace('onNavigateToAddons = { navController.navigate(Screen.AddonManager.route) },','onNavigateToAddons = { section -> navController.navigate(Screen.AddonManager.route + "?section=" + section) },')
    marker='                onNavigateToCatalogs = { navController.navigate(Screen.CatalogOrder.route) },'
    if 'onNavigateToCollections = { navController.navigate(Screen.Collections.route) },\n'+marker not in code:
        code=code.replace(marker,'                onNavigateToCollections = { navController.navigate(Screen.Collections.route) },\n'+marker,1)
    code=code.replace('''        composable(Screen.AddonManager.route) {
            AddonManagerScreen(''','''        composable(
            Screen.AddonManager.route + "?section={section}",
            arguments = listOf(navArgument("section") { type = NavType.StringType; defaultValue = "current" })
        ) { entry ->
            AddonManagerScreen(
                section = entry.arguments?.getString("section") ?: "current",''')
    nav.write_text(code,encoding='utf8',newline='\n')
    refine(settings+'NetworkSettingsScreen.kt','        item(key = "reset_preferences") { OmniaResetSettingsControl() }\n','') if 'item(key = "reset_preferences")' in (ROOT/(settings+'NetworkSettingsScreen.kt')).read_text() else None
    control=ROOT/(settings+'OmniaResetSettingsControl.kt');code=control.read_text()
    if 'initialFocusRequester: FocusRequester?' not in code:
        code=code.replace('package com.nuvio.tv.ui.screens.settings','package com.nuvio.tv.ui.screens.settings\n\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.focus.FocusRequester\nimport androidx.compose.ui.focus.focusRequester')
        code=code.replace('internal fun OmniaResetSettingsControl(viewModel:', 'internal fun OmniaResetSettingsControl(initialFocusRequester: FocusRequester? = null, viewModel:')
        code=code.replace('            leadingIcon = Icons.Default.Restore,','            leadingIcon = Icons.Default.Restore,\n            modifier = if (initialFocusRequester != null) Modifier.focusRequester(initialFocusRequester) else Modifier,')
        control.write_text(code,encoding='utf8',newline='\n')
    refine('app/src/main/res/values/omnia_finish.xml','<string name="omnia_reset_title">Reset settings</string>','<string name="omnia_reset_title">Restore default settings</string>')
    test=ROOT/'app/src/test/java/com/nuvio/tv/ui/screens/settings/SettingsCatalogTest.kt';code=test.read_text()
    if 'SettingsCategory.RESTORE_DEFAULTS,' not in code:
        code=code.replace('                SettingsCategory.ADVANCED,','                SettingsCategory.ADVANCED,\n                SettingsCategory.RESTORE_DEFAULTS,')
    if 'fun `restore defaults is available exactly once in essentials and advanced`' not in code:
        code=code.replace('class SettingsCatalogTest {','''class SettingsCatalogTest {
    @Test
    fun `restore defaults is available exactly once in essentials and advanced`() {
        allCombinations().forEach { categories ->
            assertEquals(1, categories.count { it == SettingsCategory.RESTORE_DEFAULTS })
            assertEquals(SettingsRailGroup.SYSTEM, SettingsCategory.RESTORE_DEFAULTS.group)
        }
    }
''')
    test.write_text(code,encoding='utf8',newline='\n')
    build=ROOT/'app/build.gradle.kts';code=build.read_text()
    code=re.sub(r'(?m)^(\s*versionCode\s*=\s*)\d+',r'\g<1>24',code,count=1)
    code=re.sub(r'(?m)^(\s*versionName\s*=\s*)"[^"]+"',r'\g<1>"0.3.18"',code,count=1)
    build.write_text(code,encoding='utf8',newline='\n')

print('Prepared single-location settings: Content/Collections, four Add-on sections, independent Restore defaults.')


if (ROOT/'app').exists():
    import base64,re
    for rel,encoded in {'app/src/main/java/com/nuvio/tv/core/sync/OmniaPreferencesSyncService.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQgYW5kcm9pZC5jb250ZW50LkNvbnRleHQKaW1wb3J0IGFuZHJvaWR4LmRhdGFzdG9yZS5wcmVmZXJlbmNlcy5jb3JlLmJvb2xlYW5QcmVmZXJlbmNlc0tleQppbXBvcnQgYW5kcm9pZHguZGF0YXN0b3JlLnByZWZlcmVuY2VzLmNvcmUuZWRpdAppbXBvcnQgYW5kcm9pZHguZGF0YXN0b3JlLnByZWZlcmVuY2VzLmNvcmUuc3RyaW5nUHJlZmVyZW5jZXNLZXkKaW1wb3J0IGNvbS5udXZpby50di5jb3JlLmF1dGguQXV0aE1hbmFnZXIKaW1wb3J0IGNvbS5udXZpby50di5jb3JlLnByb2ZpbGUuUHJvZmlsZU1hbmFnZXIKaW1wb3J0IGNvbS5udXZpby50di5kYXRhLmxvY2FsLkNvbGxlY3Rpb25zRGF0YVN0b3JlCmltcG9ydCBjb20ubnV2aW8udHYuZGF0YS5sb2NhbC5MYXlvdXRQcmVmZXJlbmNlRGF0YVN0b3JlCmltcG9ydCBjb20ubnV2aW8udHYuZGF0YS5sb2NhbC5Qcm9maWxlRGF0YVN0b3JlRmFjdG9yeQppbXBvcnQgY29tLm51dmlvLnR2LmRvbWFpbi5tb2RlbC5BdXRoU3RhdGUKaW1wb3J0IGNvbS5udXZpby50di5kb21haW4ucmVwb3NpdG9yeS5BZGRvblJlcG9zaXRvcnkKaW1wb3J0IGRhZ2dlci5oaWx0LmFuZHJvaWQucXVhbGlmaWVycy5BcHBsaWNhdGlvbkNvbnRleHQKaW1wb3J0IGlvLmdpdGh1Yi5qYW4uc3VwYWJhc2UucG9zdGdyZXN0LlBvc3RncmVzdAppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLioKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5mbG93LioKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLioKaW1wb3J0IGphdmF4LmluamVjdC5JbmplY3QKaW1wb3J0IGphdmF4LmluamVjdC5TaW5nbGV0b24KCi8qKiBDYWxsZWQgYmVmb3JlIHB1Ymxpc2hpbmcgaWRlbnRpdHkgdHJhbnNpdGlvbnMsIGluY2x1ZGluZyBjb25mbGF0ZWQgQeKGkkLihpJBIGNoYW5nZXMuICovCmludGVybmFsIG9iamVjdCBPbW5pYVByZWZlcmVuY2VzSW52YWxpZGF0aW9uIHsKICAgIEBWb2xhdGlsZSB2YXIgaW52YWxpZGF0ZTogKCkgLT4gVW5pdCA9IHt9CiAgICBmdW4gYmVmb3JlSWRlbnRpdHlDaGFuZ2UoKSA9IGludmFsaWRhdGUoKQp9CgpAU2luZ2xldG9uCmNsYXNzIE9tbmlhUHJlZmVyZW5jZXNTeW5jU2VydmljZSBASW5qZWN0IGNvbnN0cnVjdG9yKAogICAgcHJpdmF0ZSB2YWwgYXV0aE1hbmFnZXI6IEF1dGhNYW5hZ2VyLAogICAgcHJpdmF0ZSB2YWwgcHJvZmlsZU1hbmFnZXI6IFByb2ZpbGVNYW5hZ2VyLAogICAgcHJpdmF0ZSB2YWwgZmFjdG9yeTogUHJvZmlsZURhdGFTdG9yZUZhY3RvcnksCiAgICBwcml2YXRlIHZhbCBsYXlvdXQ6IExheW91dFByZWZlcmVuY2VEYXRhU3RvcmUsCiAgICBwcml2YXRlIHZhbCBhZGRvbnM6IEFkZG9uUmVwb3NpdG9yeSwKICAgIHByaXZhdGUgdmFsIGNvbGxlY3Rpb25zOiBDb2xsZWN0aW9uc0RhdGFTdG9yZSwKICAgIHByaXZhdGUgdmFsIHBvc3RncmVzdDogUG9zdGdyZXN0LAogICAgQEFwcGxpY2F0aW9uQ29udGV4dCBjb250ZXh0OiBDb250ZXh0LAopIHsKICAgIHByaXZhdGUgdmFsIHNjb3BlID0gQ29yb3V0aW5lU2NvcGUoU3VwZXJ2aXNvckpvYigpICsgRGlzcGF0Y2hlcnMuSU8pCiAgICBwcml2YXRlIHZhbCBqc29uID0gSnNvbiB7IGlnbm9yZVVua25vd25LZXlzID0gdHJ1ZTsgZW5jb2RlRGVmYXVsdHMgPSB0cnVlIH0KICAgIHByaXZhdGUgdmFsIHN0b3JhZ2UgPSBjb250ZXh0LmdldFNoYXJlZFByZWZlcmVuY2VzKCJvbW5pYV9vcHRpb25hbF9wcmVmZXJlbmNlcyIsIENvbnRleHQuTU9ERV9QUklWQVRFKQogICAgcHJpdmF0ZSB2YXIgcGVuZGluZzogSm9iPyA9IG51bGwKICAgIEBWb2xhdGlsZSBwcml2YXRlIHZhciBhcHBseWluZyA9IGZhbHNlCgogICAgcHJpdmF0ZSBmdW4gY3VycmVudFNjb3BlKCk6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGU/IHsKICAgICAgICB2YWwgYXV0aCA9IGF1dGhNYW5hZ2VyLmF1dGhTdGF0ZS52YWx1ZSBhcz8gQXV0aFN0YXRlLkZ1bGxBY2NvdW50ID86IHJldHVybiBudWxsCiAgICAgICAgaWYgKCFwcm9maWxlTWFuYWdlci5hY3RpdmVQcm9maWxlUmVhZHkudmFsdWUpIHJldHVybiBudWxsCiAgICAgICAgcmV0dXJuIFNoYXJlZFByZWZlcmVuY2VzU2NvcGUoYXV0aC51c2VySWQsIHByb2ZpbGVNYW5hZ2VyLmFjdGl2ZVByb2ZpbGVJZC52YWx1ZSkKICAgIH0KCiAgICBwcml2YXRlIHZhbCBkZXZpY2UgPSBvYmplY3QgOiBTaGFyZWRQcmVmZXJlbmNlc0RldmljZSB7CiAgICAgICAgb3ZlcnJpZGUgdmFsIHN1cHBvcnRlZEtleXMgPSBzZXRPZigiY29udGludWVXYXRjaGluZ1Zpc2libGUiLCAiaGVyb0VuYWJsZWQiLCAiaGlkZVVucmVsZWFzZWRDb250ZW50IiwgImF1ZGlvTGFuZ3VhZ2UiLCAic3VidGl0bGVMYW5ndWFnZSIsICJob21lQ2F0YWxvZ3MiKQogICAgICAgIG92ZXJyaWRlIGZ1biBjdXJyZW50U2NvcGUoKSA9IHRoaXNAT21uaWFQcmVmZXJlbmNlc1N5bmNTZXJ2aWNlLmN1cnJlbnRTY29wZSgpCgogICAgICAgIG92ZXJyaWRlIHN1c3BlbmQgZnVuIGV4cG9ydChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSk6IEpzb25PYmplY3QgewogICAgICAgICAgICBjaGVjayhjdXJyZW50U2NvcGUoKSA9PSBzY29wZSkKICAgICAgICAgICAgdmFsIGhvbWUgPSBmYWN0b3J5LmdldChzY29wZS5wcm9maWxlSWQsICJsYXlvdXRfc2V0dGluZ3MiKS5kYXRhLmZpcnN0KCkKICAgICAgICAgICAgdmFsIHBsYXllciA9IGZhY3RvcnkuZ2V0KHNjb3BlLnByb2ZpbGVJZCwgInBsYXllcl9zZXR0aW5ncyIpLmRhdGEuZmlyc3QoKQogICAgICAgICAgICB2YWwgaW5zdGFsbGVkID0gYWRkb25zLmdldEluc3RhbGxlZEFkZG9ucygpLmZpcnN0KCkKICAgICAgICAgICAgdmFsIGdyb3VwcyA9IGNvbGxlY3Rpb25zLmdldEN1cnJlbnRDb2xsZWN0aW9ucygpCiAgICAgICAgICAgIGNoZWNrKGN1cnJlbnRTY29wZSgpID09IHNjb3BlKQogICAgICAgICAgICB2YWwgY2F0YWxvZ3MgPSBsYXlvdXQuZXhwb3J0Q2F0YWxvZ1NldHRpbmdzVG9TeW5jUGF5bG9hZChpbnN0YWxsZWQsIGdyb3Vwcywgc2NvcGUucHJvZmlsZUlkKQogICAgICAgICAgICBjaGVjayhjdXJyZW50U2NvcGUoKSA9PSBzY29wZSkKICAgICAgICAgICAgcmV0dXJuIGJ1aWxkSnNvbk9iamVjdCB7CiAgICAgICAgICAgICAgICBwdXQoImNvbnRpbnVlV2F0Y2hpbmdWaXNpYmxlIiwgaG9tZVtib29sZWFuUHJlZmVyZW5jZXNLZXkoImNvbnRpbnVlX3dhdGNoaW5nX2VuYWJsZWQiKV0gPzogdHJ1ZSkKICAgICAgICAgICAgICAgIHB1dCgiaGVyb0VuYWJsZWQiLCBob21lW2Jvb2xlYW5QcmVmZXJlbmNlc0tleSgiaGVyb19zZWN0aW9uX2VuYWJsZWQiKV0gPzogdHJ1ZSkKICAgICAgICAgICAgICAgIHB1dCgiaGlkZVVucmVsZWFzZWRDb250ZW50IiwgaG9tZVtib29sZWFuUHJlZmVyZW5jZXNLZXkoImhpZGVfdW5yZWxlYXNlZF9jb250ZW50IildID86IGZhbHNlKQogICAgICAgICAgICAgICAgcHV0KCJhdWRpb0xhbmd1YWdlIiwgcGxheWVyW3N0cmluZ1ByZWZlcmVuY2VzS2V5KCJwcmVmZXJyZWRfYXVkaW9fbGFuZ3VhZ2UiKV0gPzogImRldmljZSIpCiAgICAgICAgICAgICAgICBwdXQoInN1YnRpdGxlTGFuZ3VhZ2UiLCBwbGF5ZXJbc3RyaW5nUHJlZmVyZW5jZXNLZXkoInN1YnRpdGxlX3ByZWZlcnJlZF9sYW5ndWFnZSIpXSA/OiAiZGV2aWNlIikKICAgICAgICAgICAgICAgIHB1dCgiaG9tZUNhdGFsb2dzIiwgSnNvbkFycmF5KGNhdGFsb2dzLml0ZW1zLmZpbHRlciB7IHJvdyAtPgogICAgICAgICAgICAgICAgICAgIGlmIChyb3cuaXNDb2xsZWN0aW9uKSBpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eShyb3cuY29sbGVjdGlvbklkLCAxMjgpCiAgICAgICAgICAgICAgICAgICAgZWxzZSBpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eShyb3cuYWRkb25JZCwgNTEyKSAmJiBpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eShyb3cudHlwZSwgNjQpICYmIGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KHJvdy5jYXRhbG9nSWQsIDEwMjQpCiAgICAgICAgICAgICAgICB9Lm1hcCB7IGpzb24uZW5jb2RlVG9Kc29uRWxlbWVudChTeW5jQ2F0YWxvZ0l0ZW0uc2VyaWFsaXplcigpLCBpdCkgfSkpCiAgICAgICAgICAgIH0KICAgICAgICB9CgogICAgICAgIG92ZXJyaWRlIHN1c3BlbmQgZnVuIGFwcGx5KHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCBwcmVmZXJlbmNlczogSnNvbk9iamVjdCwgc3RpbGxDdXJyZW50OiAoKSAtPiBCb29sZWFuKSB7CiAgICAgICAgICAgIGZ1biBndWFyZCgpIHsgY2hlY2soc3RpbGxDdXJyZW50KCkgJiYgY3VycmVudFNjb3BlKCkgPT0gc2NvcGUpIHsgIkFjY291bnQsIHByb2ZpbGUgb3Igc3luYyBjaG9pY2UgY2hhbmdlZCIgfSB9CiAgICAgICAgICAgIGd1YXJkKCk7IGFwcGx5aW5nID0gdHJ1ZQogICAgICAgICAgICB0cnkgewogICAgICAgICAgICAgICAgcHJlZmVyZW5jZXNbImhvbWVDYXRhbG9ncyJdPy5sZXQgeyByb3dzIC0+CiAgICAgICAgICAgICAgICAgICAgdmFsIGl0ZW1zID0gKHJvd3MgYXMgSnNvbkFycmF5KS5tYXAgeyBqc29uLmRlY29kZUZyb21Kc29uRWxlbWVudChTeW5jQ2F0YWxvZ0l0ZW0uc2VyaWFsaXplcigpLCBpdCkgfQogICAgICAgICAgICAgICAgICAgIHZhbCBob21lID0gZmFjdG9yeS5nZXQoc2NvcGUucHJvZmlsZUlkLCAibGF5b3V0X3NldHRpbmdzIikuZGF0YS5maXJzdCgpCiAgICAgICAgICAgICAgICAgICAgZ3VhcmQoKQogICAgICAgICAgICAgICAgICAgIGxheW91dC5hcHBseUNhdGFsb2dTZXR0aW5nc0Zyb21SZW1vdGUoCiAgICAgICAgICAgICAgICAgICAgICAgIFN5bmNIb21lQ2F0YWxvZ1BheWxvYWQoaG9tZVtib29sZWFuUHJlZmVyZW5jZXNLZXkoImhpZGVfdW5yZWxlYXNlZF9jb250ZW50IildID86IGZhbHNlLCBpdGVtcyksCiAgICAgICAgICAgICAgICAgICAgICAgIHNjb3BlLnByb2ZpbGVJZCwgOjpndWFyZCwKICAgICAgICAgICAgICAgICAgICApCiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICBmYWN0b3J5LmdldChzY29wZS5wcm9maWxlSWQsICJsYXlvdXRfc2V0dGluZ3MiKS5lZGl0IHsgdmFsdWVzIC0+CiAgICAgICAgICAgICAgICAgICAgZ3VhcmQoKQogICAgICAgICAgICAgICAgICAgIG1hcE9mKCJjb250aW51ZVdhdGNoaW5nVmlzaWJsZSIgdG8gImNvbnRpbnVlX3dhdGNoaW5nX2VuYWJsZWQiLCAiaGVyb0VuYWJsZWQiIHRvICJoZXJvX3NlY3Rpb25fZW5hYmxlZCIsICJoaWRlVW5yZWxlYXNlZENvbnRlbnQiIHRvICJoaWRlX3VucmVsZWFzZWRfY29udGVudCIpLmZvckVhY2ggeyAod2lyZSwga2V5KSAtPgogICAgICAgICAgICAgICAgICAgICAgICBwcmVmZXJlbmNlc1t3aXJlXT8uanNvblByaW1pdGl2ZT8uYm9vbGVhbk9yTnVsbD8ubGV0IHsgdmFsdWVzW2Jvb2xlYW5QcmVmZXJlbmNlc0tleShrZXkpXSA9IGl0IH0KICAgICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICBmYWN0b3J5LmdldChzY29wZS5wcm9maWxlSWQsICJwbGF5ZXJfc2V0dGluZ3MiKS5lZGl0IHsgdmFsdWVzIC0+CiAgICAgICAgICAgICAgICAgICAgZ3VhcmQoKQogICAgICAgICAgICAgICAgICAgIHByZWZlcmVuY2VzWyJhdWRpb0xhbmd1YWdlIl0/Lmpzb25QcmltaXRpdmU/LmNvbnRlbnRPck51bGw/LmxldCB7IHZhbHVlc1tzdHJpbmdQcmVmZXJlbmNlc0tleSgicHJlZmVycmVkX2F1ZGlvX2xhbmd1YWdlIildID0gaXQgfQogICAgICAgICAgICAgICAgICAgIHByZWZlcmVuY2VzWyJzdWJ0aXRsZUxhbmd1YWdlIl0/Lmpzb25QcmltaXRpdmU/LmNvbnRlbnRPck51bGw/LmxldCB7IHZhbHVlc1tzdHJpbmdQcmVmZXJlbmNlc0tleSgic3VidGl0bGVfcHJlZmVycmVkX2xhbmd1YWdlIildID0gaXQgfQogICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgZ3VhcmQoKQogICAgICAgICAgICB9IGZpbmFsbHkgeyBhcHBseWluZyA9IGZhbHNlIH0KICAgICAgICB9CiAgICB9CgogICAgcHJpdmF0ZSBmdW4gSnNvbk9iamVjdC5zbmFwc2hvdCgpID0gU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgKICAgICAgICByZXF1aXJlTm90TnVsbCh0aGlzWyJyZXZpc2lvbiJdPy5qc29uUHJpbWl0aXZlPy5sb25nT3JOdWxsKSwKICAgICAgICB0aGlzWyJwcmVmZXJlbmNlcyJdIGFzPyBKc29uT2JqZWN0ID86IGVycm9yKCJJbnZhbGlkIHNhdmVkIHByZWZlcmVuY2VzIiksCiAgICAgICAgcmVxdWlyZU5vdE51bGwodGhpc1sicHJvZmlsZV9pbnN0YW5jZSJdPy5qc29uUHJpbWl0aXZlPy5jb250ZW50T3JOdWxsKS5hbHNvIHsgcmVxdWlyZShpdC5pc05vdEJsYW5rKCkpIH0sCiAgICApCgogICAgcHJpdmF0ZSB2YWwgdHJhbnNwb3J0ID0gb2JqZWN0IDogU2hhcmVkUHJlZmVyZW5jZXNUcmFuc3BvcnQgewogICAgICAgIG92ZXJyaWRlIHN1c3BlbmQgZnVuIHB1bGwoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpOiBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90ID0gcG9zdGdyZXN0LnJwYygib21uaWFfcHVsbF9wcmVmZXJlbmNlc192MSIsIGJ1aWxkSnNvbk9iamVjdCB7CiAgICAgICAgICAgIHB1dCgicF9leHBlY3RlZF9vd25lciIsIHNjb3BlLm93bmVyKTsgcHV0KCJwX3Byb2ZpbGVfaWQiLCBzY29wZS5wcm9maWxlSWQpCiAgICAgICAgfSkuZGVjb2RlQXM8SnNvbk9iamVjdD4oKS5zbmFwc2hvdCgpCgogICAgICAgIG92ZXJyaWRlIHN1c3BlbmQgZnVuIHB1c2goc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIGV4cGVjdGVkUmV2aXNpb246IExvbmcsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCBleHBlY3RlZFByb2ZpbGVJbnN0YW5jZTogU3RyaW5nPyk6IFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdCB7CiAgICAgICAgICAgIHZhbCByZXN1bHQgPSBwb3N0Z3Jlc3QucnBjKCJvbW5pYV9wdXNoX3ByZWZlcmVuY2VzX3YxIiwgYnVpbGRKc29uT2JqZWN0IHsKICAgICAgICAgICAgICAgIHB1dCgicF9leHBlY3RlZF9vd25lciIsIHNjb3BlLm93bmVyKTsgcHV0KCJwX3Byb2ZpbGVfaWQiLCBzY29wZS5wcm9maWxlSWQpCiAgICAgICAgICAgICAgICBwdXQoInBfZXhwZWN0ZWRfcmV2aXNpb24iLCBleHBlY3RlZFJldmlzaW9uKTsgcHV0KCJwX3ByZWZlcmVuY2VzIiwgcHJlZmVyZW5jZXMpCiAgICAgICAgICAgICAgICBwdXQoInBfZXhwZWN0ZWRfcHJvZmlsZV9pbnN0YW5jZSIsIHJlcXVpcmVOb3ROdWxsKGV4cGVjdGVkUHJvZmlsZUluc3RhbmNlKSkKICAgICAgICAgICAgfSkuZGVjb2RlQXM8SnNvbk9iamVjdD4oKQogICAgICAgICAgICByZXR1cm4gU2hhcmVkUHJlZmVyZW5jZXNQdXNoUmVzdWx0KAogICAgICAgICAgICAgICAgcmVxdWlyZU5vdE51bGwocmVzdWx0WyJjb25mbGljdCJdPy5qc29uUHJpbWl0aXZlPy5ib29sZWFuT3JOdWxsKSwKICAgICAgICAgICAgICAgIHJlcXVpcmVOb3ROdWxsKHJlc3VsdFsic25hcHNob3QiXSBhcz8gSnNvbk9iamVjdCkuc25hcHNob3QoKSwKICAgICAgICAgICAgKQogICAgICAgIH0KICAgIH0KCiAgICBwcml2YXRlIHZhbCByZWNvcmRzID0gT21uaWFQcmVmZXJlbmNlc1N5bmNSZWNvcmRTdG9yZSgKICAgICAgICB7IHN0b3JhZ2UuZ2V0U3RyaW5nKGl0LCBudWxsKSB9LAogICAgICAgIHsga2V5LCB2YWx1ZSAtPiBjaGVjayhzdG9yYWdlLmVkaXQoKS5wdXRTdHJpbmcoa2V5LCB2YWx1ZSkuY29tbWl0KCkpIHsgIlVuYWJsZSB0byBzYXZlIGRldmljZSBzeW5jIGNob2ljZSIgfSB9LAogICAgKQogICAgcHJpdmF0ZSB2YWwgZW5naW5lID0gT21uaWFTaGFyZWRQcmVmZXJlbmNlc0VuZ2luZShkZXZpY2UsIHJlY29yZHMsIHRyYW5zcG9ydCkKICAgIGludGVybmFsIHZhbCBzdGF0ZSA9IGVuZ2luZS5zdGF0ZQoKICAgIGluaXQgewogICAgICAgIE9tbmlhUHJlZmVyZW5jZXNJbnZhbGlkYXRpb24uaW52YWxpZGF0ZSA9IDo6aW52YWxpZGF0ZVJlcXVlc3RzCiAgICAgICAgZW5naW5lLnJlZnJlc2hMb2NhbFN0YXRlKCkKICAgICAgICBzY29wZS5sYXVuY2ggewogICAgICAgICAgICBjb21iaW5lKGF1dGhNYW5hZ2VyLmF1dGhTdGF0ZSwgcHJvZmlsZU1hbmFnZXIuYWN0aXZlUHJvZmlsZUlkLCBwcm9maWxlTWFuYWdlci5hY3RpdmVQcm9maWxlUmVhZHkpIHsgXywgXywgXyAtPiBjdXJyZW50U2NvcGUoKSB9CiAgICAgICAgICAgICAgICAuZGlzdGluY3RVbnRpbENoYW5nZWQoKS5jb2xsZWN0IHsgcGVuZGluZz8uY2FuY2VsKCk7IGVuZ2luZS5yZWZyZXNoTG9jYWxTdGF0ZSgpOyByZXF1ZXN0U3luYygpIH0KICAgICAgICB9CiAgICAgICAgc2NvcGUubGF1bmNoIHsKICAgICAgICAgICAgcHJvZmlsZU1hbmFnZXIuYWN0aXZlUHJvZmlsZUlkLmZsYXRNYXBMYXRlc3QgeyBpZCAtPgogICAgICAgICAgICAgICAgY29tYmluZShmYWN0b3J5LmdldChpZCwibGF5b3V0X3NldHRpbmdzIikuZGF0YSwgZmFjdG9yeS5nZXQoaWQsInBsYXllcl9zZXR0aW5ncyIpLmRhdGEpIHsgXywgXyAtPgogICAgICAgICAgICAgICAgICAgIGN1cnJlbnRTY29wZSgpPy5sZXQgeyBkZXZpY2UuZXhwb3J0KGl0KS50b1N0cmluZygpIH0KICAgICAgICAgICAgICAgIH0uZGlzdGluY3RVbnRpbENoYW5nZWQoKS5kcm9wKDEpCiAgICAgICAgICAgIH0uY29sbGVjdCB7IHJlcXVlc3RTeW5jKCkgfQogICAgICAgIH0KICAgIH0KCiAgICBpbnRlcm5hbCBmdW4gaW52YWxpZGF0ZVJlcXVlc3RzKCkgeyBwZW5kaW5nPy5jYW5jZWwoKTsgZW5naW5lLnJlZnJlc2hMb2NhbFN0YXRlKCkgfQogICAgaW50ZXJuYWwgZnVuIHJlcXVlc3RTeW5jKCkgewogICAgICAgIGlmIChhcHBseWluZyB8fCAhc3RhdGUudmFsdWUuZW5hYmxlZCkgcmV0dXJuCiAgICAgICAgdmFsIGV4cGVjdGVkID0gY3VycmVudFNjb3BlKCkgPzogcmV0dXJuCiAgICAgICAgcGVuZGluZz8uY2FuY2VsKCkKICAgICAgICBwZW5kaW5nID0gc2NvcGUubGF1bmNoIHsgZGVsYXkoNzUwKTsgaWYgKGN1cnJlbnRTY29wZSgpID09IGV4cGVjdGVkKSBlbmdpbmUuc3luY2hyb25pemUoKSB9CiAgICB9CiAgICBpbnRlcm5hbCBzdXNwZW5kIGZ1biBzeW5jaHJvbml6ZSgpID0gZW5naW5lLnN5bmNocm9uaXplKCkKICAgIGludGVybmFsIHN1c3BlbmQgZnVuIGVuYWJsZShjaG9pY2U6IFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZT8gPSBudWxsKSA9IGVuZ2luZS5lbmFibGUoY2hvaWNlKQogICAgaW50ZXJuYWwgc3VzcGVuZCBmdW4gZGlzYWJsZSgpID0gZW5naW5lLmRpc2FibGUoKQogICAgaW50ZXJuYWwgZnVuIGNhbmNlbEluaXRpYWxDaG9pY2UoKSA9IGVuZ2luZS5yZWZyZXNoTG9jYWxTdGF0ZSgpCn0K', 'app/src/main/java/com/nuvio/tv/core/sync/OmniaSharedPreferencesPolicy.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbkVsZW1lbnQKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25BcnJheQppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvblByaW1pdGl2ZQppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uYm9vbGVhbk9yTnVsbAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uY29udGVudE9yTnVsbAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uaW50T3JOdWxsCmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5qc29uUHJpbWl0aXZlCgovKiogV2lyZSBuYW1lcyBkZWxpYmVyYXRlbHkgZXhjbHVkZSBkZXZpY2UgdHVuaW5nLCBjcmVkZW50aWFscyBhbmQgdGhlIGxvY2FsIG9wdC1pbi4gKi8KaW50ZXJuYWwgdmFsIHNoYXJlZFByZWZlcmVuY2VLZXlzID0gc2V0T2YoCiAgICAiY29udGludWVXYXRjaGluZ1Zpc2libGUiLCAiaGVyb0VuYWJsZWQiLCAiaGVyb1RyYWlsZXJzRW5hYmxlZCIsICJoZXJvVHJhaWxlck11dGVkIiwKICAgICJoaWRlVW5yZWxlYXNlZENvbnRlbnQiLCAiYXVkaW9MYW5ndWFnZSIsICJzdWJ0aXRsZUxhbmd1YWdlIiwgImhvbWVDYXRhbG9ncyIsCikKCi8qKiBDYXRhbG9nIHByZWZlcmVuY2VzIGNhcnJ5IHB1YmxpYyBpZGVudGlmaWVycywgbmV2ZXIgY29uZmlndXJlZCBlbmRwb2ludCBVUkxzLiAqLwppbnRlcm5hbCBmdW4gaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkodmFsdWU6IFN0cmluZywgbWF4TGVuZ3RoOiBJbnQpOiBCb29sZWFuID0KICAgIHZhbHVlLmlzTm90QmxhbmsoKSAmJiB2YWx1ZS5sZW5ndGggPD0gbWF4TGVuZ3RoICYmCiAgICAgICAgIjovLyIgIWluIHZhbHVlICYmICc/JyAhaW4gdmFsdWUgJiYgJyMnICFpbiB2YWx1ZSAmJgogICAgICAgIHZhbHVlLm5vbmUgeyBpdC5pc0lTT0NvbnRyb2woKSB8fCBpdCA9PSAnXFwnIH0KCmludGVybmFsIGRhdGEgY2xhc3MgU2hhcmVkUHJlZmVyZW5jZXNTY29wZSh2YWwgb3duZXI6IFN0cmluZywgdmFsIHByb2ZpbGVJZDogSW50KSB7CiAgICBpbml0IHsKICAgICAgICByZXF1aXJlKG93bmVyLmlzTm90QmxhbmsoKSkKICAgICAgICByZXF1aXJlKHByb2ZpbGVJZCBpbiAxLi42KQogICAgfQp9CgppbnRlcm5hbCBkYXRhIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QodmFsIHJldmlzaW9uOiBMb25nLCB2YWwgcHJlZmVyZW5jZXM6IEpzb25PYmplY3QsIHZhbCBwcm9maWxlSW5zdGFuY2U6IFN0cmluZz8gPSBudWxsKSB7CiAgICBpbml0IHsgcmVxdWlyZShyZXZpc2lvbiA+PSAwKSB9Cn0KCmludGVybmFsIGRhdGEgY2xhc3MgU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KAogICAgdmFsIHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLAogICAgdmFsIGdlbmVyYXRpb246IExvbmcsCikKCmludGVybmFsIGVudW0gY2xhc3MgU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlIHsgVXNlVGhpc0RldmljZSwgVXNlU2F2ZWRTZXR0aW5ncyB9CmludGVybmFsIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzQ2hvaWNlUmVxdWlyZWRFeGNlcHRpb24gOiBJbGxlZ2FsU3RhdGVFeGNlcHRpb24oIkNob29zZSB3aGljaCBjYXRhbG9nIHNldHRpbmdzIHRvIGtlZXAiKQoKLyoqIEEgcmVzcG9uc2UgbWF5IG9ubHkgYXBwbHkgdG8gdGhlIHN0aWxsLWVuYWJsZWQgYWNjb3VudCwgcHJvZmlsZSBhbmQgZ2VuZXJhdGlvbi4gKi8KaW50ZXJuYWwgZnVuIGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoCiAgICByZXF1ZXN0OiBTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3QsCiAgICBhY3RpdmVTY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZT8sCiAgICBhY3RpdmVHZW5lcmF0aW9uOiBMb25nLAogICAgZW5hYmxlZDogQm9vbGVhbiwKKTogQm9vbGVhbiA9IGVuYWJsZWQgJiYgcmVxdWVzdC5zY29wZSA9PSBhY3RpdmVTY29wZSAmJiByZXF1ZXN0LmdlbmVyYXRpb24gPT0gYWN0aXZlR2VuZXJhdGlvbgoKLyoqCiAqIE1lcmdlIHRoZSB1c2VyJ3MgaW50ZW50aW9uYWwgY2hhbmdlcyBvbnRvIHRoZSBsYXRlc3QgcmVtb3RlIHNuYXBzaG90LgogKiBUaGUgZXhwb3J0aW5nIGRldmljZSBvd25zIG9ubHkgdGhlIGtleXMgaXQgY2FuIHJlcHJlc2VudC4gVW5rbm93biBrZXlzIGFuZAogKiByZW1vdGUgY2hhbmdlcyB0byB1bnRvdWNoZWQgcHJlZmVyZW5jZXMgc3Vydml2ZS4gQSBtaXNzaW5nIGJhc2VsaW5lIHJlcXVpcmVzCiAqIHRoZSBleHBsaWNpdCBmaXJzdC1zeW5jIGNob2ljZSBpbnN0ZWFkIG9mIGFzc3VtaW5nIHRoYXQgbG9jYWwgZGVmYXVsdHMgYXJlIGVkaXRzLgogKi8KaW50ZXJuYWwgZnVuIG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMoCiAgICBiYXNlbGluZTogSnNvbk9iamVjdD8sCiAgICBsb2NhbDogSnNvbk9iamVjdCwKICAgIHJlbW90ZTogSnNvbk9iamVjdCwKICAgIHN1cHBvcnRlZEtleXM6IFNldDxTdHJpbmc+LAopOiBKc29uT2JqZWN0IHsKICAgIHJlcXVpcmVOb3ROdWxsKGJhc2VsaW5lKSB7ICJDaG9vc2UgaW5pdGlhbCBzZXR0aW5ncyBiZWZvcmUgc3luY2hyb25pemluZyIgfQogICAgcmVxdWlyZShzdXBwb3J0ZWRLZXlzLmFsbCB7IGl0IGluIHNoYXJlZFByZWZlcmVuY2VLZXlzIH0pCiAgICByZXF1aXJlKGxvY2FsLmtleXMgPT0gc3VwcG9ydGVkS2V5cykgeyAiSW5jb21wbGV0ZSBkZXZpY2UgcHJlZmVyZW5jZSBleHBvcnQiIH0KICAgIHZhbCBtZXJnZWQgPSByZW1vdGUudG9NdXRhYmxlTWFwKCkKICAgIHN1cHBvcnRlZEtleXMuZm9yRWFjaCB7IGtleSAtPgogICAgICAgIGlmIChsb2NhbFtrZXldICE9IGJhc2VsaW5lW2tleV0pIHsKICAgICAgICAgICAgdmFsIHZhbHVlID0gbG9jYWxba2V5XQogICAgICAgICAgICBpZiAoa2V5ID09ICJob21lQ2F0YWxvZ3MiKSB7CiAgICAgICAgICAgICAgICBtZXJnZWRba2V5XSA9IG1lcmdlSG9tZUNhdGFsb2dQcmVmZXJlbmNlcygKICAgICAgICAgICAgICAgICAgICBiYXNlbGluZVtrZXldIGFzPyBKc29uQXJyYXkgPzogSnNvbkFycmF5KGVtcHR5TGlzdCgpKSwKICAgICAgICAgICAgICAgICAgICB2YWx1ZSBhcz8gSnNvbkFycmF5ID86IGVycm9yKCJJbnZhbGlkIGNhdGFsb2cgcHJlZmVyZW5jZXMiKSwKICAgICAgICAgICAgICAgICAgICByZW1vdGVba2V5XSBhcz8gSnNvbkFycmF5ID86IEpzb25BcnJheShlbXB0eUxpc3QoKSksCiAgICAgICAgICAgICAgICApCiAgICAgICAgICAgIH0gZWxzZSBpZiAodmFsdWUgIT0gbnVsbCkgbWVyZ2VkW2tleV0gPSB2YWx1ZSBlbHNlIG1lcmdlZC5yZW1vdmUoa2V5KQogICAgICAgIH0KICAgIH0KICAgIHJldHVybiBKc29uT2JqZWN0KG1lcmdlZCkKfQoKaW50ZXJuYWwgZnVuIGluaXRpYWxTaGFyZWRQcmVmZXJlbmNlcygKICAgIGNob2ljZTogU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLAogICAgbG9jYWw6IEpzb25PYmplY3QsCiAgICByZW1vdGU6IEpzb25PYmplY3QsCiAgICBzdXBwb3J0ZWRLZXlzOiBTZXQ8U3RyaW5nPiwKKTogSnNvbk9iamVjdCB7CiAgICByZXF1aXJlKHN1cHBvcnRlZEtleXMuYWxsIHsgaXQgaW4gc2hhcmVkUHJlZmVyZW5jZUtleXMgfSkKICAgIHJlcXVpcmUobG9jYWwua2V5cyA9PSBzdXBwb3J0ZWRLZXlzKSB7ICJJbmNvbXBsZXRlIGRldmljZSBwcmVmZXJlbmNlIGV4cG9ydCIgfQogICAgaWYgKGNob2ljZSA9PSBTaGFyZWRQcmVmZXJlbmNlc0luaXRpYWxDaG9pY2UuVXNlU2F2ZWRTZXR0aW5ncykgcmV0dXJuIHJlbW90ZQogICAgcmV0dXJuIEpzb25PYmplY3QocmVtb3RlLnRvTXV0YWJsZU1hcCgpLmFwcGx5IHsKICAgICAgICBzdXBwb3J0ZWRLZXlzLmZvckVhY2ggeyBrZXkgLT4KICAgICAgICAgICAgdmFsIHZhbHVlID0gbG9jYWxba2V5XQogICAgICAgICAgICBpZiAodmFsdWUgIT0gbnVsbCkgcHV0KGtleSwgdmFsdWUpIGVsc2UgcmVtb3ZlKGtleSkKICAgICAgICB9CiAgICB9KQp9CgovKiogT25seSBleHBsaWNpdCwgc3VwcG9ydGVkIHZhbHVlcyBhcmUgYXBwbGllZDsgb21pdHRlZCByZW1vdGUgdmFsdWVzIGtlZXAgZGV2aWNlIGRlZmF1bHRzLiAqLwppbnRlcm5hbCBmdW4gYXBwbGljYWJsZVNoYXJlZFByZWZlcmVuY2VzKHJlbW90ZTogSnNvbk9iamVjdCwgc3VwcG9ydGVkS2V5czogU2V0PFN0cmluZz4pOiBNYXA8U3RyaW5nLCBKc29uRWxlbWVudD4gPQogICAgcmVtb3RlLmZpbHRlcktleXMgeyBpdCBpbiBzdXBwb3J0ZWRLZXlzICYmIGl0IGluIHNoYXJlZFByZWZlcmVuY2VLZXlzIH0KCi8qKiBNZXJnZSByb3cgZmllbGRzIGluZGVwZW5kZW50bHk7IGFuIHVubG9hZGVkL2Fic2VudCBsb2NhbCBjYXRhbG9nIGlzIG5ldmVyIGEgZGVsZXRpb24uICovCmludGVybmFsIGZ1biBtZXJnZUhvbWVDYXRhbG9nUHJlZmVyZW5jZXMoYmFzZWxpbmU6IEpzb25BcnJheSwgbG9jYWw6IEpzb25BcnJheSwgcmVtb3RlOiBKc29uQXJyYXkpOiBKc29uQXJyYXkgewogICAgZnVuIGlkZW50aXR5KHJvdzogSnNvbk9iamVjdCk6IFN0cmluZyB7CiAgICAgICAgaWYgKHJvd1siaXNfY29sbGVjdGlvbiJdPy5qc29uUHJpbWl0aXZlPy5ib29sZWFuT3JOdWxsID09IHRydWUpIHsKICAgICAgICAgICAgcmV0dXJuICJjb2xsZWN0aW9uOiIgKyByZXF1aXJlTm90TnVsbChyb3dbImNvbGxlY3Rpb25faWQiXT8uanNvblByaW1pdGl2ZT8uY29udGVudE9yTnVsbCkuYWxzbyB7IHJlcXVpcmUoaXQuaXNOb3RCbGFuaygpKSB9CiAgICAgICAgfQogICAgICAgIHJldHVybiBKc29uQXJyYXkobGlzdE9mKCJhZGRvbl9pZCIsICJ0eXBlIiwgImNhdGFsb2dfaWQiKS5tYXAgeyBrZXkgLT4KICAgICAgICAgICAgSnNvblByaW1pdGl2ZShyZXF1aXJlTm90TnVsbChyb3dba2V5XT8uanNvblByaW1pdGl2ZT8uY29udGVudE9yTnVsbCkuYWxzbyB7IHJlcXVpcmUoaXQuaXNOb3RCbGFuaygpKSB9KQogICAgICAgIH0pLnRvU3RyaW5nKCkKICAgIH0KICAgIGZ1biByb3dzKHZhbHVlOiBKc29uQXJyYXkpOiBNYXA8U3RyaW5nLCBKc29uT2JqZWN0PiB7CiAgICAgICAgdmFsIHJlc3VsdCA9IGxpbmtlZE1hcE9mPFN0cmluZywgSnNvbk9iamVjdD4oKQogICAgICAgIHZhbHVlLmZvckVhY2hJbmRleGVkIHsgaW5kZXgsIGVsZW1lbnQgLT4KICAgICAgICAgICAgdmFsIHJhdyA9IGVsZW1lbnQgYXM/IEpzb25PYmplY3QgPzogZXJyb3IoIkludmFsaWQgY2F0YWxvZyBwcmVmZXJlbmNlIHJvdyIpCiAgICAgICAgICAgIHZhbCByb3cgPSBKc29uT2JqZWN0KG1hcE9mKAogICAgICAgICAgICAgICAgImVuYWJsZWQiIHRvIEpzb25QcmltaXRpdmUodHJ1ZSksICJjdXN0b21fdGl0bGUiIHRvIEpzb25QcmltaXRpdmUoIiIpLAogICAgICAgICAgICAgICAgIm9yZGVyIiB0byBKc29uUHJpbWl0aXZlKGluZGV4KSwgImlzX2NvbGxlY3Rpb24iIHRvIEpzb25QcmltaXRpdmUoZmFsc2UpLAogICAgICAgICAgICAgICAgImNvbGxlY3Rpb25faWQiIHRvIEpzb25QcmltaXRpdmUoIiIpLAogICAgICAgICAgICApICsgcmF3KQogICAgICAgICAgICB2YWwga2V5ID0gaWRlbnRpdHkocm93KQogICAgICAgICAgICByZXF1aXJlKGtleSAhaW4gcmVzdWx0KSB7ICJEdXBsaWNhdGUgY2F0YWxvZyBwcmVmZXJlbmNlIHJvdyIgfQogICAgICAgICAgICByZXN1bHRba2V5XSA9IHJvdwogICAgICAgIH0KICAgICAgICByZXR1cm4gcmVzdWx0CiAgICB9CiAgICB2YWwgYmFzZVJvd3MgPSByb3dzKGJhc2VsaW5lKQogICAgdmFsIGxvY2FsUm93cyA9IHJvd3MobG9jYWwpCiAgICB2YWwgcmVtb3RlUm93cyA9IHJvd3MocmVtb3RlKQogICAgdmFsIG1lcmdlZCA9IHJlbW90ZVJvd3MudG9NdXRhYmxlTWFwKCkKICAgIGxvY2FsUm93cy5mb3JFYWNoIHsgKGtleSwgcm93KSAtPgogICAgICAgIHZhbCBiZWZvcmUgPSBiYXNlUm93c1trZXldCiAgICAgICAgdmFsIGxhdGVzdCA9IHJlbW90ZVJvd3Nba2V5XQogICAgICAgIGlmIChiZWZvcmUgPT0gbnVsbCkgewogICAgICAgICAgICBpZiAobGF0ZXN0ID09IG51bGwpIG1lcmdlZFtrZXldID0gcm93CiAgICAgICAgICAgIGVsc2UgaWYgKHJvdyAhPSBsYXRlc3QpIHRocm93IFNoYXJlZFByZWZlcmVuY2VzQ2hvaWNlUmVxdWlyZWRFeGNlcHRpb24oKQogICAgICAgIH0gZWxzZSBpZiAocm93ICE9IGJlZm9yZSkgewogICAgICAgICAgICBpZiAobGF0ZXN0ID09IG51bGwpIG1lcmdlZFtrZXldID0gcm93CiAgICAgICAgICAgIGVsc2UgewogICAgICAgICAgICAgICAgdmFsIGZpZWxkcyA9IGxhdGVzdC50b011dGFibGVNYXAoKQogICAgICAgICAgICAgICAgLy8gT25seSBlZGl0YWJsZSBmaWVsZHMgYXJlIGNoYW5nZXM7IGlkZW50aXR5IGlzIHN0YWJsZSBhY3Jvc3MgY2xpZW50cy4KICAgICAgICAgICAgICAgIGxpc3RPZigiZW5hYmxlZCIsICJjdXN0b21fdGl0bGUiLCAib3JkZXIiKS5mb3JFYWNoIHsgZmllbGQgLT4KICAgICAgICAgICAgICAgICAgICBpZiAocm93W2ZpZWxkXSAhPSBiZWZvcmVbZmllbGRdKSB7CiAgICAgICAgICAgICAgICAgICAgICAgIHZhbCB2YWx1ZSA9IHJvd1tmaWVsZF0KICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHZhbHVlICE9IG51bGwpIGZpZWxkc1tmaWVsZF0gPSB2YWx1ZSBlbHNlIGZpZWxkcy5yZW1vdmUoZmllbGQpCiAgICAgICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgbWVyZ2VkW2tleV0gPSBKc29uT2JqZWN0KGZpZWxkcykKICAgICAgICAgICAgfQogICAgICAgIH0KICAgIH0KICAgIHZhbCByZW1vdGVQb3NpdGlvbnMgPSByZW1vdGVSb3dzLmtleXMud2l0aEluZGV4KCkuYXNzb2NpYXRlIHsgaXQudmFsdWUgdG8gaXQuaW5kZXggfQogICAgdmFsIG9yZGVyZWQgPSBtZXJnZWQuZW50cmllcy5zb3J0ZWRXaXRoKGNvbXBhcmVCeTxNYXAuRW50cnk8U3RyaW5nLCBKc29uT2JqZWN0Pj4gewogICAgICAgIGl0LnZhbHVlWyJvcmRlciJdPy5qc29uUHJpbWl0aXZlPy5pbnRPck51bGwgPzogSW50Lk1BWF9WQUxVRQogICAgfS50aGVuQnkgeyByZW1vdGVQb3NpdGlvbnNbaXQua2V5XSA/OiBJbnQuTUFYX1ZBTFVFIH0udGhlbkJ5IHsgaXQua2V5IH0pCiAgICByZXR1cm4gSnNvbkFycmF5KG9yZGVyZWQubWFwSW5kZXhlZCB7IGluZGV4LCBlbnRyeSAtPiBKc29uT2JqZWN0KGVudHJ5LnZhbHVlICsgKCJvcmRlciIgdG8gSnNvblByaW1pdGl2ZShpbmRleCkpKSB9KQp9Cg==', 'app/src/main/java/com/nuvio/tv/core/sync/OmniaSharedPreferencesEngine.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLkNhbmNlbGxhdGlvbkV4Y2VwdGlvbgppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmZsb3cuTXV0YWJsZVN0YXRlRmxvdwppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmZsb3cuU3RhdGVGbG93CmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuZmxvdy5hc1N0YXRlRmxvdwppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmZsb3cudXBkYXRlCmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuc3luYy5NdXRleAppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLnN5bmMud2l0aExvY2sKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25PYmplY3QKCmludGVybmFsIGRhdGEgY2xhc3MgU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCgKICAgIHZhbCBlbmFibGVkOiBCb29sZWFuID0gZmFsc2UsCiAgICB2YWwgYmFzZWxpbmU6IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3Q/ID0gbnVsbCwKKQoKaW50ZXJuYWwgaW50ZXJmYWNlIFNoYXJlZFByZWZlcmVuY2VzTG9jYWxTdG9yZSB7CiAgICBmdW4gbG9hZChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSk6IFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQKICAgIGZ1biBzYXZlKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCByZWNvcmQ6IFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQpCn0KCmludGVybmFsIGRhdGEgY2xhc3MgU2hhcmVkUHJlZmVyZW5jZXNQdXNoUmVzdWx0KAogICAgdmFsIGNvbmZsaWN0OiBCb29sZWFuLAogICAgdmFsIHNuYXBzaG90OiBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90LAopCgppbnRlcm5hbCBpbnRlcmZhY2UgU2hhcmVkUHJlZmVyZW5jZXNUcmFuc3BvcnQgewogICAgc3VzcGVuZCBmdW4gcHVsbChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSk6IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QKICAgIHN1c3BlbmQgZnVuIHB1c2goc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIGV4cGVjdGVkUmV2aXNpb246IExvbmcsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCBleHBlY3RlZFByb2ZpbGVJbnN0YW5jZTogU3RyaW5nPyk6IFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdAp9CgppbnRlcm5hbCBpbnRlcmZhY2UgU2hhcmVkUHJlZmVyZW5jZXNEZXZpY2UgewogICAgdmFsIHN1cHBvcnRlZEtleXM6IFNldDxTdHJpbmc+CiAgICBmdW4gY3VycmVudFNjb3BlKCk6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGU/CiAgICBzdXNwZW5kIGZ1biBleHBvcnQoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpOiBKc29uT2JqZWN0CiAgICAvKiogQWRhcHRlciBjaGVja3MgdGhlIHN1cHBsaWVkIGd1YXJkIGluc2lkZSBldmVyeSBhc3luY2hyb25vdXMgc3RvcmFnZSBlZGl0LiAqLwogICAgc3VzcGVuZCBmdW4gYXBwbHkoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCBzdGlsbEN1cnJlbnQ6ICgpIC0+IEJvb2xlYW4pCn0KCmludGVybmFsIGVudW0gY2xhc3MgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzIHsgT2ZmLCBSZWFkeSwgQ2hvb3NlSW5pdGlhbFNldHRpbmdzLCBTeW5jaW5nLCBTeW5jZWQsIFNpZ25JblJlcXVpcmVkLCBFcnJvciB9CgppbnRlcm5hbCBkYXRhIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXRlKAogICAgdmFsIGVuYWJsZWQ6IEJvb2xlYW4gPSBmYWxzZSwKICAgIHZhbCBzdGF0dXM6IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cyA9IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYsCikKCi8qKgogKiBEZXZpY2UtbG9jYWwgb3B0LWluIHdpdGggYWNjb3VudC9wcm9maWxlIGd1YXJkcyBhcm91bmQgZXZlcnkgc3VzcGVuZCBib3VuZGFyeS4KICogRGlzYWJsZSBuZXZlciB3YWl0cyBiZWhpbmQgYSBuZXR3b3JrIG11dGV4IGFuZCBjYW5ub3QgYmUgdW5kb25lIGJ5IGEgbGF0ZSByZXNwb25zZS4KICovCmludGVybmFsIGNsYXNzIE9tbmlhU2hhcmVkUHJlZmVyZW5jZXNFbmdpbmUoCiAgICBwcml2YXRlIHZhbCBkZXZpY2U6IFNoYXJlZFByZWZlcmVuY2VzRGV2aWNlLAogICAgcHJpdmF0ZSB2YWwgc3RvcmU6IFNoYXJlZFByZWZlcmVuY2VzTG9jYWxTdG9yZSwKICAgIHByaXZhdGUgdmFsIHRyYW5zcG9ydDogU2hhcmVkUHJlZmVyZW5jZXNUcmFuc3BvcnQsCikgewogICAgcHJpdmF0ZSB2YWwgbXV0ZXggPSBNdXRleCgpCiAgICBwcml2YXRlIHZhbCBzdGF0ZU11dGV4ID0gTXV0ZXgoKQogICAgcHJpdmF0ZSB2YWwgZ2VuZXJhdGlvbiA9IE11dGFibGVTdGF0ZUZsb3coMEwpCiAgICBwcml2YXRlIHZhbCBfc3RhdGUgPSBNdXRhYmxlU3RhdGVGbG93KFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXRlKCkpCiAgICB2YWwgc3RhdGU6IFN0YXRlRmxvdzxTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZT4gPSBfc3RhdGUuYXNTdGF0ZUZsb3coKQoKICAgIGZ1biByZWZyZXNoTG9jYWxTdGF0ZSgpIHsKICAgICAgICBnZW5lcmF0aW9uLnVwZGF0ZSB7IGl0ICsgMSB9CiAgICAgICAgdmFsIHNjb3BlID0gZGV2aWNlLmN1cnJlbnRTY29wZSgpCiAgICAgICAgdmFsIGVuYWJsZWQgPSBzY29wZT8ubGV0IHsgc3RvcmUubG9hZChpdCkuZW5hYmxlZCB9ID09IHRydWUKICAgICAgICBfc3RhdGUudmFsdWUgPSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZShlbmFibGVkLCBpZiAoZW5hYmxlZCkgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlJlYWR5IGVsc2UgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZikKICAgIH0KCiAgICBzdXNwZW5kIGZ1biBkaXNhYmxlKCkgewogICAgICAgIGdlbmVyYXRpb24udXBkYXRlIHsgaXQgKyAxIH0KICAgICAgICB2YWwgc2NvcGUgPSBkZXZpY2UuY3VycmVudFNjb3BlKCkKICAgICAgICBzdGF0ZU11dGV4LndpdGhMb2NrIHsKICAgICAgICAgICAgc2NvcGU/LmxldCB7IHN0b3JlLnNhdmUoaXQsIHN0b3JlLmxvYWQoaXQpLmNvcHkoZW5hYmxlZCA9IGZhbHNlKSkgfQogICAgICAgIH0KICAgICAgICBpZiAoc2NvcGUgPT0gZGV2aWNlLmN1cnJlbnRTY29wZSgpKSBfc3RhdGUudmFsdWUgPSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZSgpCiAgICAgICAgZWxzZSByZWZyZXNoTG9jYWxTdGF0ZSgpCiAgICB9CgogICAgcHJpdmF0ZSBmdW4gY3VycmVudChyZXF1ZXN0OiBTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3QsIHJlcXVpcmVFbmFibGVkOiBCb29sZWFuKTogQm9vbGVhbiA9CiAgICAgICAgcmVxdWVzdC5zY29wZSA9PSBkZXZpY2UuY3VycmVudFNjb3BlKCkgJiYgcmVxdWVzdC5nZW5lcmF0aW9uID09IGdlbmVyYXRpb24udmFsdWUgJiYKICAgICAgICAgICAgKCFyZXF1aXJlRW5hYmxlZCB8fCBzdG9yZS5sb2FkKHJlcXVlc3Quc2NvcGUpLmVuYWJsZWQpCgogICAgcHJpdmF0ZSBmdW4gdXBkYXRlKHJlcXVlc3Q6IFNoYXJlZFByZWZlcmVuY2VzUmVxdWVzdCwgc3RhdHVzOiBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMpIHsKICAgICAgICBpZiAoY3VycmVudChyZXF1ZXN0LCByZXF1aXJlRW5hYmxlZCA9IGZhbHNlKSkgewogICAgICAgICAgICBfc3RhdGUudmFsdWUgPSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZShzdG9yZS5sb2FkKHJlcXVlc3Quc2NvcGUpLmVuYWJsZWQsIHN0YXR1cykKICAgICAgICB9CiAgICB9CgogICAgc3VzcGVuZCBmdW4gZW5hYmxlKGNob2ljZTogU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlPyA9IG51bGwpOiBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMgPSBtdXRleC53aXRoTG9jayB7CiAgICAgICAgdmFsIHNjb3BlID0gZGV2aWNlLmN1cnJlbnRTY29wZSgpID86IHJ1biB7CiAgICAgICAgICAgIF9zdGF0ZS52YWx1ZSA9IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXRlKGZhbHNlLCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU2lnbkluUmVxdWlyZWQpCiAgICAgICAgICAgIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU2lnbkluUmVxdWlyZWQKICAgICAgICB9CiAgICAgICAgdmFsIHJlcXVlc3QgPSBTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIGdlbmVyYXRpb24udmFsdWUpCiAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jaW5nKQogICAgICAgIHRyeSB7CiAgICAgICAgICAgIHZhbCBsb2NhbCA9IGRldmljZS5leHBvcnQoc2NvcGUpCiAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCBmYWxzZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgIHZhciByZW1vdGUgPSB0cmFuc3BvcnQucHVsbChzY29wZSkKICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIGZhbHNlKSkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICAgICAgaWYgKHJlbW90ZS5wcmVmZXJlbmNlcy5pc05vdEVtcHR5KCkgJiYgY2hvaWNlID09IG51bGwpIHsKICAgICAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzKQogICAgICAgICAgICAgICAgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MKICAgICAgICAgICAgfQogICAgICAgICAgICB2YWwgcmVzb2x2ZWRDaG9pY2UgPSBjaG9pY2UgPzogU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLlVzZVRoaXNEZXZpY2UKICAgICAgICAgICAgcmVwZWF0KDMpIHsKICAgICAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCBmYWxzZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICB2YWwgaW5pdGlhbCA9IGluaXRpYWxTaGFyZWRQcmVmZXJlbmNlcyhyZXNvbHZlZENob2ljZSwgbG9jYWwsIHJlbW90ZS5wcmVmZXJlbmNlcywgZGV2aWNlLnN1cHBvcnRlZEtleXMpCiAgICAgICAgICAgICAgICB2YWwgYWNjZXB0ZWQgPSBpZiAoaW5pdGlhbCA9PSByZW1vdGUucHJlZmVyZW5jZXMpIFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdChmYWxzZSwgcmVtb3RlKQogICAgICAgICAgICAgICAgICAgIGVsc2UgdHJhbnNwb3J0LnB1c2goc2NvcGUsIHJlbW90ZS5yZXZpc2lvbiwgaW5pdGlhbCwgcmVtb3RlLnByb2ZpbGVJbnN0YW5jZSkKICAgICAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCBmYWxzZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICBpZiAoYWNjZXB0ZWQuc25hcHNob3QucHJvZmlsZUluc3RhbmNlICE9IHJlbW90ZS5wcm9maWxlSW5zdGFuY2UpIHJldHVybkB3aXRoTG9jayByZXF1aXJlTmV3UHJvZmlsZUNob2ljZShyZXF1ZXN0KQogICAgICAgICAgICAgICAgcmVtb3RlID0gYWNjZXB0ZWQuc25hcHNob3QKICAgICAgICAgICAgICAgIGlmICghYWNjZXB0ZWQuY29uZmxpY3QpIHsKICAgICAgICAgICAgICAgICAgICAvLyBQZXJzaXN0IGVuYWJsZWQgb25seSBhZnRlciB0aGUgZXhwbGljaXQgaW5pdGlhbCBhY3Rpb24gc3VjY2VlZHMuCiAgICAgICAgICAgICAgICAgICAgc3RhdGVNdXRleC53aXRoTG9jayB7CiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChjdXJyZW50KHJlcXVlc3QsIGZhbHNlKSkgc3RvcmUuc2F2ZShzY29wZSwgc3RvcmUubG9hZChzY29wZSkuY29weShlbmFibGVkID0gdHJ1ZSkpCiAgICAgICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgICAgIGFwcGx5V2l0aG91dE92ZXJ3cml0aW5nTmV3TG9jYWxFZGl0cyhyZXF1ZXN0LCBsb2NhbCwgcmVtb3RlKQogICAgICAgICAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCB0cnVlKSkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICAgICAgICAgICAgICBhY2tub3dsZWRnZShyZXF1ZXN0LCBsb2NhbCwgcmVtb3RlKQogICAgICAgICAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCB0cnVlKSkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICAgICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCkKICAgICAgICAgICAgICAgICAgICByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZAogICAgICAgICAgICAgICAgfQogICAgICAgICAgICB9CiAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IpCiAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5FcnJvcgogICAgICAgIH0gY2F0Y2ggKGNhbmNlbGxlZDogQ2FuY2VsbGF0aW9uRXhjZXB0aW9uKSB7CiAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBpZiAoc3RvcmUubG9hZChzY29wZSkuZW5hYmxlZCkgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlJlYWR5IGVsc2UgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZikKICAgICAgICAgICAgdGhyb3cgY2FuY2VsbGVkCiAgICAgICAgfSBjYXRjaCAoXzogU2hhcmVkUHJlZmVyZW5jZXNDaG9pY2VSZXF1aXJlZEV4Y2VwdGlvbikgewogICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkNob29zZUluaXRpYWxTZXR0aW5ncykKICAgICAgICAgICAgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkNob29zZUluaXRpYWxTZXR0aW5ncwogICAgICAgIH0gY2F0Y2ggKF86IEV4Y2VwdGlvbikgewogICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgZmFsc2UpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yKQogICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IKICAgICAgICB9CiAgICB9CgogICAgc3VzcGVuZCBmdW4gc3luY2hyb25pemUoKTogU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzID0gbXV0ZXgud2l0aExvY2sgewogICAgICAgIHZhbCBzY29wZSA9IGRldmljZS5jdXJyZW50U2NvcGUoKSA/OiByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlNpZ25JblJlcXVpcmVkCiAgICAgICAgdmFsIHJlcXVlc3QgPSBTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIGdlbmVyYXRpb24udmFsdWUpCiAgICAgICAgdmFsIHJlY29yZCA9IHN0b3JlLmxvYWQoc2NvcGUpCiAgICAgICAgaWYgKCFyZWNvcmQuZW5hYmxlZCkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICBpZiAocmVjb3JkLmJhc2VsaW5lID09IG51bGwpIHsKICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MpCiAgICAgICAgICAgIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzCiAgICAgICAgfQogICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2luZykKICAgICAgICB0cnkgewogICAgICAgICAgICB2YWwgbG9jYWwgPSBkZXZpY2UuZXhwb3J0KHNjb3BlKQogICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgIHZhciByZW1vdGUgPSB0cmFuc3BvcnQucHVsbChzY29wZSkKICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICBpZiAocmVjb3JkLmJhc2VsaW5lLnByb2ZpbGVJbnN0YW5jZSAhPSByZW1vdGUucHJvZmlsZUluc3RhbmNlKSByZXR1cm5Ad2l0aExvY2sgcmVxdWlyZU5ld1Byb2ZpbGVDaG9pY2UocmVxdWVzdCkKICAgICAgICAgICAgcmVwZWF0KDMpIHsKICAgICAgICAgICAgICAgIHZhbCBtZXJnZWQgPSBtZXJnZVNoYXJlZFByZWZlcmVuY2VzKHJlY29yZC5iYXNlbGluZS5wcmVmZXJlbmNlcywgbG9jYWwsIHJlbW90ZS5wcmVmZXJlbmNlcywgZGV2aWNlLnN1cHBvcnRlZEtleXMpCiAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICB2YWwgYWNjZXB0ZWQgPSBpZiAobWVyZ2VkID09IHJlbW90ZS5wcmVmZXJlbmNlcykgU2hhcmVkUHJlZmVyZW5jZXNQdXNoUmVzdWx0KGZhbHNlLCByZW1vdGUpCiAgICAgICAgICAgICAgICAgICAgZWxzZSB0cmFuc3BvcnQucHVzaChzY29wZSwgcmVtb3RlLnJldmlzaW9uLCBtZXJnZWQsIHJlbW90ZS5wcm9maWxlSW5zdGFuY2UpCiAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICBpZiAoYWNjZXB0ZWQuc25hcHNob3QucHJvZmlsZUluc3RhbmNlICE9IHJlbW90ZS5wcm9maWxlSW5zdGFuY2UpIHJldHVybkB3aXRoTG9jayByZXF1aXJlTmV3UHJvZmlsZUNob2ljZShyZXF1ZXN0KQogICAgICAgICAgICAgICAgcmVtb3RlID0gYWNjZXB0ZWQuc25hcHNob3QKICAgICAgICAgICAgICAgIGlmICghYWNjZXB0ZWQuY29uZmxpY3QpIHsKICAgICAgICAgICAgICAgICAgICBhcHBseVdpdGhvdXRPdmVyd3JpdGluZ05ld0xvY2FsRWRpdHMocmVxdWVzdCwgbG9jYWwsIHJlbW90ZSkKICAgICAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICAgICAgYWNrbm93bGVkZ2UocmVxdWVzdCwgbG9jYWwsIHJlbW90ZSkKICAgICAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQpCiAgICAgICAgICAgICAgICAgICAgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQKICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgfQogICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yKQogICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IKICAgICAgICB9IGNhdGNoIChjYW5jZWxsZWQ6IENhbmNlbGxhdGlvbkV4Y2VwdGlvbikgewogICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgaWYgKHN0b3JlLmxvYWQoc2NvcGUpLmVuYWJsZWQpIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5SZWFkeSBlbHNlIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYpCiAgICAgICAgICAgIHRocm93IGNhbmNlbGxlZAogICAgICAgIH0gY2F0Y2ggKF86IFNoYXJlZFByZWZlcmVuY2VzQ2hvaWNlUmVxdWlyZWRFeGNlcHRpb24pIHsKICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MpCiAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MKICAgICAgICB9IGNhdGNoIChfOiBFeGNlcHRpb24pIHsKICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIGZhbHNlKSkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5FcnJvcikKICAgICAgICAgICAgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yCiAgICAgICAgfQogICAgfQoKICAgIHByaXZhdGUgc3VzcGVuZCBmdW4gcmVxdWlyZU5ld1Byb2ZpbGVDaG9pY2UocmVxdWVzdDogU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KTogU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzIHsKICAgICAgICBzdGF0ZU11dGV4LndpdGhMb2NrIHsKICAgICAgICAgICAgaWYgKGN1cnJlbnQocmVxdWVzdCwgZmFsc2UpKSBzdG9yZS5zYXZlKHJlcXVlc3Quc2NvcGUsIFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQoKSkKICAgICAgICB9CiAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MpCiAgICAgICAgcmV0dXJuIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MKICAgIH0KCiAgICBwcml2YXRlIHN1c3BlbmQgZnVuIGFwcGx5V2l0aG91dE92ZXJ3cml0aW5nTmV3TG9jYWxFZGl0cygKICAgICAgICByZXF1ZXN0OiBTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3QsCiAgICAgICAgZXhwb3J0ZWQ6IEpzb25PYmplY3QsCiAgICAgICAgYWNrbm93bGVkZ2VkOiBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90LAogICAgKSB7CiAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm4KICAgICAgICB2YWwgbGF0ZXN0ID0gZGV2aWNlLmV4cG9ydChyZXF1ZXN0LnNjb3BlKQogICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCB0cnVlKSkgcmV0dXJuCiAgICAgICAgLy8gQSBwcmVmZXJlbmNlIGNoYW5nZWQgd2hpbGUgdGhlIG5ldHdvcmsgcmVxdWVzdCB3YXMgaW4gZmxpZ2h0IHJlbWFpbnMgbG9jYWwsCiAgICAgICAgLy8gYW5kIGRpZmZlcnMgZnJvbSB0aGUgYWNrbm93bGVkZ2VkIGJhc2VsaW5lIG9uIHRoZSBuZXh0IHN5bmNocm9uaXphdGlvbi4KICAgICAgICB2YWwgc2FmZVRvQXBwbHkgPSBKc29uT2JqZWN0KGFwcGxpY2FibGVTaGFyZWRQcmVmZXJlbmNlcyhhY2tub3dsZWRnZWQucHJlZmVyZW5jZXMsIGRldmljZS5zdXBwb3J0ZWRLZXlzKQogICAgICAgICAgICAuZmlsdGVyS2V5cyB7IGtleSAtPiBsYXRlc3Rba2V5XSA9PSBleHBvcnRlZFtrZXldIH0pCiAgICAgICAgZGV2aWNlLmFwcGx5KHJlcXVlc3Quc2NvcGUsIHNhZmVUb0FwcGx5KSB7IGN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkgfQogICAgfQoKICAgIHByaXZhdGUgc3VzcGVuZCBmdW4gYWNrbm93bGVkZ2UoCiAgICAgICAgcmVxdWVzdDogU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0LAogICAgICAgIGV4cG9ydGVkOiBKc29uT2JqZWN0LAogICAgICAgIGFja25vd2xlZGdlZDogU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCwKICAgICkgewogICAgICAgIC8vIFJlY29yZCB0aGUgZXhwZWN0ZWQgYXBwbGllZCB2YWx1ZXMgb25seSBhZnRlciBzdG9yYWdlIGFwcGxpY2F0aW9uIHN1Y2NlZWRzLgogICAgICAgIC8vIERlZmF1bHRzIG9taXR0ZWQgYnkgYW5vdGhlciBwbGF0Zm9ybSBhcmUgbm90IG1pc3Rha2VuIGZvciBuZXcgbG9jYWwgZWRpdHMuCiAgICAgICAgdmFsIGJhc2VsaW5lID0gYWNrbm93bGVkZ2VkLmNvcHkocHJlZmVyZW5jZXMgPSBKc29uT2JqZWN0KGV4cG9ydGVkICsgYWNrbm93bGVkZ2VkLnByZWZlcmVuY2VzKSkKICAgICAgICBzdGF0ZU11dGV4LndpdGhMb2NrIHsKICAgICAgICAgICAgaWYgKGN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHN0b3JlLnNhdmUocmVxdWVzdC5zY29wZSwgU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCh0cnVlLCBiYXNlbGluZSkpCiAgICAgICAgfQogICAgfQp9Cg==', 'app/src/main/java/com/nuvio/tv/core/sync/OmniaPreferencesSyncRecordStore.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbgppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uYm9vbGVhbk9yTnVsbAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uY29udGVudE9yTnVsbAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uYnVpbGRKc29uT2JqZWN0CmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5qc29uT2JqZWN0CmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5qc29uUHJpbWl0aXZlCmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5sb25nT3JOdWxsCmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5wdXQKCi8qKiBJbnZhbGlkL2luY29tcGxldGUgZGV2aWNlIHJlY29yZHMgZmFpbCBjbG9zZWQgdG8gb2ZmLCBuZXZlciB0byBhdXRvbWF0aWMgdXBsb2FkLiAqLwppbnRlcm5hbCBjbGFzcyBPbW5pYVByZWZlcmVuY2VzU3luY1JlY29yZFN0b3JlKAogICAgcHJpdmF0ZSB2YWwgcmVhZDogKFN0cmluZykgLT4gU3RyaW5nPywKICAgIHByaXZhdGUgdmFsIHdyaXRlOiAoU3RyaW5nLCBTdHJpbmcpIC0+IFVuaXQsCikgOiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsU3RvcmUgewogICAgcHJpdmF0ZSBmdW4ga2V5KHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKSA9ICJvbW5pYS5zZXR0aW5ncy5zeW5jLnYxLiIgKyBzY29wZS5vd25lciArICIuIiArIHNjb3BlLnByb2ZpbGVJZAogICAgb3ZlcnJpZGUgZnVuIGxvYWQoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpOiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkID0gcnVuQ2F0Y2hpbmcgewogICAgICAgIHZhbCByYXcgPSByZWFkKGtleShzY29wZSkpID86IHJldHVybkBydW5DYXRjaGluZyBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKCkKICAgICAgICB2YWwgZGF0YSA9IEpzb24ucGFyc2VUb0pzb25FbGVtZW50KHJhdykuanNvbk9iamVjdAogICAgICAgIHJlcXVpcmUoZGF0YVsidmVyc2lvbiJdPy5qc29uUHJpbWl0aXZlPy5sb25nT3JOdWxsID09IDFMKQogICAgICAgIHZhbCBlbmFibGVkID0gcmVxdWlyZU5vdE51bGwoZGF0YVsiZW5hYmxlZCJdPy5qc29uUHJpbWl0aXZlPy5ib29sZWFuT3JOdWxsKQogICAgICAgIHZhbCBiYXNlbGluZSA9IGRhdGFbImJhc2VsaW5lIl0/LmxldCB7IGVsZW1lbnQgLT4KICAgICAgICAgICAgdmFsIHNuYXBzaG90ID0gZWxlbWVudC5qc29uT2JqZWN0CiAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoCiAgICAgICAgICAgICAgICByZXF1aXJlTm90TnVsbChzbmFwc2hvdFsicmV2aXNpb24iXT8uanNvblByaW1pdGl2ZT8ubG9uZ09yTnVsbCksCiAgICAgICAgICAgICAgICBzbmFwc2hvdFsicHJlZmVyZW5jZXMiXSBhcz8gSnNvbk9iamVjdCA/OiBlcnJvcigiSW52YWxpZCBiYXNlbGluZSIpLAogICAgICAgICAgICAgICAgc25hcHNob3RbInByb2ZpbGVJbnN0YW5jZSJdPy5qc29uUHJpbWl0aXZlPy5jb250ZW50T3JOdWxsLAogICAgICAgICAgICApCiAgICAgICAgfQogICAgICAgIFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQoZW5hYmxlZCwgYmFzZWxpbmUpCiAgICB9LmdldE9yRGVmYXVsdChTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKCkpCgogICAgb3ZlcnJpZGUgZnVuIHNhdmUoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIHJlY29yZDogU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCkgewogICAgICAgIHZhbCBkYXRhID0gYnVpbGRKc29uT2JqZWN0IHsKICAgICAgICAgICAgcHV0KCJ2ZXJzaW9uIiwgMSkKICAgICAgICAgICAgcHV0KCJlbmFibGVkIiwgcmVjb3JkLmVuYWJsZWQpCiAgICAgICAgICAgIHJlY29yZC5iYXNlbGluZT8ubGV0IHsgc25hcHNob3QgLT4KICAgICAgICAgICAgICAgIHB1dCgiYmFzZWxpbmUiLCBidWlsZEpzb25PYmplY3QgewogICAgICAgICAgICAgICAgICAgIHB1dCgicmV2aXNpb24iLCBzbmFwc2hvdC5yZXZpc2lvbikKICAgICAgICAgICAgICAgICAgICBwdXQoInByZWZlcmVuY2VzIiwgc25hcHNob3QucHJlZmVyZW5jZXMpCiAgICAgICAgICAgICAgICAgICAgc25hcHNob3QucHJvZmlsZUluc3RhbmNlPy5sZXQgeyBwdXQoInByb2ZpbGVJbnN0YW5jZSIsIGl0KSB9CiAgICAgICAgICAgICAgICB9KQogICAgICAgICAgICB9CiAgICAgICAgfQogICAgICAgIHdyaXRlKGtleShzY29wZSksIGRhdGEudG9TdHJpbmcoKSkKICAgIH0KfQo=', 'app/src/test/java/com/nuvio/tv/core/sync/OmniaSharedPreferencesPolicyTest.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQga290bGluLnRlc3QuVGVzdAppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RXF1YWxzCmltcG9ydCBrb3RsaW4udGVzdC5hc3NlcnRGYWxzZQppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0VHJ1ZQppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RmFpbHNXaXRoCmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5Kc29uT2JqZWN0CmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5Kc29uQXJyYXkKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25QcmltaXRpdmUKCmNsYXNzIE9tbmlhU2hhcmVkUHJlZmVyZW5jZXNQb2xpY3lUZXN0IHsKICAgIEBUZXN0IGZ1biBwdWJsaWNDYXRhbG9nSWRlbnRpZmllcnNBcmVTaGFyZWFibGUoKSB7CiAgICAgICAgYXNzZXJ0VHJ1ZShpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eSgib3JnLm9tbmlhLmluZGlhIiwgNTEyKSkKICAgICAgICBhc3NlcnRUcnVlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJtb3ZpZTpwb3B1bGFyL2hpIiwgMTAyNCkpCiAgICB9CiAgICBAVGVzdCBmdW4gY29uZmlndXJlZEVuZHBvaW50VXJsc1N0YXlPdXRPZlByZWZlcmVuY2VzKCkgewogICAgICAgIGFzc2VydEZhbHNlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJodHRwczovL3N5bnRoZXRpYy5leGFtcGxlL3UvcHJpdmF0ZS9tYW5pZmVzdC5qc29uIiwgMTAyNCkpCiAgICAgICAgYXNzZXJ0RmFsc2UoaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkoImFkZG9uP3Rva2VuPXN5bnRoZXRpYyIsIDUxMikpCiAgICAgICAgYXNzZXJ0RmFsc2UoaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkoImFkZG9uI3N5bnRoZXRpYyIsIDUxMikpCiAgICB9CiAgICBAVGVzdCBmdW4gaW52YWxpZE9yT3ZlcnNpemVkSWRlbnRpdGllc0FyZU5vdFNoYXJlZCgpIHsKICAgICAgICBhc3NlcnRGYWxzZShpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eSgiICIsIDUxMikpCiAgICAgICAgYXNzZXJ0RmFsc2UoaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkoImFiIiwgMSkpCiAgICAgICAgYXNzZXJ0RmFsc2UoaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkoImFcbmIiLCA1MTIpKQogICAgICAgIGFzc2VydEZhbHNlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJhXFxiIiwgNTEyKSkKICAgIH0KICAgIHByaXZhdGUgZnVuIHJvdyhpZDogU3RyaW5nLCBlbmFibGVkOiBCb29sZWFuID0gdHJ1ZSwgdGl0bGU6IFN0cmluZyA9ICIiLCBvcmRlcjogSW50ID0gMCkgPSBKc29uT2JqZWN0KG1hcE9mKAogICAgICAgICJhZGRvbl9pZCIgdG8gSnNvblByaW1pdGl2ZSgic3ludGhldGljLWFkZG9uIiksICJ0eXBlIiB0byBKc29uUHJpbWl0aXZlKCJtb3ZpZSIpLCAiY2F0YWxvZ19pZCIgdG8gSnNvblByaW1pdGl2ZShpZCksCiAgICAgICAgImVuYWJsZWQiIHRvIEpzb25QcmltaXRpdmUoZW5hYmxlZCksICJjdXN0b21fdGl0bGUiIHRvIEpzb25QcmltaXRpdmUodGl0bGUpLCAib3JkZXIiIHRvIEpzb25QcmltaXRpdmUob3JkZXIpLAogICAgICAgICJpc19jb2xsZWN0aW9uIiB0byBKc29uUHJpbWl0aXZlKGZhbHNlKSwgImNvbGxlY3Rpb25faWQiIHRvIEpzb25QcmltaXRpdmUoIiIpLAogICAgKSkKICAgIHByaXZhdGUgZnVuIGhvbWUodmFyYXJnIHJvd3M6IEpzb25PYmplY3QpID0gSnNvbk9iamVjdChtYXBPZigiaG9tZUNhdGFsb2dzIiB0byBKc29uQXJyYXkocm93cy50b0xpc3QoKSkpKQogICAgcHJpdmF0ZSBmdW4gbWVyZ2VIb21lKGJhc2U6IEpzb25PYmplY3QsIGxvY2FsOiBKc29uT2JqZWN0LCByZW1vdGU6IEpzb25PYmplY3QpID0gbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhiYXNlLCBsb2NhbCwgcmVtb3RlLCBzZXRPZigiaG9tZUNhdGFsb2dzIikpWyJob21lQ2F0YWxvZ3MiXSBhcyBKc29uQXJyYXkKICAgIHByaXZhdGUgdmFsIGtleXMgPSBzZXRPZigiaGVyb0VuYWJsZWQiLCAiY29udGludWVXYXRjaGluZ1Zpc2libGUiKQogICAgcHJpdmF0ZSBmdW4gcHJlZnMoaGVybzogQm9vbGVhbiwgd2F0Y2hpbmc6IEJvb2xlYW4pID0gSnNvbk9iamVjdChtYXBPZigiaGVyb0VuYWJsZWQiIHRvIEpzb25QcmltaXRpdmUoaGVybyksICJjb250aW51ZVdhdGNoaW5nVmlzaWJsZSIgdG8gSnNvblByaW1pdGl2ZSh3YXRjaGluZykpKQogICAgcHJpdmF0ZSB2YWwgc2NvcGUgPSBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCJpc29sYXRlZC1zeW50aGV0aWMtb3duZXIiLCAxKQoKICAgIEBUZXN0IGZ1biBkaXNhYmxlZERldmljZVJlamVjdHNBbkluZmxpZ2h0UmVzcG9uc2UoKSB7CiAgICAgICAgYXNzZXJ0RmFsc2UoY2FuQXBwbHlTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIDIpLCBzY29wZSwgMiwgZmFsc2UpKQogICAgfQogICAgQFRlc3QgZnVuIGRpc2FibGluZ0FuZFJlZW5hYmxpbmdJbnZhbGlkYXRlc09sZGVyUmVxdWVzdHMoKSB7CiAgICAgICAgYXNzZXJ0RmFsc2UoY2FuQXBwbHlTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIDIpLCBzY29wZSwgNCwgdHJ1ZSkpCiAgICB9CiAgICBAVGVzdCBmdW4gYWNjb3VudFN3aXRjaFJlamVjdHNQcmV2aW91c0FjY291bnRzUmVzcG9uc2UoKSB7CiAgICAgICAgYXNzZXJ0RmFsc2UoY2FuQXBwbHlTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIDIpLCBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCJhbm90aGVyLW93bmVyIiwgMSksIDIsIHRydWUpKQogICAgfQogICAgQFRlc3QgZnVuIHByb2ZpbGVTd2l0Y2hSZWplY3RzUHJldmlvdXNQcm9maWxlc1Jlc3BvbnNlKCkgewogICAgICAgIGFzc2VydEZhbHNlKGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCAyKSwgc2NvcGUuY29weShwcm9maWxlSWQgPSAyKSwgMiwgdHJ1ZSkpCiAgICB9CiAgICBAVGVzdCBmdW4gc2lnbk91dFJlamVjdHNQZW5kaW5nUmVzcG9uc2UoKSB7CiAgICAgICAgYXNzZXJ0RmFsc2UoY2FuQXBwbHlTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIDIpLCBudWxsLCAyLCB0cnVlKSkKICAgIH0KICAgIEBUZXN0IGZ1biBjdXJyZW50RW5hYmxlZFNjb3BlQWNjZXB0c0l0c1Jlc3BvbnNlKCkgewogICAgICAgIGFzc2VydFRydWUoY2FuQXBwbHlTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3Qoc2NvcGUsIDIpLCBzY29wZSwgMiwgdHJ1ZSkpCiAgICB9CiAgICBAVGVzdCBmdW4gdW5yZWxhdGVkQ29uY3VycmVudEVkaXRzU3Vydml2ZSgpIHsKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsIGZhbHNlKSwgbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhwcmVmcyh0cnVlLCB0cnVlKSwgcHJlZnMoZmFsc2UsIHRydWUpLCBwcmVmcyh0cnVlLCBmYWxzZSksIGtleXMpKQogICAgfQogICAgQFRlc3QgZnVuIHVudG91Y2hlZExvY2FsVmFsdWVzRG9Ob3RSZXZlcnRSZW1vdGVDaGFuZ2VzKCkgewogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyhmYWxzZSwgZmFsc2UpLCBtZXJnZVNoYXJlZFByZWZlcmVuY2VzKHByZWZzKHRydWUsIHRydWUpLCBwcmVmcyh0cnVlLCB0cnVlKSwgcHJlZnMoZmFsc2UsIGZhbHNlKSwga2V5cykpCiAgICB9CiAgICBAVGVzdCBmdW4gZGVsaWJlcmF0ZUxvY2FsQ2hhbmdlV2luc1RoZVNhbWVGaWVsZCgpIHsKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsIGZhbHNlKSwgbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhwcmVmcyh0cnVlLCB0cnVlKSwgcHJlZnMoZmFsc2UsIHRydWUpLCBwcmVmcyh0cnVlLCBmYWxzZSksIGtleXMpKQogICAgfQogICAgQFRlc3QgZnVuIHVuc3VwcG9ydGVkUmVtb3RlRmllbGRzQXJlUmV0YWluZWQoKSB7CiAgICAgICAgdmFsIHJlbW90ZSA9IEpzb25PYmplY3QocHJlZnModHJ1ZSwgdHJ1ZSkgKyAoInN1YnRpdGxlTGFuZ3VhZ2UiIHRvIEpzb25QcmltaXRpdmUoImhpIikpKQogICAgICAgIGFzc2VydEVxdWFscygiaGkiLCAobWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhwcmVmcyh0cnVlLCB0cnVlKSwgcHJlZnMoZmFsc2UsIHRydWUpLCByZW1vdGUsIGtleXMpWyJzdWJ0aXRsZUxhbmd1YWdlIl0gYXMgSnNvblByaW1pdGl2ZSkuY29udGVudCkKICAgIH0KICAgIEBUZXN0IGZ1biBtaXNzaW5nQmFzZWxpbmVOZXZlclVwbG9hZHNEZWZhdWx0c0FzQ2hhbmdlcygpIHsKICAgICAgICBhc3NlcnRGYWlsc1dpdGg8SWxsZWdhbEFyZ3VtZW50RXhjZXB0aW9uPiB7IG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMobnVsbCwgcHJlZnModHJ1ZSwgdHJ1ZSksIHByZWZzKGZhbHNlLCBmYWxzZSksIGtleXMpIH0KICAgIH0KICAgIEBUZXN0IGZ1biB1bnN1cHBvcnRlZExvY2FsRmllbGRzQXJlUmVqZWN0ZWQoKSB7CiAgICAgICAgdmFsIGxvY2FsID0gSnNvbk9iamVjdChtYXBPZigiZGVjb2RlciIgdG8gSnNvblByaW1pdGl2ZSgiaGFyZHdhcmUiKSkpCiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPElsbGVnYWxBcmd1bWVudEV4Y2VwdGlvbj4geyBtZXJnZVNoYXJlZFByZWZlcmVuY2VzKEpzb25PYmplY3QoZW1wdHlNYXAoKSksIGxvY2FsLCBKc29uT2JqZWN0KGVtcHR5TWFwKCkpLCBrZXlzKSB9CiAgICB9CiAgICBAVGVzdCBmdW4gb3B0aW5nSW5DYW5FeHBsaWNpdGx5Q2hvb3NlU2F2ZWRTZXR0aW5ncygpIHsKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsIGZhbHNlKSwgaW5pdGlhbFNoYXJlZFByZWZlcmVuY2VzKFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZS5Vc2VTYXZlZFNldHRpbmdzLCBwcmVmcyh0cnVlLCB0cnVlKSwgcHJlZnMoZmFsc2UsIGZhbHNlKSwga2V5cykpCiAgICB9CiAgICBAVGVzdCBmdW4gY2hvb3NpbmdUaGlzRGV2aWNlUHJlc2VydmVzRmllbGRzSXRDYW5ub3RSZXByZXNlbnQoKSB7CiAgICAgICAgdmFsIHJlbW90ZSA9IEpzb25PYmplY3QocHJlZnMoZmFsc2UsIGZhbHNlKSArICgic3VidGl0bGVMYW5ndWFnZSIgdG8gSnNvblByaW1pdGl2ZSgiaGkiKSkpCiAgICAgICAgdmFsIG1lcmdlZCA9IGluaXRpYWxTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc0luaXRpYWxDaG9pY2UuVXNlVGhpc0RldmljZSwgcHJlZnModHJ1ZSwgdHJ1ZSksIHJlbW90ZSwga2V5cykKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZSh0cnVlKSwgbWVyZ2VkWyJoZXJvRW5hYmxlZCJdKQogICAgICAgIGFzc2VydEVxdWFscyhKc29uUHJpbWl0aXZlKCJoaSIpLCBtZXJnZWRbInN1YnRpdGxlTGFuZ3VhZ2UiXSkKICAgIH0KICAgIEBUZXN0IGZ1biByZW1vdGVPbWlzc2lvbnNEb05vdENsZWFyTG9jYWxEZWZhdWx0cygpIHsKICAgICAgICBhc3NlcnRFcXVhbHMoZW1wdHlNYXAoKSwgYXBwbGljYWJsZVNoYXJlZFByZWZlcmVuY2VzKEpzb25PYmplY3QoZW1wdHlNYXAoKSksIGtleXMpKQogICAgfQogICAgQFRlc3QgZnVuIGhhcmR3YXJlQW5kT3B0SW5TdGF0ZUNhbm5vdEJlU3luY2VkKCkgewogICAgICAgIGFzc2VydEZhbHNlKCJkZWNvZGVyIiBpbiBzaGFyZWRQcmVmZXJlbmNlS2V5cykKICAgICAgICBhc3NlcnRGYWxzZSgiYnVmZmVyU2l6ZSIgaW4gc2hhcmVkUHJlZmVyZW5jZUtleXMpCiAgICAgICAgYXNzZXJ0RmFsc2UoImVuYWJsZWQiIGluIHNoYXJlZFByZWZlcmVuY2VLZXlzKQogICAgICAgIGFzc2VydEZhbHNlKCJyZWFsRGVicmlkQXBpS2V5IiBpbiBzaGFyZWRQcmVmZXJlbmNlS2V5cykKICAgIH0KICAgIEBUZXN0IGZ1biBibGFua093bmVyQW5kSW52YWxpZFByb2ZpbGVzQXJlUmVqZWN0ZWQoKSB7CiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPElsbGVnYWxBcmd1bWVudEV4Y2VwdGlvbj4geyBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCIiLCAxKSB9CiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPElsbGVnYWxBcmd1bWVudEV4Y2VwdGlvbj4geyBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCJvd25lciIsIDApIH0KICAgICAgICBhc3NlcnRGYWlsc1dpdGg8SWxsZWdhbEFyZ3VtZW50RXhjZXB0aW9uPiB7IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUoIm93bmVyIiwgNykgfQogICAgfQogICAgQFRlc3QgZnVuIG5lZ2F0aXZlUmV2aXNpb25Jc1JlamVjdGVkKCkgewogICAgICAgIGFzc2VydEZhaWxzV2l0aDxJbGxlZ2FsQXJndW1lbnRFeGNlcHRpb24+IHsgU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgtMSwgSnNvbk9iamVjdChlbXB0eU1hcCgpKSkgfQogICAgfQogICAgQFRlc3QgZnVuIGNvbmN1cnJlbnRDaGFuZ2VzVG9EaWZmZXJlbnRDYXRhbG9nc1N1cnZpdmUoKSB7CiAgICAgICAgdmFsIHJlc3VsdD1tZXJnZUhvbWUoaG9tZShyb3coImEiKSxyb3coImIiLG9yZGVyPTEpKSxob21lKHJvdygiYSIsZW5hYmxlZD1mYWxzZSkscm93KCJiIixvcmRlcj0xKSksaG9tZShyb3coImEiKSxyb3coImIiLHRpdGxlPSJSZW1vdGUgdGl0bGUiLG9yZGVyPTEpKSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZShmYWxzZSksKHJlc3VsdFswXSBhcyBKc29uT2JqZWN0KVsiZW5hYmxlZCJdKQogICAgICAgIGFzc2VydEVxdWFscyhKc29uUHJpbWl0aXZlKCJSZW1vdGUgdGl0bGUiKSwocmVzdWx0WzFdIGFzIEpzb25PYmplY3QpWyJjdXN0b21fdGl0bGUiXSkKICAgIH0KICAgIEBUZXN0IGZ1biBkaWZmZXJlbnRGaWVsZHNPblRoZVNhbWVDYXRhbG9nQXJlTWVyZ2VkKCkgewogICAgICAgIHZhbCByZXN1bHQ9bWVyZ2VIb21lKGhvbWUocm93KCJhIikpLGhvbWUocm93KCJhIixlbmFibGVkPWZhbHNlKSksaG9tZShyb3coImEiLHRpdGxlPSJSZW1vdGUgdGl0bGUiKSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKEpzb25QcmltaXRpdmUoZmFsc2UpLChyZXN1bHRbMF0gYXMgSnNvbk9iamVjdClbImVuYWJsZWQiXSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZSgiUmVtb3RlIHRpdGxlIiksKHJlc3VsdFswXSBhcyBKc29uT2JqZWN0KVsiY3VzdG9tX3RpdGxlIl0pCiAgICB9CiAgICBAVGVzdCBmdW4gYWJzZW50TG9jYWxDYXRhbG9nRG9lc05vdERlbGV0ZUFSZW1vdGVSb3coKSB7CiAgICAgICAgYXNzZXJ0RXF1YWxzKEpzb25BcnJheShsaXN0T2Yocm93KCJhIikpKSxtZXJnZUhvbWUoaG9tZShyb3coImEiKSksaG9tZSgpLGhvbWUocm93KCJhIikpKSkKICAgIH0KICAgIEBUZXN0IGZ1biBuZXdSZW1vdGVDYXRhbG9nSXNQcmVzZXJ2ZWRXaGlsZUVkaXRpbmdBbm90aGVyKCkgewogICAgICAgIHZhbCByZXN1bHQ9bWVyZ2VIb21lKGhvbWUocm93KCJhIikpLGhvbWUocm93KCJhIixlbmFibGVkPWZhbHNlKSksaG9tZShyb3coImEiKSxyb3coIm5ldyIsb3JkZXI9MSkpKQogICAgICAgIGFzc2VydEVxdWFscygyLHJlc3VsdC5zaXplKQogICAgICAgIGFzc2VydEVxdWFscyhKc29uUHJpbWl0aXZlKCJuZXciKSwocmVzdWx0WzFdIGFzIEpzb25PYmplY3QpWyJjYXRhbG9nX2lkIl0pCiAgICB9CiAgICBAVGVzdCBmdW4gbmV3Q29uZmxpY3RpbmdDYXRhbG9nRG9lc05vdFRyZWF0RGVmYXVsdHNBc0ludGVudGlvbmFsRWRpdHMoKSB7CiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPFNoYXJlZFByZWZlcmVuY2VzQ2hvaWNlUmVxdWlyZWRFeGNlcHRpb24+IHsgbWVyZ2VIb21lKGhvbWUoKSxob21lKHJvdygiYSIpKSxob21lKHJvdygiYSIsZW5hYmxlZD1mYWxzZSkpKSB9CiAgICB9CiAgICBAVGVzdCBmdW4gZHVwbGljYXRlQ2F0YWxvZ0lkZW50aXRpZXNBcmVSZWplY3RlZCgpIHsKICAgICAgICBhc3NlcnRGYWlsc1dpdGg8SWxsZWdhbEFyZ3VtZW50RXhjZXB0aW9uPiB7IG1lcmdlSG9tZShob21lKCksaG9tZShyb3coImEiKSxyb3coImEiKSksaG9tZSgpKSB9CiAgICB9CiAgICBAVGVzdCBmdW4gaWRlbnRpdHlEb2VzTm90Q29uZnVzZUNvbG9uc0luc2lkZUlkZW50aWZpZXJDb21wb25lbnRzKCkgewogICAgICAgIHZhbCBhPUpzb25PYmplY3Qocm93KCJjIikgKyAoImFkZG9uX2lkIiB0byBKc29uUHJpbWl0aXZlKCJhOmIiKSkgKyAoInR5cGUiIHRvIEpzb25QcmltaXRpdmUoIm1vdmllIikpKQogICAgICAgIHZhbCBiPUpzb25PYmplY3Qocm93KCJtb3ZpZTpjIikgKyAoImFkZG9uX2lkIiB0byBKc29uUHJpbWl0aXZlKCJhIikpICsgKCJ0eXBlIiB0byBKc29uUHJpbWl0aXZlKCJiIikpKQogICAgICAgIGFzc2VydEVxdWFscygyLG1lcmdlSG9tZShob21lKCksaG9tZShhLGIpLGhvbWUoKSkuc2l6ZSkKICAgIH0KICAgIEBUZXN0IGZ1biBwYXJ0aWFsRXhwb3J0c0Nhbm5vdEVyYXNlUHJlZmVyZW5jZXNUaGV5RmFpbGVkVG9SZWFkKCkgewogICAgICAgIGFzc2VydEZhaWxzV2l0aDxJbGxlZ2FsQXJndW1lbnRFeGNlcHRpb24+IHsgbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhwcmVmcyh0cnVlLHRydWUpLEpzb25PYmplY3QobWFwT2YoImhlcm9FbmFibGVkIiB0byBKc29uUHJpbWl0aXZlKGZhbHNlKSkpLHByZWZzKHRydWUsZmFsc2UpLGtleXMpIH0KICAgIH0KICAgIEBUZXN0IGZ1biBvbWl0dGVkQ2F0YWxvZ0RlZmF1bHRzRG9Ob3RCZWNvbWVJbnRlbnRpb25hbExvY2FsQ2hhbmdlcygpIHsKICAgICAgICB2YWwgc3BhcnNlPUpzb25PYmplY3Qocm93KCJhIikuZmlsdGVyS2V5cyB7IGl0ICFpbiBzZXRPZigiZW5hYmxlZCIsImN1c3RvbV90aXRsZSIsImlzX2NvbGxlY3Rpb24iLCJjb2xsZWN0aW9uX2lkIikgfSkKICAgICAgICB2YWwgcmVzdWx0PW1lcmdlSG9tZShob21lKHNwYXJzZSksaG9tZShyb3coImEiKSksaG9tZShyb3coImEiLGVuYWJsZWQ9ZmFsc2UsdGl0bGU9IlJlbW90ZSB0aXRsZSIpKSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZShmYWxzZSksKHJlc3VsdFswXSBhcyBKc29uT2JqZWN0KVsiZW5hYmxlZCJdKQogICAgICAgIGFzc2VydEVxdWFscyhKc29uUHJpbWl0aXZlKCJSZW1vdGUgdGl0bGUiKSwocmVzdWx0WzBdIGFzIEpzb25PYmplY3QpWyJjdXN0b21fdGl0bGUiXSkKICAgIH0KfQo=', 'app/src/test/java/com/nuvio/tv/core/sync/OmniaSharedPreferencesEngineTest.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQga290bGluLnRlc3QuVGVzdAppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RXF1YWxzCmltcG9ydCBrb3RsaW4udGVzdC5hc3NlcnRGYWxzZQppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0VHJ1ZQppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLnRlc3QucnVuVGVzdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvblByaW1pdGl2ZQoKY2xhc3MgT21uaWFTaGFyZWRQcmVmZXJlbmNlc0VuZ2luZVRlc3QgewogICAgcHJpdmF0ZSBmdW4gcHJlZnMoaGVybzogQm9vbGVhbiwgd2F0Y2hpbmc6IEJvb2xlYW4pID0gSnNvbk9iamVjdChtYXBPZigiaGVyb0VuYWJsZWQiIHRvIEpzb25QcmltaXRpdmUoaGVybyksICJjb250aW51ZVdhdGNoaW5nVmlzaWJsZSIgdG8gSnNvblByaW1pdGl2ZSh3YXRjaGluZykpKQogICAgcHJpdmF0ZSBpbm5lciBjbGFzcyBGaXh0dXJlIHsKICAgICAgICB2YXIgYWN0aXZlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlPyA9IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUoInN5bnRoZXRpYy1vd25lciIsIDEpCiAgICAgICAgdmFyIGxvY2FsID0gcHJlZnModHJ1ZSwgdHJ1ZSkKICAgICAgICB2YXIgcmVtb3RlID0gU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgwLCBKc29uT2JqZWN0KGVtcHR5TWFwKCkpKQogICAgICAgIHZhciBwdWxscyA9IDAKICAgICAgICB2YXIgcHVzaGVzID0gMAogICAgICAgIHZhciBhcHBsaWVzID0gMAogICAgICAgIHZhciBhZnRlclB1bGw6IHN1c3BlbmQgKCkgLT4gVW5pdCA9IHt9CiAgICAgICAgdmFyIGFmdGVyUHVzaDogc3VzcGVuZCAoKSAtPiBVbml0ID0ge30KICAgICAgICB2YXIgY29uZmxpY3RzID0gMAogICAgICAgIHZhbCByZWNvcmRzID0gbXV0YWJsZU1hcE9mPFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQ+KCkKICAgICAgICB2YWwgc3RvcmUgPSBvYmplY3QgOiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsU3RvcmUgewogICAgICAgICAgICBvdmVycmlkZSBmdW4gbG9hZChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSkgPSByZWNvcmRzW3Njb3BlXSA/OiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKCkKICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIHNhdmUoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIHJlY29yZDogU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCkgeyByZWNvcmRzW3Njb3BlXSA9IHJlY29yZCB9CiAgICAgICAgfQogICAgICAgIHZhbCBkZXZpY2UgPSBvYmplY3QgOiBTaGFyZWRQcmVmZXJlbmNlc0RldmljZSB7CiAgICAgICAgICAgIG92ZXJyaWRlIHZhbCBzdXBwb3J0ZWRLZXlzID0gc2V0T2YoImhlcm9FbmFibGVkIiwgImNvbnRpbnVlV2F0Y2hpbmdWaXNpYmxlIikKICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIGN1cnJlbnRTY29wZSgpID0gYWN0aXZlCiAgICAgICAgICAgIG92ZXJyaWRlIHN1c3BlbmQgZnVuIGV4cG9ydChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSkgPSBsb2NhbAogICAgICAgICAgICBvdmVycmlkZSBzdXNwZW5kIGZ1biBhcHBseShzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSwgcHJlZmVyZW5jZXM6IEpzb25PYmplY3QsIHN0aWxsQ3VycmVudDogKCkgLT4gQm9vbGVhbikgewogICAgICAgICAgICAgICAgaWYgKHN0aWxsQ3VycmVudCgpKSB7IGxvY2FsID0gSnNvbk9iamVjdChsb2NhbCArIHByZWZlcmVuY2VzKTsgYXBwbGllcysrIH0KICAgICAgICAgICAgfQogICAgICAgIH0KICAgICAgICB2YWwgdHJhbnNwb3J0ID0gb2JqZWN0IDogU2hhcmVkUHJlZmVyZW5jZXNUcmFuc3BvcnQgewogICAgICAgICAgICBvdmVycmlkZSBzdXNwZW5kIGZ1biBwdWxsKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKTogU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCB7IHB1bGxzKys7YWZ0ZXJQdWxsKCk7cmV0dXJuIHJlbW90ZSB9CiAgICAgICAgICAgIG92ZXJyaWRlIHN1c3BlbmQgZnVuIHB1c2goc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIGV4cGVjdGVkUmV2aXNpb246IExvbmcsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCBleHBlY3RlZFByb2ZpbGVJbnN0YW5jZTogU3RyaW5nPyk6IFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdCB7CiAgICAgICAgICAgICAgICBwdXNoZXMrKzthZnRlclB1c2goKQogICAgICAgICAgICAgICAgaWYgKGNvbmZsaWN0cyA+IDApIHsgY29uZmxpY3RzLS07cmVtb3RlID0gcmVtb3RlLmNvcHkocmV2aXNpb24gPSByZW1vdGUucmV2aXNpb24gKyAxKTtyZXR1cm4gU2hhcmVkUHJlZmVyZW5jZXNQdXNoUmVzdWx0KHRydWUsIHJlbW90ZSkgfQogICAgICAgICAgICAgICAgYXNzZXJ0RXF1YWxzKHJlbW90ZS5yZXZpc2lvbiwgZXhwZWN0ZWRSZXZpc2lvbikKICAgICAgICAgICAgICAgIGFzc2VydEVxdWFscyhyZW1vdGUucHJvZmlsZUluc3RhbmNlLCBleHBlY3RlZFByb2ZpbGVJbnN0YW5jZSkKICAgICAgICAgICAgICAgIHJlbW90ZSA9IHJlbW90ZS5jb3B5KHJldmlzaW9uID0gcmVtb3RlLnJldmlzaW9uICsgMSwgcHJlZmVyZW5jZXMgPSBwcmVmZXJlbmNlcykKICAgICAgICAgICAgICAgIHJldHVybiBTaGFyZWRQcmVmZXJlbmNlc1B1c2hSZXN1bHQoZmFsc2UsIHJlbW90ZSkKICAgICAgICAgICAgfQogICAgICAgIH0KICAgICAgICB2YWwgZW5naW5lID0gT21uaWFTaGFyZWRQcmVmZXJlbmNlc0VuZ2luZShkZXZpY2UsIHN0b3JlLCB0cmFuc3BvcnQpCiAgICB9CgogICAgQFRlc3QgZnVuIHJldXNlZFByb2ZpbGVTbG90RG9lc05vdEluaGVyaXRBdXRvbWF0aWNTeW5jKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5yZW1vdGU9Zi5yZW1vdGUuY29weShwcm9maWxlSW5zdGFuY2U9Im9yaWdpbmFsLXByb2ZpbGUiKTtmLmVuZ2luZS5lbmFibGUoKQogICAgICAgIHZhbCBiZWZvcmU9Zi5hcHBsaWVzO3ZhbCBwdXNoZXM9Zi5wdXNoZXMKICAgICAgICBmLnJlbW90ZT1TaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDAsSnNvbk9iamVjdChlbXB0eU1hcCgpKSwicmVwbGFjZW1lbnQtcHJvZmlsZSIpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MsZi5lbmdpbmUuc3luY2hyb25pemUoKSkKICAgICAgICBhc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCk7YXNzZXJ0RXF1YWxzKGJlZm9yZSxmLmFwcGxpZXMpO2Fzc2VydEVxdWFscyhwdXNoZXMsZi5wdXNoZXMpCiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKHRydWUsdHJ1ZSksZi5sb2NhbCkKICAgIH0KICAgIEBUZXN0IGZ1biBwcm9maWxlUmVwbGFjZW1lbnREdXJpbmdDb25mbGljdFJlcXVpcmVzTmV3Q29uc2VudCgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVtb3RlPWYucmVtb3RlLmNvcHkocHJvZmlsZUluc3RhbmNlPSJvcmlnaW5hbC1wcm9maWxlIik7Zi5lbmdpbmUuZW5hYmxlKCk7Zi5sb2NhbD1wcmVmcyhmYWxzZSx0cnVlKQogICAgICAgIHZhbCBiZWZvcmU9Zi5hcHBsaWVzO2YuY29uZmxpY3RzPTE7Zi5hZnRlclB1c2g9e2YucmVtb3RlPWYucmVtb3RlLmNvcHkocHJvZmlsZUluc3RhbmNlPSJyZXBsYWNlbWVudC1wcm9maWxlIil9CiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MsZi5lbmdpbmUuc3luY2hyb25pemUoKSkKICAgICAgICBhc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCk7YXNzZXJ0RXF1YWxzKGJlZm9yZSxmLmFwcGxpZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gcHJvZmlsZVJlcGxhY2VtZW50RHVyaW5nRmlyc3RFbmFibGVOZXZlckVuYWJsZXNOZXdQcm9maWxlKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5yZW1vdGU9Zi5yZW1vdGUuY29weShwcm9maWxlSW5zdGFuY2U9Im9yaWdpbmFsLXByb2ZpbGUiKTtmLmNvbmZsaWN0cz0xCiAgICAgICAgZi5hZnRlclB1c2g9e2YucmVtb3RlPWYucmVtb3RlLmNvcHkocHJvZmlsZUluc3RhbmNlPSJyZXBsYWNlbWVudC1wcm9maWxlIil9CiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MsZi5lbmdpbmUuZW5hYmxlKCkpCiAgICAgICAgYXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpO2Fzc2VydEVxdWFscygwLGYuYXBwbGllcykKICAgIH0KICAgIEBUZXN0IGZ1biBkZWZhdWx0T2ZmUGVyZm9ybXNOb05ldHdvcmtDYWxscygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2Fzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmLGYuZW5naW5lLnN5bmNocm9uaXplKCkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKDAsZi5wdWxscyk7YXNzZXJ0RXF1YWxzKDAsZi5wdXNoZXMpO2Fzc2VydEVxdWFscygwLGYuYXBwbGllcykKICAgIH0KICAgIEBUZXN0IGZ1biBzYXZlZFNldHRpbmdzUmVxdWlyZUFuRXhwbGljaXRJbml0aWFsQ2hvaWNlKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5yZW1vdGU9U2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgxLHByZWZzKGZhbHNlLGZhbHNlKSkKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkNob29zZUluaXRpYWxTZXR0aW5ncyxmLmVuZ2luZS5lbmFibGUoKSkKICAgICAgICBhc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCk7YXNzZXJ0RXF1YWxzKHByZWZzKHRydWUsdHJ1ZSksZi5sb2NhbCk7YXNzZXJ0RXF1YWxzKDAsZi5wdXNoZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gZmlyc3RFbmFibGVDYW5DaG9vc2VTYXZlZFNldHRpbmdzKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5yZW1vdGU9U2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgxLHByZWZzKGZhbHNlLGZhbHNlKSkKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCxmLmVuZ2luZS5lbmFibGUoU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLlVzZVNhdmVkU2V0dGluZ3MpKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyhmYWxzZSxmYWxzZSksZi5sb2NhbCk7YXNzZXJ0VHJ1ZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCk7YXNzZXJ0RXF1YWxzKDAsZi5wdXNoZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gZW1wdHlBY2NvdW50Q2FuVXNlVGhlQ3VycmVudERldmljZSgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2Fzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkLGYuZW5naW5lLmVuYWJsZSgpKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyh0cnVlLHRydWUpLGYucmVtb3RlLnByZWZlcmVuY2VzKTthc3NlcnRFcXVhbHMoMSxmLnB1c2hlcykKICAgIH0KICAgIEBUZXN0IGZ1biBkZWZhdWx0c09taXR0ZWRCeUFub3RoZXJQbGF0Zm9ybURvTm90QmVjb21lTG9jYWxFZGl0cygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMSxKc29uT2JqZWN0KG1hcE9mKCJoZXJvRW5hYmxlZCIgdG8gSnNvblByaW1pdGl2ZShmYWxzZSkpKSkKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCxmLmVuZ2luZS5lbmFibGUoU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLlVzZVNhdmVkU2V0dGluZ3MpKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyhmYWxzZSx0cnVlKSxmLmxvY2FsKQogICAgICAgIGYucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMixwcmVmcyhmYWxzZSxmYWxzZSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQsZi5lbmdpbmUuc3luY2hyb25pemUoKSkKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsZmFsc2UpLGYubG9jYWwpO2Fzc2VydEVxdWFscygwLGYucHVzaGVzKQogICAgfQogICAgQFRlc3QgZnVuIGRpc2FibGVQcmVzZXJ2ZXNDdXJyZW50VmFsdWVzQW5kU3RvcHNCb3RoRGlyZWN0aW9ucygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YuZW5naW5lLmVuYWJsZSgpO2YuZW5naW5lLmRpc2FibGUoKTtmLmxvY2FsPXByZWZzKGZhbHNlLHRydWUpO2YucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMixwcmVmcyh0cnVlLGZhbHNlKSkKICAgICAgICB2YWwgYmVmb3JlPWxpc3RPZihmLnB1bGxzLGYucHVzaGVzLGYuYXBwbGllcykKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZixmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKTthc3NlcnRFcXVhbHMoYmVmb3JlLGxpc3RPZihmLnB1bGxzLGYucHVzaGVzLGYuYXBwbGllcykpO2Fzc2VydEVxdWFscyhwcmVmcyhmYWxzZSx0cnVlKSxmLmxvY2FsKQogICAgfQogICAgQFRlc3QgZnVuIGRpc2FibGVEdXJpbmdJbml0aWFsUHVsbENhbm5vdEJlVW5kb25lQnlJdHNSZXNwb25zZSgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YuYWZ0ZXJQdWxsPXtmLmVuZ2luZS5kaXNhYmxlKCl9CiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYsZi5lbmdpbmUuZW5hYmxlKCkpCiAgICAgICAgYXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpO2Fzc2VydEVxdWFscygwLGYucHVzaGVzKTthc3NlcnRFcXVhbHMoMCxmLmFwcGxpZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gZGlzYWJsZUR1cmluZ1B1c2hQcmV2ZW50c0FwcGx5aW5nVGhlUmVzcG9uc2UoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLmVuZ2luZS5lbmFibGUoKTtmLmxvY2FsPXByZWZzKGZhbHNlLHRydWUpO3ZhbCBiZWZvcmU9Zi5hcHBsaWVzCiAgICAgICAgZi5hZnRlclB1c2g9e2YuZW5naW5lLmRpc2FibGUoKX0KICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZixmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKQogICAgICAgIGFzc2VydEZhbHNlKGYuc3RvcmUubG9hZChmLmFjdGl2ZSEhKS5lbmFibGVkKTthc3NlcnRFcXVhbHMoYmVmb3JlLGYuYXBwbGllcykKICAgIH0KICAgIEBUZXN0IGZ1biBhY2NvdW50U3dpdGNoRHVyaW5nUHVsbE5ldmVyQXBwbGllc1RvVGhlTmV3QWNjb3VudCgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO3ZhbCBvcmlnaW5hbD1mLmFjdGl2ZSEhO2YuZW5naW5lLmVuYWJsZSgpO3ZhbCBiZWZvcmU9Zi5hcHBsaWVzCiAgICAgICAgZi5hZnRlclB1bGw9e2YuYWN0aXZlPVNoYXJlZFByZWZlcmVuY2VzU2NvcGUoIm90aGVyLW93bmVyIiwxKTtmLmVuZ2luZS5yZWZyZXNoTG9jYWxTdGF0ZSgpfQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmLGYuZW5naW5lLnN5bmNocm9uaXplKCkpO2Fzc2VydEVxdWFscyhiZWZvcmUsZi5hcHBsaWVzKQogICAgICAgIGFzc2VydEZhbHNlKGYuc3RvcmUubG9hZChmLmFjdGl2ZSEhKS5lbmFibGVkKTthc3NlcnRUcnVlKGYuc3RvcmUubG9hZChvcmlnaW5hbCkuZW5hYmxlZCkKICAgIH0KICAgIEBUZXN0IGZ1biByZXR1cm5pbmdUb0FuQWNjb3VudFN0aWxsSW52YWxpZGF0ZXNJdHNPbGRSZXF1ZXN0KCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7dmFsIG9yaWdpbmFsPWYuYWN0aXZlISE7Zi5lbmdpbmUuZW5hYmxlKCk7dmFsIGJlZm9yZT1mLmFwcGxpZXMKICAgICAgICBmLmFmdGVyUHVsbD17Zi5hY3RpdmU9U2hhcmVkUHJlZmVyZW5jZXNTY29wZSgib3RoZXItb3duZXIiLDEpO2YuZW5naW5lLnJlZnJlc2hMb2NhbFN0YXRlKCk7Zi5hY3RpdmU9b3JpZ2luYWw7Zi5lbmdpbmUucmVmcmVzaExvY2FsU3RhdGUoKX0KICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZixmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKTthc3NlcnRFcXVhbHMoYmVmb3JlLGYuYXBwbGllcykKICAgIH0KICAgIEBUZXN0IGZ1biBjb25jdXJyZW50VW5yZWxhdGVkU2V0dGluZ3NBcmVNZXJnZWQoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLmVuZ2luZS5lbmFibGUoKTtmLmxvY2FsPXByZWZzKGZhbHNlLHRydWUpO2YucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMixwcmVmcyh0cnVlLGZhbHNlKSkKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCxmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyhmYWxzZSxmYWxzZSksZi5yZW1vdGUucHJlZmVyZW5jZXMpO2Fzc2VydEVxdWFscyhwcmVmcyhmYWxzZSxmYWxzZSksZi5sb2NhbCkKICAgIH0KICAgIEBUZXN0IGZ1biBjaGFuZ2VzTWFkZUR1cmluZ1RoZVJlcXVlc3RSZW1haW5Mb2NhbEZvclRoZU5leHRTeW5jKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5lbmdpbmUuZW5hYmxlKCk7Zi5yZW1vdGU9U2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgyLHByZWZzKHRydWUsZmFsc2UpKQogICAgICAgIGYuYWZ0ZXJQdWxsPXtmLmxvY2FsPXByZWZzKGZhbHNlLHRydWUpfQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkLGYuZW5naW5lLnN5bmNocm9uaXplKCkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKGZhbHNlLGZhbHNlKSxmLmxvY2FsKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyh0cnVlLGZhbHNlKSxmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuYmFzZWxpbmUhIS5wcmVmZXJlbmNlcykKICAgICAgICBmLmFmdGVyUHVsbD17fQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkLGYuZW5naW5lLnN5bmNocm9uaXplKCkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKGZhbHNlLGZhbHNlKSxmLnJlbW90ZS5wcmVmZXJlbmNlcykKICAgIH0KICAgIEBUZXN0IGZ1biBuZXR3b3JrRmFpbHVyZURvZXNOb3RFbmFibGVTeW5jT3JSZXBvcnRTdWNjZXNzKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5hZnRlclB1bGw9e3Rocm93IElsbGVnYWxTdGF0ZUV4Y2VwdGlvbigiU3ludGhldGljIG9mZmxpbmUiKX0KICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yLGYuZW5naW5lLmVuYWJsZSgpKTthc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCkKICAgIH0KICAgIEBUZXN0IGZ1biByZXRyaWVzQXJlQm91bmRlZEFuZE5ldmVyQ2xhaW1TdWNjZXNzT25SZXBlYXRlZENvbmZsaWN0KCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5jb25mbGljdHM9OAogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IsZi5lbmdpbmUuZW5hYmxlKCkpO2Fzc2VydEVxdWFscygzLGYucHVzaGVzKTthc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCkKICAgIH0KICAgIEBUZXN0IGZ1biBtaXNzaW5nQmFzZWxpbmVDYW5ub3RVcGxvYWREZXZpY2VEZWZhdWx0cygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVjb3Jkc1tmLmFjdGl2ZSEhXT1TaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKHRydWUsbnVsbCkKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkNob29zZUluaXRpYWxTZXR0aW5ncyxmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKTthc3NlcnRFcXVhbHMoMCxmLnB1bGxzKTthc3NlcnRFcXVhbHMoMCxmLnB1c2hlcykKICAgIH0KfQo=', 'app/src/test/java/com/nuvio/tv/core/sync/OmniaPreferencesSyncRecordStoreTest.kt': 'cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQga290bGluLnRlc3QuVGVzdAppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RXF1YWxzCmltcG9ydCBrb3RsaW4udGVzdC5hc3NlcnRGYWxzZQppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvblByaW1pdGl2ZQoKY2xhc3MgT21uaWFQcmVmZXJlbmNlc1N5bmNSZWNvcmRTdG9yZVRlc3QgewogICAgcHJpdmF0ZSB2YWwgdmFsdWVzID0gbXV0YWJsZU1hcE9mPFN0cmluZywgU3RyaW5nPigpCiAgICBwcml2YXRlIHZhbCBzdG9yZSA9IE9tbmlhUHJlZmVyZW5jZXNTeW5jUmVjb3JkU3RvcmUodmFsdWVzOjpnZXQpIHsga2V5LCB2YWx1ZSAtPiB2YWx1ZXNba2V5XSA9IHZhbHVlIH0KICAgIHByaXZhdGUgdmFsIHNjb3BlID0gU2hhcmVkUHJlZmVyZW5jZXNTY29wZSgic3ludGhldGljLW93bmVyIiwgMSkKICAgIEBUZXN0IGZ1biBwcm9maWxlSW5zdGFuY2VSb3VuZFRyaXBzV2l0aFRoZUJhc2VsaW5lKCkgewogICAgICAgIHZhbCByZWNvcmQ9U2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCh0cnVlLFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMyxKc29uT2JqZWN0KGVtcHR5TWFwKCkpLCJzeW50aGV0aWMtcHJvZmlsZS1pbnN0YW5jZSIpKQogICAgICAgIHN0b3JlLnNhdmUoc2NvcGUscmVjb3JkKTthc3NlcnRFcXVhbHMocmVjb3JkLHN0b3JlLmxvYWQoc2NvcGUpKQogICAgfQogICAgQFRlc3QgZnVuIGFic2VudFJlY29yZERlZmF1bHRzVG9PZmYoKSB7IGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKCksIHN0b3JlLmxvYWQoc2NvcGUpKSB9CiAgICBAVGVzdCBmdW4gbWFsZm9ybWVkUmVjb3JkRGVmYXVsdHNUb09mZigpIHsKICAgICAgICB2YWx1ZXNbIm9tbmlhLnNldHRpbmdzLnN5bmMudjEuc3ludGhldGljLW93bmVyLjEiXSA9ICJ7aW52YWxpZCIKICAgICAgICBhc3NlcnRGYWxzZShzdG9yZS5sb2FkKHNjb3BlKS5lbmFibGVkKQogICAgfQogICAgQFRlc3QgZnVuIHVua25vd25SZWNvcmRWZXJzaW9uRGVmYXVsdHNUb09mZigpIHsKICAgICAgICB2YWx1ZXNbIm9tbmlhLnNldHRpbmdzLnN5bmMudjEuc3ludGhldGljLW93bmVyLjEiXSA9ICJ7XCJ2ZXJzaW9uXCI6OTksXCJlbmFibGVkXCI6dHJ1ZX0iCiAgICAgICAgYXNzZXJ0RmFsc2Uoc3RvcmUubG9hZChzY29wZSkuZW5hYmxlZCkKICAgIH0KICAgIEBUZXN0IGZ1biBvcHRJbkFuZEJhc2VsaW5lUm91bmRUcmlwRXhhY3RseSgpIHsKICAgICAgICB2YWwgcmVjb3JkID0gU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCh0cnVlLCBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDcsIEpzb25PYmplY3QobWFwT2YoImhlcm9FbmFibGVkIiB0byBKc29uUHJpbWl0aXZlKGZhbHNlKSkpKSkKICAgICAgICBzdG9yZS5zYXZlKHNjb3BlLCByZWNvcmQpO2Fzc2VydEVxdWFscyhyZWNvcmQsIHN0b3JlLmxvYWQoc2NvcGUpKQogICAgfQogICAgQFRlc3QgZnVuIG90aGVyQWNjb3VudHNBbmRQcm9maWxlc0RvTm90U2hhcmVPcHRJbigpIHsKICAgICAgICBzdG9yZS5zYXZlKHNjb3BlLCBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKHRydWUsIFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMCwgSnNvbk9iamVjdChlbXB0eU1hcCgpKSkpKQogICAgICAgIGFzc2VydEZhbHNlKHN0b3JlLmxvYWQoc2NvcGUuY29weShvd25lciA9ICJvdGhlci1vd25lciIpKS5lbmFibGVkKQogICAgICAgIGFzc2VydEZhbHNlKHN0b3JlLmxvYWQoc2NvcGUuY29weShwcm9maWxlSWQgPSAyKSkuZW5hYmxlZCkKICAgIH0KICAgIEBUZXN0IGZ1biBkaXNhYmxpbmdSZXRhaW5zVGhlQmFzZWxpbmVXaXRob3V0UmVzZXR0aW5nUHJlZmVyZW5jZXMoKSB7CiAgICAgICAgdmFsIGJhc2VsaW5lID0gU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgzLCBKc29uT2JqZWN0KG1hcE9mKCJoZXJvRW5hYmxlZCIgdG8gSnNvblByaW1pdGl2ZShmYWxzZSkpKSkKICAgICAgICBzdG9yZS5zYXZlKHNjb3BlLCBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKGZhbHNlLCBiYXNlbGluZSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQoZmFsc2UsIGJhc2VsaW5lKSwgc3RvcmUubG9hZChzY29wZSkpCiAgICB9Cn0K'}.items():
        p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(encoded))
    prefix='app/src/main/java/com/nuvio/tv/'
    def replace_function(code, marker, replacement):
        start=code.index(marker)
        # All targets have a block body; braces in strings are balanced in these functions.
        body=code.index('{',start);depth=1;end=body+1
        while depth:
            depth += (code[end]=='{')-(code[end]=='}');end+=1
        return code[:start]+replacement+code[end:]
    p=ROOT/(prefix+'data/local/LayoutPreferenceDataStore.kt');s=p.read_text()
    s=s.replace('internal suspend fun getHomeCatalogSettingsState(): LocalHomeCatalogSettingsState {\n        return readHomeCatalogSettingsState(store().data.first())', 'internal suspend fun getHomeCatalogSettingsState(profileId: Int = profileManager.activeProfileId.value): LocalHomeCatalogSettingsState {\n        return readHomeCatalogSettingsState(store(profileId).data.first())')
    s=s.replace('collections: List<Collection>\n    ): SyncHomeCatalogPayload', 'collections: List<Collection>,\n        profileId: Int = profileManager.activeProfileId.value\n    ): SyncHomeCatalogPayload')
    s=s.replace('localState = getHomeCatalogSettingsState()','localState = getHomeCatalogSettingsState(profileId)')
    s=s.replace('suspend fun applyCatalogSettingsFromRemote(payload: SyncHomeCatalogPayload) {', 'suspend fun applyCatalogSettingsFromRemote(payload: SyncHomeCatalogPayload, profileId: Int = profileManager.activeProfileId.value, guard: () -> Unit = {}) {')
    start=s.index('    suspend fun applyCatalogSettingsFromRemote(');end=s.index('    private fun readHomeCatalogSettingsState',start)
    segment=s[start:end].replace('store().edit { prefs ->','store(profileId).edit { prefs ->\n            guard()')
    s=s[:start]+segment+s[end:];p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/(prefix+'core/sync/ProfileSettingsSyncService.kt');s=p.read_text()
    if 'private val omniaPreferencesSyncService:' not in s:
        s=s.replace('    private val authManager: AuthManager,','    private val authManager: AuthManager,\n    private val omniaPreferencesSyncService: OmniaPreferencesSyncService,',1)
    s=s.replace('        observeLocalSettingsChangesAndSync()','        omniaPreferencesSyncService.requestSync()')
    start=s.index('    suspend fun pushCurrentProfileToRemote(): Result<Unit> =')
    end=s.index('    private suspend fun pushProfileSettingsToRemote',start)
    s=s[:start]+'    suspend fun pushCurrentProfileToRemote(): Result<Unit> = runCatching {\n        check(omniaPreferencesSyncService.synchronize() != SharedPreferencesSyncStatus.Error) { "Settings could not sync" }\n    }\n\n'+s[end:]
    s=replace_function(s,'    suspend fun pullCurrentProfileFromRemote(): Result<Boolean>', '    suspend fun pullCurrentProfileFromRemote(): Result<Boolean> = runCatching {\n        val status = omniaPreferencesSyncService.synchronize()\n        check(status != SharedPreferencesSyncStatus.Error) { "Settings could not sync" }\n        status == SharedPreferencesSyncStatus.Synced\n    }')
    s=replace_function(s,'    fun requestForegroundPull(force: Boolean = false)', '    fun requestForegroundPull(force: Boolean = false) {\n        providerCredentialSyncService.requestForegroundPull(force)\n        mediaServerSyncService.requestForegroundPull(force)\n        omniaPreferencesSyncService.requestSync()\n    }')
    if '    private fun observeLocalSettingsChangesAndSync() = Unit' not in s:
        s=replace_function(s,'    private fun observeLocalSettingsChangesAndSync()', '    private fun observeLocalSettingsChangesAndSync() = Unit')
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/(prefix+'core/sync/HomeCatalogSettingsSyncService.kt');s=p.read_text().split('@Singleton\nclass HomeCatalogSettingsSyncService')[0]
    s+='@Singleton\nclass HomeCatalogSettingsSyncService @Inject constructor(private val preferences: OmniaPreferencesSyncService) {\n    val isSyncingFromRemote: Boolean get() = preferences.state.value.status == SharedPreferencesSyncStatus.Syncing\n    suspend fun pushToRemote(reason: String = "unspecified"): Result<Unit> = runCatching {\n        check(preferences.synchronize() != SharedPreferencesSyncStatus.Error) { "Settings could not sync" }\n    }\n    suspend fun pullFromRemote(): Result<Boolean> = runCatching {\n        val status = preferences.synchronize()\n        check(status != SharedPreferencesSyncStatus.Error) { "Settings could not sync" }\n        status == SharedPreferencesSyncStatus.Synced\n    }\n    fun triggerPush() = preferences.requestSync()\n}\n'
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/(prefix+'core/profile/ProfileManager.kt');s=p.read_text()
    transition='        com.nuvio.tv.core.sync.OmniaPreferencesInvalidation.beforeIdentityChange()\n'
    for anchor in ['    suspend fun setActiveProfile(id: Int) {\n','    suspend fun replaceAllProfiles(remoteProfiles: List<UserProfile>) {\n','    private suspend fun removeLocalProfileData(id: Int) {\n']:
        if anchor+transition not in s:s=s.replace(anchor,anchor+transition,1)
    marker='        if (id == 1) return\n        credentialStores.forEach'
    replacement='        if (id == 1) return\n        context.getSharedPreferences("omnia_optional_preferences", Context.MODE_PRIVATE).let { records ->\n            val edit = records.edit()\n            records.all.keys.filter { it.startsWith("omnia.settings.sync.v1.") && it.endsWith(".$id") }.forEach { edit.remove(it) }\n            check(edit.commit()) { "Unable to clear deleted profile sync choice" }\n        }\n        credentialStores.forEach'
    if replacement not in s:
        assert marker in s;s=s.replace(marker,replacement,1)
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/(prefix+'core/auth/AuthManager.kt');s=p.read_text()
    s=re.sub(r'(?m)^( +)(_authState.value = )',lambda m:m[1]+'com.nuvio.tv.core.sync.OmniaPreferencesInvalidation.beforeIdentityChange()\n'+m[1]+m[2] if not s[:m.start()].endswith('com.nuvio.tv.core.sync.OmniaPreferencesInvalidation.beforeIdentityChange()\n') else m[0],s)
    # Canonicalize repeated replay insertions before identity publication.
    s=re.sub(r'(?m)^( +)com.nuvio.tv.core.sync.OmniaPreferencesInvalidation.beforeIdentityChange()\n(?:\1com.nuvio.tv.core.sync.OmniaPreferencesInvalidation.beforeIdentityChange()\n)+',r'\1com.nuvio.tv.core.sync.OmniaPreferencesInvalidation.beforeIdentityChange()\n',s)
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/(prefix+'ui/screens/account/AccountViewModel.kt');s=p.read_text()
    if 'private val omniaPreferences:' not in s:s=s.replace('    private val authManager: AuthManager,','    private val authManager: AuthManager,\n    private val omniaPreferences: com.nuvio.tv.core.sync.OmniaPreferencesSyncService,',1)
    anchor='    private val _uiState = MutableStateFlow(AccountUiState())'
    methods='    internal val preferencesSyncState = omniaPreferences.state\n    internal fun enablePreferencesSync(choice: com.nuvio.tv.core.sync.SharedPreferencesInitialChoice? = null) { viewModelScope.launch { omniaPreferences.enable(choice) } }\n    internal fun disablePreferencesSync() { viewModelScope.launch { omniaPreferences.disable() } }\n    internal fun synchronizePreferences() { viewModelScope.launch { omniaPreferences.synchronize() } }\n    internal fun cancelPreferencesChoice() = omniaPreferences.cancelInitialChoice()\n\n'
    if methods not in s:s=s.replace(anchor,methods+anchor,1)
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/(prefix+'ui/screens/account/AccountSettingsContent.kt');s=p.read_text()
    for imp in ['import androidx.lifecycle.compose.collectAsStateWithLifecycle','import com.nuvio.tv.core.sync.SharedPreferencesSyncStatus','import com.nuvio.tv.core.sync.SharedPreferencesInitialChoice']:
        if imp not in s:s=s.replace('import androidx.compose.runtime.Composable',imp+'\nimport androidx.compose.runtime.Composable',1)
    anchor='            item(key = "account_sync_note_signed_in") {'
    item='            item(key = "omnia_optional_settings_sync") { OmniaPreferencesSyncSettings(viewModel) }\n'
    if item not in s:s=s.replace(anchor,item+anchor,1)
    if 'private fun OmniaPreferencesSyncSettings(' not in s:s+='\n@Composable\nprivate fun OmniaPreferencesSyncSettings(viewModel: AccountViewModel) {\n    val state by viewModel.preferencesSyncState.collectAsStateWithLifecycle()\n    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {\n        SettingsActionButton(\n            icon = Icons.Default.CheckCircle,\n            title = "Sync settings across devices · " + if (state.enabled) "On" else "Off",\n            subtitle = "Optional for this account and profile. Off keeps this device’s settings separate. Add-ons, library and history sync separately.",\n            onClick = { if (state.enabled) viewModel.disablePreferencesSync() else if (state.status != SharedPreferencesSyncStatus.Syncing) viewModel.enablePreferencesSync() },\n        )\n        AccountInlineNote(when (state.status) {\n            SharedPreferencesSyncStatus.Off -> "This device keeps its own settings."\n            SharedPreferencesSyncStatus.Ready -> "Ready to sync settings."\n            SharedPreferencesSyncStatus.ChooseInitialSettings -> "Saved settings exist. Choose the starting settings for this device."\n            SharedPreferencesSyncStatus.Syncing -> "Syncing settings…"\n            SharedPreferencesSyncStatus.Synced -> "Settings synced."\n            SharedPreferencesSyncStatus.SignInRequired -> "Sign in to sync settings."\n            SharedPreferencesSyncStatus.Error -> "Settings could not sync. Your local preferences are kept. Try again."\n        })\n        AccountInlineNote("Shares compatible Home catalog order, visibility and names; Continue Watching and hero visibility; release filtering; and audio/subtitle languages. Device playback tuning stays local.")\n        if (state.status == SharedPreferencesSyncStatus.ChooseInitialSettings) {\n            SettingsActionButton(Icons.Default.CheckCircle, "Use saved settings", "Start from this profile’s saved preferences.", { viewModel.enablePreferencesSync(SharedPreferencesInitialChoice.UseSavedSettings) })\n            SettingsActionButton(Icons.Default.CheckCircle, "Use this device’s settings", "Use this device’s compatible preferences as the starting settings.", { viewModel.enablePreferencesSync(SharedPreferencesInitialChoice.UseThisDevice) })\n            SettingsActionButton(Icons.Default.CheckCircle, "Cancel", "Keep settings sync off.", viewModel::cancelPreferencesChoice)\n        } else if (state.enabled && state.status != SharedPreferencesSyncStatus.Syncing) {\n            SettingsActionButton(Icons.Default.CheckCircle, "Sync settings now", "Pull saved settings and share your changes.", viewModel::synchronizePreferences)\n        } else if (!state.enabled && state.status == SharedPreferencesSyncStatus.Syncing) {\n            SettingsActionButton(Icons.Default.CheckCircle, "Cancel enabling sync", "Keep this device’s settings separate.", viewModel::disablePreferencesSync)\n        }\n    }\n}\n'
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/'app/build.gradle.kts';s=p.read_text()
    s=re.sub(r'versionCode = \d+', 'versionCode = 25',s, count=1)
    s=re.sub(r'versionName = "[^"]+"', 'versionName = "0.3.19"',s, count=1)
    p.write_text(s,encoding='utf8',newline='\n')
    print('Prepared TV optional compatible preferences, with one Account control. App build, runtime and protocol deployment still required.')


# Omnia preferences TV test integration r2
if (ROOT/'app').exists():
    import base64
    p=ROOT/'app/build.gradle.kts';s=p.read_text()
    dependency='    testImplementation(kotlin("test-junit"))'
    if dependency not in s:
        anchor='    testImplementation("junit:junit:4.13.2")'
        assert anchor in s
        s=s.replace(anchor,anchor+'\n'+dependency,1)
        p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/'app/src/test/java/com/nuvio/tv/core/sync/ProfileSettingsPluginSyncTest.kt'
    p.write_bytes(base64.b64decode('cGFja2FnZSBjb20ubnV2aW8udHYuY29yZS5zeW5jCgppbXBvcnQgaW8uZ2l0aHViLmphbi5zdXBhYmFzZS5wb3N0Z3Jlc3QuUG9zdGdyZXN0CmltcG9ydCBpby5tb2Nray5DYWxsZWQKaW1wb3J0IGlvLm1vY2trLmNvRXZlcnkKaW1wb3J0IGlvLm1vY2trLmNvVmVyaWZ5CmltcG9ydCBpby5tb2Nray5tb2NrawppbXBvcnQgaW8ubW9ja2sudmVyaWZ5CmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMudGVzdC5ydW5UZXN0CmltcG9ydCBvcmcuanVuaXQuQXNzZXJ0LmFzc2VydEZhbHNlCmltcG9ydCBvcmcuanVuaXQuQXNzZXJ0LmFzc2VydFRydWUKaW1wb3J0IG9yZy5qdW5pdC5UZXN0CgovKiogUHVibGljIGxlZ2FjeSBlbnRyeSBwb2ludHMgbXVzdCByZXNwZWN0IG9wdGlvbmFsIHN5bmMgcmF0aGVyIHRoYW4gYnlwYXNzIGl0cyBjb25zZW50LiAqLwpjbGFzcyBQcm9maWxlU2V0dGluZ3NQbHVnaW5TeW5jVGVzdCB7CiAgICBwcml2YXRlIHZhbCBwcmVmZXJlbmNlcyA9IG1vY2trPE9tbmlhUHJlZmVyZW5jZXNTeW5jU2VydmljZT4ocmVsYXhlZCA9IHRydWUpCiAgICBwcml2YXRlIHZhbCBwb3N0Z3Jlc3QgPSBtb2NrazxQb3N0Z3Jlc3Q+KCkKICAgIHByaXZhdGUgdmFsIGNyZWRlbnRpYWxzID0gbW9ja2s8UHJvdmlkZXJDcmVkZW50aWFsU3luY1NlcnZpY2U+KHJlbGF4ZWQgPSB0cnVlKQogICAgcHJpdmF0ZSB2YWwgbWVkaWFTZXJ2ZXJzID0gbW9ja2s8TWVkaWFTZXJ2ZXJTeW5jU2VydmljZT4ocmVsYXhlZCA9IHRydWUpCiAgICBwcml2YXRlIGZ1biBzZXJ2aWNlKCkgPSBQcm9maWxlU2V0dGluZ3NTeW5jU2VydmljZSgKICAgICAgICBhdXRoTWFuYWdlciA9IG1vY2trKHJlbGF4ZWQgPSB0cnVlKSwKICAgICAgICBvbW5pYVByZWZlcmVuY2VzU3luY1NlcnZpY2UgPSBwcmVmZXJlbmNlcywKICAgICAgICBwb3N0Z3Jlc3QgPSBwb3N0Z3Jlc3QsCiAgICAgICAgcHJvZmlsZU1hbmFnZXIgPSBtb2NrayhyZWxheGVkID0gdHJ1ZSksCiAgICAgICAgcHJvZmlsZURhdGFTdG9yZUZhY3RvcnkgPSBtb2NrayhyZWxheGVkID0gdHJ1ZSksCiAgICAgICAgc3luY0NsaWVudElkZW50aXR5ID0gbW9ja2socmVsYXhlZCA9IHRydWUpLAogICAgICAgIHByb3ZpZGVyQ3JlZGVudGlhbFN5bmNTZXJ2aWNlID0gY3JlZGVudGlhbHMsCiAgICAgICAgbWVkaWFTZXJ2ZXJTeW5jU2VydmljZSA9IG1lZGlhU2VydmVycywKICAgICAgICB0bWRiU2V0dGluZ3NEYXRhU3RvcmUgPSBtb2NrayhyZWxheGVkID0gdHJ1ZSksCiAgICAgICAgbWV0YVJlcG9zaXRvcnkgPSBtb2NrayhyZWxheGVkID0gdHJ1ZSksCiAgICAgICAgY3dFbnJpY2htZW50Q2FjaGUgPSBtb2NrayhyZWxheGVkID0gdHJ1ZSksCiAgICApCgogICAgQFRlc3QgZnVuIHN0YXJ0dXBSZXF1ZXN0c0NvbnNlbnRBd2FyZVN5bmNXaXRob3V0VXNpbmdMZWdhY3lUcmFuc3BvcnQoKSB7CiAgICAgICAgc2VydmljZSgpCiAgICAgICAgdmVyaWZ5KGV4YWN0bHkgPSAxKSB7IHByZWZlcmVuY2VzLnJlcXVlc3RTeW5jKCkgfQogICAgICAgIHZlcmlmeSB7IHBvc3RncmVzdCB3YXNOb3QgQ2FsbGVkIH0KICAgIH0KCiAgICBAVGVzdCBmdW4gb2ZmQW5kSW5pdGlhbENob2ljZURvTm90Q2xhaW1TZXR0aW5nc1dlcmVQdWxsZWQoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBzZXJ2aWNlID0gc2VydmljZSgpCiAgICAgICAgZm9yIChzdGF0dXMgaW4gbGlzdE9mKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TaWduSW5SZXF1aXJlZCkpIHsKICAgICAgICAgICAgY29FdmVyeSB7IHByZWZlcmVuY2VzLnN5bmNocm9uaXplKCkgfSByZXR1cm5zIHN0YXR1cwogICAgICAgICAgICBhc3NlcnRGYWxzZShzZXJ2aWNlLnB1bGxDdXJyZW50UHJvZmlsZUZyb21SZW1vdGUoKS5nZXRPclRocm93KCkpCiAgICAgICAgICAgIGFzc2VydFRydWUoc2VydmljZS5wdXNoQ3VycmVudFByb2ZpbGVUb1JlbW90ZSgpLmlzU3VjY2VzcykKICAgICAgICB9CiAgICAgICAgY29WZXJpZnkoZXhhY3RseSA9IDYpIHsgcHJlZmVyZW5jZXMuc3luY2hyb25pemUoKSB9CiAgICAgICAgdmVyaWZ5IHsgcG9zdGdyZXN0IHdhc05vdCBDYWxsZWQgfQogICAgfQoKICAgIEBUZXN0IGZ1biBzdWNjZXNzZnVsUHVsbFJlcG9ydHNBcHBsaWVkUHJlZmVyZW5jZXMoKSA9IHJ1blRlc3QgewogICAgICAgIGNvRXZlcnkgeyBwcmVmZXJlbmNlcy5zeW5jaHJvbml6ZSgpIH0gcmV0dXJucyBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkCiAgICAgICAgYXNzZXJ0VHJ1ZShzZXJ2aWNlKCkucHVsbEN1cnJlbnRQcm9maWxlRnJvbVJlbW90ZSgpLmdldE9yVGhyb3coKSkKICAgICAgICB2ZXJpZnkgeyBwb3N0Z3Jlc3Qgd2FzTm90IENhbGxlZCB9CiAgICB9CgogICAgQFRlc3QgZnVuIGVycm9yc1Byb3BhZ2F0ZVdpdGhvdXRGYWxsYmFja1RvTGVnYWN5VHJhbnNwb3J0KCkgPSBydW5UZXN0IHsKICAgICAgICBjb0V2ZXJ5IHsgcHJlZmVyZW5jZXMuc3luY2hyb25pemUoKSB9IHJldHVybnMgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yCiAgICAgICAgdmFsIHNlcnZpY2UgPSBzZXJ2aWNlKCkKICAgICAgICBhc3NlcnRUcnVlKHNlcnZpY2UucHVsbEN1cnJlbnRQcm9maWxlRnJvbVJlbW90ZSgpLmlzRmFpbHVyZSkKICAgICAgICBhc3NlcnRUcnVlKHNlcnZpY2UucHVzaEN1cnJlbnRQcm9maWxlVG9SZW1vdGUoKS5pc0ZhaWx1cmUpCiAgICAgICAgdmVyaWZ5IHsgcG9zdGdyZXN0IHdhc05vdCBDYWxsZWQgfQogICAgfQoKICAgIEBUZXN0IGZ1biB0aHJvd25UcmFuc3BvcnRFcnJvcklzUmV0dXJuZWRBc0ZhaWx1cmUoKSA9IHJ1blRlc3QgewogICAgICAgIGNvRXZlcnkgeyBwcmVmZXJlbmNlcy5zeW5jaHJvbml6ZSgpIH0gdGhyb3dzIElsbGVnYWxTdGF0ZUV4Y2VwdGlvbigiU3ludGhldGljIG9mZmxpbmUiKQogICAgICAgIHZhbCBzZXJ2aWNlID0gc2VydmljZSgpCiAgICAgICAgYXNzZXJ0VHJ1ZShzZXJ2aWNlLnB1bGxDdXJyZW50UHJvZmlsZUZyb21SZW1vdGUoKS5pc0ZhaWx1cmUpCiAgICAgICAgYXNzZXJ0VHJ1ZShzZXJ2aWNlLnB1c2hDdXJyZW50UHJvZmlsZVRvUmVtb3RlKCkuaXNGYWlsdXJlKQogICAgICAgIHZlcmlmeSB7IHBvc3RncmVzdCB3YXNOb3QgQ2FsbGVkIH0KICAgIH0KCiAgICBAVGVzdCBmdW4gZm9yZWdyb3VuZFJlcXVlc3RSZXRhaW5zSW5kZXBlbmRlbnRDcmVkZW50aWFsQW5kTWVkaWFTZXJ2ZXJTeW5jKCkgewogICAgICAgIHZhbCBzZXJ2aWNlID0gc2VydmljZSgpCiAgICAgICAgc2VydmljZS5yZXF1ZXN0Rm9yZWdyb3VuZFB1bGwoZm9yY2UgPSB0cnVlKQogICAgICAgIHZlcmlmeShleGFjdGx5ID0gMikgeyBwcmVmZXJlbmNlcy5yZXF1ZXN0U3luYygpIH0KICAgICAgICB2ZXJpZnkoZXhhY3RseSA9IDEpIHsgY3JlZGVudGlhbHMucmVxdWVzdEZvcmVncm91bmRQdWxsKHRydWUpIH0KICAgICAgICB2ZXJpZnkoZXhhY3RseSA9IDEpIHsgbWVkaWFTZXJ2ZXJzLnJlcXVlc3RGb3JlZ3JvdW5kUHVsbCh0cnVlKSB9CiAgICAgICAgdmVyaWZ5IHsgcG9zdGdyZXN0IHdhc05vdCBDYWxsZWQgfQogICAgfQp9Cg=='))


# Omnia inline Discover in Search.
if (ROOT/'app').exists():
    p=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/search/SearchScreen.kt';s=p.read_text()
    if 'import androidx.compose.foundation.layout.BoxWithConstraints' not in s:
        s=s.replace('import androidx.compose.foundation.layout.Box\n','import androidx.compose.foundation.layout.Box\nimport androidx.compose.foundation.layout.BoxWithConstraints\n',1)
    anchor='    val discoverFirstItemFocusRequester = remember { FocusRequester() }'
    if 'val inlineDiscoverFilterFocusRequester' not in s:
        s=s.replace(anchor,anchor+'\n    val inlineDiscoverFilterFocusRequester = remember { FocusRequester() }',1)
    s=s.replace('''        if (isDiscoverMode) {
            false
        } else {''','''        if (isDiscoverMode) {
            true // Filters remain reachable while discovery is loading or empty.
        } else {''',1)
    s=s.replace('''    // Restore the Discover button after returning.
    LaunchedEffect(restoreDiscoverFocus) {
        if (!restoreDiscoverFocus) return@LaunchedEffect
        repeat(2) { withFrameNanos { } }
        runCatching { discoverButtonFocusRequester.requestFocus() }
        restoreDiscoverFocus = false
    }''','''    // Inline discovery restores its own poster; ordinary search returns to its input.
    LaunchedEffect(restoreDiscoverFocus, isDiscoverMode) {
        if (!restoreDiscoverFocus || isDiscoverMode) return@LaunchedEffect
        repeat(2) { withFrameNanos { } }
        runCatching { searchFocusRequester.requestFocus() }
        restoreDiscoverFocus = false
    }''',1)
    anchor='''    Box(
        modifier = Modifier
            .fillMaxSize()
            .onPreviewKeyEvent { keyEvent ->'''
    replacement=anchor.replace('    Box(','    BoxWithConstraints(',1)
    if anchor in s:s=s.replace(anchor,replacement,1)
    start=s.index('    BoxWithConstraints(')
    tail=s[start:]
    tail=tail.replace('''        contentAlignment = Alignment.TopCenter
    ) {
        val listState = rememberLazyListState()''','''        contentAlignment = Alignment.TopCenter
    ) {
        // The nested result grid must have a finite viewport inside the search list.
        val inlineDiscoverHeight = (maxHeight - 124.dp).coerceAtLeast(200.dp)
        val listState = rememberLazyListState()''',1)
    tail=tail.replace('''                    onSubmit = {
                        submitCurrentQuery(uiState.query.trim())
                    },''','''                    onSubmit = {
                        if (isDiscoverMode && uiState.query.isBlank()) {
                            keyboardController?.hide()
                            runCatching { inlineDiscoverFilterFocusRequester.requestFocus() }
                        } else submitCurrentQuery(uiState.query.trim())
                    },''',1)
    tail=tail.replace('''                        viewModel.onEvent(SearchEvent.RememberSearchFromTextInput)
                        focusResults = true''','''                        viewModel.onEvent(SearchEvent.RememberSearchFromTextInput)
                        if (isDiscoverMode) {
                            runCatching { inlineDiscoverFilterFocusRequester.requestFocus() }
                        } else focusResults = true''',1)
    tail=tail.replace('showDiscoverButton = uiState.discoverLocation == DiscoverLocation.IN_SEARCH,','showDiscoverButton = false,',1)
    tail=tail.replace('clearHistoryFocusRequester = if (showRecentSearches) recentClearHistoryFocusRequester else null,','clearHistoryFocusRequester = if (showRecentSearches && !isDiscoverMode) recentClearHistoryFocusRequester else null,',1)
    marker='''            if (isDiscoverMode) {
                if (showRecentSearches) {'''
    if marker in tail:
        tail=tail.replace(marker,'''            if (isDiscoverMode) {
                item(key = "omnia_inline_discover") {
                    DiscoverSection(
                        uiState = uiState,
                        posterCardStyle = posterCardStyle,
                        watchedMovieIds = watchedMovieIds,
                        watchedSeriesIds = watchedSeriesIds,
                        focusResults = focusResults,
                        showBuiltInHeader = true,
                        firstItemFocusRequester = discoverFirstItemFocusRequester,
                        focusedItemIndex = discoverFocusedItemIndex,
                        shouldRestoreFocusedItem = restoreDiscoverFocus,
                        blockFilterFocus = restoreDiscoverFocus || pendingDiscoverRestoreOnResume,
                        externalFilterFocusRequester = inlineDiscoverFilterFocusRequester,
                        onMoveUpFromFilters = {
                            keyboardController?.hide()
                            backToFieldLatched = true
                            coroutineScope.launch {
                                listState.scrollToItem(0)
                                runCatching { searchFocusRequester.requestFocus() }
                            }
                        },
                        onRestoreFocusedItemHandled = { restoreDiscoverFocus = false },
                        onNavigateToDetail = { id, type, addonBaseUrl ->
                            pendingDiscoverRestoreOnResume = true
                            onNavigateToDetail(id, type, addonBaseUrl)
                        },
                        onDiscoverItemFocused = { index ->
                            discoverFocusedItemIndex = index
                            uiState.discoverResults.getOrNull(index)?.let { viewModel.prefetchMetaOnFocus(it.id, it.rawType) }
                        },
                        onSelectType = { discoverFocusedItemIndex = 0; viewModel.onEvent(SearchEvent.SelectDiscoverType(it)) },
                        onSelectCatalog = { discoverFocusedItemIndex = 0; viewModel.onEvent(SearchEvent.SelectDiscoverCatalog(it)) },
                        onSelectGenre = { discoverFocusedItemIndex = 0; viewModel.onEvent(SearchEvent.SelectDiscoverGenre(it)) },
                        onLoadMore = { viewModel.onEvent(SearchEvent.LoadNextDiscoverResults) },
                        onItemLongPress = { item, addonBaseUrl -> viewModel.posterOptions.show(item, addonBaseUrl) },
                        modifier = Modifier.height(inlineDiscoverHeight)
                    )
                }
                if (showRecentSearches) {''',1)
        # Empty "start searching" card is replaced by actual discovery, not shown below it.
        begin=tail.index('''                } else {
                    item(key = "search_start")''',tail.index('item(key = "omnia_inline_discover")'))
        end=tail.index('''            } else {
                // The "press Done to search"''',begin)
        tail=tail[:begin]+'''                }
'''+tail[end:]
    s=s[:start]+tail
    s=s.replace('keyEvent.nativeKeyEvent.keyCode, showDiscoverButton))','keyEvent.nativeKeyEvent.keyCode, showDiscoverButton || showVoiceSearch))',1)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/search/SearchDiscoverSection.kt';s=p.read_text()
    anchor='''    blockFilterFocus: Boolean = false,
    onRestoreFocusedItemHandled: () -> Unit,'''
    replacement='''    blockFilterFocus: Boolean = false,
    externalFilterFocusRequester: FocusRequester? = null,
    onMoveUpFromFilters: (() -> Unit)? = null,
    onRestoreFocusedItemHandled: () -> Unit,'''
    if replacement not in s:
        assert anchor in s;s=s.replace(anchor,replacement,1)
    s=s.replace('val filterFocusRequester = remember { FocusRequester() }','val rememberedFilterFocusRequester = remember { FocusRequester() }\n    val filterFocusRequester = externalFilterFocusRequester ?: rememberedFilterFocusRequester',1)
    anchor='    var gridHasFocus by remember { mutableStateOf(false) }'
    if 'var filterRowHasFocus' not in s:
        s=s.replace(anchor,anchor+'\n    var filterRowHasFocus by remember { mutableStateOf(false) }\n\n    androidx.activity.compose.BackHandler(enabled = filterRowHasFocus && expandedPicker == null && onMoveUpFromFilters != null) {\n        onMoveUpFromFilters?.invoke()\n    }',1)
    anchor='''        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.md)
        ) {'''
    replacement='''        Row(
            modifier = Modifier.fillMaxWidth()
                .onFocusChanged { filterRowHasFocus = it.hasFocus }
                .onPreviewKeyEvent { event ->
                    if (expandedPicker == null && onMoveUpFromFilters != null &&
                        event.nativeKeyEvent.keyCode == AndroidKeyEvent.KEYCODE_DPAD_UP
                    ) {
                        if (event.nativeKeyEvent.action == AndroidKeyEvent.ACTION_DOWN) onMoveUpFromFilters()
                        true
                    } else false
                },
            horizontalArrangement = Arrangement.spacedBy(NuvioTheme.spacing.md)
        ) {'''
    if replacement not in s:
        assert anchor in s;s=s.replace(anchor,replacement,1)
    p.write_text(s,encoding='utf-8',newline='\n')

if (ROOT/'app').exists():
    prefix=ROOT/'app/src/main/java/com/nuvio/tv/ui/screens/search'
    p=prefix/'SearchUiState.kt';s=p.read_text()
    if 'val discoverFailed:' not in s:s=s.replace('    val discoverLoading: Boolean = false,','    val discoverLoading: Boolean = false,\n    val discoverFailed: Boolean = false,',1)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=prefix/'SearchViewModel.kt';s=p.read_text()
    anchor='    fun ensureDiscoverLoaded() {'
    if 'fun retryDiscover()' not in s:
        s=s.replace(anchor,'    fun retryDiscover() {\n        if (_uiState.value.selectedDiscoverCatalogKey == null) viewModelScope.launch { loadDiscoverCatalogs() }\n        else fetchDiscoverContent(reset = true)\n    }\n\n'+anchor,1)
    s=s.replace('it.copy(discoverLoading = true)','it.copy(discoverLoading = true, discoverFailed = false)')
    s=s.replace('''        } catch (_: Exception) {
            _uiState.update { it.copy(discoverInitialized = true, discoverLoading = false) }''','''        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            _uiState.update { it.copy(discoverInitialized = true, discoverLoading = false, discoverFailed = true) }''',1)
    s=s.replace('if (state.query.trim().isNotEmpty()) return@launch','if (state.query.trim().length >= MIN_SEARCH_QUERY_LENGTH) return@launch',1)
    # Only the discovery fetch section is changed here; ordinary search errors remain separate.
    start=s.index('    private fun fetchDiscoverContent(reset: Boolean)')
    end=s.index('    private fun pickDiscoverCatalog(',start)
    segment=s[start:end]
    segment=segment.replace('                        discoverLoading = true,','                        discoverLoading = true,\n                        discoverFailed = false,',1)
    segment=segment.replace('it.copy(discoverLoadingMore = true)','it.copy(discoverLoadingMore = true, discoverFailed = false)',1)
    anchor='''                    is NetworkResult.Error -> {
                        revealBatchAfterNextDiscoverFetch = false'''
    if anchor in segment:
        pos=segment.index(anchor)
        head,tail=segment[:pos],segment[pos:]
        tail=tail.replace('                                discoverLoading = false,','                                discoverLoading = false,\n                                discoverFailed = true,',1)
        segment=head+tail
    s=s[:start]+segment+s[end:]
    import re
    for value in ['false','true']:
        s=re.sub(r'(?m)^([ \t]*)discoverFailed = '+value+r',\n(?:\1discoverFailed = '+value+r',\n)+',r'\1discoverFailed = '+value+',\n',s)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=prefix/'SearchDiscoverSection.kt';s=p.read_text()
    if 'onRetryDiscover:' not in s:s=s.replace('    onLoadMore: () -> Unit,','    onLoadMore: () -> Unit,\n    onRetryDiscover: () -> Unit = {},',1)
    anchor='''        when {
            uiState.discoverLoading && uiState.discoverResults.isEmpty() -> {'''
    replacement='''        when {
            uiState.discoverFailed && uiState.discoverResults.isEmpty() -> {
                com.nuvio.tv.ui.components.ErrorState(
                    message = "Discover could not load. Your selected catalog and filters are kept.",
                    onRetry = onRetryDiscover
                )
            }
            uiState.discoverLoading && uiState.discoverResults.isEmpty() -> {'''
    if replacement not in s:
        assert anchor in s;s=s.replace(anchor,replacement,1)
    p.write_text(s,encoding='utf-8',newline='\n')
    for name in ['SearchScreen.kt','DiscoverScreen.kt']:
        p=prefix/name;s=p.read_text()
        anchor='onLoadMore = { viewModel.onEvent(SearchEvent.LoadNextDiscoverResults) },'
        if 'onRetryDiscover = { viewModel.retryDiscover() }' not in s:
            assert anchor in s;s=s.replace(anchor,anchor+'\n                        onRetryDiscover = { viewModel.retryDiscover() },',1)
        p.write_text(s,encoding='utf-8',newline='\n')

# Priority storage release: account/media storage and catalog defaults stay unchanged.
exec(compile('"""Bound browsing caches and remove obsolete installers without touching account/media data."""\nfrom pathlib import Path\nimport re\n\nmobile=(ROOT/\'composeApp\').is_dir()\npackage=\'com.nuvio.app.features.updater\' if mobile else \'com.nuvio.tv.updater\'\nbase=\'composeApp/src/androidMain/kotlin/com/nuvio/app/features/updater/\' if mobile else \'app/src/main/java/com/nuvio/tv/updater/\'\n\ndef write(relative,text):\n p=ROOT/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n\ndef replace(relative,old,new):\n p=ROOT/relative;s=p.read_text()\n if new in s:\n  p.write_text(s,encoding=\'utf-8\',newline=\'\\n\');return\n assert s.count(old)==1,(relative,old[:80],s.count(old))\n p.write_text(s.replace(old,new,1),encoding=\'utf-8\',newline=\'\\n\')\n\nutility=\'\'\'package PACKAGE\n\nimport java.io.File\n\n/** Operates on direct installer files in the app-owned updates directory only. */\ninternal object OmniaUpdateFiles {\n    private fun managed(directory: File): List<File> = directory.listFiles().orEmpty().filter {\n        it.isFile && it.canonicalFile.parentFile == directory.canonicalFile &&\n            (it.name.endsWith(".apk") || it.name.endsWith(".apk.part") || it.name == "update.dm")\n    }\n\n    fun prune(directory: File, keep: File? = null) {\n        require(keep == null || keep.canonicalFile.parentFile == directory.canonicalFile)\n        managed(directory).filter { it != keep }.forEach { it.delete() }\n    }\n\n    fun removeInstalled(directory: File, installedCode: Long, archiveCode: (File) -> Long?) {\n        managed(directory).forEach { file ->\n            val code = if (file.name.endsWith(".apk")) archiveCode(file) else null\n            if (code == null || code <= installedCode) file.delete()\n        }\n    }\n}\n\'\'\'.replace(\'PACKAGE\',package)\nwrite(base+\'OmniaUpdateFiles.kt\',utility)\n\ntests=\'\'\'package PACKAGE\n\nimport java.nio.file.Files\nimport org.junit.Assert.*\nimport org.junit.Test\n\nclass OmniaUpdateFilesTest {\n    @Test fun upgradeRemovesInstalledAndCorruptFilesButKeepsPendingUpdateAndUserFiles() {\n        val root = Files.createTempDirectory("omnia-update-cleanup").toFile()\n        try {\n            val names = listOf("old.apk", "current.apk", "future.apk", "corrupt.apk", "future.apk.part", "update.dm", "notes.txt")\n            names.forEach { root.resolve(it).writeText(it) }\n            val versions = mapOf("old.apk" to 1L, "current.apk" to 2L, "future.apk" to 3L)\n            OmniaUpdateFiles.removeInstalled(root, 2) { versions[it.name] }\n            assertEquals(setOf("future.apk", "notes.txt"), root.list()!!.toSet())\n            OmniaUpdateFiles.removeInstalled(root, 3) { versions[it.name] }\n            assertEquals(setOf("notes.txt"), root.list()!!.toSet())\n        } finally { root.deleteRecursively() }\n    }\n\n    @Test fun nextDownloadReclaimsOldInstallersWithoutRecursingIntoOtherData() {\n        val root = Files.createTempDirectory("omnia-update-prune").toFile()\n        try {\n            val pending = root.resolve("new.apk").apply { writeText("new") }\n            root.resolve("old.apk").writeText("old")\n            root.resolve("failed.apk.part").writeText("partial")\n            val unrelated = root.resolve("nested").apply { mkdir() }.resolve("saved.apk").apply { writeText("saved") }\n            OmniaUpdateFiles.prune(root, pending)\n            assertTrue(pending.exists());assertTrue(unrelated.exists())\n            assertFalse(root.resolve("old.apk").exists());assertFalse(root.resolve("failed.apk.part").exists())\n        } finally { root.deleteRecursively() }\n    }\n\n    @Test fun anOutsideKeepPathIsRejected() {\n        val root = Files.createTempDirectory("omnia-update-boundary").toFile()\n        try {\n            assertThrows(IllegalArgumentException::class.java) { OmniaUpdateFiles.prune(root, root.parentFile.resolve("outside.apk")) }\n        } finally { root.deleteRecursively() }\n    }\n\n    @Test fun symlinksCannotDeleteOutsideTheInstallerDirectory() {\n        val root = Files.createTempDirectory("omnia-update-symlink").toFile()\n        val outside = Files.createTempFile("omnia-preserved", ".apk").toFile()\n        try {\n            outside.writeText("preserved")\n            Files.createSymbolicLink(root.resolve("linked.apk").toPath(), outside.toPath())\n            OmniaUpdateFiles.prune(root)\n            assertEquals("preserved", outside.readText())\n        } finally { root.deleteRecursively();outside.delete() }\n    }\n}\n\'\'\'.replace(\'PACKAGE\',package)\ntestbase=\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/updater/\' if mobile else \'app/src/test/java/com/nuvio/tv/updater/\'\nwrite(testbase+\'OmniaUpdateFilesTest.kt\',tests)\n\ntransfer_tests=\'\'\'package PACKAGE\n\nimport java.io.File\nimport java.nio.file.Files\nimport java.util.concurrent.TimeUnit\nimport kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.runBlocking\nimport okhttp3.OkHttpClient\nimport okhttp3.mockwebserver.MockResponse\nimport okhttp3.mockwebserver.MockWebServer\nimport okhttp3.mockwebserver.SocketPolicy\nimport okio.Buffer\nimport org.junit.Assert.*\nimport org.junit.Test\nPLATFORM_IMPORTS\nPLATFORM_ANNOTATIONS\nclass OmniaDownloadTransferTest {\n    private fun directory(): File { PLATFORM_DIRECTORY }\n    private suspend fun download(server: MockWebServer, root: File, progress: (Long, Long?) -> Unit = { _, _ -> }): Result<File> {\n        PLATFORM_DOWNLOAD\n    }\n\n    @Test fun completeDownloadIsAtomicAndDoesNotEnterTheHttpCache() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            val data = ByteArray(16384) { (it % 255).toByte() }\n            server.enqueue(MockResponse().setBody(Buffer().write(data)))\n            val file = download(server, root).getOrThrow()\n            assertArrayEquals(data, file.readBytes())\n            assertFalse(root.resolve("candidate.apk.part").exists())\n            assertEquals("no-store", server.takeRequest().getHeader("Cache-Control"))\n        } } finally { root.deleteRecursively() }\n    } }\n\n    @Test fun httpFailureLeavesNoInstallerOrPartialFile() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            server.enqueue(MockResponse().setResponseCode(503).setBody("Unavailable"))\n            assertTrue(download(server, root).isFailure)\n            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())\n        } } finally { root.deleteRecursively() }\n    } }\n\n    @Test fun truncatedDownloadCannotBecomeAnInstallableFile() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            server.enqueue(MockResponse().setBody("short").setHeader("Content-Length", 4096).setSocketPolicy(SocketPolicy.DISCONNECT_AT_END))\n            assertTrue(download(server, root).isFailure)\n            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())\n        } } finally { root.deleteRecursively() }\n    } }\n\n    @Test fun cancellationIsPropagatedAndReclaimsThePartialDownload() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            server.enqueue(MockResponse().setBody("candidate bytes"))\n            var cancelled = false\n            try { download(server, root) { _, _ -> throw CancellationException("cancelled by test") } }\n            catch (_: CancellationException) { cancelled = true }\n            assertTrue(cancelled)\n            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())\n        } } finally { root.deleteRecursively() }\n    } }\n}\n\'\'\'.replace(\'PACKAGE\',package)\nif mobile:\n transfer_tests=transfer_tests.replace(\'PLATFORM_IMPORTS\',\'import android.app.Application\\nimport org.junit.runner.RunWith\\nimport org.robolectric.RobolectricTestRunner\\nimport org.robolectric.RuntimeEnvironment\\nimport org.robolectric.annotation.Config\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_ANNOTATIONS\',\'@RunWith(RobolectricTestRunner::class)\\n@Config(sdk = [34], application = Application::class)\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DIRECTORY\',\'val context = RuntimeEnvironment.getApplication<Application>(); AndroidAppUpdaterPlatform.initialize(context); return File(context.cacheDir, "updates").apply { mkdirs() }\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DOWNLOAD\',\'return AndroidAppUpdaterPlatform.downloadApk(server.url("/candidate.apk").toString(), "candidate.apk", progress).map { File(it) }\')\n write(\'composeApp/src/androidFullHostTest/kotlin/com/nuvio/app/features/updater/OmniaDownloadTransferTest.kt\',transfer_tests)\nelse:\n transfer_tests=transfer_tests.replace(\'PLATFORM_IMPORTS\',\'\').replace(\'PLATFORM_ANNOTATIONS\',\'\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DIRECTORY\',\'return Files.createTempDirectory("omnia-transfer").toFile()\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DOWNLOAD\',\'return ApkDownloader(OkHttpClient.Builder().readTimeout(2, TimeUnit.SECONDS).build()).download(server.url("/candidate.apk").toString(), root.resolve("candidate.apk"), progress)\')\n write(testbase+\'OmniaDownloadTransferTest.kt\',transfer_tests)\n\nif mobile:\n updater=\'composeApp/src/androidFull/kotlin/com/nuvio/app/features/updater/AndroidAppUpdaterPlatform.kt\'\n replace(updater,\'import kotlinx.coroutines.Dispatchers\',\'\'\'import kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.CoroutineScope\nimport kotlinx.coroutines.SupervisorJob\nimport kotlinx.coroutines.launch\nimport kotlinx.coroutines.sync.Mutex\nimport kotlinx.coroutines.sync.withLock\nimport kotlinx.coroutines.Dispatchers\'\'\')\n replace(updater,\'    private var appContext: Context? = null\',\'\'\'    private var appContext: Context? = null\n    private val downloadMutex = Mutex()\n    private val maintenanceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)\n    private var cleanupScheduled = false\'\'\')\n replace(updater,\'\'\'        appContext = context.applicationContext\n    }\n\'\'\',\'\'\'        appContext = context.applicationContext\n        val schedule = synchronized(this) {\n            if (cleanupScheduled) false else { cleanupScheduled = true; true }\n        }\n        if (schedule) maintenanceScope.launch {\n            downloadMutex.withLock {\n                runCatching {\n                    val current = context.packageManager.getPackageInfo(context.packageName, 0)\n                    val code = if (Build.VERSION.SDK_INT >= 28) current.longVersionCode else current.versionCode.toLong()\n                    listOf(File(context.cacheDir, "updates"), File(context.filesDir, "updates")).forEach { directory ->\n                    OmniaUpdateFiles.removeInstalled(directory, code) { file ->\n                        context.packageManager.getPackageArchiveInfo(file.path, 0)?.takeIf { it.packageName == context.packageName }?.let {\n                            if (Build.VERSION.SDK_INT >= 28) it.longVersionCode else it.versionCode.toLong()\n                        }\n                    }\n                    }\n                }\n            }\n        }\n    }\n\'\'\')\n p=ROOT/updater;s=p.read_text();start=s.index(\'    suspend fun downloadApk(\');end=s.index(\'    fun canRequestPackageInstalls()\',start)\n s=s[:start]+\'\'\'    suspend fun downloadApk(\n        assetUrl: String,\n        assetName: String,\n        onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,\n    ): Result<String> = withContext(Dispatchers.IO) {\n        downloadMutex.withLock {\n            val context = requireContext()\n            val safeName = assetName.replace(Regex("[^a-zA-Z0-9._-]"), "_")\n            val directory = File(context.cacheDir, "updates").apply { mkdirs() }\n            val destination = File(directory, safeName)\n            val partial = File(directory, "$safeName.part")\n            try {\n                require(safeName.endsWith(".apk")) { "Invalid update filename" }\n                OmniaUpdateFiles.prune(directory)\n                val request = Request.Builder().url(assetUrl).header("Cache-Control", "no-store").build()\n                httpClient.newCall(request).execute().use { response ->\n                    check(response.isSuccessful) { "Download failed: HTTP ${response.code}" }\n                    val body = checkNotNull(response.body) { "Empty update download" }\n                    val totalBytes = body.contentLength().takeIf { it > 0L }\n                    var received = 0L\n                    body.byteStream().use { input ->\n                        FileOutputStream(partial).use { output ->\n                            val buffer = ByteArray(64 * 1024)\n                            while (true) {\n                                currentCoroutineContext().ensureActive()\n                                val read = input.read(buffer)\n                                if (read < 0) break\n                                if (read == 0) continue\n                                output.write(buffer, 0, read);received += read\n                                onProgress(received, totalBytes)\n                            }\n                            output.fd.sync()\n                        }\n                    }\n                    check(received > 0L && (totalBytes == null || received == totalBytes)) { "Incomplete update download. Please retry." }\n                }\n                currentCoroutineContext().ensureActive()\n                check(partial.renameTo(destination)) { "Could not save update. Check free storage." }\n                Result.success(destination.absolutePath)\n            } catch (cancelled: CancellationException) {\n                throw cancelled\n            } catch (error: Exception) {\n                Result.failure(error)\n            } finally {\n                partial.delete()\n            }\n        }\n    }\n\n\'\'\'+s[end:];p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n replace(updater,\'\'\'        check(apkFile.exists()) { runBlocking { getString(Res.string.updates_downloaded_file_missing) } }\n\'\'\',\'\'\'        check(apkFile.exists()) { runBlocking { getString(Res.string.updates_downloaded_file_missing) } }\n        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)\n        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }\n\'\'\')\n app=\'composeApp/src/androidMain/kotlin/com/nuvio/app/NuvioApplication.kt\'\n replace(app,\'import coil3.ImageLoader\',\'import coil3.disk.DiskCache\\nimport okio.Path.Companion.toOkioPath\\nimport coil3.ImageLoader\')\n replace(app,\'            .diskCachePolicy(CachePolicy.ENABLED)\',\'\'\'            .diskCachePolicy(CachePolicy.ENABLED)\n            .diskCache {\n                DiskCache.Builder()\n                    .directory(context.cacheDir.resolve("image_cache").toOkioPath())\n                    .maxSizeBytes(96L * 1024 * 1024)\n                    .build()\n            }\'\'\')\n badge=\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/BadgeImageLoader.kt\'\n replace(badge,\'import coil3.ImageLoader\',\'import coil3.SingletonImageLoader\\nimport coil3.ImageLoader\')\n replace(badge,\'                .diskCachePolicy(CachePolicy.ENABLED)\',\'\'\'                .diskCachePolicy(CachePolicy.ENABLED)\n                .diskCache { SingletonImageLoader.get(context).diskCache }\'\'\')\n ios=\'composeApp/src/iosMain/kotlin/com/nuvio/app/core/ui/PlatformImageLoader.ios.kt\'\n write(ios,\'\'\'package com.nuvio.app.core.ui\n\nimport coil3.ImageLoader\nimport coil3.disk.DiskCache\nimport okio.Path.Companion.toPath\nimport platform.Foundation.NSCachesDirectory\nimport platform.Foundation.NSSearchPathForDirectoriesInDomains\nimport platform.Foundation.NSUserDomainMask\n\ninternal actual fun ImageLoader.Builder.configurePlatformImageLoader(): ImageLoader.Builder = diskCache {\n    val root = NSSearchPathForDirectoriesInDomains(NSCachesDirectory, NSUserDomainMask, true).first() as String\n    DiskCache.Builder()\n        .directory((root + "/image_cache").toPath())\n        .maxSizeBytes(96L * 1024 * 1024)\n        .build()\n}\n\ninternal actual val platformProvidesImageLoader: Boolean = false\n\'\'\')\n replace(\'composeApp/src/androidMain/kotlin/com/nuvio/app/features/addons/AddonPlatform.android.kt\',\'private const val cacheSizeBytes = 50L * 1024L * 1024L\',\'private const val cacheSizeBytes = 32L * 1024L * 1024L\')\n # Independent platform versions retain installed identity and release-channel matching.\n write(\'iosApp/Configuration/Version.xcconfig\',\'CURRENT_PROJECT_VERSION=27\\nMARKETING_VERSION=0.4.19\\n\')\n p=ROOT/\'prepare_omnia_ios_tests.py\';s=p.read_text().replace(\'Version 0.4.18 (26)\',\'Version 0.4.19 (27)\');p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\nelse:\n app=\'app/src/main/java/com/nuvio/tv/NuvioApplication.kt\'\n replace(app,\'.maxSizeBytes(200L * 1024 * 1024)\',\'.maxSizeBytes(96L * 1024 * 1024)\')\n badge=\'app/src/main/java/com/nuvio/tv/ui/components/StreamBadgeChips.kt\'\n replace(badge,\'.maxSizeBytes(50L * 1024 * 1024)\',\'.maxSizeBytes(8L * 1024 * 1024)\')\n net=\'app/src/main/java/com/nuvio/tv/core/di/NetworkModule.kt\';p=ROOT/net;s=p.read_text().replace(\'50L * 1024 * 1024\',\'32L * 1024 * 1024\').replace(\'// 50 MB disk cache\',\'// 32 MB disk cache\');p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n hooks=\'app/src/full/java/com/nuvio/tv/core/runtime/PluginRuntimeHooks.kt\';p=ROOT/hooks;s=p.read_text().replace(\'50L * 1024L * 1024L\',\'32L * 1024L * 1024L\');p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n store=\'app/src/full/java/com/nuvio/tv/updater/UpdateDownloadStore.kt\'\n replace(store,\'        val destination = destinationFor(update)\\n\',\'        val destination = destinationFor(update)\\n        OmniaUpdateFiles.prune(updatesDir)\\n\')\n replace(store,\'import kotlinx.coroutines.flow.first\',\'import kotlinx.coroutines.Dispatchers\\nimport kotlinx.coroutines.withContext\\nimport kotlinx.coroutines.flow.first\')\n p=ROOT/store;s=p.read_text();start=s.index(\'    suspend fun clearIfInstalled()\');end=s.index(\'\\n    }\',start)+len(\'\\n    }\')\n s=s[:start]+\'\'\'    suspend fun clearIfInstalled() = withContext(Dispatchers.IO) {\n        downloadMutex.withLock {\n            // Includes orphan installers and the cache location used by older releases.\n            listOf(File(context.cacheDir, "updates"), updatesDir).forEach { directory ->\n                OmniaUpdateFiles.removeInstalled(directory, BuildConfig.VERSION_CODE.toLong()) { file ->\n                    runCatching {\n                        context.packageManager.getPackageArchiveInfo(file.path, 0)?.takeIf { it.packageName == context.packageName }?.let {\n                            if (android.os.Build.VERSION.SDK_INT >= 28) it.longVersionCode else it.versionCode.toLong()\n                        }\n                    }.getOrNull()\n                }\n            }\n            val pending = updatePreferences.downloadedUpdate.first()\n            if (pending != null && !VersionUtils.isRemoteNewer(pending.first, BuildConfig.VERSION_NAME)) clear()\n        }\n    }\'\'\'+s[end:];p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n installer=\'app/src/full/java/com/nuvio/tv/updater/ApkInstaller.kt\'\n replace(installer,\'        val packageInstaller = context.packageManager.packageInstaller\',\'\'\'        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)\n        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }\n        val packageInstaller = context.packageManager.packageInstaller\'\'\')\n replace(installer,\'        val authority = "${BuildConfig.APPLICATION_ID}.fileprovider"\',\'\'\'        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)\n        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }\n        val authority = "${BuildConfig.APPLICATION_ID}.fileprovider"\'\'\')\n write(\'app/src/full/java/com/nuvio/tv/updater/ApkDownloader.kt\',\'\'\'package com.nuvio.tv.updater\n\nimport kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.currentCoroutineContext\nimport kotlinx.coroutines.ensureActive\nimport kotlinx.coroutines.withContext\nimport okhttp3.OkHttpClient\nimport okhttp3.Request\nimport java.io.File\nimport java.io.FileOutputStream\nimport javax.inject.Inject\nimport javax.inject.Singleton\n\n@Singleton\nclass ApkDownloader @Inject constructor(private val okHttpClient: OkHttpClient) {\n    suspend fun download(\n        url: String,\n        destinationFile: File,\n        onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit\n    ): Result<File> = withContext(Dispatchers.IO) {\n        val partial = File(destinationFile.parentFile, "${destinationFile.name}.part")\n        try {\n            destinationFile.parentFile?.mkdirs()\n            if (destinationFile.exists()) check(destinationFile.delete()) { "Could not replace the saved update" }\n            val request = Request.Builder().url(url).header("Cache-Control", "no-store").build()\n            okHttpClient.newCall(request).execute().use { response ->\n                check(response.isSuccessful) { "Download failed: HTTP ${response.code}" }\n                val body = checkNotNull(response.body) { "Empty update download" }\n                val total = body.contentLength().takeIf { it > 0 }\n                var received = 0L\n                body.byteStream().use { input ->\n                    FileOutputStream(partial).use { output ->\n                        val buffer = ByteArray(64 * 1024)\n                        while (true) {\n                            currentCoroutineContext().ensureActive()\n                            val read = input.read(buffer)\n                            if (read < 0) break\n                            if (read == 0) continue\n                            output.write(buffer, 0, read);received += read\n                            onProgress(received, total)\n                        }\n                        output.fd.sync()\n                    }\n                }\n                check(received > 0L && (total == null || received == total)) { "Incomplete update download. Please retry." }\n            }\n            currentCoroutineContext().ensureActive()\n            check(partial.renameTo(destinationFile)) { "Could not save update. Check free storage." }\n            Result.success(destinationFile)\n        } catch (cancelled: CancellationException) {\n            throw cancelled\n        } catch (error: Exception) {\n            Result.failure(error)\n        } finally {\n            partial.delete()\n        }\n    }\n}\n\'\'\')\n p=ROOT/\'app/build.gradle.kts\';s=p.read_text();s,n=re.subn(r\'versionCode = \\d+\',\'versionCode = 26\',s,count=1);assert n==1;s,n=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.20"\',s,count=1);assert n==1;p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n\n# Display labels are independent of the technical tags consumed by installed updaters.\npaths=([\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/updater/VersionUtils.kt\',\n        \'composeApp/src/commonMain/kotlin/com/nuvio/app/features/updater/AppUpdaterBanner.kt\'] if mobile else\n       [\'app/src/main/java/com/nuvio/tv/updater/VersionUtils.kt\',\n        \'app/src/full/java/com/nuvio/tv/updater/ui/UpdateBanner.kt\'])\np=ROOT/paths[0];s=p.read_text()\nif \'fun displayLabel(\' not in s:\n anchor=\'    fun parse(raw: String?): SemanticVersion? {\'\n assert s.count(anchor)==1\n s=s.replace(anchor,"    fun displayLabel(raw: String?): String {\\n        val normalized = normalize(raw)\\n        return if (parse(normalized) != null) normalized.substringBefore(\'+\') else normalized\\n    }\\n\\n"+anchor,1)\np.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\nif not mobile:\n p=ROOT/paths[1];s=p.read_text()\n if \'import com.nuvio.tv.updater.VersionUtils\' not in s:s=s.replace(\'import com.nuvio.tv.updater.UpdateUiState\',\'import com.nuvio.tv.updater.VersionUtils\\nimport com.nuvio.tv.updater.UpdateUiState\',1)\n p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\nreplace(paths[1],\'        update.tag,\\n\',\'        VersionUtils.displayLabel(update.tag),\\n\')\n\nprint(\'Prepared bounded browsing caches, obsolete installer cleanup and same-package install guard; account/media storage unchanged.\')\n', "omnia-storage-update-overlay", "exec"))

exec(compile('"""Fresh-profile catalog defaults and display-only version labels; no stored-list rewrite."""\nCORE_URL=\'https://omnia.161.97.128.244.sslip.io/catalogs/core/manifest.json\'\nif (ROOT/\'composeApp\').exists():\n    prefix=\'composeApp/src/commonMain/kotlin/com/nuvio/app/\'\n    p=ROOT/prefix/\'features/addons/OmniaAddonDefaults.kt\'\n    p.write_text(\'\'\'package com.nuvio.app.features.addons\n\n// Fallback for a profile with no saved local list. Explicitly empty lists and\n// existing configured add-ons are preserved by the platform storage readers.\ninternal val omniaDefaultAddonUrls = listOf(\n    "\'\'\'+CORE_URL+\'\'\'",\n    "https://opensubtitles-v3.strem.io/manifest.json",\n)\n\'\'\',encoding=\'utf-8\',newline=\'\\n\')\n    version=ROOT/\'iosApp/Configuration/Version.xcconfig\'\n    version.write_text(\'CURRENT_PROJECT_VERSION=27\\nMARKETING_VERSION=0.4.19\\n\',encoding=\'utf-8\',newline=\'\\n\')\n    p=ROOT/\'prepare_omnia_ios_tests.py\'\n    p.write_text(p.read_text().replace(\'Version 0.4.18 (26)\',\'Version 0.4.19 (27)\'),encoding=\'utf-8\',newline=\'\\n\')\n    paths=[prefix+\'features/updater/VersionUtils.kt\',prefix+\'features/updater/AppUpdaterBanner.kt\']\nelse:\n    p=ROOT/\'app/src/main/java/com/nuvio/tv/data/local/AddonPreferences.kt\';s=p.read_text()\n    pattern=r\'private fun getDefaultAddons\\(\\): Set<String> = setOf\\(.*?\\n    \\)\'\n    new=\'private fun getDefaultAddons(): Set<String> = setOf(\\n        "\'+CORE_URL+\'",\\n        "https://opensubtitles-v3.strem.io"\\n    )\'\n    assert len(re.findall(pattern,s,re.S))==1\n    p.write_text(re.sub(pattern,lambda _:new,s,count=1,flags=re.S),encoding=\'utf-8\',newline=\'\\n\')\n    p=ROOT/\'app/build.gradle.kts\';s=p.read_text()\n    s,count=re.subn(r\'versionCode = \\d+\',\'versionCode = 26\',s,count=1);assert count==1\n    s,count=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.20"\',s,count=1);assert count==1\n    p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n    paths=[\'app/src/main/java/com/nuvio/tv/updater/VersionUtils.kt\',\'app/src/full/java/com/nuvio/tv/updater/ui/UpdateBanner.kt\']\n    banner=ROOT/paths[1];s=banner.read_text()\n    if \'import com.nuvio.tv.updater.VersionUtils\' not in s:s=s.replace(\'import com.nuvio.tv.updater.UpdateUiState\',\'import com.nuvio.tv.updater.VersionUtils\\nimport com.nuvio.tv.updater.UpdateUiState\',1)\n    banner.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n\np=ROOT/paths[0];s=p.read_text();anchor=\'    fun parse(raw: String?): SemanticVersion? {\'\naddition=\'\'\'    /** Keep technical release tags intact for comparison, downloads and ignored updates. */\n    fun displayLabel(raw: String?): String {\n        val normalized = normalize(raw)\n        return if (parse(normalized) != null) normalized.substringBefore(\'+\') else normalized\n    }\n\n\'\'\'\nif \'fun displayLabel(\' not in s:\n    assert s.count(anchor)==1;s=s.replace(anchor,addition+anchor,1)\np.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\np=ROOT/paths[1];s=p.read_text();old=\'        update.tag,\\n\';new=\'        VersionUtils.displayLabel(update.tag),\\n\'\nif new not in s:\n    assert s.count(old)==1;s=s.replace(old,new,1)\np.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n\n# This deliberately does not replace values in saved addon lists, sync envelopes,\n# Home catalog records or release models. A configured profile keeps its choices.\nprint(\'Prepared fresh-profile Omnia Catalog default and clean display-only version labels. Build/native rollout still gated.\')\n', "omnia-core-defaults-overlay", "exec"))
exec(compile('"""Catalog/hero follow-up on top of the preserved storage candidates."""\nfrom pathlib import Path\nimport re\n\nmobile=(ROOT/\'composeApp\').is_dir()\ndef write(path,text):\n    dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True)\n    dest.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n\nif mobile:\n    prefix=\'composeApp/src/commonMain/kotlin/com/nuvio/app/\'\n    path=prefix+\'features/details/MetaScreenSettingsRepository.kt\'\n    text=(ROOT/path).read_text()\n    # Missing/default values become on; explicitly stored false remains false.\n    text=text.replace(\'heroTrailerPlayback: Boolean = false\',\'heroTrailerPlayback: Boolean = true\')\n    text=text.replace(\'heroTrailerPlayback = false\',\'heroTrailerPlayback = true\')\n    write(path,text)\n    path=prefix+\'features/details/HeroTrailerAudioState.kt\'\n    text=(ROOT/path).read_text().replace(\'MutableStateFlow(true)\',\'MutableStateFlow(false)\')\n    write(path,text)\n    path=prefix+\'features/home/HomeCatalogSettingsRepository.kt\'\n    text=(ROOT/path).read_text().replace(\'const val HERO_SOURCE_SELECTION_LIMIT = 6\',\'const val HERO_SOURCE_SELECTION_LIMIT = 12\')\n    write(path,text)\n    path=prefix+\'features/home/HomeRepository.kt\'\n    text=(ROOT/path).read_text().replace(\'private const val HOME_COLLECTION_HERO_SOURCE_LIMIT = 6\',\'private const val HOME_COLLECTION_HERO_SOURCE_LIMIT = HomeCatalogSettingsRepository.HERO_SOURCE_SELECTION_LIMIT\')\n    write(path,text)\n    path=\'composeApp/src/iosMain/kotlin/com/nuvio/app/core/ui/PlatformImageLoader.ios.kt\'\n    text=(ROOT/path).read_text()\n    if not text.startswith(\'@file:OptIn(\'):text=\'@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)\\n\\n\'+text\n    write(path,text)\n    path=\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/home/HomeCatalogSettingsRepositoryTest.kt\'\n    text=(ROOT/path).read_text()\n    text=text.replace(\'omniaAllowsSixHeroCatalogsAndReplacingASelection\',\'omniaAllowsTwelveHeroCatalogsAndReplacingASelection\')\n    start=text.index(\'    fun omniaAllowsTwelveHeroCatalogsAndReplacingASelection()\')\n    end=text.index(\'    private fun addon()\',start)\n    # Replace the whole test deterministically; replay must not append assertions.\n    block=\'\'\'    fun omniaAllowsTwelveHeroCatalogsAndReplacingASelection() {\n        val base = addon()\n        val manifest = requireNotNull(base.manifest)\n        val catalogs = listOf(base.copy(\n            manifest = manifest.copy(catalogs = (1..13).map {\n                AddonCatalog(type = "movie", id = "catalog$it", name = "Catalog $it")\n            }),\n        ))\n        HomeCatalogSettingsRepository.syncCatalogs(catalogs)\n        val keys = HomeCatalogSettingsRepository.uiState.value.items.map { it.key }\n        assertEquals(12, HomeCatalogSettingsRepository.HERO_SOURCE_SELECTION_LIMIT)\n        keys.forEach { HomeCatalogSettingsRepository.setHeroSourceEnabled(it, false) }\n        keys.take(12).forEach { HomeCatalogSettingsRepository.setHeroSourceEnabled(it, true) }\n        HomeCatalogSettingsRepository.setHeroSourceEnabled(keys.last(), true)\n        assertEquals(12, HomeCatalogSettingsRepository.uiState.value.items.count { it.heroSourceEnabled })\n        assertTrue(!HomeCatalogSettingsRepository.uiState.value.items.last().heroSourceEnabled)\n        HomeCatalogSettingsRepository.setHeroSourceEnabled(keys.first(), false)\n        HomeCatalogSettingsRepository.setHeroSourceEnabled(keys.last(), true)\n        assertEquals(12, HomeCatalogSettingsRepository.uiState.value.items.count { it.heroSourceEnabled })\n        assertTrue(HomeCatalogSettingsRepository.uiState.value.items.last().heroSourceEnabled)\n        HomeCatalogSettingsRepository.onProfileChanged()\n        HomeCatalogSettingsRepository.syncCatalogs(catalogs)\n        assertEquals(12, HomeCatalogSettingsRepository.uiState.value.items.count { it.heroSourceEnabled })\n        assertTrue(!HomeCatalogSettingsRepository.uiState.value.items.first().heroSourceEnabled)\n        assertTrue(HomeCatalogSettingsRepository.uiState.value.items.last().heroSourceEnabled)\n    }\n\n\'\'\'\n    write(path,text[:start]+block+text[end:])\n    write(\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/details/OmniaHeroDefaultsTest.kt\',\'\'\'package com.nuvio.app.features.details\n\nimport android.app.Application\nimport android.content.Context\nimport org.junit.Before\nimport org.junit.After\nimport org.junit.Test\nimport org.junit.Assert.*\nimport org.junit.runner.RunWith\nimport org.robolectric.RobolectricTestRunner\nimport org.robolectric.RuntimeEnvironment\nimport org.robolectric.annotation.Config\n\n@RunWith(RobolectricTestRunner::class)\n@Config(sdk = [34], application = Application::class)\nclass OmniaHeroDefaultsTest {\n    @Before fun initialize() {\n        val context = RuntimeEnvironment.getApplication()\n        context.getSharedPreferences("nuvio_meta_screen_settings", Context.MODE_PRIVATE).edit().clear().commit()\n        MetaScreenSettingsStorage.initialize(context)\n        MetaScreenSettingsRepository.clearLocalState()\n    }\n    @After fun finish() { MetaScreenSettingsRepository.clearLocalState() }\n\n    @Test fun freshProfileEnablesTrailers() {\n        MetaScreenSettingsRepository.ensureLoaded()\n        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        assertTrue(MetaScreenSettingsStorage.loadPayload()!!.contains("\\\\"hero_trailer_playback\\\\":true"))\n    }\n    @Test fun olderPayloadWithoutTrailerSettingUsesDefaultAndKeepsOtherChoices() {\n        MetaScreenSettingsStorage.savePayload("""{"blur_unwatched_episodes":true}""")\n        MetaScreenSettingsRepository.onProfileChanged()\n        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        assertTrue(MetaScreenSettingsRepository.uiState.value.blurUnwatchedEpisodes)\n    }\n    @Test fun explicitOffSurvivesProfileReloadAndUnrelatedChanges() {\n        MetaScreenSettingsRepository.setHeroTrailerPlayback(false)\n        MetaScreenSettingsRepository.setShowOverallRatings(false)\n        MetaScreenSettingsRepository.onProfileChanged()\n        assertFalse(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        assertFalse(MetaScreenSettingsRepository.uiState.value.showOverallRatings)\n    }\n    @Test fun resetRestoresDefaultButDoesNotChangeRetainedPayload() {\n        MetaScreenSettingsRepository.setHeroTrailerPlayback(false)\n        val before = MetaScreenSettingsStorage.loadPayload()!!\n        MetaScreenSettingsRepository.resetToDefaults()\n        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        MetaScreenSettingsStorage.savePayload(before)\n        MetaScreenSettingsRepository.onProfileChanged()\n        assertFalse(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n    }\n}\n\'\'\')\n    write(\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/details/OmniaHeroAudioStateTest.kt\',\'\'\'package com.nuvio.app.features.details\n\nimport kotlin.test.Test\nimport kotlin.test.assertFalse\nimport kotlin.test.assertTrue\n\nclass OmniaHeroAudioStateTest {\n    @Test fun defaultIsAudibleAndExplicitMuteCanBeToggledBack() {\n        assertFalse(HeroTrailerAudioState.muted.value)\n        HeroTrailerAudioState.toggleMuted()\n        try { assertTrue(HeroTrailerAudioState.muted.value) }\n        finally { HeroTrailerAudioState.toggleMuted() }\n        assertFalse(HeroTrailerAudioState.muted.value)\n    }\n}\n\'\'\')\n    write(\'iosApp/Configuration/Version.xcconfig\',\'CURRENT_PROJECT_VERSION=28\\nMARKETING_VERSION=0.4.20\\n\')\n    path=\'prepare_omnia_ios_tests.py\'\n    text=(ROOT/path).read_text().replace(\'Version 0.4.19 (27)\',\'Version 0.4.20 (28)\').replace(\'Version 0.4.18 (26)\',\'Version 0.4.20 (28)\')\n    write(path,text)\nelse:\n    path=\'app/src/main/java/com/nuvio/tv/data/local/LayoutPreferenceDataStore.kt\'\n    text=(ROOT/path).read_text()\n    # Playback enablement and the user\'s audio choice are independent preferences.\n    text=text.replace(\'                prefs[focusedPosterBackdropTrailerMutedKey] = true\\n\',\'\')\n    write(path,text)\n    write(\'app/src/test/java/com/nuvio/tv/data/local/OmniaHeroPreferencesTest.kt\',\'\'\'package com.nuvio.tv.data.local\n\nimport androidx.datastore.preferences.core.booleanPreferencesKey\nimport com.nuvio.tv.TestPreferencesStore\nimport com.nuvio.tv.core.profile.ProfileManager\nimport io.mockk.every\nimport io.mockk.mockk\nimport kotlinx.coroutines.flow.MutableStateFlow\nimport kotlinx.coroutines.flow.first\nimport kotlinx.coroutines.runBlocking\nimport org.junit.Assert.*\nimport org.junit.Test\n\nclass OmniaHeroPreferencesTest {\n    private fun preferences(): Pair<LayoutPreferenceDataStore, TestPreferencesStore> {\n        val store = TestPreferencesStore()\n        val profiles = mockk<ProfileManager>()\n        every { profiles.activeProfileId } returns MutableStateFlow(1)\n        every { profiles.profiles } returns MutableStateFlow(emptyList())\n        val factory = mockk<ProfileDataStoreFactory>()\n        every { factory.get(1, "layout_settings") } returns store\n        return LayoutPreferenceDataStore(factory, profiles) to store\n    }\n    @Test fun freshProfilePlaysHeroTrailersWithAudio() = runBlocking {\n        val (prefs, _) = preferences()\n        assertTrue(prefs.focusedPosterBackdropTrailerEnabled.first())\n        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())\n    }\n    @Test fun disablingAndReenablingTrailersKeepsAnAudibleChoice() = runBlocking {\n        val (prefs, store) = preferences()\n        prefs.setFocusedPosterBackdropTrailerMuted(false)\n        prefs.setFocusedPosterBackdropTrailerEnabled(false)\n        prefs.setFocusedPosterBackdropTrailerEnabled(true)\n        assertTrue(prefs.focusedPosterBackdropTrailerEnabled.first())\n        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())\n        assertFalse(store.value[booleanPreferencesKey("focused_poster_backdrop_trailer_muted")]!!)\n    }\n    @Test fun explicitMuteSurvivesTrailerAndExpansionToggles() = runBlocking {\n        val (prefs, _) = preferences()\n        prefs.setFocusedPosterBackdropTrailerMuted(true)\n        prefs.setFocusedPosterBackdropTrailerEnabled(false)\n        prefs.setFocusedPosterBackdropTrailerEnabled(true)\n        prefs.setFocusedPosterBackdropExpandEnabled(false)\n        prefs.setFocusedPosterBackdropExpandEnabled(true)\n        assertTrue(prefs.focusedPosterBackdropTrailerMuted.first())\n    }\n    @Test fun disablingExpansionDoesNotOverwriteAnAudibleChoice() = runBlocking {\n        val (prefs, _) = preferences()\n        prefs.setFocusedPosterBackdropTrailerMuted(false)\n        prefs.setFocusedPosterBackdropExpandEnabled(false)\n        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())\n    }\n}\n\'\'\')\n    path=\'app/build.gradle.kts\';text=(ROOT/path).read_text()\n    text,n=re.subn(r\'versionCode = \\d+\',\'versionCode = 27\',text,count=1);assert n==1\n    text,n=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.21"\',text,count=1);assert n==1\n    write(path,text)\n\nprint(\'Prepared next catalog/hero candidate with saved-choice preservation; compilation/runtime/release remain gated.\')\n', "omnia-major-catalog-hero-overlay", "exec"))
exec(compile('"""Use the existing Omnia account portal without duplicating account storage."""\nmobile=(ROOT/\'composeApp\').is_dir()\ndef write(path,text):\n    path=ROOT/path;path.parent.mkdir(parents=True,exist_ok=True)\n    path.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n\npackage=\'com.nuvio.app.features.auth\' if mobile else \'com.nuvio.tv.ui.screens.account\'\npolicy=\'\'\'package PACKAGE\n\n/** Fixed public account entry points. Never carries app credentials or session tokens. */\ninternal object OmniaAccountPortal {\n    const val ORIGIN = "https://omnia.161.97.128.244.sslip.io"\n    const val ACCOUNT_URL = "$ORIGIN/discord-account/"\n    const val SIGNUP_URL = "$ORIGIN/account/signup"\n    const val RECOVERY_URL = "$ORIGIN/account/recover"\n\n    fun availableFor(backendUrl: String): Boolean =\n        backendUrl.trim().trimEnd(\'/\').equals(ORIGIN, ignoreCase = true)\n}\n\'\'\'.replace(\'PACKAGE\',package)\npath=(\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/auth/\' if mobile else \'app/src/main/java/com/nuvio/tv/ui/screens/account/\')\nwrite(path+\'OmniaAccountPortal.kt\',policy)\n\nif mobile:\n    file=path+\'AuthScreen.kt\';text=(ROOT/file).read_text()\n    old=\'\'\'        // Omnia currently uses a single pre-provisioned private account.\n        // Public signup is disabled on the server and is not offered here.\'\'\'\n    if \'        OmniaAccountPortalLinks(enabled = !isLoading)\' not in text:\n        assert text.count(old)==1\n        text=text.replace(old,\'        OmniaAccountPortalLinks(enabled = !isLoading)\',1)\n    write(file,text)\n    write(path+\'OmniaAccountPortalLinks.kt\',\'\'\'package com.nuvio.app.features.auth\n\nimport androidx.compose.foundation.layout.Arrangement\nimport androidx.compose.foundation.layout.Column\nimport androidx.compose.foundation.layout.Row\nimport androidx.compose.foundation.layout.fillMaxWidth\nimport androidx.compose.foundation.layout.padding\nimport androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.Text\nimport androidx.compose.material3.TextButton\nimport androidx.compose.runtime.Composable\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.setValue\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.platform.LocalUriHandler\nimport androidx.compose.ui.unit.dp\nimport androidx.lifecycle.compose.collectAsStateWithLifecycle\nimport com.nuvio.app.core.network.ServerConfigurationRepository\n\n@Composable\ninternal fun OmniaAccountPortalLinks(enabled: Boolean) {\n    val server by ServerConfigurationRepository.active.collectAsStateWithLifecycle()\n    if (!OmniaAccountPortal.availableFor(server.backendUrl)) return\n    val handler = LocalUriHandler.current\n    var fallbackUrl by remember { mutableStateOf<String?>(null) }\n    fun open(url: String) {\n        fallbackUrl = if (runCatching { handler.openUri(url) }.isSuccess) null else url\n    }\n    Column(modifier = Modifier.fillMaxWidth()) {\n        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {\n            TextButton(enabled = enabled, onClick = { open(OmniaAccountPortal.SIGNUP_URL) }) { Text("Create account") }\n            TextButton(enabled = enabled, onClick = { open(OmniaAccountPortal.RECOVERY_URL) }) { Text("Forgot password?") }\n        }\n        TextButton(enabled = enabled, onClick = { open(OmniaAccountPortal.ACCOUNT_URL) }) { Text("Google or Discord account") }\n        Text(\n            "Set an Omnia app password in Account, then use the same email and password on every device.",\n            modifier = Modifier.padding(horizontal = 12.dp),\n            style = MaterialTheme.typography.bodySmall,\n            color = MaterialTheme.colorScheme.onSurfaceVariant,\n        )\n        fallbackUrl?.let { url ->\n            Text("Open in a browser: $url", style = MaterialTheme.typography.bodySmall)\n        }\n    }\n}\n\'\'\')\nelse:\n    file=path+\'AccountViewModel.kt\';text=(ROOT/file).read_text()\n    anchor=\'    internal val preferencesSyncState = omniaPreferences.state\'\n    if \'internal val hasOmniaAccountPortal:\' not in text:\n        assert text.count(anchor)==1\n        text=text.replace(anchor,\'    internal val hasOmniaAccountPortal: Boolean = OmniaAccountPortal.availableFor(serverConfiguration.backendUrl)\\n\\n\'+anchor,1)\n    write(file,text)\n    file=path+\'AuthQrSignInScreen.kt\';text=(ROOT/file).read_text()\n    for imp in [\'import androidx.compose.foundation.rememberScrollState\',\'import androidx.compose.foundation.verticalScroll\']:\n        if imp not in text:text=text.replace(\'import androidx.compose.runtime.Composable\',imp+\'\\nimport androidx.compose.runtime.Composable\',1)\n    if \'                hasOmniaAccountPortal = viewModel.hasOmniaAccountPortal,\' not in text:\n        anchor=\'                onSignIn = viewModel::signIn,\';assert text.count(anchor)==1\n        text=text.replace(anchor,\'                hasOmniaAccountPortal = viewModel.hasOmniaAccountPortal,\\n\'+anchor,1)\n    anchor=\'    useEmailLogin: Boolean,\\n    needsServer: Boolean,\\n\'\n    if \'    hasOmniaAccountPortal: Boolean,\\n\' not in text:\n        assert text.count(anchor)==1;text=text.replace(anchor,anchor+\'    hasOmniaAccountPortal: Boolean,\\n\',1)\n    text=text.replace(\'modifier = modifier.padding(horizontal = 48.dp),\',\'modifier = modifier.verticalScroll(rememberScrollState()).padding(horizontal = 48.dp, vertical = 24.dp),\',1)\n    anchor=\'\'\'                initialFocusRequester = initialFocusRequester\n            )\n        } else {\n            AuthQrCodeBlock(uiState = uiState)\'\'\'\n    replacement=\'\'\'                initialFocusRequester = initialFocusRequester\n            )\n            if (hasOmniaAccountPortal) OmniaTvAccountPortalLink(enabled = !uiState.isLoading)\n        } else {\n            AuthQrCodeBlock(uiState = uiState)\'\'\'\n    if replacement not in text:\n        assert text.count(anchor)==1;text=text.replace(anchor,replacement,1)\n    write(file,text)\n    write(path+\'OmniaTvAccountPortalLink.kt\',\'\'\'@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)\n\npackage com.nuvio.tv.ui.screens.account\n\nimport androidx.compose.foundation.layout.Column\nimport androidx.compose.foundation.layout.Spacer\nimport androidx.compose.foundation.layout.fillMaxWidth\nimport androidx.compose.foundation.layout.height\nimport androidx.tv.material3.MaterialTheme\nimport androidx.tv.material3.Text\nimport androidx.compose.runtime.Composable\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.setValue\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.graphics.Color\nimport androidx.compose.ui.platform.LocalUriHandler\nimport androidx.compose.ui.unit.dp\nimport androidx.tv.material3.Button\n\n@Composable\ninternal fun OmniaTvAccountPortalLink(enabled: Boolean) {\n    val handler = LocalUriHandler.current\n    var browserUnavailable by remember { mutableStateOf(false) }\n    Column {\n        Spacer(Modifier.height(10.dp))\n        Button(\n            enabled = enabled,\n            modifier = Modifier.fillMaxWidth(),\n            onClick = { browserUnavailable = runCatching { handler.openUri(OmniaAccountPortal.ACCOUNT_URL) }.isFailure },\n        ) { Text("Account options") }\n        Spacer(Modifier.height(6.dp))\n        Text(\n            "Create an account, reset your password, or set an app password for a linked Google or Discord account.",\n            style = MaterialTheme.typography.bodySmall,\n            color = Color(0xFF969CA3),\n        )\n        if (browserUnavailable) Text(\n            "Open in a browser: ${OmniaAccountPortal.ACCOUNT_URL}",\n            style = MaterialTheme.typography.bodySmall,\n            color = Color(0xFF969CA3),\n        )\n    }\n}\n\'\'\')\n\ntests=\'\'\'package PACKAGE\n\nIMPORTS\n\nclass OmniaAccountPortalTest {\n    @Test fun acceptsOnlyTheExactOmniaBackend() {\n        assertTrue(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN))\n        assertTrue(OmniaAccountPortal.availableFor("  " + OmniaAccountPortal.ORIGIN + "/  "))\n        assertFalse(OmniaAccountPortal.availableFor("http://omnia.161.97.128.244.sslip.io"))\n        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + ".example.com"))\n        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + "@example.com"))\n        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + "?redirect=example.com"))\n        assertFalse(OmniaAccountPortal.availableFor("https://custom.example.com"))\n    }\n    @Test fun accountLinksHaveNoCredentialsOrSessionParameters() {\n        assertTrue(OmniaAccountPortal.ACCOUNT_URL == OmniaAccountPortal.ORIGIN + "/discord-account/")\n        assertTrue(OmniaAccountPortal.SIGNUP_URL == OmniaAccountPortal.ORIGIN + "/account/signup")\n        assertTrue(OmniaAccountPortal.RECOVERY_URL == OmniaAccountPortal.ORIGIN + "/account/recover")\n        listOf(OmniaAccountPortal.ACCOUNT_URL, OmniaAccountPortal.SIGNUP_URL, OmniaAccountPortal.RECOVERY_URL).forEach {\n            assertFalse(\'?\' in it || \'#\' in it || \'@\' in it)\n        }\n    }\n}\n\'\'\'.replace(\'PACKAGE\',package)\nif mobile:\n    tests=tests.replace(\'IMPORTS\',\'import kotlin.test.Test\\nimport kotlin.test.assertTrue\\nimport kotlin.test.assertFalse\')\n    write(\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/auth/OmniaAccountPortalTest.kt\',tests)\nelse:\n    tests=tests.replace(\'IMPORTS\',\'import org.junit.Test\\nimport org.junit.Assert.assertTrue\\nimport org.junit.Assert.assertFalse\')\n    write(\'app/src/test/java/com/nuvio/tv/ui/screens/account/OmniaAccountPortalTest.kt\',tests)\nprint(\'Prepared shared-account registration/recovery entry points; existing native sessions and authentication backend unchanged.\')\n', "omnia-account-entrypoints-overlay", "exec"))
exec(compile('"""Keep remote focus in Account when temporary sync actions disappear."""\nif not (ROOT/\'composeApp\').is_dir():\n    path=ROOT/\'app/src/main/java/com/nuvio/tv/ui/screens/account/AccountSettingsContent.kt\'\n    text=path.read_text()\n    start=text.index(\'private fun OmniaPreferencesSyncSettings(viewModel: AccountViewModel) {\')\n    before,block=text[:start],text[start:]\n    anchor=\'    val state by viewModel.preferencesSyncState.collectAsStateWithLifecycle()\\n\'\n    if \'val syncControlFocus = remember { FocusRequester() }\' not in block:\n        assert block.count(anchor)==1\n        block=block.replace(anchor,anchor+\'\'\'    val syncControlFocus = remember { FocusRequester() }\n    fun fromStableControl(action: () -> Unit) {\n        // The clicked choice/manual action is removed during synchronization.\n        // Move focus before it leaves the tree, keeping DPAD navigation in this panel.\n        syncControlFocus.requestFocus()\n        action()\n    }\n\'\'\',1)\n    anchor=\'            onClick = { if (state.enabled) viewModel.disablePreferencesSync() else if (state.status != SharedPreferencesSyncStatus.Syncing) viewModel.enablePreferencesSync() },\\n\'\n    if \'            modifier = Modifier.focusRequester(syncControlFocus),\' not in block:\n        assert block.count(anchor)==1\n        block=block.replace(anchor,anchor+\'            modifier = Modifier.focusRequester(syncControlFocus),\\n\',1)\n    for choice in [\'UseSavedSettings\',\'UseThisDevice\']:\n        old=\'{ viewModel.enablePreferencesSync(SharedPreferencesInitialChoice.\'+choice+\') }\'\n        new=\'{ fromStableControl { viewModel.enablePreferencesSync(SharedPreferencesInitialChoice.\'+choice+\') } }\'\n        if new not in block:\n            assert block.count(old)==1;block=block.replace(old,new,1)\n    for method in [\'cancelPreferencesChoice\',\'synchronizePreferences\']:\n        old=\'viewModel::\'+method+\')\';new=\'{ fromStableControl(viewModel::\'+method+\') })\'\n        if new not in block:\n            assert block.count(old)==1;block=block.replace(old,new,1)\n    old=\'"Keep this device’s settings separate.", viewModel::disablePreferencesSync)\'\n    new=\'"Keep this device’s settings separate.", { fromStableControl(viewModel::disablePreferencesSync) })\'\n    if new not in block:\n        assert block.count(old)==1;block=block.replace(old,new,1)\n    path.write_text(before+block,encoding=\'utf-8\',newline=\'\\n\')\n    print(\'Prepared stable TV account-sync focus before temporary action removal; native recheck required.\')\n', "omnia-tv-account-focus-overlay", "exec"))

exec(compile("# Security transport and shared mobile tools, reviewed as a single prepared candidate.\n# Each file is captured from the tested source tree; this preserves existing player/settings behavior.\nimport base64,gzip\n_omnia_security_files = {'app/build.gradle.kts': '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', 'app/src/main/java/com/nuvio/tv/core/di/NetworkModule.kt': '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', 'app/src/main/java/com/nuvio/tv/core/network/OmniaHttpSecurity.kt': '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', 'app/src/main/java/com/nuvio/tv/core/player/OpenSubtitlesHasher.kt': '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', 'app/src/main/java/com/nuvio/tv/core/player/SubtitleFileCache.kt': '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', 'app/src/main/java/com/nuvio/tv/ui/screens/player/PlayerMediaSourceFactory.kt': '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', 'app/src/main/java/com/nuvio/tv/ui/screens/player/PlayerPlaybackNetworking.kt': 'H4sIAAAAAAACCs1XTXMiNxC9+1eofBqqZlXleDcHKt4EA463FgPFRy6pFCWGBmvRSBNJg83u8t/TQgPzhfG6kkPmwtSoX6v1+nW3SFi0ZisgkYqpTDdcUbuhKacm0gDS0ESwLeiLCx4nSlvC5EIrvnimMSw4u6YIi5WkqeWCTqWxbC6glfCXzBfMMqNSHQHt4Ot4//ojxrBkqbBvwqj1o7UJHazv8aeOLB04UhqoBPuk9Jp+Gm7e33FtbEea162HSNAcSRyraA32jkVW6e3rsEEsOXORjSFKNbdHiA/7Oou7LThIe1j7wjbMeaBuaTrqtZWUEFmuZMlin41ISXSsEU0nPIap5BazKC1oyQRR8y8IJMN9dg9H6PvYuFyRbxcEn0TzDbNOHJhaskFcbzAY3rban2ejbqszm3x66A6mk9m42x70O2NyQ37+0LvYQ487OVSSbZCfqEmK5yPzLRHs6zbb1j0OtuAmYTZ6BI2eD7x0jh+DBmVJIooo98TseQR/p2CscQG9f2lxCPpe4bFuyPVPR5vd8a0YH71NuVi4HUvOaB5gkL9WbaQJiooKGhUDUxROcFJOFQRsMKYeNxYk6Cow10TXmZkKNtHKqkgJEwh0MFgGB16H2QK9n0yGs6vZVTXOyDt2YlKpDa4+hOQgLJoJoILQwBZvMH/CMoA32C+VEOpphIWvMS4TWJ3CSZOxEWetNFi9HcicuTvGRarhlK0AG9Rqt9l0tCK2Yjx3sslEs/N1sUwlwdaKVZXLKziiFr7P3SNxoE2TPLDkl7HVWJEh8b8fUa8QJ3aLS0EjPCJTAz0lV6Oc8ia5VUoAk4hYMmEgN/YdcqpFM/P6K9rIVAhv0qhUZ7kq574WEFEva2xOT/Va4UsS1ONrVOo281tSzdl2c04ghTquJgtHm0ogyLYLczLCCv25NxRIquUhwpogyDfSd02++6yyhgp6qXTMZAT3IBI81L5RZf11kFge86/MKc0EHInYvSqb34rDta6jfLwd2sH/T1J5jDQLsiIs7RtzFinCy6HTmCV9ZfvoEwkPNHv6DNuQ4O8fTGCdkncfSzQ6l2vYoh9vSjGsuNLBN35ApeCt9o5O2TkFoy/KTdcRFTTI9+8eWP7kbPAUSE1wOWJyBZch4SuJg7/NjNtk31GqynePo6r0cUcACT5h6c5kld+9jMjVT63aJ7PEb+Sr+abef8rMhycyXyiTslM3PA7pvCHVy9Yh04Hf+/TANmCz+102mnEUYc1YDqYSWT0p5XUqlUTKCHaEYiamBvS71goDOJkOsjuVEIzK4fawwJf1g7tjlsqMdrp3rWlvMpuOu6NZ6/duf9J4KSfVbtJTqxXWSb10C5SG5NKN48sf7QVn+gCObwvPWMLZlZnuP2DLbvuF8D/oGP+yCWTE1C77uYqyUM92vnL4BeFiLLmIa0MZJVe4AeS8pflp8oM+nuEmt4rBPqpFHV2+ST2gm0+ywH9hANbXXFOpsnsgt/avoNJgY9ArWCAoC991iXSvpHKzcIXlbV0ZFavqZEUdi8hj/iyu/oW7vaF4qlKoD+9KmlI3tv2+YcZ3WOM3LFMaehYPCthd/AOa8h+HBA8AAA==', 'app/src/main/java/com/nuvio/tv/ui/screens/player/PlayerRuntimeControllerInitialization.kt': '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', 'app/src/main/java/com/nuvio/tv/ui/screens/player/PlayerRuntimeControllerSubtitleTiming.kt': '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', 'app/src/test/java/com/nuvio/tv/core/di/OmniaAddonNetworkSecurityTest.kt': 'H4sIAAAAAAACCo1VTXPTMBC951cYn2wmETDcWspQAgwcoEwa4NKZjiptiBpZCtq1k0wn/52V8mUnfFQHO5ZWb9/uvt3MpZrJn5ApXwlXN8YLaoTyAYQ2vZ6p5j5QJp0O3mjedwSOxDC+l7Q75kuVV7OZgAbC6mQ3PXe7fjYlmr8UV7OP/B5aw3jHZyP4VQOebEecBdwhBHYjPvPXCHDuHcL/LX/A3XX6OjYli+Ijx4dTOYMhBDIToyQB/tEQrG7Z7E3CT3FfO0PiEtkniaenJ+NWQPeykYLT8+nq/VLBnIx3nSPHZxNjQXzgB/Z6ykrE7KpyRl5q7d0XoIUPs2tQdTC0itDZQy/j9Sb9ntQuk9Fwk94R3IMi/OYo1EigxxYvnb5ydjUCMgFwPIWvECqDaBoYSjWFotwCxtVIm2m2U+TD6iJxEioAJ2AM1fzd7qTIfWQ4SJ4HKsIMOI+Ul4J8vFWUHUi1EdFFkserraReF+V5UlH2sDMQCYrdZOssANXB4YHOHnG/Izggbxso8kTkNlbvNkEwkWrGdi0ej7j1zFs9CFuhMcSCU86BL6nIa8dxGM2J0NnELJkaG/wTWylfOxrMeSeqUXfxTjFSnlIRL7ZF/+x1zcqYB98YDUkO33ck2j1VbLPX72yWB2iKOd5/xSWTeD9Ii1A8Lp2wNEjYRj3gvP9VM9IhqP4j88HC0ikd/0Q9JnO7r8Rt8yLvb3K2Uc6TJ+Lg2skKurgxxRbk5OKoucXb2lgNrBYee1XFXcdXi9x6Je3UJ1kziev6LjbXpSUIThL3z6nZXQQqul47M4ld1AiseMwGrztmcWE8jDXE4o+DqkV02g2hiHHt/QtEe81ugUu8adiyP4nFLs9RIMlARxw3zsHxMK6haM/bCAb01mtu+oeb3Oib/Owmj81+k6/z8hRmU7zxNPgFFq2xd3aWZpuIY6+MLb+pm4PFUFpbbP8IWhHWwRaYnvmzSjozicf36B173QUadcmjkSJNZX2km63/Qmmrp+d9ZOElZ8OoyG4Eh8tr7nPHzFYHrjuNbT2dH7SmwQLBKE7pOFjtas9j3Vv3fgOxuHn7eQcAAA==', 'app/src/test/java/com/nuvio/tv/core/network/NoDelaySocketFactoryTest.kt': 'H4sIAAAAAAACCrVWW2/bNhR+96/ghD3IgEs73fZirN2cNEOLBXEQu28FVpo6sRlTpMKLUy/wf9+hLpbkyHG2YgR0wSHP9TsXZoyv2RII1ylVfiM0dRvKtQGqwD1qs+71RJpp49onvKCWGwBlaSbZFgy9yT/hvUCR1wWzUMuKXa9XzmU/0Qsm5TOaVgq4E1od7lxuQLkrYR0oMIeb0/VH/F5IgWcO927hwYOtyWZJ770Sjk6sBeMoyz+XD55Je+LQjKVw4sjc+I4j84YB92zDQkjpJ3xNksSAtc/2ZmA2YGaar6HN6J2QiIri3hh0ls5FCp9RxYuHmNOp4HSSf27hDpDK92autZNCNc+7lQGW9HpcolPkWn8ABLMw5g/GnTbb4BB56vUIrt9z78LfnVfkq1e8ABESYnMesmKWKE2SIOZr3EdGUq4u2RTTiTkoaHGfegvkidThjTGgjmcla5/scmm7TmMOTbFoywaOGNMMejwakJ8HpIERXYK70joLSV2S4n5lnc1ZyZv3e2FhbZgksmQh704Ka/GejkwleVBqp1JzJm8Q0tfG7N/roittKx++T+9LqBWlS/i+GZxOpP8Fu9C4cOcdKQqioa5aZQQY55DVuVpaeyCxKVmozDsUXJwM5n0KlJlDPSnKWfi7UKXJLaoFc5Aa1XpcCQkk/iEXRoOFV0IBcgt77aWcmss0c1t0lOQdoktErX/qXdMAlmVy2+HwXrcRDuLo43x+MzyjZ+TtaESmf34xXxS2cOzR7s0VqKVbjcnbklhCOSZcaguBGB69jqjT51sHE2NYMPaoyjvp7epIKHa9lym7Z9iqIiURg4O2+Ou51hKYen+gKjDxfMIgT3Pg0HMvZDdK1DZLKu6qsw4maI66WC/uMXJkTFoTsJX8zaUxH41IIK+kuoIm/MELTKgYS1WOSZi9g8Y2Uvb//RdgL6NGLVZZzV26iWnTqPXX4tQRgGBjGGzau/gMi7kacnR2eTG9/jDrYFkEDDoQ80YiXFHoJ+Ph8MensmBFozc0WtpuvD+xb2q7YdSSWuQATunHEMS4vF7USUBRZYxPv7KpT+EbcO/gYJYVV444whIYEHRuoZPtb9Q6g3elULTtWBW9iN5roeJf/hqNRm1fWyIddt7BHqtlQKb/qsablZe20klLmEqw+YEwmCuZAEuCA8K1e299OYqrW18rxQfk2JWQVgob1WS7q+M7lBSTrFYRpyyb3sXRxLuVNuJvFnI4Ik6T6FvUx7GmveHwuc4ci6mTQiIYIsnSTMJwgxWmo/4xYzst/K/3ml3vH6BGQQ+bCwAA', 'app/src/test/java/com/nuvio/tv/ui/screens/player/Http1OnlyTest.kt': 'H4sIAAAAAAACCo2QwW7CMAyG73kKH1tpsoR2nrQNIXGilcYdQnAhaxpnScrGJt59TVcQg0ksF0f2b/v356Sq5YZAcYO23WnGuMNWY1CeyAZ0Ru7JC6Ebxz4C19sY3T0W9bSLY6PJxsta6TmyYnPK+w2+tlZHfAqBfETZh8lbK024IXqRDV1L5hSiEMp0Gkg+RoU1+5SELyGge4+9Iv2q1sIyHbHqDgXVGw4QHMkakl0YLUbAXfsyy7tuGN5OmkEMDzBLXCYfXPYsSvIV+0ZaRVMyjjxK58x+RvGdfV24qBv9KaNmG7JzTPjcarMmn+U5rtI3y0/rzolkRodYVNkRI07n83LR2czvBkvohlK4nJBwZbfshq30tB6ztaSSzZLZnEarX+mf+Yc/oa5kILgiK+0a4pYgmgCVNKYv3sT93/uHk4alA3JtN3j0cYb7AtJBHMQ3rs4khu0CAAA=', 'app/src/test/java/com/nuvio/tv/ui/screens/player/OmniaPlaybackSecurityTest.kt': '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', 'app/src/test/java/com/nuvio/tv/ui/screens/player/PlaybackNetworkingSslVerificationTest.kt': 'H4sIAAAAAAACCo2SzW7CMBCE736KcAtVZaWqOBQJqQi14sKPRNr7Nixg4tipvU6LKt69JiE0gNLWl1jamW92N84hSWGNQaIzrlwhNKeCO8FtYhCV5bmEHRrGRJZrQ4FON0T5PZ+lY/8dSYGKTjWz5lunBPGhtWiI31xXYrTEWCLB2mDu0W8+for0oU0q1Hph5SsasRIJkNDqIA6+WODPY3lfORXkR9eLRRtv0ENopU021pYUZFj50QzVMjbO0gSUH8+E3SPocAqQgfIekIPmHGH3TFEHDeblCq675bWisYoaAOUGFr6hsErim4sGb08BV6XuBWaqaeqkrEmfveihOVub/MT/y/D07kDaNnyn0++XP4xvoYDbVuq5riXjrhdF0Q8j0UphQrHIUDuaCCmF/Z/TICx/tfnWMGzIyexmalTl+bf1DEI6g5Vrz/bsG199aagJAwAA', 'app/src/test/java/com/nuvio/tv/ui/screens/player/SubtitleCredentialScopeTest.kt': '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'}\nfor _name,_encoded in _omnia_security_files.items():\n    _target=ROOT/_name\n    _target.parent.mkdir(parents=True,exist_ok=True)\n    _target.write_bytes(gzip.decompress(base64.b64decode(_encoded)))\nprint('Prepared strict TLS, provider-origin credential scope and tested settings tools.')\n", "omnia-security-tools-candidate-overlay", "exec"))

exec(compile('import re\np=ROOT/\'app/build.gradle.kts\';s=p.read_text()\ns,n=re.subn(r\'versionCode = \\d+\',\'versionCode = 28\',s,count=1);assert n==1\ns,n=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.22"\',s,count=1);assert n==1\np.write_text(s,encoding=\'utf8\',newline=\'\\n\')\n', "omnia-security-release-version", "exec"))

exec(compile('import base64,gzip,sys,subprocess,re\nfrom pathlib import Path\n_omnia_device_files={\'apply_native_signin.py\': \'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\', \'native/tv/OmniaAuthLogPrivacy.kt\': \'H4sIAAAAAAACCrWTW2/TQBCF3/0rBgu1dmRtSFVxsVSFlAYJCQJqmmc0WU+cbdc7y14SpKr/nY1VlzwUeGJfbNlzznxzPLYo77AlkNwJE3eKRdgJyY4ExrDNsvFoBLN0B8rYGHwFjrxl4wnW3CjygKYB+inJBsUGOvI+2Xnoog9gaEcuKVBuQXMrMQgYjbP3y2ht8vFFvlqslvOr799m17Mv85v5dV5mygRyBjXw+pZkgK+dUXhA+Mwt3GeQziYaaIqAbQ3L4JRpq6Hx8KCs4ZMJcAGvngT7vwoqIOfY1XCzdbzHtaZpUpuo9WDVGx1OmtixakQMSosEJXrnCvKZlBxTKVty2MexR2eSeQ0v7w9xfkSlo6MPGtPsfb/yIU08ENJ/I6Q/Em4SEjX/AHzIfn+VA+jzpcdk5UCdEPuXU3GLO+yrp8KrzmpaYEcwrSGPxluSaqOoyZ/pdKWwNeyDkiurGRs/05r31BTrtLtkmqOATGM56Y+24JJZE5rHcIYCofyCw6VGc1eUcHICLx69RNJ1Rdlf5qYpTsenpaAfEbUvnuLNtyFYX4/HfFhNMXk9Ee/eiMnZW3F2fi6818oKxXkFKnGniDD9LRcQXKSq9yizXxHkO5x2AwAA\', \'native/tv/OmniaAuthLogPrivacyTest.kt\': \'H4sIAAAAAAACCqVS22oCMRB9369Y9mkX2ogivUGh4gUKvUi1z2XIjmtqNkkziVVK/72JtiIqWDAvCbtnzjkzcwzwGVSYcl0z5edCMzdnXFtk4N00SURttHWpthV790o41iFC6xisrv6HB0lHQIMAwSOYsfUHIGMklyRcBkz6XCsBneDpQVdDK+bAl/F3+pWk4dyt3hOvUh1xPY30pN2rkRrKWITKCQ5OaDWEZfxIefFbGs+W0Tz23RNQKU2hZk1BHSn1J5Z5NnXO0E2jsZJhzYsmu75kzdYVa7XbjEgKw4RuZGfpBmkxdkUMF1AbiUyoOUhRZkVxgjz35MLGdjmD7D5vnO3JtP/s5ntnG1F2AEJ6iyNf12CX/QWXvkR6RKIQPOqosgue8NBC1vHKs3spsQI5cuAw1KOJiwyutti7MST5QWCeAedB7c3pGapbE8Pj8Dz49hhIXnzIRr0NV1px3MEVxd5c/9x5RQa5mAgsD3lSXsrNdL6TH0VssHVxAwAA\', \'native/tv/OmniaDeviceLoginUrl.kt\': \'H4sIAAAAAAACCmVRXWvbMBR9D+Q/XERYrSyRl1K6NWBK25USKA2028vGHhT51tGqSJ4+vI20/33XSbxuiTC20dE59+icWqonWSEotxI2NdqJ2IikRVAe0QYhlXLJxn6v38uHQ5hb8xviEqFOC6MVhKXzkcglKXgXAgbQNjqQsPDuZ0Av4BOdLrHRCsE6276xQQ+lwyBgmPd7REBvpQG3+I4qwnxltfy4Ydy6StvP3sC63wNaytkQoaGz8/vZzewOCmDLGOswzXPX0sTkdCLO3ovJ8QdxfHIiQjC6Ftqxff7lxcN1yx5shfJSB+V8Od7dNzfaPu1Ij8mCDhtX2YLiQltO4SF6bSs+hUvnDEpLWjtMELLK+OZzbcvsKD/iAn8kaUK2HTYCXVnn8UoGJF70CfnrKApeRswShXdFuXajRlB71+gSfbdzzru/Lp52tZfb9FFAJyFSXaNXNI1seayNVJixMRsBY/yV6cmk9pjdY4W/Mvb1Yvzl3fjs2/r0hXGxklEtMWStNOewBjazNEqXXbctwODlUK6zDUUBNhkDz8/w7x6rnKsMcff3d5UcAriS2rD/THT4noOYvKWO27LPW4PFYGvzLehHOHDGKQ9AQ6WwNx1WDP5Kb4VJn54/IbDbSjcDAAA=\', \'native/tv/OmniaDeviceLoginUrlTest.kt\': \'H4sIAAAAAAACCq1U32/aMBB+R+J/sPKAQNuMtLEXVLZRxiakaiDKtGfXOZJbHDuznZSp6v++MylrRCNWjUZJJOd+fN/dd5dCyEwkwKTJuS4rNNxXvETupAXQjgspTal9t9PtYF4Y61lmvELNPTjPN/RqNQjnwPr5r1Iod8LhC5nhpB2V+4E+PeGzsSUEelLRmS1zjeIzVCjhyiSov1sVSLK7bofR9Wl/2Jaa3VhzS+FrkIAVuKVWvzcpXKcEMjMxTHU8VcrcKnQe4pU1FcZg+4NDonA1i+y3APPL6fWcvWLRR0kZJ9PL2dt3o17xkGuSGJMoiF63cebUfuGhH4kb+YaiyCt68B8MXoxBjE4aG/+DQh0VGBz8X5AC5CTxswnU3mfDPxdPl0o1wbbGsn7Iw1CzMBnL7cG7p42WMHFASXygmnpfuPFwSBCKo66EwtDoKDx1yHsqhB3N+cVCKUiEmtqkzEH7+U5C4dHoD+zuFOdAqjEi7P64Q2cjNFSoUXoWYrQg/SSU+Ih5f7xpxiKlmqUgszX8pAB3ZUxG/cjArWjdHO3afOetWAmfurYVCyveKi66/ddW23K9+Lr4FqQfRk9EdOV2i7umjPxYqPFotK92CIFbUyv6Z/0/mxr56Qifk5ZbKJSQJFI9dYf5GxPrwV9V6P4DQ2Vj+u4FAAA=\', \'native/tv/OmniaDeviceSessionImport.kt\': \'H4sIAAAAAAACCn1PvWoDMQze/RQa7w7i7BkKIR27lTyAcdSryJ1kLNkEQt49vlxbyJBq+6TvTynEcxgRosyeSyXxVn2UjD4U+3aO5iTZ4Cw2EV+WixQjRvWx5Ixsh9/NQdjwYv8okLVk3Eejis5thwE+MFTiESRDxjSFuIATVooISiNviGEuapAy1hYGAaZg2MiahHUlLRpiD8PWUauQOUygRRPyCb4Kw1pojX1/eH+iKgl36+UH7f5EXQ+bNzgyWQ9XB21e/Nr1Tz91/YP85Np2N3cHauLMPmUBAAA=\', \'native/tv/OmniaDeviceSessionImportTest.kt\': \'H4sIAAAAAAACCp2T30/CMBDH3/dX9HELpsFXExMRZiQxYgCfTS0HdJR2ttcJIfzvdhs/iuBIvJfdrp9dv/djOeMLNgPC9ZIqVwhNsaBcG6DM4TyKxDLXBslCoxRqVZ5oh0KBpV2mOEjJUGiVrjjkpdPE790RMoMNIK8SNwHOGFB4SNjVCmHVlFIyp/i8ATBOPUrNF0LN9pQ2M5o5JZB2rAWDlFWP9Msxaa9AY+PgHBmDxSji0jNksFSC9aAQHEZgrW9dv8JLhmwi4u2h8qdOEcZRFFDTT1J/16hNV/5Arge+XXFC7klQxC5FaQUzpJZiPdM+xOtYJ0i9E0I2e77VItsDH5Yf397smaQCtr8U1zOUMDmKHkIGHG3nhSEMweZa2f/ILuMGps7CxMenXgwEZ5Jk+tPH64HHtlw1/3q6e/T9tdcfvXXG3ee0lwR3lvbHcsXJbi/j5ARHsz7062ovg25WVzHkcxJ/3JGL/5JXFlSKfqWC74+eL5hmWqhA2HEJ412C5PIY22dj3EY/DYB2fhIEAAA=\', \'native/tv/OmniaTvAccountPortalLink.kt\': \'H4sIAAAAAAACCr1VyW7bMBC96yumQQ8SEBAtejOaZjGcNkASB15S9FTQEmUPTHEEipLtBvn3DC3LsZLWbnooTxT5ZntvhjpLUatOP3dXJpQmsYTJUrhKZNIpi1J/Er1lzrtMGSf1qLppzs9z7HRiLYsiCnIZz+VUQUyZMGWF5D2UKIrYKmUKIeOYSuOCALOcrINtIDbIqVAi5etEOiQjtFxR6cS5tdJMlQ/7Bqsu6TIzbzAY0OINaOZK38jld0zc7I9mlitlujgX/y0nWh2ETpW7l7o8DMxK5x0OHavQTw/CLfOXTZQ9CCwOJcBi3lCCKe5xxphcS5eSzcQ1xVKPLX5jlN5vUxp0IslfQWaonTCywmmtQWPiz+9RLTgfpV9ZtVr3onSOzH7MSC23Hfayf92MCRS3/mTkt0FwtquqYR9GakhLA/3MoBxV53Wn37E3qa/RzENlPDjpwAWRVtIcQ9Uk34ENfFsOnECrvDCK4CEAXhXHmdVkMugFvSIurfWTUiMtpFLrCQ/l2GqYrKDpA3iAdgd9HjqLZnr6JTSl1hE8rj3UUxRmG8E5XqN9awLCiGtR1iHnsjOuDN/5EgU/Diq5WIUfP7DK23r84uELZ2TxF/m35Z9c+FWr3BDNtpvdMZDpaoznfPTQouQEMIWQm78rXTxjAvh+Q66gXBlmNlwL2pJTDK++3o7vfo4H18yUwOJSoi6timAvFpQuFHh+4ZFTB99w4VHXKlYANi/jUUP9f69p0Ov273uDH39X1S7693Vdkp2Sg5z/CwuyyWmrsuedz3U3+3cnUHdg7aXPCcP7XQAakDCxtCi4nqNjHlVNvjOfh1Osj4r1QA9VTPx221UU1HEfgychWIkN6QYAAA==\', \'native/tv/OmniaTvBrowserSignIn.kt\': \'H4sIAAAAAAACCr1VXW/TMBR9768wFZoSsXmgvaBKwNaCYNK2jrUb4tFz3ORSxzfYTrZR7b9znTT91DaGEHlybu7nOec6hxPQqjcs/LGJhEksQnLLfcVz4ZUFoQ/4p9uCTrkyXuhxddrajwro9aQWzsWdQsipSBWTmHNTVoAhQwncSauUcVxIiaXxnQ7kBVrPFoUooECn+IQ+J8IDGq7FHZaeH1krTKpC2WdEDVCXuXlGwAXePMObsNKn4vYbJD57MMzSpAQX9RLexbVWT7pK1FpJf+RGnuB90j1V/kro8mFHgv4UE5iAso/5FFr4Cdqcn6AU+tLCF/LSj8eUBjxPii2XDLTnRlSQNoi1IcF+BeqG+lF6K2pNaP3SezSP+4zV7UIPm2rzGcmFnwXLOBw7ncNVDgzlMEKzSWnYMDcgxlXf4o1TdgSpIfkrExyTHusjaiXMLqvaxnvsqJHwYhT2jq2NFsUxm3UYPRXVcIFHdn23zEAN1uRucB3Fi5isAZ8Sb9DBZWlt2IPg2Sg8yuf0knfL9Jo6o5i6V9YDZVpZJXJfeeOOFlcl/bvoLVG6GCA8AeeoO7TMETYMDLsBn3V3CXONoegSZV6bXM3MSEmklbF38SIRLViUoYVfGO6PP2jlzevNXsLTaKOliGLb084Oe1GjzcGdoEjApLsMzUCDnJLbbIUBcrO+Zn6d926KmGrVjdk9lZ2P/nlh+399JOAk2mS9kY9L46KT5akp+dOeYArmknINqMQHrpWnBJLObO/92gBN0u9Y2vpzj3XZq/rEZVaaqUqig5j/QDBjHHlLU0TdvW78FPHn9INYo31FQ4Uy7OWsnne+ROe0vULz4cXx5+Oz+/352Hvzv8S+BjMNkhPsusEn3AUENO0v8xm4pl3aBDMBm5NJsURVIBXzyCZgwGW1bKn5kCZTVvG/ke4/lO82VVa3LJVWE0nbynpcTvQvGAgvszDkrL07OBLYdHFElJP0siqjmoY5nt3621aDz+xgKWhJt6X92gw2Us7R/R+taXggjFR6a5k2BX3fue/8BsTjI9qQCAAA\'}\nfor _name,_encoded in _omnia_device_files.items():\n    _target=ROOT/\'scripts/omnia-device-signin\'/_name\n    _target.parent.mkdir(parents=True,exist_ok=True)\n    _target.write_bytes(gzip.decompress(base64.b64decode(_encoded)))\nsubprocess.run([sys.executable,str(ROOT/\'scripts/omnia-device-signin/apply_native_signin.py\'),\'--root\',str(ROOT),\'--platform\',\'tv\'],check=True)\n_p=ROOT/\'app/build.gradle.kts\';_s=_p.read_text();_s,_n=re.subn(r\'versionCode = \\d+\',\'versionCode = 31\',_s,count=1);assert _n==1;_s,_n=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.25"\',_s,count=1);assert _n==1;_p.write_text(_s,encoding=\'utf8\',newline=\'\\n\')\n',"omnia-native-device-signin-overlay","exec"))

# The native client label is Omnia; retain installation-ID compatibility.
if (ROOT/'app').exists():
    _test=ROOT/'app/src/test/java/com/nuvio/tv/core/auth/DeviceSessionRegistrationTest.kt'
    _source=_test.read_text(encoding='utf8')
    _old='assertEquals("Nuvio TV", params.getValue("p_client_name").jsonPrimitive.content)'
    _new='assertEquals("Omnia TV", params.getValue("p_client_name").jsonPrimitive.content)'
    if _new not in _source:
        assert _source.count(_old)==1, 'Unexpected registration test fixture'
        _test.write_text(_source.replace(_old,_new,1),encoding='utf8',newline='\n')

exec(compile('\nfrom pathlib import Path\nimport base64,gzip\ndef layout_replace(path,old,new):\n p=Path(path);s=p.read_text(encoding=\'utf-8\')\n if new in s:return\n if s.count(old)!=1:raise ValueError(\'Login layout source anchor changed: \'+str(p))\n p.write_text(s.replace(old,new,1),encoding=\'utf-8\')\nif \'tv\'==\'tv\':\n screen=\'app/src/main/java/com/nuvio/tv/ui/screens/account/AuthQrSignInScreen.kt\'\n layout_replace(screen,\'if (BuildConfig.FEATURE_CUSTOM_SERVER_CONNECTIONS_ENABLED) {\',\'if (BuildConfig.FEATURE_CUSTOM_SERVER_CONNECTIONS_ENABLED && !viewModel.hasOmniaAccountPortal) {\')\n layout_replace(screen,\'                useEmailLogin = useEmailLogin\\n\',\'                useEmailLogin = useEmailLogin,\\n                isOmniaAccount = viewModel.hasOmniaAccountPortal\\n\')\n layout_replace(screen,\'    useEmailLogin: Boolean\\n) {\',\'    useEmailLogin: Boolean,\\n    isOmniaAccount: Boolean\\n) {\')\n layout_replace(screen,\'                    stringResource(R.string.auth_qr_connected)\\n                } else {\',\'                    stringResource(R.string.auth_qr_connected)\\n                } else if (isOmniaAccount) {\\n                    "Sign in to Omnia to bring your profiles, library and watch history together."\\n                } else {\')\n # This was infrastructure copy, not a consent or license notice. QR/custom flows retain their existing notice.\n layout_replace(screen,\'        AuthTermsAcknowledgement()\\n        uiState.error?\', \'        // Account actions follow the sign-in form.\\n        uiState.error?\')\n target=\'app/src/main/java/com/nuvio/tv/ui/screens/account/OmniaTvAccountPortalLink.kt\'\nelse:\n screen=\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/auth/AuthScreen.kt\'\n layout_replace(screen,\'if (AppFeaturePolicy.customServerConnectionsEnabled) {\\n            ServerConnectionMenu(\', \'if (AppFeaturePolicy.customServerConnectionsEnabled && !OmniaAccountPortal.availableFor(serverConnectionState.activeServer.backendUrl)) {\\n            ServerConnectionMenu(\')\n target=\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/auth/OmniaAccountPortalLinks.kt\'\nPath(target).write_bytes(gzip.decompress(base64.b64decode(\'H4sIAAAAAAACCtVVS2/bMAy++1dwxQ42EAjrtsMQrGvToN0KtE2RR4edBsWWbaGyaMhSHi3630fFcZt0bR7ALtNJlj6S4veR9EkqlWj3SnuhQ64TgzKZMTthBbfCSK4+sbNZSbtCaMvVcHLVnHdK2W7HildVFJQ8vuOZgBgLpt1EovfgJKtiI4SuGI9jdNoGgSxKNBaeApFBiZVgKV0n3ErUTPE5Oss6xnCdCR92D6suKlfoPQz6ON0DnQuZ5cTUHiYlTxKpszctiCUrZpZVdq4EG9K2o2S2TwQSUF3x2U+Z2PxNM0P0k4ZEkP/mYyW2QjNhb7ly24GFs97hwFJp9NKtcEOiFmNhtgKrbQ8g7q4wkanc4IwwpeI2RVOwS4y5Ghn5g1Bqs43T0rKk/Auy1hmnzlrUmzFe0Qbxsj1sTlSwa38y9NsgOFnVR5MPzRWkTkOv0JIPJ526kW7IG1eXUt+FQntw0oZTRCW4juAhAFoTMszrPOEIXmTOYmeM76waaSDlSo2piUdGwXgOjUTwAOvifh1YQ9V8/C3UTqkIHhce6q4Li6UWFK+RZa04w6jphtBiSajDL0Rx1IKJMFbSA1d6nm5XvlhFE0Ykp/Pw8IM3aZL0izp4h8gtyNHIe/RDbJcwH1+G8avW+9Vo08VkCA/T6GlIhIXUBPm8THIpFJ0sdy1A3VUyvqOjhzUFjkCmEFIbdLmNc+KL7pdaMiyFJiHDRUGslQMbXHy/Ht38HvUvSRgmq3MulTMigo1YEKoS4OWER0oYfMGGB10jSHBYDu6DFuxCsW2mF4GeJhnrCl/ITa38J1z2z7q927P+r93YXEW/zuc5mgwtlPS7nKJJjv8xo887n+1q/u+OoG7V+h09ShnerwKIWA5jg9OK4tOzYlTo3/Q8ltjiqFqMsoGIkf4/Zh4FddzH4A8LAa8GQggAAA==\')))\n',"omnia-login-layout","exec"))

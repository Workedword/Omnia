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
    # Detect the actual diagnostics call, allowing other Advanced sections before it.
    # A positional-prefix check duplicated the section after adding connection tools.
    if 'com.nuvio.app.features.addons.OmniaAddonDiagnostics()' not in (ROOT/advanced).read_text():
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
    if replacement not in s:
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

# AVAudioSession is process-wide. Serialize activation/deactivation across player
# controller instances as well as within one controller during rapid title changes.
if (ROOT/'composeApp').exists():
    p=ROOT/'iosApp/iosApp/Player/PlayerAudioSessionController.swift'
    text=p.read_text(encoding='utf-8')
    text=text.replace('private let audioQueue = DispatchQueue(', 'private static let audioQueue = DispatchQueue(')
    text=text.replace('        audioQueue.async', '        Self.audioQueue.async')
    assert text.count('private static let audioQueue')==1
    assert text.count('Self.audioQueue.async')==2
    p.write_text(text,encoding='utf-8',newline='\n')
    print('Prepared shared serial iOS audio-session queue; Apple SDK compilation is still required')

# Replaying the legacy test overlay used to append the same Current Add-ons tap
# before its unchanged comment on every pass. Canonicalize this generated action.
if (ROOT/'composeApp').exists():
    p=ROOT/'prepare_omnia_ios_tests.py'
    text=p.read_text(encoding='utf-8')
    action='            if item("Current Add-ons").exists && item("Current Add-ons").isHittable { tap("Current Add-ons") }\n'
    while action+action in text:
        text=text.replace(action+action,action)
    assert text.count(action)==1
    p.write_text(text,encoding='utf-8',newline='\n')


# Omnia provider media-type contract batch. Keep TV's existing adapter unchanged.
if (ROOT/'composeApp').exists():
    package=ROOT/'composeApp/src/commonMain/kotlin/com/nuvio/app/features/plugins'
    (package/'PluginMediaType.kt').write_text(r'''
package com.nuvio.app.features.plugins

/** Preserve the episodic type declared by a provider after normalizing catalog aliases. */
internal fun jsPluginMediaType(
    mediaType: String,
    supportedTypes: List<String>,
    season: Int?,
    episode: Int?,
): String {
    val normalizedType = normalizePluginType(mediaType)
    return if (
        normalizedType == "tv" && season != null && episode != null &&
        supportedTypes.any { it.equals("series", ignoreCase = true) }
    ) "series" else normalizedType
}
'''.lstrip(),encoding='utf8',newline='\n')
    repository=ROOT/'composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/plugins/PluginRepository.kt'
    code=repository.read_text(encoding='utf8')
    old='mediaType = normalizePluginType(mediaType),'
    new='mediaType = jsPluginMediaType(mediaType, scraper.supportedTypes, season, episode),'
    assert old in code or new in code
    code=code.replace(old,new)
    assert code.count(new)==1
    repository.write_text(code,encoding='utf8',newline='\n')
    tests=ROOT/'composeApp/src/commonTest/kotlin/com/nuvio/app/features/plugins/OmniaPluginMediaTypeTest.kt'
    tests.write_text(r'''
package com.nuvio.app.features.plugins

import kotlin.test.Test
import kotlin.test.assertEquals

class OmniaPluginMediaTypeTest {
    @Test
    fun `declared series provider receives episodic series`() {
        assertEquals("series", jsPluginMediaType("series", listOf("movie", "series"), 2, 5))
        assertEquals("series", jsPluginMediaType("tv", listOf("movie", "series"), 2, 5))
    }

    @Test
    fun `ordinary tv providers retain their existing contract`() {
        assertEquals("tv", jsPluginMediaType("series", listOf("movie", "tv"), 2, 5))
    }

    @Test
    fun `movie requests never become episodic requests`() {
        assertEquals("movie", jsPluginMediaType("movie", listOf("movie", "series"), null, null))
        assertEquals("movie", jsPluginMediaType("movie", listOf("movie", "series"), 1, 1))
    }

    @Test
    fun `both episode indices are required for the episodic adapter`() {
        assertEquals("tv", jsPluginMediaType("series", listOf("series"), null, 1))
        assertEquals("tv", jsPluginMediaType("series", listOf("series"), 1, null))
    }

    @Test
    fun `case variants and season zero specials keep the declared contract`() {
        assertEquals("series", jsPluginMediaType("TV", listOf("movie", "SERIES"), 0, 1))
    }

    @Test
    fun `unknown content types are not coerced into television`() {
        assertEquals("custom", jsPluginMediaType("custom", listOf("series"), 1, 1))
    }
}
'''.lstrip(),encoding='utf8',newline='\n')
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=24\nMARKETING_VERSION=0.4.16\n',encoding='utf8',newline='\n')
    ios_tests=ROOT/'prepare_omnia_ios_tests.py'
    ios_tests.write_text(ios_tests.read_text(encoding='utf8').replace('Version 0.4.15 (23)','Version 0.4.16 (24)'),encoding='utf8',newline='\n')
    print('Prepared declared-series provider compatibility for shared Android/iOS source; new iOS compilation still requires Mac/Xcode')

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

"""Require real navigation for every Add-ons hub, including standalone routes."""
if (ROOT/'composeApp').exists():
    import re
    base='composeApp/src/commonMain/kotlin/com/nuvio/app/'
    def patch(rel,old,new):
        p=ROOT/(base+rel);s=p.read_text()
        if old in s:s=s.replace(old,new)
        else:assert new in s,(rel,old[:90])
        p.write_text(s,encoding='utf8',newline='\n')
    patch('features/settings/AddonsSettingsPage.kt','onPageClick: (SettingsPage) -> Unit = {},','onPageClick: (SettingsPage) -> Unit,')
    patch('features/settings/SettingsScreen.kt','private fun settingsPageTitles():','internal fun settingsPageTitles():')
    patch('features/settings/SettingsScreen.kt','else addonsSettingsContent()','else addonsSettingsContent(onPageClick = onPageChange)')
    # The tablet fallback must keep using its inline navigation, just like its hub.
    p=ROOT/(base+'features/settings/SettingsScreen.kt');s=p.read_text()
    marker='SettingsPage.Plugins -> if (AppFeaturePolicy.pluginsEnabled) pluginsSettingsContent() else addonsSettingsContent(onPageClick = onPageChange)'
    tablet=s.index('private fun TabletSettingsScreen')
    s=s[:tablet]+s[tablet:].replace(marker,'SettingsPage.Plugins -> if (AppFeaturePolicy.pluginsEnabled) pluginsSettingsContent() else addonsSettingsContent(onPageClick = { openInlinePage(it) }, isTablet = true)')
    p.write_text(s,encoding='utf8',newline='\n')
    full=ROOT/(base+'features/settings/SettingsFullScreenPages.kt');s=full.read_text()
    s=s.replace('''fun AddonsSettingsScreen(
    onBack: () -> Unit,
) {''','''fun AddonsSettingsScreen(
    onBack: () -> Unit,
    onNavigatePage: (pageName: String, title: String) -> Unit,
) {
    val pageTitles = settingsPageTitles()''')
    s=s.replace('        addonsSettingsContent()','        addonsSettingsContent(onPageClick = { page -> onNavigatePage(page.name, pageTitles.getValue(page)) })')
    s=s.replace('''fun PluginsSettingsScreen(
    onBack: () -> Unit,
) {''','''fun PluginsSettingsScreen(
    onBack: () -> Unit,
    onNavigatePage: (pageName: String, title: String) -> Unit,
) {''')
    s=s.replace('AddonsSettingsScreen(onBack = onBack)','AddonsSettingsScreen(onBack = onBack, onNavigatePage = onNavigatePage)')
    assert 'addonsSettingsContent()' not in s
    assert 'val pageTitles = settingsPageTitles()' in s
    full.write_text(s,encoding='utf8',newline='\n')
    app=ROOT/(base+'MainAppContent.kt');s=app.read_text()
    for name in ['AddonsSettingsScreen','PluginsSettingsScreen']:
        s=s.replace(name+'(onBack = onBack)',name+'(onBack = onBack, onNavigatePage = { pageName, title -> navController.navigate(com.nuvio.app.navigation.SettingsPageRoute(pageName, title)) })')
        assert name+'(onBack = onBack)' not in s
    app.write_text(s,encoding='utf8',newline='\n')
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=25\nMARKETING_VERSION=0.4.17\n',encoding='utf8',newline='\n')
    p=ROOT/'prepare_omnia_ios_tests.py';s=p.read_text().replace('Version 0.4.16 (24)','Version 0.4.17 (25)');p.write_text(s,encoding='utf8',newline='\n')
    print('Prepared required standalone Add-ons/Script Providers navigation callbacks; no empty default handler remains.')


# Next batch: optional compatible preferences, never the legacy platform blob.
if (ROOT/'composeApp').exists():
    import base64
    for rel,encoded in {'composeApp/src/commonMain/kotlin/com/nuvio/app/core/sync/OmniaSharedPreferencesPolicy.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25FbGVtZW50CmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5Kc29uQXJyYXkKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25PYmplY3QKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25QcmltaXRpdmUKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLmJvb2xlYW5Pck51bGwKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLmNvbnRlbnRPck51bGwKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLmludE9yTnVsbAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uanNvblByaW1pdGl2ZQoKLyoqIFdpcmUgbmFtZXMgZGVsaWJlcmF0ZWx5IGV4Y2x1ZGUgZGV2aWNlIHR1bmluZywgY3JlZGVudGlhbHMgYW5kIHRoZSBsb2NhbCBvcHQtaW4uICovCmludGVybmFsIHZhbCBzaGFyZWRQcmVmZXJlbmNlS2V5cyA9IHNldE9mKAogICAgImNvbnRpbnVlV2F0Y2hpbmdWaXNpYmxlIiwgImhlcm9FbmFibGVkIiwgImhlcm9UcmFpbGVyc0VuYWJsZWQiLCAiaGVyb1RyYWlsZXJNdXRlZCIsCiAgICAiaGlkZVVucmVsZWFzZWRDb250ZW50IiwgImF1ZGlvTGFuZ3VhZ2UiLCAic3VidGl0bGVMYW5ndWFnZSIsICJob21lQ2F0YWxvZ3MiLAopCgovKiogQ2F0YWxvZyBwcmVmZXJlbmNlcyBjYXJyeSBwdWJsaWMgaWRlbnRpZmllcnMsIG5ldmVyIGNvbmZpZ3VyZWQgZW5kcG9pbnQgVVJMcy4gKi8KaW50ZXJuYWwgZnVuIGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KHZhbHVlOiBTdHJpbmcsIG1heExlbmd0aDogSW50KTogQm9vbGVhbiA9CiAgICB2YWx1ZS5pc05vdEJsYW5rKCkgJiYgdmFsdWUubGVuZ3RoIDw9IG1heExlbmd0aCAmJgogICAgICAgICI6Ly8iICFpbiB2YWx1ZSAmJiAnPycgIWluIHZhbHVlICYmICcjJyAhaW4gdmFsdWUgJiYKICAgICAgICB2YWx1ZS5ub25lIHsgaXQuaXNJU09Db250cm9sKCkgfHwgaXQgPT0gJ1xcJyB9CgppbnRlcm5hbCBkYXRhIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzU2NvcGUodmFsIG93bmVyOiBTdHJpbmcsIHZhbCBwcm9maWxlSWQ6IEludCkgewogICAgaW5pdCB7CiAgICAgICAgcmVxdWlyZShvd25lci5pc05vdEJsYW5rKCkpCiAgICAgICAgcmVxdWlyZShwcm9maWxlSWQgaW4gMS4uNikKICAgIH0KfQoKaW50ZXJuYWwgZGF0YSBjbGFzcyBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KHZhbCByZXZpc2lvbjogTG9uZywgdmFsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCB2YWwgcHJvZmlsZUluc3RhbmNlOiBTdHJpbmc/ID0gbnVsbCkgewogICAgaW5pdCB7IHJlcXVpcmUocmV2aXNpb24gPj0gMCkgfQp9CgppbnRlcm5hbCBkYXRhIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzUmVxdWVzdCgKICAgIHZhbCBzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSwKICAgIHZhbCBnZW5lcmF0aW9uOiBMb25nLAopCgppbnRlcm5hbCBlbnVtIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZSB7IFVzZVRoaXNEZXZpY2UsIFVzZVNhdmVkU2V0dGluZ3MgfQppbnRlcm5hbCBjbGFzcyBTaGFyZWRQcmVmZXJlbmNlc0Nob2ljZVJlcXVpcmVkRXhjZXB0aW9uIDogSWxsZWdhbFN0YXRlRXhjZXB0aW9uKCJDaG9vc2Ugd2hpY2ggY2F0YWxvZyBzZXR0aW5ncyB0byBrZWVwIikKCi8qKiBBIHJlc3BvbnNlIG1heSBvbmx5IGFwcGx5IHRvIHRoZSBzdGlsbC1lbmFibGVkIGFjY291bnQsIHByb2ZpbGUgYW5kIGdlbmVyYXRpb24uICovCmludGVybmFsIGZ1biBjYW5BcHBseVNoYXJlZFByZWZlcmVuY2VzKAogICAgcmVxdWVzdDogU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0LAogICAgYWN0aXZlU2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGU/LAogICAgYWN0aXZlR2VuZXJhdGlvbjogTG9uZywKICAgIGVuYWJsZWQ6IEJvb2xlYW4sCik6IEJvb2xlYW4gPSBlbmFibGVkICYmIHJlcXVlc3Quc2NvcGUgPT0gYWN0aXZlU2NvcGUgJiYgcmVxdWVzdC5nZW5lcmF0aW9uID09IGFjdGl2ZUdlbmVyYXRpb24KCi8qKgogKiBNZXJnZSB0aGUgdXNlcidzIGludGVudGlvbmFsIGNoYW5nZXMgb250byB0aGUgbGF0ZXN0IHJlbW90ZSBzbmFwc2hvdC4KICogVGhlIGV4cG9ydGluZyBkZXZpY2Ugb3ducyBvbmx5IHRoZSBrZXlzIGl0IGNhbiByZXByZXNlbnQuIFVua25vd24ga2V5cyBhbmQKICogcmVtb3RlIGNoYW5nZXMgdG8gdW50b3VjaGVkIHByZWZlcmVuY2VzIHN1cnZpdmUuIEEgbWlzc2luZyBiYXNlbGluZSByZXF1aXJlcwogKiB0aGUgZXhwbGljaXQgZmlyc3Qtc3luYyBjaG9pY2UgaW5zdGVhZCBvZiBhc3N1bWluZyB0aGF0IGxvY2FsIGRlZmF1bHRzIGFyZSBlZGl0cy4KICovCmludGVybmFsIGZ1biBtZXJnZVNoYXJlZFByZWZlcmVuY2VzKAogICAgYmFzZWxpbmU6IEpzb25PYmplY3Q/LAogICAgbG9jYWw6IEpzb25PYmplY3QsCiAgICByZW1vdGU6IEpzb25PYmplY3QsCiAgICBzdXBwb3J0ZWRLZXlzOiBTZXQ8U3RyaW5nPiwKKTogSnNvbk9iamVjdCB7CiAgICByZXF1aXJlTm90TnVsbChiYXNlbGluZSkgeyAiQ2hvb3NlIGluaXRpYWwgc2V0dGluZ3MgYmVmb3JlIHN5bmNocm9uaXppbmciIH0KICAgIHJlcXVpcmUoc3VwcG9ydGVkS2V5cy5hbGwgeyBpdCBpbiBzaGFyZWRQcmVmZXJlbmNlS2V5cyB9KQogICAgcmVxdWlyZShsb2NhbC5rZXlzID09IHN1cHBvcnRlZEtleXMpIHsgIkluY29tcGxldGUgZGV2aWNlIHByZWZlcmVuY2UgZXhwb3J0IiB9CiAgICB2YWwgbWVyZ2VkID0gcmVtb3RlLnRvTXV0YWJsZU1hcCgpCiAgICBzdXBwb3J0ZWRLZXlzLmZvckVhY2ggeyBrZXkgLT4KICAgICAgICBpZiAobG9jYWxba2V5XSAhPSBiYXNlbGluZVtrZXldKSB7CiAgICAgICAgICAgIHZhbCB2YWx1ZSA9IGxvY2FsW2tleV0KICAgICAgICAgICAgaWYgKGtleSA9PSAiaG9tZUNhdGFsb2dzIikgewogICAgICAgICAgICAgICAgbWVyZ2VkW2tleV0gPSBtZXJnZUhvbWVDYXRhbG9nUHJlZmVyZW5jZXMoCiAgICAgICAgICAgICAgICAgICAgYmFzZWxpbmVba2V5XSBhcz8gSnNvbkFycmF5ID86IEpzb25BcnJheShlbXB0eUxpc3QoKSksCiAgICAgICAgICAgICAgICAgICAgdmFsdWUgYXM/IEpzb25BcnJheSA/OiBlcnJvcigiSW52YWxpZCBjYXRhbG9nIHByZWZlcmVuY2VzIiksCiAgICAgICAgICAgICAgICAgICAgcmVtb3RlW2tleV0gYXM/IEpzb25BcnJheSA/OiBKc29uQXJyYXkoZW1wdHlMaXN0KCkpLAogICAgICAgICAgICAgICAgKQogICAgICAgICAgICB9IGVsc2UgaWYgKHZhbHVlICE9IG51bGwpIG1lcmdlZFtrZXldID0gdmFsdWUgZWxzZSBtZXJnZWQucmVtb3ZlKGtleSkKICAgICAgICB9CiAgICB9CiAgICByZXR1cm4gSnNvbk9iamVjdChtZXJnZWQpCn0KCmludGVybmFsIGZ1biBpbml0aWFsU2hhcmVkUHJlZmVyZW5jZXMoCiAgICBjaG9pY2U6IFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZSwKICAgIGxvY2FsOiBKc29uT2JqZWN0LAogICAgcmVtb3RlOiBKc29uT2JqZWN0LAogICAgc3VwcG9ydGVkS2V5czogU2V0PFN0cmluZz4sCik6IEpzb25PYmplY3QgewogICAgcmVxdWlyZShzdXBwb3J0ZWRLZXlzLmFsbCB7IGl0IGluIHNoYXJlZFByZWZlcmVuY2VLZXlzIH0pCiAgICByZXF1aXJlKGxvY2FsLmtleXMgPT0gc3VwcG9ydGVkS2V5cykgeyAiSW5jb21wbGV0ZSBkZXZpY2UgcHJlZmVyZW5jZSBleHBvcnQiIH0KICAgIGlmIChjaG9pY2UgPT0gU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLlVzZVNhdmVkU2V0dGluZ3MpIHJldHVybiByZW1vdGUKICAgIHJldHVybiBKc29uT2JqZWN0KHJlbW90ZS50b011dGFibGVNYXAoKS5hcHBseSB7CiAgICAgICAgc3VwcG9ydGVkS2V5cy5mb3JFYWNoIHsga2V5IC0+CiAgICAgICAgICAgIHZhbCB2YWx1ZSA9IGxvY2FsW2tleV0KICAgICAgICAgICAgaWYgKHZhbHVlICE9IG51bGwpIHB1dChrZXksIHZhbHVlKSBlbHNlIHJlbW92ZShrZXkpCiAgICAgICAgfQogICAgfSkKfQoKLyoqIE9ubHkgZXhwbGljaXQsIHN1cHBvcnRlZCB2YWx1ZXMgYXJlIGFwcGxpZWQ7IG9taXR0ZWQgcmVtb3RlIHZhbHVlcyBrZWVwIGRldmljZSBkZWZhdWx0cy4gKi8KaW50ZXJuYWwgZnVuIGFwcGxpY2FibGVTaGFyZWRQcmVmZXJlbmNlcyhyZW1vdGU6IEpzb25PYmplY3QsIHN1cHBvcnRlZEtleXM6IFNldDxTdHJpbmc+KTogTWFwPFN0cmluZywgSnNvbkVsZW1lbnQ+ID0KICAgIHJlbW90ZS5maWx0ZXJLZXlzIHsgaXQgaW4gc3VwcG9ydGVkS2V5cyAmJiBpdCBpbiBzaGFyZWRQcmVmZXJlbmNlS2V5cyB9CgovKiogTWVyZ2Ugcm93IGZpZWxkcyBpbmRlcGVuZGVudGx5OyBhbiB1bmxvYWRlZC9hYnNlbnQgbG9jYWwgY2F0YWxvZyBpcyBuZXZlciBhIGRlbGV0aW9uLiAqLwppbnRlcm5hbCBmdW4gbWVyZ2VIb21lQ2F0YWxvZ1ByZWZlcmVuY2VzKGJhc2VsaW5lOiBKc29uQXJyYXksIGxvY2FsOiBKc29uQXJyYXksIHJlbW90ZTogSnNvbkFycmF5KTogSnNvbkFycmF5IHsKICAgIGZ1biBpZGVudGl0eShyb3c6IEpzb25PYmplY3QpOiBTdHJpbmcgewogICAgICAgIGlmIChyb3dbImlzX2NvbGxlY3Rpb24iXT8uanNvblByaW1pdGl2ZT8uYm9vbGVhbk9yTnVsbCA9PSB0cnVlKSB7CiAgICAgICAgICAgIHJldHVybiAiY29sbGVjdGlvbjoiICsgcmVxdWlyZU5vdE51bGwocm93WyJjb2xsZWN0aW9uX2lkIl0/Lmpzb25QcmltaXRpdmU/LmNvbnRlbnRPck51bGwpLmFsc28geyByZXF1aXJlKGl0LmlzTm90QmxhbmsoKSkgfQogICAgICAgIH0KICAgICAgICByZXR1cm4gSnNvbkFycmF5KGxpc3RPZigiYWRkb25faWQiLCAidHlwZSIsICJjYXRhbG9nX2lkIikubWFwIHsga2V5IC0+CiAgICAgICAgICAgIEpzb25QcmltaXRpdmUocmVxdWlyZU5vdE51bGwocm93W2tleV0/Lmpzb25QcmltaXRpdmU/LmNvbnRlbnRPck51bGwpLmFsc28geyByZXF1aXJlKGl0LmlzTm90QmxhbmsoKSkgfSkKICAgICAgICB9KS50b1N0cmluZygpCiAgICB9CiAgICBmdW4gcm93cyh2YWx1ZTogSnNvbkFycmF5KTogTWFwPFN0cmluZywgSnNvbk9iamVjdD4gewogICAgICAgIHZhbCByZXN1bHQgPSBsaW5rZWRNYXBPZjxTdHJpbmcsIEpzb25PYmplY3Q+KCkKICAgICAgICB2YWx1ZS5mb3JFYWNoSW5kZXhlZCB7IGluZGV4LCBlbGVtZW50IC0+CiAgICAgICAgICAgIHZhbCByYXcgPSBlbGVtZW50IGFzPyBKc29uT2JqZWN0ID86IGVycm9yKCJJbnZhbGlkIGNhdGFsb2cgcHJlZmVyZW5jZSByb3ciKQogICAgICAgICAgICB2YWwgcm93ID0gSnNvbk9iamVjdChtYXBPZigKICAgICAgICAgICAgICAgICJlbmFibGVkIiB0byBKc29uUHJpbWl0aXZlKHRydWUpLCAiY3VzdG9tX3RpdGxlIiB0byBKc29uUHJpbWl0aXZlKCIiKSwKICAgICAgICAgICAgICAgICJvcmRlciIgdG8gSnNvblByaW1pdGl2ZShpbmRleCksICJpc19jb2xsZWN0aW9uIiB0byBKc29uUHJpbWl0aXZlKGZhbHNlKSwKICAgICAgICAgICAgICAgICJjb2xsZWN0aW9uX2lkIiB0byBKc29uUHJpbWl0aXZlKCIiKSwKICAgICAgICAgICAgKSArIHJhdykKICAgICAgICAgICAgdmFsIGtleSA9IGlkZW50aXR5KHJvdykKICAgICAgICAgICAgcmVxdWlyZShrZXkgIWluIHJlc3VsdCkgeyAiRHVwbGljYXRlIGNhdGFsb2cgcHJlZmVyZW5jZSByb3ciIH0KICAgICAgICAgICAgcmVzdWx0W2tleV0gPSByb3cKICAgICAgICB9CiAgICAgICAgcmV0dXJuIHJlc3VsdAogICAgfQogICAgdmFsIGJhc2VSb3dzID0gcm93cyhiYXNlbGluZSkKICAgIHZhbCBsb2NhbFJvd3MgPSByb3dzKGxvY2FsKQogICAgdmFsIHJlbW90ZVJvd3MgPSByb3dzKHJlbW90ZSkKICAgIHZhbCBtZXJnZWQgPSByZW1vdGVSb3dzLnRvTXV0YWJsZU1hcCgpCiAgICBsb2NhbFJvd3MuZm9yRWFjaCB7IChrZXksIHJvdykgLT4KICAgICAgICB2YWwgYmVmb3JlID0gYmFzZVJvd3Nba2V5XQogICAgICAgIHZhbCBsYXRlc3QgPSByZW1vdGVSb3dzW2tleV0KICAgICAgICBpZiAoYmVmb3JlID09IG51bGwpIHsKICAgICAgICAgICAgaWYgKGxhdGVzdCA9PSBudWxsKSBtZXJnZWRba2V5XSA9IHJvdwogICAgICAgICAgICBlbHNlIGlmIChyb3cgIT0gbGF0ZXN0KSB0aHJvdyBTaGFyZWRQcmVmZXJlbmNlc0Nob2ljZVJlcXVpcmVkRXhjZXB0aW9uKCkKICAgICAgICB9IGVsc2UgaWYgKHJvdyAhPSBiZWZvcmUpIHsKICAgICAgICAgICAgaWYgKGxhdGVzdCA9PSBudWxsKSBtZXJnZWRba2V5XSA9IHJvdwogICAgICAgICAgICBlbHNlIHsKICAgICAgICAgICAgICAgIHZhbCBmaWVsZHMgPSBsYXRlc3QudG9NdXRhYmxlTWFwKCkKICAgICAgICAgICAgICAgIC8vIE9ubHkgZWRpdGFibGUgZmllbGRzIGFyZSBjaGFuZ2VzOyBpZGVudGl0eSBpcyBzdGFibGUgYWNyb3NzIGNsaWVudHMuCiAgICAgICAgICAgICAgICBsaXN0T2YoImVuYWJsZWQiLCAiY3VzdG9tX3RpdGxlIiwgIm9yZGVyIikuZm9yRWFjaCB7IGZpZWxkIC0+CiAgICAgICAgICAgICAgICAgICAgaWYgKHJvd1tmaWVsZF0gIT0gYmVmb3JlW2ZpZWxkXSkgewogICAgICAgICAgICAgICAgICAgICAgICB2YWwgdmFsdWUgPSByb3dbZmllbGRdCiAgICAgICAgICAgICAgICAgICAgICAgIGlmICh2YWx1ZSAhPSBudWxsKSBmaWVsZHNbZmllbGRdID0gdmFsdWUgZWxzZSBmaWVsZHMucmVtb3ZlKGZpZWxkKQogICAgICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgICAgIG1lcmdlZFtrZXldID0gSnNvbk9iamVjdChmaWVsZHMpCiAgICAgICAgICAgIH0KICAgICAgICB9CiAgICB9CiAgICB2YWwgcmVtb3RlUG9zaXRpb25zID0gcmVtb3RlUm93cy5rZXlzLndpdGhJbmRleCgpLmFzc29jaWF0ZSB7IGl0LnZhbHVlIHRvIGl0LmluZGV4IH0KICAgIHZhbCBvcmRlcmVkID0gbWVyZ2VkLmVudHJpZXMuc29ydGVkV2l0aChjb21wYXJlQnk8TWFwLkVudHJ5PFN0cmluZywgSnNvbk9iamVjdD4+IHsKICAgICAgICBpdC52YWx1ZVsib3JkZXIiXT8uanNvblByaW1pdGl2ZT8uaW50T3JOdWxsID86IEludC5NQVhfVkFMVUUKICAgIH0udGhlbkJ5IHsgcmVtb3RlUG9zaXRpb25zW2l0LmtleV0gPzogSW50Lk1BWF9WQUxVRSB9LnRoZW5CeSB7IGl0LmtleSB9KQogICAgcmV0dXJuIEpzb25BcnJheShvcmRlcmVkLm1hcEluZGV4ZWQgeyBpbmRleCwgZW50cnkgLT4gSnNvbk9iamVjdChlbnRyeS52YWx1ZSArICgib3JkZXIiIHRvIEpzb25QcmltaXRpdmUoaW5kZXgpKSkgfSkKfQo=', 'composeApp/src/commonMain/kotlin/com/nuvio/app/core/sync/OmniaSharedPreferencesEngine.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5DYW5jZWxsYXRpb25FeGNlcHRpb24KaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5mbG93Lk11dGFibGVTdGF0ZUZsb3cKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5mbG93LlN0YXRlRmxvdwppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmZsb3cuYXNTdGF0ZUZsb3cKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5mbG93LnVwZGF0ZQppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLnN5bmMuTXV0ZXgKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5zeW5jLndpdGhMb2NrCmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5Kc29uT2JqZWN0CgppbnRlcm5hbCBkYXRhIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQoCiAgICB2YWwgZW5hYmxlZDogQm9vbGVhbiA9IGZhbHNlLAogICAgdmFsIGJhc2VsaW5lOiBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90PyA9IG51bGwsCikKCmludGVybmFsIGludGVyZmFjZSBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsU3RvcmUgewogICAgZnVuIGxvYWQoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpOiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkCiAgICBmdW4gc2F2ZShzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSwgcmVjb3JkOiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKQp9CgppbnRlcm5hbCBkYXRhIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdCgKICAgIHZhbCBjb25mbGljdDogQm9vbGVhbiwKICAgIHZhbCBzbmFwc2hvdDogU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCwKKQoKaW50ZXJuYWwgaW50ZXJmYWNlIFNoYXJlZFByZWZlcmVuY2VzVHJhbnNwb3J0IHsKICAgIHN1c3BlbmQgZnVuIHB1bGwoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpOiBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90CiAgICBzdXNwZW5kIGZ1biBwdXNoKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCBleHBlY3RlZFJldmlzaW9uOiBMb25nLCBwcmVmZXJlbmNlczogSnNvbk9iamVjdCwgZXhwZWN0ZWRQcm9maWxlSW5zdGFuY2U6IFN0cmluZz8pOiBTaGFyZWRQcmVmZXJlbmNlc1B1c2hSZXN1bHQKfQoKaW50ZXJuYWwgaW50ZXJmYWNlIFNoYXJlZFByZWZlcmVuY2VzRGV2aWNlIHsKICAgIHZhbCBzdXBwb3J0ZWRLZXlzOiBTZXQ8U3RyaW5nPgogICAgZnVuIGN1cnJlbnRTY29wZSgpOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlPwogICAgc3VzcGVuZCBmdW4gZXhwb3J0KHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKTogSnNvbk9iamVjdAogICAgLyoqIEFkYXB0ZXIgY2hlY2tzIHRoZSBzdXBwbGllZCBndWFyZCBpbnNpZGUgZXZlcnkgYXN5bmNocm9ub3VzIHN0b3JhZ2UgZWRpdC4gKi8KICAgIHN1c3BlbmQgZnVuIGFwcGx5KHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCBwcmVmZXJlbmNlczogSnNvbk9iamVjdCwgc3RpbGxDdXJyZW50OiAoKSAtPiBCb29sZWFuKQp9CgppbnRlcm5hbCBlbnVtIGNsYXNzIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cyB7IE9mZiwgUmVhZHksIENob29zZUluaXRpYWxTZXR0aW5ncywgU3luY2luZywgU3luY2VkLCBTaWduSW5SZXF1aXJlZCwgRXJyb3IgfQoKaW50ZXJuYWwgZGF0YSBjbGFzcyBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZSgKICAgIHZhbCBlbmFibGVkOiBCb29sZWFuID0gZmFsc2UsCiAgICB2YWwgc3RhdHVzOiBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMgPSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmLAopCgovKioKICogRGV2aWNlLWxvY2FsIG9wdC1pbiB3aXRoIGFjY291bnQvcHJvZmlsZSBndWFyZHMgYXJvdW5kIGV2ZXJ5IHN1c3BlbmQgYm91bmRhcnkuCiAqIERpc2FibGUgbmV2ZXIgd2FpdHMgYmVoaW5kIGEgbmV0d29yayBtdXRleCBhbmQgY2Fubm90IGJlIHVuZG9uZSBieSBhIGxhdGUgcmVzcG9uc2UuCiAqLwppbnRlcm5hbCBjbGFzcyBPbW5pYVNoYXJlZFByZWZlcmVuY2VzRW5naW5lKAogICAgcHJpdmF0ZSB2YWwgZGV2aWNlOiBTaGFyZWRQcmVmZXJlbmNlc0RldmljZSwKICAgIHByaXZhdGUgdmFsIHN0b3JlOiBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsU3RvcmUsCiAgICBwcml2YXRlIHZhbCB0cmFuc3BvcnQ6IFNoYXJlZFByZWZlcmVuY2VzVHJhbnNwb3J0LAopIHsKICAgIHByaXZhdGUgdmFsIG11dGV4ID0gTXV0ZXgoKQogICAgcHJpdmF0ZSB2YWwgc3RhdGVNdXRleCA9IE11dGV4KCkKICAgIHByaXZhdGUgdmFsIGdlbmVyYXRpb24gPSBNdXRhYmxlU3RhdGVGbG93KDBMKQogICAgcHJpdmF0ZSB2YWwgX3N0YXRlID0gTXV0YWJsZVN0YXRlRmxvdyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZSgpKQogICAgdmFsIHN0YXRlOiBTdGF0ZUZsb3c8U2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdGU+ID0gX3N0YXRlLmFzU3RhdGVGbG93KCkKCiAgICBmdW4gcmVmcmVzaExvY2FsU3RhdGUoKSB7CiAgICAgICAgZ2VuZXJhdGlvbi51cGRhdGUgeyBpdCArIDEgfQogICAgICAgIHZhbCBzY29wZSA9IGRldmljZS5jdXJyZW50U2NvcGUoKQogICAgICAgIHZhbCBlbmFibGVkID0gc2NvcGU/LmxldCB7IHN0b3JlLmxvYWQoaXQpLmVuYWJsZWQgfSA9PSB0cnVlCiAgICAgICAgX3N0YXRlLnZhbHVlID0gU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdGUoZW5hYmxlZCwgaWYgKGVuYWJsZWQpIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5SZWFkeSBlbHNlIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYpCiAgICB9CgogICAgc3VzcGVuZCBmdW4gZGlzYWJsZSgpIHsKICAgICAgICBnZW5lcmF0aW9uLnVwZGF0ZSB7IGl0ICsgMSB9CiAgICAgICAgdmFsIHNjb3BlID0gZGV2aWNlLmN1cnJlbnRTY29wZSgpCiAgICAgICAgc3RhdGVNdXRleC53aXRoTG9jayB7CiAgICAgICAgICAgIHNjb3BlPy5sZXQgeyBzdG9yZS5zYXZlKGl0LCBzdG9yZS5sb2FkKGl0KS5jb3B5KGVuYWJsZWQgPSBmYWxzZSkpIH0KICAgICAgICB9CiAgICAgICAgaWYgKHNjb3BlID09IGRldmljZS5jdXJyZW50U2NvcGUoKSkgX3N0YXRlLnZhbHVlID0gU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdGUoKQogICAgICAgIGVsc2UgcmVmcmVzaExvY2FsU3RhdGUoKQogICAgfQoKICAgIHByaXZhdGUgZnVuIGN1cnJlbnQocmVxdWVzdDogU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0LCByZXF1aXJlRW5hYmxlZDogQm9vbGVhbik6IEJvb2xlYW4gPQogICAgICAgIHJlcXVlc3Quc2NvcGUgPT0gZGV2aWNlLmN1cnJlbnRTY29wZSgpICYmIHJlcXVlc3QuZ2VuZXJhdGlvbiA9PSBnZW5lcmF0aW9uLnZhbHVlICYmCiAgICAgICAgICAgICghcmVxdWlyZUVuYWJsZWQgfHwgc3RvcmUubG9hZChyZXF1ZXN0LnNjb3BlKS5lbmFibGVkKQoKICAgIHByaXZhdGUgZnVuIHVwZGF0ZShyZXF1ZXN0OiBTaGFyZWRQcmVmZXJlbmNlc1JlcXVlc3QsIHN0YXR1czogU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzKSB7CiAgICAgICAgaWYgKGN1cnJlbnQocmVxdWVzdCwgcmVxdWlyZUVuYWJsZWQgPSBmYWxzZSkpIHsKICAgICAgICAgICAgX3N0YXRlLnZhbHVlID0gU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdGUoc3RvcmUubG9hZChyZXF1ZXN0LnNjb3BlKS5lbmFibGVkLCBzdGF0dXMpCiAgICAgICAgfQogICAgfQoKICAgIHN1c3BlbmQgZnVuIGVuYWJsZShjaG9pY2U6IFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZT8gPSBudWxsKTogU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzID0gbXV0ZXgud2l0aExvY2sgewogICAgICAgIHZhbCBzY29wZSA9IGRldmljZS5jdXJyZW50U2NvcGUoKSA/OiBydW4gewogICAgICAgICAgICBfc3RhdGUudmFsdWUgPSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0ZShmYWxzZSwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlNpZ25JblJlcXVpcmVkKQogICAgICAgICAgICByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlNpZ25JblJlcXVpcmVkCiAgICAgICAgfQogICAgICAgIHZhbCByZXF1ZXN0ID0gU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCBnZW5lcmF0aW9uLnZhbHVlKQogICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2luZykKICAgICAgICB0cnkgewogICAgICAgICAgICB2YWwgbG9jYWwgPSBkZXZpY2UuZXhwb3J0KHNjb3BlKQogICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgZmFsc2UpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICB2YXIgcmVtb3RlID0gdHJhbnNwb3J0LnB1bGwoc2NvcGUpCiAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCBmYWxzZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgIGlmIChyZW1vdGUucHJlZmVyZW5jZXMuaXNOb3RFbXB0eSgpICYmIGNob2ljZSA9PSBudWxsKSB7CiAgICAgICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkNob29zZUluaXRpYWxTZXR0aW5ncykKICAgICAgICAgICAgICAgIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzCiAgICAgICAgICAgIH0KICAgICAgICAgICAgdmFsIHJlc29sdmVkQ2hvaWNlID0gY2hvaWNlID86IFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZS5Vc2VUaGlzRGV2aWNlCiAgICAgICAgICAgIHJlcGVhdCgzKSB7CiAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgZmFsc2UpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICAgICAgdmFsIGluaXRpYWwgPSBpbml0aWFsU2hhcmVkUHJlZmVyZW5jZXMocmVzb2x2ZWRDaG9pY2UsIGxvY2FsLCByZW1vdGUucHJlZmVyZW5jZXMsIGRldmljZS5zdXBwb3J0ZWRLZXlzKQogICAgICAgICAgICAgICAgdmFsIGFjY2VwdGVkID0gaWYgKGluaXRpYWwgPT0gcmVtb3RlLnByZWZlcmVuY2VzKSBTaGFyZWRQcmVmZXJlbmNlc1B1c2hSZXN1bHQoZmFsc2UsIHJlbW90ZSkKICAgICAgICAgICAgICAgICAgICBlbHNlIHRyYW5zcG9ydC5wdXNoKHNjb3BlLCByZW1vdGUucmV2aXNpb24sIGluaXRpYWwsIHJlbW90ZS5wcm9maWxlSW5zdGFuY2UpCiAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgZmFsc2UpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICAgICAgaWYgKGFjY2VwdGVkLnNuYXBzaG90LnByb2ZpbGVJbnN0YW5jZSAhPSByZW1vdGUucHJvZmlsZUluc3RhbmNlKSByZXR1cm5Ad2l0aExvY2sgcmVxdWlyZU5ld1Byb2ZpbGVDaG9pY2UocmVxdWVzdCkKICAgICAgICAgICAgICAgIHJlbW90ZSA9IGFjY2VwdGVkLnNuYXBzaG90CiAgICAgICAgICAgICAgICBpZiAoIWFjY2VwdGVkLmNvbmZsaWN0KSB7CiAgICAgICAgICAgICAgICAgICAgLy8gUGVyc2lzdCBlbmFibGVkIG9ubHkgYWZ0ZXIgdGhlIGV4cGxpY2l0IGluaXRpYWwgYWN0aW9uIHN1Y2NlZWRzLgogICAgICAgICAgICAgICAgICAgIHN0YXRlTXV0ZXgud2l0aExvY2sgewogICAgICAgICAgICAgICAgICAgICAgICBpZiAoY3VycmVudChyZXF1ZXN0LCBmYWxzZSkpIHN0b3JlLnNhdmUoc2NvcGUsIHN0b3JlLmxvYWQoc2NvcGUpLmNvcHkoZW5hYmxlZCA9IHRydWUpKQogICAgICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgICAgICAgICBhcHBseVdpdGhvdXRPdmVyd3JpdGluZ05ld0xvY2FsRWRpdHMocmVxdWVzdCwgbG9jYWwsIHJlbW90ZSkKICAgICAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICAgICAgYWNrbm93bGVkZ2UocmVxdWVzdCwgbG9jYWwsIHJlbW90ZSkKICAgICAgICAgICAgICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQpCiAgICAgICAgICAgICAgICAgICAgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQKICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgfQogICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yKQogICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IKICAgICAgICB9IGNhdGNoIChjYW5jZWxsZWQ6IENhbmNlbGxhdGlvbkV4Y2VwdGlvbikgewogICAgICAgICAgICB1cGRhdGUocmVxdWVzdCwgaWYgKHN0b3JlLmxvYWQoc2NvcGUpLmVuYWJsZWQpIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5SZWFkeSBlbHNlIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYpCiAgICAgICAgICAgIHRocm93IGNhbmNlbGxlZAogICAgICAgIH0gY2F0Y2ggKF86IFNoYXJlZFByZWZlcmVuY2VzQ2hvaWNlUmVxdWlyZWRFeGNlcHRpb24pIHsKICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MpCiAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MKICAgICAgICB9IGNhdGNoIChfOiBFeGNlcHRpb24pIHsKICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIGZhbHNlKSkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5FcnJvcikKICAgICAgICAgICAgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yCiAgICAgICAgfQogICAgfQoKICAgIHN1c3BlbmQgZnVuIHN5bmNocm9uaXplKCk6IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cyA9IG11dGV4LndpdGhMb2NrIHsKICAgICAgICB2YWwgc2NvcGUgPSBkZXZpY2UuY3VycmVudFNjb3BlKCkgPzogcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TaWduSW5SZXF1aXJlZAogICAgICAgIHZhbCByZXF1ZXN0ID0gU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCBnZW5lcmF0aW9uLnZhbHVlKQogICAgICAgIHZhbCByZWNvcmQgPSBzdG9yZS5sb2FkKHNjb3BlKQogICAgICAgIGlmICghcmVjb3JkLmVuYWJsZWQpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgaWYgKHJlY29yZC5iYXNlbGluZSA9PSBudWxsKSB7CiAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzKQogICAgICAgICAgICByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkNob29zZUluaXRpYWxTZXR0aW5ncwogICAgICAgIH0KICAgICAgICB1cGRhdGUocmVxdWVzdCwgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNpbmcpCiAgICAgICAgdHJ5IHsKICAgICAgICAgICAgdmFsIGxvY2FsID0gZGV2aWNlLmV4cG9ydChzY29wZSkKICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICB2YXIgcmVtb3RlID0gdHJhbnNwb3J0LnB1bGwoc2NvcGUpCiAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCB0cnVlKSkgcmV0dXJuQHdpdGhMb2NrIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYKICAgICAgICAgICAgaWYgKHJlY29yZC5iYXNlbGluZS5wcm9maWxlSW5zdGFuY2UgIT0gcmVtb3RlLnByb2ZpbGVJbnN0YW5jZSkgcmV0dXJuQHdpdGhMb2NrIHJlcXVpcmVOZXdQcm9maWxlQ2hvaWNlKHJlcXVlc3QpCiAgICAgICAgICAgIHJlcGVhdCgzKSB7CiAgICAgICAgICAgICAgICB2YWwgbWVyZ2VkID0gbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhyZWNvcmQuYmFzZWxpbmUucHJlZmVyZW5jZXMsIGxvY2FsLCByZW1vdGUucHJlZmVyZW5jZXMsIGRldmljZS5zdXBwb3J0ZWRLZXlzKQogICAgICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICAgICAgdmFsIGFjY2VwdGVkID0gaWYgKG1lcmdlZCA9PSByZW1vdGUucHJlZmVyZW5jZXMpIFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdChmYWxzZSwgcmVtb3RlKQogICAgICAgICAgICAgICAgICAgIGVsc2UgdHJhbnNwb3J0LnB1c2goc2NvcGUsIHJlbW90ZS5yZXZpc2lvbiwgbWVyZ2VkLCByZW1vdGUucHJvZmlsZUluc3RhbmNlKQogICAgICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICAgICAgaWYgKGFjY2VwdGVkLnNuYXBzaG90LnByb2ZpbGVJbnN0YW5jZSAhPSByZW1vdGUucHJvZmlsZUluc3RhbmNlKSByZXR1cm5Ad2l0aExvY2sgcmVxdWlyZU5ld1Byb2ZpbGVDaG9pY2UocmVxdWVzdCkKICAgICAgICAgICAgICAgIHJlbW90ZSA9IGFjY2VwdGVkLnNuYXBzaG90CiAgICAgICAgICAgICAgICBpZiAoIWFjY2VwdGVkLmNvbmZsaWN0KSB7CiAgICAgICAgICAgICAgICAgICAgYXBwbHlXaXRob3V0T3ZlcndyaXRpbmdOZXdMb2NhbEVkaXRzKHJlcXVlc3QsIGxvY2FsLCByZW1vdGUpCiAgICAgICAgICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICAgICAgICAgIGFja25vd2xlZGdlKHJlcXVlc3QsIGxvY2FsLCByZW1vdGUpCiAgICAgICAgICAgICAgICAgICAgaWYgKCFjdXJyZW50KHJlcXVlc3QsIHRydWUpKSByZXR1cm5Ad2l0aExvY2sgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZgogICAgICAgICAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkKQogICAgICAgICAgICAgICAgICAgIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkCiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIH0KICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5FcnJvcikKICAgICAgICAgICAgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yCiAgICAgICAgfSBjYXRjaCAoY2FuY2VsbGVkOiBDYW5jZWxsYXRpb25FeGNlcHRpb24pIHsKICAgICAgICAgICAgdXBkYXRlKHJlcXVlc3QsIGlmIChzdG9yZS5sb2FkKHNjb3BlKS5lbmFibGVkKSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuUmVhZHkgZWxzZSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmKQogICAgICAgICAgICB0aHJvdyBjYW5jZWxsZWQKICAgICAgICB9IGNhdGNoIChfOiBTaGFyZWRQcmVmZXJlbmNlc0Nob2ljZVJlcXVpcmVkRXhjZXB0aW9uKSB7CiAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzKQogICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzCiAgICAgICAgfSBjYXRjaCAoXzogRXhjZXB0aW9uKSB7CiAgICAgICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCBmYWxzZSkpIHJldHVybkB3aXRoTG9jayBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmCiAgICAgICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IpCiAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5FcnJvcgogICAgICAgIH0KICAgIH0KCiAgICBwcml2YXRlIHN1c3BlbmQgZnVuIHJlcXVpcmVOZXdQcm9maWxlQ2hvaWNlKHJlcXVlc3Q6IFNoYXJlZFByZWZlcmVuY2VzUmVxdWVzdCk6IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cyB7CiAgICAgICAgc3RhdGVNdXRleC53aXRoTG9jayB7CiAgICAgICAgICAgIGlmIChjdXJyZW50KHJlcXVlc3QsIGZhbHNlKSkgc3RvcmUuc2F2ZShyZXF1ZXN0LnNjb3BlLCBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKCkpCiAgICAgICAgfQogICAgICAgIHVwZGF0ZShyZXF1ZXN0LCBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzKQogICAgICAgIHJldHVybiBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzCiAgICB9CgogICAgcHJpdmF0ZSBzdXNwZW5kIGZ1biBhcHBseVdpdGhvdXRPdmVyd3JpdGluZ05ld0xvY2FsRWRpdHMoCiAgICAgICAgcmVxdWVzdDogU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0LAogICAgICAgIGV4cG9ydGVkOiBKc29uT2JqZWN0LAogICAgICAgIGFja25vd2xlZGdlZDogU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCwKICAgICkgewogICAgICAgIGlmICghY3VycmVudChyZXF1ZXN0LCB0cnVlKSkgcmV0dXJuCiAgICAgICAgdmFsIGxhdGVzdCA9IGRldmljZS5leHBvcnQocmVxdWVzdC5zY29wZSkKICAgICAgICBpZiAoIWN1cnJlbnQocmVxdWVzdCwgdHJ1ZSkpIHJldHVybgogICAgICAgIC8vIEEgcHJlZmVyZW5jZSBjaGFuZ2VkIHdoaWxlIHRoZSBuZXR3b3JrIHJlcXVlc3Qgd2FzIGluIGZsaWdodCByZW1haW5zIGxvY2FsLAogICAgICAgIC8vIGFuZCBkaWZmZXJzIGZyb20gdGhlIGFja25vd2xlZGdlZCBiYXNlbGluZSBvbiB0aGUgbmV4dCBzeW5jaHJvbml6YXRpb24uCiAgICAgICAgdmFsIHNhZmVUb0FwcGx5ID0gSnNvbk9iamVjdChhcHBsaWNhYmxlU2hhcmVkUHJlZmVyZW5jZXMoYWNrbm93bGVkZ2VkLnByZWZlcmVuY2VzLCBkZXZpY2Uuc3VwcG9ydGVkS2V5cykKICAgICAgICAgICAgLmZpbHRlcktleXMgeyBrZXkgLT4gbGF0ZXN0W2tleV0gPT0gZXhwb3J0ZWRba2V5XSB9KQogICAgICAgIGRldmljZS5hcHBseShyZXF1ZXN0LnNjb3BlLCBzYWZlVG9BcHBseSkgeyBjdXJyZW50KHJlcXVlc3QsIHRydWUpIH0KICAgIH0KCiAgICBwcml2YXRlIHN1c3BlbmQgZnVuIGFja25vd2xlZGdlKAogICAgICAgIHJlcXVlc3Q6IFNoYXJlZFByZWZlcmVuY2VzUmVxdWVzdCwKICAgICAgICBleHBvcnRlZDogSnNvbk9iamVjdCwKICAgICAgICBhY2tub3dsZWRnZWQ6IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QsCiAgICApIHsKICAgICAgICAvLyBSZWNvcmQgdGhlIGV4cGVjdGVkIGFwcGxpZWQgdmFsdWVzIG9ubHkgYWZ0ZXIgc3RvcmFnZSBhcHBsaWNhdGlvbiBzdWNjZWVkcy4KICAgICAgICAvLyBEZWZhdWx0cyBvbWl0dGVkIGJ5IGFub3RoZXIgcGxhdGZvcm0gYXJlIG5vdCBtaXN0YWtlbiBmb3IgbmV3IGxvY2FsIGVkaXRzLgogICAgICAgIHZhbCBiYXNlbGluZSA9IGFja25vd2xlZGdlZC5jb3B5KHByZWZlcmVuY2VzID0gSnNvbk9iamVjdChleHBvcnRlZCArIGFja25vd2xlZGdlZC5wcmVmZXJlbmNlcykpCiAgICAgICAgc3RhdGVNdXRleC53aXRoTG9jayB7CiAgICAgICAgICAgIGlmIChjdXJyZW50KHJlcXVlc3QsIHRydWUpKSBzdG9yZS5zYXZlKHJlcXVlc3Quc2NvcGUsIFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQodHJ1ZSwgYmFzZWxpbmUpKQogICAgICAgIH0KICAgIH0KfQo=', 'composeApp/src/commonMain/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSyncRecordStore.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb24KaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25PYmplY3QKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLmJvb2xlYW5Pck51bGwKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLmNvbnRlbnRPck51bGwKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLmJ1aWxkSnNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uanNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uanNvblByaW1pdGl2ZQppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24ubG9uZ09yTnVsbAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24ucHV0CgovKiogSW52YWxpZC9pbmNvbXBsZXRlIGRldmljZSByZWNvcmRzIGZhaWwgY2xvc2VkIHRvIG9mZiwgbmV2ZXIgdG8gYXV0b21hdGljIHVwbG9hZC4gKi8KaW50ZXJuYWwgY2xhc3MgT21uaWFQcmVmZXJlbmNlc1N5bmNSZWNvcmRTdG9yZSgKICAgIHByaXZhdGUgdmFsIHJlYWQ6IChTdHJpbmcpIC0+IFN0cmluZz8sCiAgICBwcml2YXRlIHZhbCB3cml0ZTogKFN0cmluZywgU3RyaW5nKSAtPiBVbml0LAopIDogU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFN0b3JlIHsKICAgIHByaXZhdGUgZnVuIGtleShzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSkgPSAib21uaWEuc2V0dGluZ3Muc3luYy52MS4iICsgc2NvcGUub3duZXIgKyAiLiIgKyBzY29wZS5wcm9maWxlSWQKICAgIG92ZXJyaWRlIGZ1biBsb2FkKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKTogU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCA9IHJ1bkNhdGNoaW5nIHsKICAgICAgICB2YWwgcmF3ID0gcmVhZChrZXkoc2NvcGUpKSA/OiByZXR1cm5AcnVuQ2F0Y2hpbmcgU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCgpCiAgICAgICAgdmFsIGRhdGEgPSBKc29uLnBhcnNlVG9Kc29uRWxlbWVudChyYXcpLmpzb25PYmplY3QKICAgICAgICByZXF1aXJlKGRhdGFbInZlcnNpb24iXT8uanNvblByaW1pdGl2ZT8ubG9uZ09yTnVsbCA9PSAxTCkKICAgICAgICB2YWwgZW5hYmxlZCA9IHJlcXVpcmVOb3ROdWxsKGRhdGFbImVuYWJsZWQiXT8uanNvblByaW1pdGl2ZT8uYm9vbGVhbk9yTnVsbCkKICAgICAgICB2YWwgYmFzZWxpbmUgPSBkYXRhWyJiYXNlbGluZSJdPy5sZXQgeyBlbGVtZW50IC0+CiAgICAgICAgICAgIHZhbCBzbmFwc2hvdCA9IGVsZW1lbnQuanNvbk9iamVjdAogICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KAogICAgICAgICAgICAgICAgcmVxdWlyZU5vdE51bGwoc25hcHNob3RbInJldmlzaW9uIl0/Lmpzb25QcmltaXRpdmU/LmxvbmdPck51bGwpLAogICAgICAgICAgICAgICAgc25hcHNob3RbInByZWZlcmVuY2VzIl0gYXM/IEpzb25PYmplY3QgPzogZXJyb3IoIkludmFsaWQgYmFzZWxpbmUiKSwKICAgICAgICAgICAgICAgIHNuYXBzaG90WyJwcm9maWxlSW5zdGFuY2UiXT8uanNvblByaW1pdGl2ZT8uY29udGVudE9yTnVsbCwKICAgICAgICAgICAgKQogICAgICAgIH0KICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKGVuYWJsZWQsIGJhc2VsaW5lKQogICAgfS5nZXRPckRlZmF1bHQoU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCgpKQoKICAgIG92ZXJyaWRlIGZ1biBzYXZlKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCByZWNvcmQ6IFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQpIHsKICAgICAgICB2YWwgZGF0YSA9IGJ1aWxkSnNvbk9iamVjdCB7CiAgICAgICAgICAgIHB1dCgidmVyc2lvbiIsIDEpCiAgICAgICAgICAgIHB1dCgiZW5hYmxlZCIsIHJlY29yZC5lbmFibGVkKQogICAgICAgICAgICByZWNvcmQuYmFzZWxpbmU/LmxldCB7IHNuYXBzaG90IC0+CiAgICAgICAgICAgICAgICBwdXQoImJhc2VsaW5lIiwgYnVpbGRKc29uT2JqZWN0IHsKICAgICAgICAgICAgICAgICAgICBwdXQoInJldmlzaW9uIiwgc25hcHNob3QucmV2aXNpb24pCiAgICAgICAgICAgICAgICAgICAgcHV0KCJwcmVmZXJlbmNlcyIsIHNuYXBzaG90LnByZWZlcmVuY2VzKQogICAgICAgICAgICAgICAgICAgIHNuYXBzaG90LnByb2ZpbGVJbnN0YW5jZT8ubGV0IHsgcHV0KCJwcm9maWxlSW5zdGFuY2UiLCBpdCkgfQogICAgICAgICAgICAgICAgfSkKICAgICAgICAgICAgfQogICAgICAgIH0KICAgICAgICB3cml0ZShrZXkoc2NvcGUpLCBkYXRhLnRvU3RyaW5nKCkpCiAgICB9Cn0K', 'composeApp/src/commonMain/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSyncStorage.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKLyoqIERldmljZS1vbmx5IHN0b3JhZ2UuIFRoZXNlIHJlY29yZHMgYW5kIHRoZSBlbmFibGVkIGZsYWcgYXJlIG5ldmVyIHN5bmNlZC4gKi8KaW50ZXJuYWwgZXhwZWN0IG9iamVjdCBPbW5pYVByZWZlcmVuY2VzU3luY1N0b3JhZ2UgewogICAgZnVuIGxvYWQoa2V5OiBTdHJpbmcpOiBTdHJpbmc/CiAgICBmdW4gc2F2ZShrZXk6IFN0cmluZywgdmFsdWU6IFN0cmluZykKICAgIGZ1biBjbGVhcigpCn0K', 'composeApp/src/commonTest/kotlin/com/nuvio/app/core/sync/OmniaSharedPreferencesPolicyTest.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGtvdGxpbi50ZXN0LlRlc3QKaW1wb3J0IGtvdGxpbi50ZXN0LmFzc2VydEVxdWFscwppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RmFsc2UKaW1wb3J0IGtvdGxpbi50ZXN0LmFzc2VydFRydWUKaW1wb3J0IGtvdGxpbi50ZXN0LmFzc2VydEZhaWxzV2l0aAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbk9iamVjdAppbXBvcnQga290bGlueC5zZXJpYWxpemF0aW9uLmpzb24uSnNvbkFycmF5CmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi5Kc29uUHJpbWl0aXZlCgpjbGFzcyBPbW5pYVNoYXJlZFByZWZlcmVuY2VzUG9saWN5VGVzdCB7CiAgICBAVGVzdCBmdW4gcHVibGljQ2F0YWxvZ0lkZW50aWZpZXJzQXJlU2hhcmVhYmxlKCkgewogICAgICAgIGFzc2VydFRydWUoaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkoIm9yZy5vbW5pYS5pbmRpYSIsIDUxMikpCiAgICAgICAgYXNzZXJ0VHJ1ZShpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eSgibW92aWU6cG9wdWxhci9oaSIsIDEwMjQpKQogICAgfQogICAgQFRlc3QgZnVuIGNvbmZpZ3VyZWRFbmRwb2ludFVybHNTdGF5T3V0T2ZQcmVmZXJlbmNlcygpIHsKICAgICAgICBhc3NlcnRGYWxzZShpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eSgiaHR0cHM6Ly9zeW50aGV0aWMuZXhhbXBsZS91L3ByaXZhdGUvbWFuaWZlc3QuanNvbiIsIDEwMjQpKQogICAgICAgIGFzc2VydEZhbHNlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJhZGRvbj90b2tlbj1zeW50aGV0aWMiLCA1MTIpKQogICAgICAgIGFzc2VydEZhbHNlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJhZGRvbiNzeW50aGV0aWMiLCA1MTIpKQogICAgfQogICAgQFRlc3QgZnVuIGludmFsaWRPck92ZXJzaXplZElkZW50aXRpZXNBcmVOb3RTaGFyZWQoKSB7CiAgICAgICAgYXNzZXJ0RmFsc2UoaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkoIiAiLCA1MTIpKQogICAgICAgIGFzc2VydEZhbHNlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJhYiIsIDEpKQogICAgICAgIGFzc2VydEZhbHNlKGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KCJhXG5iIiwgNTEyKSkKICAgICAgICBhc3NlcnRGYWxzZShpc1NoYXJlYWJsZUNhdGFsb2dJZGVudGl0eSgiYVxcYiIsIDUxMikpCiAgICB9CiAgICBwcml2YXRlIGZ1biByb3coaWQ6IFN0cmluZywgZW5hYmxlZDogQm9vbGVhbiA9IHRydWUsIHRpdGxlOiBTdHJpbmcgPSAiIiwgb3JkZXI6IEludCA9IDApID0gSnNvbk9iamVjdChtYXBPZigKICAgICAgICAiYWRkb25faWQiIHRvIEpzb25QcmltaXRpdmUoInN5bnRoZXRpYy1hZGRvbiIpLCAidHlwZSIgdG8gSnNvblByaW1pdGl2ZSgibW92aWUiKSwgImNhdGFsb2dfaWQiIHRvIEpzb25QcmltaXRpdmUoaWQpLAogICAgICAgICJlbmFibGVkIiB0byBKc29uUHJpbWl0aXZlKGVuYWJsZWQpLCAiY3VzdG9tX3RpdGxlIiB0byBKc29uUHJpbWl0aXZlKHRpdGxlKSwgIm9yZGVyIiB0byBKc29uUHJpbWl0aXZlKG9yZGVyKSwKICAgICAgICAiaXNfY29sbGVjdGlvbiIgdG8gSnNvblByaW1pdGl2ZShmYWxzZSksICJjb2xsZWN0aW9uX2lkIiB0byBKc29uUHJpbWl0aXZlKCIiKSwKICAgICkpCiAgICBwcml2YXRlIGZ1biBob21lKHZhcmFyZyByb3dzOiBKc29uT2JqZWN0KSA9IEpzb25PYmplY3QobWFwT2YoImhvbWVDYXRhbG9ncyIgdG8gSnNvbkFycmF5KHJvd3MudG9MaXN0KCkpKSkKICAgIHByaXZhdGUgZnVuIG1lcmdlSG9tZShiYXNlOiBKc29uT2JqZWN0LCBsb2NhbDogSnNvbk9iamVjdCwgcmVtb3RlOiBKc29uT2JqZWN0KSA9IG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMoYmFzZSwgbG9jYWwsIHJlbW90ZSwgc2V0T2YoImhvbWVDYXRhbG9ncyIpKVsiaG9tZUNhdGFsb2dzIl0gYXMgSnNvbkFycmF5CiAgICBwcml2YXRlIHZhbCBrZXlzID0gc2V0T2YoImhlcm9FbmFibGVkIiwgImNvbnRpbnVlV2F0Y2hpbmdWaXNpYmxlIikKICAgIHByaXZhdGUgZnVuIHByZWZzKGhlcm86IEJvb2xlYW4sIHdhdGNoaW5nOiBCb29sZWFuKSA9IEpzb25PYmplY3QobWFwT2YoImhlcm9FbmFibGVkIiB0byBKc29uUHJpbWl0aXZlKGhlcm8pLCAiY29udGludWVXYXRjaGluZ1Zpc2libGUiIHRvIEpzb25QcmltaXRpdmUod2F0Y2hpbmcpKSkKICAgIHByaXZhdGUgdmFsIHNjb3BlID0gU2hhcmVkUHJlZmVyZW5jZXNTY29wZSgiaXNvbGF0ZWQtc3ludGhldGljLW93bmVyIiwgMSkKCiAgICBAVGVzdCBmdW4gZGlzYWJsZWREZXZpY2VSZWplY3RzQW5JbmZsaWdodFJlc3BvbnNlKCkgewogICAgICAgIGFzc2VydEZhbHNlKGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCAyKSwgc2NvcGUsIDIsIGZhbHNlKSkKICAgIH0KICAgIEBUZXN0IGZ1biBkaXNhYmxpbmdBbmRSZWVuYWJsaW5nSW52YWxpZGF0ZXNPbGRlclJlcXVlc3RzKCkgewogICAgICAgIGFzc2VydEZhbHNlKGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCAyKSwgc2NvcGUsIDQsIHRydWUpKQogICAgfQogICAgQFRlc3QgZnVuIGFjY291bnRTd2l0Y2hSZWplY3RzUHJldmlvdXNBY2NvdW50c1Jlc3BvbnNlKCkgewogICAgICAgIGFzc2VydEZhbHNlKGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCAyKSwgU2hhcmVkUHJlZmVyZW5jZXNTY29wZSgiYW5vdGhlci1vd25lciIsIDEpLCAyLCB0cnVlKSkKICAgIH0KICAgIEBUZXN0IGZ1biBwcm9maWxlU3dpdGNoUmVqZWN0c1ByZXZpb3VzUHJvZmlsZXNSZXNwb25zZSgpIHsKICAgICAgICBhc3NlcnRGYWxzZShjYW5BcHBseVNoYXJlZFByZWZlcmVuY2VzKFNoYXJlZFByZWZlcmVuY2VzUmVxdWVzdChzY29wZSwgMiksIHNjb3BlLmNvcHkocHJvZmlsZUlkID0gMiksIDIsIHRydWUpKQogICAgfQogICAgQFRlc3QgZnVuIHNpZ25PdXRSZWplY3RzUGVuZGluZ1Jlc3BvbnNlKCkgewogICAgICAgIGFzc2VydEZhbHNlKGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCAyKSwgbnVsbCwgMiwgdHJ1ZSkpCiAgICB9CiAgICBAVGVzdCBmdW4gY3VycmVudEVuYWJsZWRTY29wZUFjY2VwdHNJdHNSZXNwb25zZSgpIHsKICAgICAgICBhc3NlcnRUcnVlKGNhbkFwcGx5U2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNSZXF1ZXN0KHNjb3BlLCAyKSwgc2NvcGUsIDIsIHRydWUpKQogICAgfQogICAgQFRlc3QgZnVuIHVucmVsYXRlZENvbmN1cnJlbnRFZGl0c1N1cnZpdmUoKSB7CiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKGZhbHNlLCBmYWxzZSksIG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMocHJlZnModHJ1ZSwgdHJ1ZSksIHByZWZzKGZhbHNlLCB0cnVlKSwgcHJlZnModHJ1ZSwgZmFsc2UpLCBrZXlzKSkKICAgIH0KICAgIEBUZXN0IGZ1biB1bnRvdWNoZWRMb2NhbFZhbHVlc0RvTm90UmV2ZXJ0UmVtb3RlQ2hhbmdlcygpIHsKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsIGZhbHNlKSwgbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhwcmVmcyh0cnVlLCB0cnVlKSwgcHJlZnModHJ1ZSwgdHJ1ZSksIHByZWZzKGZhbHNlLCBmYWxzZSksIGtleXMpKQogICAgfQogICAgQFRlc3QgZnVuIGRlbGliZXJhdGVMb2NhbENoYW5nZVdpbnNUaGVTYW1lRmllbGQoKSB7CiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKGZhbHNlLCBmYWxzZSksIG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMocHJlZnModHJ1ZSwgdHJ1ZSksIHByZWZzKGZhbHNlLCB0cnVlKSwgcHJlZnModHJ1ZSwgZmFsc2UpLCBrZXlzKSkKICAgIH0KICAgIEBUZXN0IGZ1biB1bnN1cHBvcnRlZFJlbW90ZUZpZWxkc0FyZVJldGFpbmVkKCkgewogICAgICAgIHZhbCByZW1vdGUgPSBKc29uT2JqZWN0KHByZWZzKHRydWUsIHRydWUpICsgKCJzdWJ0aXRsZUxhbmd1YWdlIiB0byBKc29uUHJpbWl0aXZlKCJoaSIpKSkKICAgICAgICBhc3NlcnRFcXVhbHMoImhpIiwgKG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMocHJlZnModHJ1ZSwgdHJ1ZSksIHByZWZzKGZhbHNlLCB0cnVlKSwgcmVtb3RlLCBrZXlzKVsic3VidGl0bGVMYW5ndWFnZSJdIGFzIEpzb25QcmltaXRpdmUpLmNvbnRlbnQpCiAgICB9CiAgICBAVGVzdCBmdW4gbWlzc2luZ0Jhc2VsaW5lTmV2ZXJVcGxvYWRzRGVmYXVsdHNBc0NoYW5nZXMoKSB7CiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPElsbGVnYWxBcmd1bWVudEV4Y2VwdGlvbj4geyBtZXJnZVNoYXJlZFByZWZlcmVuY2VzKG51bGwsIHByZWZzKHRydWUsIHRydWUpLCBwcmVmcyhmYWxzZSwgZmFsc2UpLCBrZXlzKSB9CiAgICB9CiAgICBAVGVzdCBmdW4gdW5zdXBwb3J0ZWRMb2NhbEZpZWxkc0FyZVJlamVjdGVkKCkgewogICAgICAgIHZhbCBsb2NhbCA9IEpzb25PYmplY3QobWFwT2YoImRlY29kZXIiIHRvIEpzb25QcmltaXRpdmUoImhhcmR3YXJlIikpKQogICAgICAgIGFzc2VydEZhaWxzV2l0aDxJbGxlZ2FsQXJndW1lbnRFeGNlcHRpb24+IHsgbWVyZ2VTaGFyZWRQcmVmZXJlbmNlcyhKc29uT2JqZWN0KGVtcHR5TWFwKCkpLCBsb2NhbCwgSnNvbk9iamVjdChlbXB0eU1hcCgpKSwga2V5cykgfQogICAgfQogICAgQFRlc3QgZnVuIG9wdGluZ0luQ2FuRXhwbGljaXRseUNob29zZVNhdmVkU2V0dGluZ3MoKSB7CiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKGZhbHNlLCBmYWxzZSksIGluaXRpYWxTaGFyZWRQcmVmZXJlbmNlcyhTaGFyZWRQcmVmZXJlbmNlc0luaXRpYWxDaG9pY2UuVXNlU2F2ZWRTZXR0aW5ncywgcHJlZnModHJ1ZSwgdHJ1ZSksIHByZWZzKGZhbHNlLCBmYWxzZSksIGtleXMpKQogICAgfQogICAgQFRlc3QgZnVuIGNob29zaW5nVGhpc0RldmljZVByZXNlcnZlc0ZpZWxkc0l0Q2Fubm90UmVwcmVzZW50KCkgewogICAgICAgIHZhbCByZW1vdGUgPSBKc29uT2JqZWN0KHByZWZzKGZhbHNlLCBmYWxzZSkgKyAoInN1YnRpdGxlTGFuZ3VhZ2UiIHRvIEpzb25QcmltaXRpdmUoImhpIikpKQogICAgICAgIHZhbCBtZXJnZWQgPSBpbml0aWFsU2hhcmVkUHJlZmVyZW5jZXMoU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLlVzZVRoaXNEZXZpY2UsIHByZWZzKHRydWUsIHRydWUpLCByZW1vdGUsIGtleXMpCiAgICAgICAgYXNzZXJ0RXF1YWxzKEpzb25QcmltaXRpdmUodHJ1ZSksIG1lcmdlZFsiaGVyb0VuYWJsZWQiXSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZSgiaGkiKSwgbWVyZ2VkWyJzdWJ0aXRsZUxhbmd1YWdlIl0pCiAgICB9CiAgICBAVGVzdCBmdW4gcmVtb3RlT21pc3Npb25zRG9Ob3RDbGVhckxvY2FsRGVmYXVsdHMoKSB7CiAgICAgICAgYXNzZXJ0RXF1YWxzKGVtcHR5TWFwKCksIGFwcGxpY2FibGVTaGFyZWRQcmVmZXJlbmNlcyhKc29uT2JqZWN0KGVtcHR5TWFwKCkpLCBrZXlzKSkKICAgIH0KICAgIEBUZXN0IGZ1biBoYXJkd2FyZUFuZE9wdEluU3RhdGVDYW5ub3RCZVN5bmNlZCgpIHsKICAgICAgICBhc3NlcnRGYWxzZSgiZGVjb2RlciIgaW4gc2hhcmVkUHJlZmVyZW5jZUtleXMpCiAgICAgICAgYXNzZXJ0RmFsc2UoImJ1ZmZlclNpemUiIGluIHNoYXJlZFByZWZlcmVuY2VLZXlzKQogICAgICAgIGFzc2VydEZhbHNlKCJlbmFibGVkIiBpbiBzaGFyZWRQcmVmZXJlbmNlS2V5cykKICAgICAgICBhc3NlcnRGYWxzZSgicmVhbERlYnJpZEFwaUtleSIgaW4gc2hhcmVkUHJlZmVyZW5jZUtleXMpCiAgICB9CiAgICBAVGVzdCBmdW4gYmxhbmtPd25lckFuZEludmFsaWRQcm9maWxlc0FyZVJlamVjdGVkKCkgewogICAgICAgIGFzc2VydEZhaWxzV2l0aDxJbGxlZ2FsQXJndW1lbnRFeGNlcHRpb24+IHsgU2hhcmVkUHJlZmVyZW5jZXNTY29wZSgiIiwgMSkgfQogICAgICAgIGFzc2VydEZhaWxzV2l0aDxJbGxlZ2FsQXJndW1lbnRFeGNlcHRpb24+IHsgU2hhcmVkUHJlZmVyZW5jZXNTY29wZSgib3duZXIiLCAwKSB9CiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPElsbGVnYWxBcmd1bWVudEV4Y2VwdGlvbj4geyBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCJvd25lciIsIDcpIH0KICAgIH0KICAgIEBUZXN0IGZ1biBuZWdhdGl2ZVJldmlzaW9uSXNSZWplY3RlZCgpIHsKICAgICAgICBhc3NlcnRGYWlsc1dpdGg8SWxsZWdhbEFyZ3VtZW50RXhjZXB0aW9uPiB7IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoLTEsIEpzb25PYmplY3QoZW1wdHlNYXAoKSkpIH0KICAgIH0KICAgIEBUZXN0IGZ1biBjb25jdXJyZW50Q2hhbmdlc1RvRGlmZmVyZW50Q2F0YWxvZ3NTdXJ2aXZlKCkgewogICAgICAgIHZhbCByZXN1bHQ9bWVyZ2VIb21lKGhvbWUocm93KCJhIikscm93KCJiIixvcmRlcj0xKSksaG9tZShyb3coImEiLGVuYWJsZWQ9ZmFsc2UpLHJvdygiYiIsb3JkZXI9MSkpLGhvbWUocm93KCJhIikscm93KCJiIix0aXRsZT0iUmVtb3RlIHRpdGxlIixvcmRlcj0xKSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKEpzb25QcmltaXRpdmUoZmFsc2UpLChyZXN1bHRbMF0gYXMgSnNvbk9iamVjdClbImVuYWJsZWQiXSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZSgiUmVtb3RlIHRpdGxlIiksKHJlc3VsdFsxXSBhcyBKc29uT2JqZWN0KVsiY3VzdG9tX3RpdGxlIl0pCiAgICB9CiAgICBAVGVzdCBmdW4gZGlmZmVyZW50RmllbGRzT25UaGVTYW1lQ2F0YWxvZ0FyZU1lcmdlZCgpIHsKICAgICAgICB2YWwgcmVzdWx0PW1lcmdlSG9tZShob21lKHJvdygiYSIpKSxob21lKHJvdygiYSIsZW5hYmxlZD1mYWxzZSkpLGhvbWUocm93KCJhIix0aXRsZT0iUmVtb3RlIHRpdGxlIikpKQogICAgICAgIGFzc2VydEVxdWFscyhKc29uUHJpbWl0aXZlKGZhbHNlKSwocmVzdWx0WzBdIGFzIEpzb25PYmplY3QpWyJlbmFibGVkIl0pCiAgICAgICAgYXNzZXJ0RXF1YWxzKEpzb25QcmltaXRpdmUoIlJlbW90ZSB0aXRsZSIpLChyZXN1bHRbMF0gYXMgSnNvbk9iamVjdClbImN1c3RvbV90aXRsZSJdKQogICAgfQogICAgQFRlc3QgZnVuIGFic2VudExvY2FsQ2F0YWxvZ0RvZXNOb3REZWxldGVBUmVtb3RlUm93KCkgewogICAgICAgIGFzc2VydEVxdWFscyhKc29uQXJyYXkobGlzdE9mKHJvdygiYSIpKSksbWVyZ2VIb21lKGhvbWUocm93KCJhIikpLGhvbWUoKSxob21lKHJvdygiYSIpKSkpCiAgICB9CiAgICBAVGVzdCBmdW4gbmV3UmVtb3RlQ2F0YWxvZ0lzUHJlc2VydmVkV2hpbGVFZGl0aW5nQW5vdGhlcigpIHsKICAgICAgICB2YWwgcmVzdWx0PW1lcmdlSG9tZShob21lKHJvdygiYSIpKSxob21lKHJvdygiYSIsZW5hYmxlZD1mYWxzZSkpLGhvbWUocm93KCJhIikscm93KCJuZXciLG9yZGVyPTEpKSkKICAgICAgICBhc3NlcnRFcXVhbHMoMixyZXN1bHQuc2l6ZSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZSgibmV3IiksKHJlc3VsdFsxXSBhcyBKc29uT2JqZWN0KVsiY2F0YWxvZ19pZCJdKQogICAgfQogICAgQFRlc3QgZnVuIG5ld0NvbmZsaWN0aW5nQ2F0YWxvZ0RvZXNOb3RUcmVhdERlZmF1bHRzQXNJbnRlbnRpb25hbEVkaXRzKCkgewogICAgICAgIGFzc2VydEZhaWxzV2l0aDxTaGFyZWRQcmVmZXJlbmNlc0Nob2ljZVJlcXVpcmVkRXhjZXB0aW9uPiB7IG1lcmdlSG9tZShob21lKCksaG9tZShyb3coImEiKSksaG9tZShyb3coImEiLGVuYWJsZWQ9ZmFsc2UpKSkgfQogICAgfQogICAgQFRlc3QgZnVuIGR1cGxpY2F0ZUNhdGFsb2dJZGVudGl0aWVzQXJlUmVqZWN0ZWQoKSB7CiAgICAgICAgYXNzZXJ0RmFpbHNXaXRoPElsbGVnYWxBcmd1bWVudEV4Y2VwdGlvbj4geyBtZXJnZUhvbWUoaG9tZSgpLGhvbWUocm93KCJhIikscm93KCJhIikpLGhvbWUoKSkgfQogICAgfQogICAgQFRlc3QgZnVuIGlkZW50aXR5RG9lc05vdENvbmZ1c2VDb2xvbnNJbnNpZGVJZGVudGlmaWVyQ29tcG9uZW50cygpIHsKICAgICAgICB2YWwgYT1Kc29uT2JqZWN0KHJvdygiYyIpICsgKCJhZGRvbl9pZCIgdG8gSnNvblByaW1pdGl2ZSgiYTpiIikpICsgKCJ0eXBlIiB0byBKc29uUHJpbWl0aXZlKCJtb3ZpZSIpKSkKICAgICAgICB2YWwgYj1Kc29uT2JqZWN0KHJvdygibW92aWU6YyIpICsgKCJhZGRvbl9pZCIgdG8gSnNvblByaW1pdGl2ZSgiYSIpKSArICgidHlwZSIgdG8gSnNvblByaW1pdGl2ZSgiYiIpKSkKICAgICAgICBhc3NlcnRFcXVhbHMoMixtZXJnZUhvbWUoaG9tZSgpLGhvbWUoYSxiKSxob21lKCkpLnNpemUpCiAgICB9CiAgICBAVGVzdCBmdW4gcGFydGlhbEV4cG9ydHNDYW5ub3RFcmFzZVByZWZlcmVuY2VzVGhleUZhaWxlZFRvUmVhZCgpIHsKICAgICAgICBhc3NlcnRGYWlsc1dpdGg8SWxsZWdhbEFyZ3VtZW50RXhjZXB0aW9uPiB7IG1lcmdlU2hhcmVkUHJlZmVyZW5jZXMocHJlZnModHJ1ZSx0cnVlKSxKc29uT2JqZWN0KG1hcE9mKCJoZXJvRW5hYmxlZCIgdG8gSnNvblByaW1pdGl2ZShmYWxzZSkpKSxwcmVmcyh0cnVlLGZhbHNlKSxrZXlzKSB9CiAgICB9CiAgICBAVGVzdCBmdW4gb21pdHRlZENhdGFsb2dEZWZhdWx0c0RvTm90QmVjb21lSW50ZW50aW9uYWxMb2NhbENoYW5nZXMoKSB7CiAgICAgICAgdmFsIHNwYXJzZT1Kc29uT2JqZWN0KHJvdygiYSIpLmZpbHRlcktleXMgeyBpdCAhaW4gc2V0T2YoImVuYWJsZWQiLCJjdXN0b21fdGl0bGUiLCJpc19jb2xsZWN0aW9uIiwiY29sbGVjdGlvbl9pZCIpIH0pCiAgICAgICAgdmFsIHJlc3VsdD1tZXJnZUhvbWUoaG9tZShzcGFyc2UpLGhvbWUocm93KCJhIikpLGhvbWUocm93KCJhIixlbmFibGVkPWZhbHNlLHRpdGxlPSJSZW1vdGUgdGl0bGUiKSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKEpzb25QcmltaXRpdmUoZmFsc2UpLChyZXN1bHRbMF0gYXMgSnNvbk9iamVjdClbImVuYWJsZWQiXSkKICAgICAgICBhc3NlcnRFcXVhbHMoSnNvblByaW1pdGl2ZSgiUmVtb3RlIHRpdGxlIiksKHJlc3VsdFswXSBhcyBKc29uT2JqZWN0KVsiY3VzdG9tX3RpdGxlIl0pCiAgICB9Cn0K', 'composeApp/src/commonTest/kotlin/com/nuvio/app/core/sync/OmniaSharedPreferencesEngineTest.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGtvdGxpbi50ZXN0LlRlc3QKaW1wb3J0IGtvdGxpbi50ZXN0LmFzc2VydEVxdWFscwppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RmFsc2UKaW1wb3J0IGtvdGxpbi50ZXN0LmFzc2VydFRydWUKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy50ZXN0LnJ1blRlc3QKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25PYmplY3QKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25QcmltaXRpdmUKCmNsYXNzIE9tbmlhU2hhcmVkUHJlZmVyZW5jZXNFbmdpbmVUZXN0IHsKICAgIHByaXZhdGUgZnVuIHByZWZzKGhlcm86IEJvb2xlYW4sIHdhdGNoaW5nOiBCb29sZWFuKSA9IEpzb25PYmplY3QobWFwT2YoImhlcm9FbmFibGVkIiB0byBKc29uUHJpbWl0aXZlKGhlcm8pLCAiY29udGludWVXYXRjaGluZ1Zpc2libGUiIHRvIEpzb25QcmltaXRpdmUod2F0Y2hpbmcpKSkKICAgIHByaXZhdGUgaW5uZXIgY2xhc3MgRml4dHVyZSB7CiAgICAgICAgdmFyIGFjdGl2ZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZT8gPSBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCJzeW50aGV0aWMtb3duZXIiLCAxKQogICAgICAgIHZhciBsb2NhbCA9IHByZWZzKHRydWUsIHRydWUpCiAgICAgICAgdmFyIHJlbW90ZSA9IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMCwgSnNvbk9iamVjdChlbXB0eU1hcCgpKSkKICAgICAgICB2YXIgcHVsbHMgPSAwCiAgICAgICAgdmFyIHB1c2hlcyA9IDAKICAgICAgICB2YXIgYXBwbGllcyA9IDAKICAgICAgICB2YXIgYWZ0ZXJQdWxsOiBzdXNwZW5kICgpIC0+IFVuaXQgPSB7fQogICAgICAgIHZhciBhZnRlclB1c2g6IHN1c3BlbmQgKCkgLT4gVW5pdCA9IHt9CiAgICAgICAgdmFyIGNvbmZsaWN0cyA9IDAKICAgICAgICB2YWwgcmVjb3JkcyA9IG11dGFibGVNYXBPZjxTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCBTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkPigpCiAgICAgICAgdmFsIHN0b3JlID0gb2JqZWN0IDogU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFN0b3JlIHsKICAgICAgICAgICAgb3ZlcnJpZGUgZnVuIGxvYWQoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpID0gcmVjb3Jkc1tzY29wZV0gPzogU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCgpCiAgICAgICAgICAgIG92ZXJyaWRlIGZ1biBzYXZlKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCByZWNvcmQ6IFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQpIHsgcmVjb3Jkc1tzY29wZV0gPSByZWNvcmQgfQogICAgICAgIH0KICAgICAgICB2YWwgZGV2aWNlID0gb2JqZWN0IDogU2hhcmVkUHJlZmVyZW5jZXNEZXZpY2UgewogICAgICAgICAgICBvdmVycmlkZSB2YWwgc3VwcG9ydGVkS2V5cyA9IHNldE9mKCJoZXJvRW5hYmxlZCIsICJjb250aW51ZVdhdGNoaW5nVmlzaWJsZSIpCiAgICAgICAgICAgIG92ZXJyaWRlIGZ1biBjdXJyZW50U2NvcGUoKSA9IGFjdGl2ZQogICAgICAgICAgICBvdmVycmlkZSBzdXNwZW5kIGZ1biBleHBvcnQoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpID0gbG9jYWwKICAgICAgICAgICAgb3ZlcnJpZGUgc3VzcGVuZCBmdW4gYXBwbHkoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCBzdGlsbEN1cnJlbnQ6ICgpIC0+IEJvb2xlYW4pIHsKICAgICAgICAgICAgICAgIGlmIChzdGlsbEN1cnJlbnQoKSkgeyBsb2NhbCA9IEpzb25PYmplY3QobG9jYWwgKyBwcmVmZXJlbmNlcyk7IGFwcGxpZXMrKyB9CiAgICAgICAgICAgIH0KICAgICAgICB9CiAgICAgICAgdmFsIHRyYW5zcG9ydCA9IG9iamVjdCA6IFNoYXJlZFByZWZlcmVuY2VzVHJhbnNwb3J0IHsKICAgICAgICAgICAgb3ZlcnJpZGUgc3VzcGVuZCBmdW4gcHVsbChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSk6IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QgeyBwdWxscysrO2FmdGVyUHVsbCgpO3JldHVybiByZW1vdGUgfQogICAgICAgICAgICBvdmVycmlkZSBzdXNwZW5kIGZ1biBwdXNoKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCBleHBlY3RlZFJldmlzaW9uOiBMb25nLCBwcmVmZXJlbmNlczogSnNvbk9iamVjdCwgZXhwZWN0ZWRQcm9maWxlSW5zdGFuY2U6IFN0cmluZz8pOiBTaGFyZWRQcmVmZXJlbmNlc1B1c2hSZXN1bHQgewogICAgICAgICAgICAgICAgcHVzaGVzKys7YWZ0ZXJQdXNoKCkKICAgICAgICAgICAgICAgIGlmIChjb25mbGljdHMgPiAwKSB7IGNvbmZsaWN0cy0tO3JlbW90ZSA9IHJlbW90ZS5jb3B5KHJldmlzaW9uID0gcmVtb3RlLnJldmlzaW9uICsgMSk7cmV0dXJuIFNoYXJlZFByZWZlcmVuY2VzUHVzaFJlc3VsdCh0cnVlLCByZW1vdGUpIH0KICAgICAgICAgICAgICAgIGFzc2VydEVxdWFscyhyZW1vdGUucmV2aXNpb24sIGV4cGVjdGVkUmV2aXNpb24pCiAgICAgICAgICAgICAgICBhc3NlcnRFcXVhbHMocmVtb3RlLnByb2ZpbGVJbnN0YW5jZSwgZXhwZWN0ZWRQcm9maWxlSW5zdGFuY2UpCiAgICAgICAgICAgICAgICByZW1vdGUgPSByZW1vdGUuY29weShyZXZpc2lvbiA9IHJlbW90ZS5yZXZpc2lvbiArIDEsIHByZWZlcmVuY2VzID0gcHJlZmVyZW5jZXMpCiAgICAgICAgICAgICAgICByZXR1cm4gU2hhcmVkUHJlZmVyZW5jZXNQdXNoUmVzdWx0KGZhbHNlLCByZW1vdGUpCiAgICAgICAgICAgIH0KICAgICAgICB9CiAgICAgICAgdmFsIGVuZ2luZSA9IE9tbmlhU2hhcmVkUHJlZmVyZW5jZXNFbmdpbmUoZGV2aWNlLCBzdG9yZSwgdHJhbnNwb3J0KQogICAgfQoKICAgIEBUZXN0IGZ1biByZXVzZWRQcm9maWxlU2xvdERvZXNOb3RJbmhlcml0QXV0b21hdGljU3luYygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVtb3RlPWYucmVtb3RlLmNvcHkocHJvZmlsZUluc3RhbmNlPSJvcmlnaW5hbC1wcm9maWxlIik7Zi5lbmdpbmUuZW5hYmxlKCkKICAgICAgICB2YWwgYmVmb3JlPWYuYXBwbGllczt2YWwgcHVzaGVzPWYucHVzaGVzCiAgICAgICAgZi5yZW1vdGU9U2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCgwLEpzb25PYmplY3QoZW1wdHlNYXAoKSksInJlcGxhY2VtZW50LXByb2ZpbGUiKQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzLGYuZW5naW5lLnN5bmNocm9uaXplKCkpCiAgICAgICAgYXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpO2Fzc2VydEVxdWFscyhiZWZvcmUsZi5hcHBsaWVzKTthc3NlcnRFcXVhbHMocHVzaGVzLGYucHVzaGVzKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyh0cnVlLHRydWUpLGYubG9jYWwpCiAgICB9CiAgICBAVGVzdCBmdW4gcHJvZmlsZVJlcGxhY2VtZW50RHVyaW5nQ29uZmxpY3RSZXF1aXJlc05ld0NvbnNlbnQoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLnJlbW90ZT1mLnJlbW90ZS5jb3B5KHByb2ZpbGVJbnN0YW5jZT0ib3JpZ2luYWwtcHJvZmlsZSIpO2YuZW5naW5lLmVuYWJsZSgpO2YubG9jYWw9cHJlZnMoZmFsc2UsdHJ1ZSkKICAgICAgICB2YWwgYmVmb3JlPWYuYXBwbGllcztmLmNvbmZsaWN0cz0xO2YuYWZ0ZXJQdXNoPXtmLnJlbW90ZT1mLnJlbW90ZS5jb3B5KHByb2ZpbGVJbnN0YW5jZT0icmVwbGFjZW1lbnQtcHJvZmlsZSIpfQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzLGYuZW5naW5lLnN5bmNocm9uaXplKCkpCiAgICAgICAgYXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpO2Fzc2VydEVxdWFscyhiZWZvcmUsZi5hcHBsaWVzKQogICAgfQogICAgQFRlc3QgZnVuIHByb2ZpbGVSZXBsYWNlbWVudER1cmluZ0ZpcnN0RW5hYmxlTmV2ZXJFbmFibGVzTmV3UHJvZmlsZSgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVtb3RlPWYucmVtb3RlLmNvcHkocHJvZmlsZUluc3RhbmNlPSJvcmlnaW5hbC1wcm9maWxlIik7Zi5jb25mbGljdHM9MQogICAgICAgIGYuYWZ0ZXJQdXNoPXtmLnJlbW90ZT1mLnJlbW90ZS5jb3B5KHByb2ZpbGVJbnN0YW5jZT0icmVwbGFjZW1lbnQtcHJvZmlsZSIpfQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuQ2hvb3NlSW5pdGlhbFNldHRpbmdzLGYuZW5naW5lLmVuYWJsZSgpKQogICAgICAgIGFzc2VydEZhbHNlKGYuc3RvcmUubG9hZChmLmFjdGl2ZSEhKS5lbmFibGVkKTthc3NlcnRFcXVhbHMoMCxmLmFwcGxpZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gZGVmYXVsdE9mZlBlcmZvcm1zTm9OZXR3b3JrQ2FsbHMoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTthc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZixmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKQogICAgICAgIGFzc2VydEVxdWFscygwLGYucHVsbHMpO2Fzc2VydEVxdWFscygwLGYucHVzaGVzKTthc3NlcnRFcXVhbHMoMCxmLmFwcGxpZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gc2F2ZWRTZXR0aW5nc1JlcXVpcmVBbkV4cGxpY2l0SW5pdGlhbENob2ljZSgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMSxwcmVmcyhmYWxzZSxmYWxzZSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MsZi5lbmdpbmUuZW5hYmxlKCkpCiAgICAgICAgYXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpO2Fzc2VydEVxdWFscyhwcmVmcyh0cnVlLHRydWUpLGYubG9jYWwpO2Fzc2VydEVxdWFscygwLGYucHVzaGVzKQogICAgfQogICAgQFRlc3QgZnVuIGZpcnN0RW5hYmxlQ2FuQ2hvb3NlU2F2ZWRTZXR0aW5ncygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMSxwcmVmcyhmYWxzZSxmYWxzZSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQsZi5lbmdpbmUuZW5hYmxlKFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZS5Vc2VTYXZlZFNldHRpbmdzKSkKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsZmFsc2UpLGYubG9jYWwpO2Fzc2VydFRydWUoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpO2Fzc2VydEVxdWFscygwLGYucHVzaGVzKQogICAgfQogICAgQFRlc3QgZnVuIGVtcHR5QWNjb3VudENhblVzZVRoZUN1cnJlbnREZXZpY2UoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTthc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCxmLmVuZ2luZS5lbmFibGUoKSkKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnModHJ1ZSx0cnVlKSxmLnJlbW90ZS5wcmVmZXJlbmNlcyk7YXNzZXJ0RXF1YWxzKDEsZi5wdXNoZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gZGVmYXVsdHNPbWl0dGVkQnlBbm90aGVyUGxhdGZvcm1Eb05vdEJlY29tZUxvY2FsRWRpdHMoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLnJlbW90ZT1TaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDEsSnNvbk9iamVjdChtYXBPZigiaGVyb0VuYWJsZWQiIHRvIEpzb25QcmltaXRpdmUoZmFsc2UpKSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQsZi5lbmdpbmUuZW5hYmxlKFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZS5Vc2VTYXZlZFNldHRpbmdzKSkKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsdHJ1ZSksZi5sb2NhbCkKICAgICAgICBmLnJlbW90ZT1TaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDIscHJlZnMoZmFsc2UsZmFsc2UpKQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2VkLGYuZW5naW5lLnN5bmNocm9uaXplKCkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKHByZWZzKGZhbHNlLGZhbHNlKSxmLmxvY2FsKTthc3NlcnRFcXVhbHMoMCxmLnB1c2hlcykKICAgIH0KICAgIEBUZXN0IGZ1biBkaXNhYmxlUHJlc2VydmVzQ3VycmVudFZhbHVlc0FuZFN0b3BzQm90aERpcmVjdGlvbnMoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLmVuZ2luZS5lbmFibGUoKTtmLmVuZ2luZS5kaXNhYmxlKCk7Zi5sb2NhbD1wcmVmcyhmYWxzZSx0cnVlKTtmLnJlbW90ZT1TaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDIscHJlZnModHJ1ZSxmYWxzZSkpCiAgICAgICAgdmFsIGJlZm9yZT1saXN0T2YoZi5wdWxscyxmLnB1c2hlcyxmLmFwcGxpZXMpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYsZi5lbmdpbmUuc3luY2hyb25pemUoKSk7YXNzZXJ0RXF1YWxzKGJlZm9yZSxsaXN0T2YoZi5wdWxscyxmLnB1c2hlcyxmLmFwcGxpZXMpKTthc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsdHJ1ZSksZi5sb2NhbCkKICAgIH0KICAgIEBUZXN0IGZ1biBkaXNhYmxlRHVyaW5nSW5pdGlhbFB1bGxDYW5ub3RCZVVuZG9uZUJ5SXRzUmVzcG9uc2UoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLmFmdGVyUHVsbD17Zi5lbmdpbmUuZGlzYWJsZSgpfQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuT2ZmLGYuZW5naW5lLmVuYWJsZSgpKQogICAgICAgIGFzc2VydEZhbHNlKGYuc3RvcmUubG9hZChmLmFjdGl2ZSEhKS5lbmFibGVkKTthc3NlcnRFcXVhbHMoMCxmLnB1c2hlcyk7YXNzZXJ0RXF1YWxzKDAsZi5hcHBsaWVzKQogICAgfQogICAgQFRlc3QgZnVuIGRpc2FibGVEdXJpbmdQdXNoUHJldmVudHNBcHBseWluZ1RoZVJlc3BvbnNlKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5lbmdpbmUuZW5hYmxlKCk7Zi5sb2NhbD1wcmVmcyhmYWxzZSx0cnVlKTt2YWwgYmVmb3JlPWYuYXBwbGllcwogICAgICAgIGYuYWZ0ZXJQdXNoPXtmLmVuZ2luZS5kaXNhYmxlKCl9CiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYsZi5lbmdpbmUuc3luY2hyb25pemUoKSkKICAgICAgICBhc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCk7YXNzZXJ0RXF1YWxzKGJlZm9yZSxmLmFwcGxpZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gYWNjb3VudFN3aXRjaER1cmluZ1B1bGxOZXZlckFwcGxpZXNUb1RoZU5ld0FjY291bnQoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTt2YWwgb3JpZ2luYWw9Zi5hY3RpdmUhITtmLmVuZ2luZS5lbmFibGUoKTt2YWwgYmVmb3JlPWYuYXBwbGllcwogICAgICAgIGYuYWZ0ZXJQdWxsPXtmLmFjdGl2ZT1TaGFyZWRQcmVmZXJlbmNlc1Njb3BlKCJvdGhlci1vd25lciIsMSk7Zi5lbmdpbmUucmVmcmVzaExvY2FsU3RhdGUoKX0KICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLk9mZixmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKTthc3NlcnRFcXVhbHMoYmVmb3JlLGYuYXBwbGllcykKICAgICAgICBhc3NlcnRGYWxzZShmLnN0b3JlLmxvYWQoZi5hY3RpdmUhISkuZW5hYmxlZCk7YXNzZXJ0VHJ1ZShmLnN0b3JlLmxvYWQob3JpZ2luYWwpLmVuYWJsZWQpCiAgICB9CiAgICBAVGVzdCBmdW4gcmV0dXJuaW5nVG9BbkFjY291bnRTdGlsbEludmFsaWRhdGVzSXRzT2xkUmVxdWVzdCgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO3ZhbCBvcmlnaW5hbD1mLmFjdGl2ZSEhO2YuZW5naW5lLmVuYWJsZSgpO3ZhbCBiZWZvcmU9Zi5hcHBsaWVzCiAgICAgICAgZi5hZnRlclB1bGw9e2YuYWN0aXZlPVNoYXJlZFByZWZlcmVuY2VzU2NvcGUoIm90aGVyLW93bmVyIiwxKTtmLmVuZ2luZS5yZWZyZXNoTG9jYWxTdGF0ZSgpO2YuYWN0aXZlPW9yaWdpbmFsO2YuZW5naW5lLnJlZnJlc2hMb2NhbFN0YXRlKCl9CiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYsZi5lbmdpbmUuc3luY2hyb25pemUoKSk7YXNzZXJ0RXF1YWxzKGJlZm9yZSxmLmFwcGxpZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gY29uY3VycmVudFVucmVsYXRlZFNldHRpbmdzQXJlTWVyZ2VkKCkgPSBydW5UZXN0IHsKICAgICAgICB2YWwgZj1GaXh0dXJlKCk7Zi5lbmdpbmUuZW5hYmxlKCk7Zi5sb2NhbD1wcmVmcyhmYWxzZSx0cnVlKTtmLnJlbW90ZT1TaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDIscHJlZnModHJ1ZSxmYWxzZSkpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQsZi5lbmdpbmUuc3luY2hyb25pemUoKSkKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsZmFsc2UpLGYucmVtb3RlLnByZWZlcmVuY2VzKTthc3NlcnRFcXVhbHMocHJlZnMoZmFsc2UsZmFsc2UpLGYubG9jYWwpCiAgICB9CiAgICBAVGVzdCBmdW4gY2hhbmdlc01hZGVEdXJpbmdUaGVSZXF1ZXN0UmVtYWluTG9jYWxGb3JUaGVOZXh0U3luYygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YuZW5naW5lLmVuYWJsZSgpO2YucmVtb3RlPVNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMixwcmVmcyh0cnVlLGZhbHNlKSkKICAgICAgICBmLmFmdGVyUHVsbD17Zi5sb2NhbD1wcmVmcyhmYWxzZSx0cnVlKX0KICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCxmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyhmYWxzZSxmYWxzZSksZi5sb2NhbCkKICAgICAgICBhc3NlcnRFcXVhbHMocHJlZnModHJ1ZSxmYWxzZSksZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmJhc2VsaW5lISEucHJlZmVyZW5jZXMpCiAgICAgICAgZi5hZnRlclB1bGw9e30KICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNlZCxmLmVuZ2luZS5zeW5jaHJvbml6ZSgpKQogICAgICAgIGFzc2VydEVxdWFscyhwcmVmcyhmYWxzZSxmYWxzZSksZi5yZW1vdGUucHJlZmVyZW5jZXMpCiAgICB9CiAgICBAVGVzdCBmdW4gbmV0d29ya0ZhaWx1cmVEb2VzTm90RW5hYmxlU3luY09yUmVwb3J0U3VjY2VzcygpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YuYWZ0ZXJQdWxsPXt0aHJvdyBJbGxlZ2FsU3RhdGVFeGNlcHRpb24oIlN5bnRoZXRpYyBvZmZsaW5lIil9CiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5FcnJvcixmLmVuZ2luZS5lbmFibGUoKSk7YXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpCiAgICB9CiAgICBAVGVzdCBmdW4gcmV0cmllc0FyZUJvdW5kZWRBbmROZXZlckNsYWltU3VjY2Vzc09uUmVwZWF0ZWRDb25mbGljdCgpID0gcnVuVGVzdCB7CiAgICAgICAgdmFsIGY9Rml4dHVyZSgpO2YuY29uZmxpY3RzPTgKICAgICAgICBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yLGYuZW5naW5lLmVuYWJsZSgpKTthc3NlcnRFcXVhbHMoMyxmLnB1c2hlcyk7YXNzZXJ0RmFsc2UoZi5zdG9yZS5sb2FkKGYuYWN0aXZlISEpLmVuYWJsZWQpCiAgICB9CiAgICBAVGVzdCBmdW4gbWlzc2luZ0Jhc2VsaW5lQ2Fubm90VXBsb2FkRGV2aWNlRGVmYXVsdHMoKSA9IHJ1blRlc3QgewogICAgICAgIHZhbCBmPUZpeHR1cmUoKTtmLnJlY29yZHNbZi5hY3RpdmUhIV09U2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCh0cnVlLG51bGwpCiAgICAgICAgYXNzZXJ0RXF1YWxzKFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MsZi5lbmdpbmUuc3luY2hyb25pemUoKSk7YXNzZXJ0RXF1YWxzKDAsZi5wdWxscyk7YXNzZXJ0RXF1YWxzKDAsZi5wdXNoZXMpCiAgICB9Cn0K', 'composeApp/src/commonTest/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSyncRecordStoreTest.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGtvdGxpbi50ZXN0LlRlc3QKaW1wb3J0IGtvdGxpbi50ZXN0LmFzc2VydEVxdWFscwppbXBvcnQga290bGluLnRlc3QuYXNzZXJ0RmFsc2UKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25PYmplY3QKaW1wb3J0IGtvdGxpbnguc2VyaWFsaXphdGlvbi5qc29uLkpzb25QcmltaXRpdmUKCmNsYXNzIE9tbmlhUHJlZmVyZW5jZXNTeW5jUmVjb3JkU3RvcmVUZXN0IHsKICAgIHByaXZhdGUgdmFsIHZhbHVlcyA9IG11dGFibGVNYXBPZjxTdHJpbmcsIFN0cmluZz4oKQogICAgcHJpdmF0ZSB2YWwgc3RvcmUgPSBPbW5pYVByZWZlcmVuY2VzU3luY1JlY29yZFN0b3JlKHZhbHVlczo6Z2V0KSB7IGtleSwgdmFsdWUgLT4gdmFsdWVzW2tleV0gPSB2YWx1ZSB9CiAgICBwcml2YXRlIHZhbCBzY29wZSA9IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUoInN5bnRoZXRpYy1vd25lciIsIDEpCiAgICBAVGVzdCBmdW4gcHJvZmlsZUluc3RhbmNlUm91bmRUcmlwc1dpdGhUaGVCYXNlbGluZSgpIHsKICAgICAgICB2YWwgcmVjb3JkPVNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQodHJ1ZSxTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDMsSnNvbk9iamVjdChlbXB0eU1hcCgpKSwic3ludGhldGljLXByb2ZpbGUtaW5zdGFuY2UiKSkKICAgICAgICBzdG9yZS5zYXZlKHNjb3BlLHJlY29yZCk7YXNzZXJ0RXF1YWxzKHJlY29yZCxzdG9yZS5sb2FkKHNjb3BlKSkKICAgIH0KICAgIEBUZXN0IGZ1biBhYnNlbnRSZWNvcmREZWZhdWx0c1RvT2ZmKCkgeyBhc3NlcnRFcXVhbHMoU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCgpLCBzdG9yZS5sb2FkKHNjb3BlKSkgfQogICAgQFRlc3QgZnVuIG1hbGZvcm1lZFJlY29yZERlZmF1bHRzVG9PZmYoKSB7CiAgICAgICAgdmFsdWVzWyJvbW5pYS5zZXR0aW5ncy5zeW5jLnYxLnN5bnRoZXRpYy1vd25lci4xIl0gPSAie2ludmFsaWQiCiAgICAgICAgYXNzZXJ0RmFsc2Uoc3RvcmUubG9hZChzY29wZSkuZW5hYmxlZCkKICAgIH0KICAgIEBUZXN0IGZ1biB1bmtub3duUmVjb3JkVmVyc2lvbkRlZmF1bHRzVG9PZmYoKSB7CiAgICAgICAgdmFsdWVzWyJvbW5pYS5zZXR0aW5ncy5zeW5jLnYxLnN5bnRoZXRpYy1vd25lci4xIl0gPSAie1widmVyc2lvblwiOjk5LFwiZW5hYmxlZFwiOnRydWV9IgogICAgICAgIGFzc2VydEZhbHNlKHN0b3JlLmxvYWQoc2NvcGUpLmVuYWJsZWQpCiAgICB9CiAgICBAVGVzdCBmdW4gb3B0SW5BbmRCYXNlbGluZVJvdW5kVHJpcEV4YWN0bHkoKSB7CiAgICAgICAgdmFsIHJlY29yZCA9IFNoYXJlZFByZWZlcmVuY2VzTG9jYWxSZWNvcmQodHJ1ZSwgU2hhcmVkUHJlZmVyZW5jZXNTbmFwc2hvdCg3LCBKc29uT2JqZWN0KG1hcE9mKCJoZXJvRW5hYmxlZCIgdG8gSnNvblByaW1pdGl2ZShmYWxzZSkpKSkpCiAgICAgICAgc3RvcmUuc2F2ZShzY29wZSwgcmVjb3JkKTthc3NlcnRFcXVhbHMocmVjb3JkLCBzdG9yZS5sb2FkKHNjb3BlKSkKICAgIH0KICAgIEBUZXN0IGZ1biBvdGhlckFjY291bnRzQW5kUHJvZmlsZXNEb05vdFNoYXJlT3B0SW4oKSB7CiAgICAgICAgc3RvcmUuc2F2ZShzY29wZSwgU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZCh0cnVlLCBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KDAsIEpzb25PYmplY3QoZW1wdHlNYXAoKSkpKSkKICAgICAgICBhc3NlcnRGYWxzZShzdG9yZS5sb2FkKHNjb3BlLmNvcHkob3duZXIgPSAib3RoZXItb3duZXIiKSkuZW5hYmxlZCkKICAgICAgICBhc3NlcnRGYWxzZShzdG9yZS5sb2FkKHNjb3BlLmNvcHkocHJvZmlsZUlkID0gMikpLmVuYWJsZWQpCiAgICB9CiAgICBAVGVzdCBmdW4gZGlzYWJsaW5nUmV0YWluc1RoZUJhc2VsaW5lV2l0aG91dFJlc2V0dGluZ1ByZWZlcmVuY2VzKCkgewogICAgICAgIHZhbCBiYXNlbGluZSA9IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QoMywgSnNvbk9iamVjdChtYXBPZigiaGVyb0VuYWJsZWQiIHRvIEpzb25QcmltaXRpdmUoZmFsc2UpKSkpCiAgICAgICAgc3RvcmUuc2F2ZShzY29wZSwgU2hhcmVkUHJlZmVyZW5jZXNMb2NhbFJlY29yZChmYWxzZSwgYmFzZWxpbmUpKQogICAgICAgIGFzc2VydEVxdWFscyhTaGFyZWRQcmVmZXJlbmNlc0xvY2FsUmVjb3JkKGZhbHNlLCBiYXNlbGluZSksIHN0b3JlLmxvYWQoc2NvcGUpKQogICAgfQp9Cg==', 'composeApp/src/androidMain/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSyncStorage.android.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGFuZHJvaWQuY29udGVudC5Db250ZXh0CmltcG9ydCBhbmRyb2lkLmNvbnRlbnQuU2hhcmVkUHJlZmVyZW5jZXMKCmludGVybmFsIGFjdHVhbCBvYmplY3QgT21uaWFQcmVmZXJlbmNlc1N5bmNTdG9yYWdlIHsKICAgIHByaXZhdGUgdmFyIHByZWZlcmVuY2VzOiBTaGFyZWRQcmVmZXJlbmNlcz8gPSBudWxsCiAgICBmdW4gaW5pdGlhbGl6ZShjb250ZXh0OiBDb250ZXh0KSB7CiAgICAgICAgcHJlZmVyZW5jZXMgPSBjb250ZXh0LmFwcGxpY2F0aW9uQ29udGV4dC5nZXRTaGFyZWRQcmVmZXJlbmNlcygib21uaWFfb3B0aW9uYWxfcHJlZmVyZW5jZXMiLCBDb250ZXh0Lk1PREVfUFJJVkFURSkKICAgIH0KICAgIGFjdHVhbCBmdW4gbG9hZChrZXk6IFN0cmluZyk6IFN0cmluZz8gPSBwcmVmZXJlbmNlcz8uZ2V0U3RyaW5nKGtleSwgbnVsbCkKICAgIGFjdHVhbCBmdW4gc2F2ZShrZXk6IFN0cmluZywgdmFsdWU6IFN0cmluZykgewogICAgICAgIHJlcXVpcmUoa2V5LnN0YXJ0c1dpdGgoIm9tbmlhLnNldHRpbmdzLnN5bmMudjEuIikpCiAgICAgICAgdmFsIHN0b3JhZ2UgPSByZXF1aXJlTm90TnVsbChwcmVmZXJlbmNlcykgeyAiRGV2aWNlIHByZWZlcmVuY2Ugc3RvcmFnZSBpcyBub3QgcmVhZHkiIH0KICAgICAgICBjaGVjayhzdG9yYWdlLmVkaXQoKS5wdXRTdHJpbmcoa2V5LCB2YWx1ZSkuY29tbWl0KCkpIHsgIlVuYWJsZSB0byBzYXZlIGRldmljZSBzeW5jIHByZWZlcmVuY2UiIH0KICAgIH0KICAgIGFjdHVhbCBmdW4gY2xlYXIoKSB7CiAgICAgICAgcHJlZmVyZW5jZXM/LmxldCB7IGNoZWNrKGl0LmVkaXQoKS5jbGVhcigpLmNvbW1pdCgpKSB7ICJVbmFibGUgdG8gY2xlYXIgZGV2aWNlIHN5bmMgcHJlZmVyZW5jZXMiIH0gfQogICAgfQp9Cg==', 'composeApp/src/iosMain/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSyncStorage.ios.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IHBsYXRmb3JtLkZvdW5kYXRpb24uTlNVc2VyRGVmYXVsdHMKCmludGVybmFsIGFjdHVhbCBvYmplY3QgT21uaWFQcmVmZXJlbmNlc1N5bmNTdG9yYWdlIHsKICAgIGFjdHVhbCBmdW4gbG9hZChrZXk6IFN0cmluZyk6IFN0cmluZz8gPSBOU1VzZXJEZWZhdWx0cy5zdGFuZGFyZFVzZXJEZWZhdWx0cy5zdHJpbmdGb3JLZXkoa2V5KQogICAgYWN0dWFsIGZ1biBzYXZlKGtleTogU3RyaW5nLCB2YWx1ZTogU3RyaW5nKSB7CiAgICAgICAgcmVxdWlyZShrZXkuc3RhcnRzV2l0aCgib21uaWEuc2V0dGluZ3Muc3luYy52MS4iKSkKICAgICAgICBOU1VzZXJEZWZhdWx0cy5zdGFuZGFyZFVzZXJEZWZhdWx0cy5zZXRPYmplY3QodmFsdWUsIGZvcktleSA9IGtleSkKICAgIH0KICAgIGFjdHVhbCBmdW4gY2xlYXIoKSB7CiAgICAgICAgdmFsIGRlZmF1bHRzID0gTlNVc2VyRGVmYXVsdHMuc3RhbmRhcmRVc2VyRGVmYXVsdHMKICAgICAgICBkZWZhdWx0cy5kaWN0aW9uYXJ5UmVwcmVzZW50YXRpb24oKS5rZXlzLmZpbHRlcklzSW5zdGFuY2U8U3RyaW5nPigpCiAgICAgICAgICAgIC5maWx0ZXIgeyBpdC5zdGFydHNXaXRoKCJvbW5pYS5zZXR0aW5ncy5zeW5jLnYxLiIpIH0KICAgICAgICAgICAgLmZvckVhY2ggeyBkZWZhdWx0cy5yZW1vdmVPYmplY3RGb3JLZXkoaXQpIH0KICAgIH0KfQo=', 'composeApp/src/desktopMain/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSyncStorage.desktop.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGphdmEudXRpbC5wcmVmcy5QcmVmZXJlbmNlcwoKaW50ZXJuYWwgYWN0dWFsIG9iamVjdCBPbW5pYVByZWZlcmVuY2VzU3luY1N0b3JhZ2UgewogICAgcHJpdmF0ZSB2YWwgdmFsdWVzID0gUHJlZmVyZW5jZXMudXNlclJvb3QoKS5ub2RlKCJvbW5pYS9vcHRpb25hbC1wcmVmZXJlbmNlcyIpCiAgICBhY3R1YWwgZnVuIGxvYWQoa2V5OiBTdHJpbmcpOiBTdHJpbmc/IHsKICAgICAgICB2YWwgcGFydHMgPSB2YWx1ZXMuZ2V0SW50KGtleSArICIucGFydHMiLCAwKQogICAgICAgIGlmIChwYXJ0cyAhaW4gMS4uNjQpIHJldHVybiBudWxsCiAgICAgICAgcmV0dXJuIGJ1aWxkU3RyaW5nIHsKICAgICAgICAgICAgcmVwZWF0KHBhcnRzKSB7IGluZGV4IC0+IGFwcGVuZCh2YWx1ZXMuZ2V0KGtleSArICIuIiArIGluZGV4LCBudWxsKSA/OiByZXR1cm4gbnVsbCkgfQogICAgICAgIH0KICAgIH0KICAgIGFjdHVhbCBmdW4gc2F2ZShrZXk6IFN0cmluZywgdmFsdWU6IFN0cmluZykgewogICAgICAgIHJlcXVpcmUoa2V5LnN0YXJ0c1dpdGgoIm9tbmlhLnNldHRpbmdzLnN5bmMudjEuIikpCiAgICAgICAgdmFsIGNodW5rcyA9IHZhbHVlLmNodW5rZWQoNzUwMCkKICAgICAgICByZXF1aXJlKGNodW5rcy5zaXplIGluIDEuLjY0KQogICAgICAgIGNodW5rcy5mb3JFYWNoSW5kZXhlZCB7IGluZGV4LCBjaHVuayAtPiB2YWx1ZXMucHV0KGtleSArICIuIiArIGluZGV4LCBjaHVuaykgfQogICAgICAgIHZhbHVlcy5wdXRJbnQoa2V5ICsgIi5wYXJ0cyIsIGNodW5rcy5zaXplKQogICAgICAgIHZhbHVlcy5mbHVzaCgpCiAgICB9CiAgICBhY3R1YWwgZnVuIGNsZWFyKCkgeyB2YWx1ZXMuY2xlYXIoKTsgdmFsdWVzLmZsdXNoKCkgfQp9Cg==', 'composeApp/src/commonMain/kotlin/com/nuvio/app/core/sync/OmniaPreferencesSync.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmNvcmUuc3luYwoKaW1wb3J0IGNvbS5udXZpby5hcHAuY29yZS5hdXRoLkF1dGhSZXBvc2l0b3J5CmltcG9ydCBjb20ubnV2aW8uYXBwLmNvcmUuYXV0aC5BdXRoU3RhdGUKaW1wb3J0IGNvbS5udXZpby5hcHAuY29yZS5uZXR3b3JrLlN1cGFiYXNlUHJvdmlkZXIKaW1wb3J0IGNvbS5udXZpby5hcHAuZmVhdHVyZXMuaG9tZS5Ib21lQ2F0YWxvZ1NldHRpbmdzUmVwb3NpdG9yeQppbXBvcnQgY29tLm51dmlvLmFwcC5mZWF0dXJlcy5ob21lLlN5bmNDYXRhbG9nSXRlbQppbXBvcnQgY29tLm51dmlvLmFwcC5mZWF0dXJlcy5wbGF5ZXIuUGxheWVyU2V0dGluZ3NSZXBvc2l0b3J5CmltcG9ydCBjb20ubnV2aW8uYXBwLmZlYXR1cmVzLnByb2ZpbGVzLlByb2ZpbGVSZXBvc2l0b3J5CmltcG9ydCBjb20ubnV2aW8uYXBwLmZlYXR1cmVzLndhdGNocHJvZ3Jlc3MuQ29udGludWVXYXRjaGluZ1ByZWZlcmVuY2VzUmVwb3NpdG9yeQppbXBvcnQgaW8uZ2l0aHViLmphbi5zdXBhYmFzZS5wb3N0Z3Jlc3QucG9zdGdyZXN0CmltcG9ydCBpby5naXRodWIuamFuLnN1cGFiYXNlLnBvc3RncmVzdC5ycGMKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5Db3JvdXRpbmVTY29wZQppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLkRpc3BhdGNoZXJzCmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuSm9iCmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuU3VwZXJ2aXNvckpvYgppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmRlbGF5CmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuZmxvdy5jb21iaW5lCmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuZmxvdy5jb2xsZWN0CmltcG9ydCBrb3RsaW54LmNvcm91dGluZXMuZmxvdy5kaXN0aW5jdFVudGlsQ2hhbmdlZAppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmZsb3cuZHJvcAppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLmxhdW5jaAppbXBvcnQga290bGlueC5jb3JvdXRpbmVzLndpdGhDb250ZXh0CmltcG9ydCBrb3RsaW54LnNlcmlhbGl6YXRpb24uanNvbi4qCgovKiogQ29tcGF0aWJsZSBwcmVmZXJlbmNlcyBvbmx5LiBBY2NvdW50IHRva2Vucywgc291cmNlcyBhbmQgaGFyZHdhcmUgdHVuaW5nIG5ldmVyIGVudGVyIHRoaXMgd2lyZS4gKi8KaW50ZXJuYWwgb2JqZWN0IE9tbmlhUHJlZmVyZW5jZXNTeW5jIHsKICAgIHByaXZhdGUgdmFsIHNjb3BlID0gQ29yb3V0aW5lU2NvcGUoU3VwZXJ2aXNvckpvYigpICsgRGlzcGF0Y2hlcnMuTWFpbi5pbW1lZGlhdGUpCiAgICBwcml2YXRlIHZhbCBqc29uID0gSnNvbiB7IGlnbm9yZVVua25vd25LZXlzID0gdHJ1ZTsgZW5jb2RlRGVmYXVsdHMgPSB0cnVlIH0KICAgIHByaXZhdGUgdmFyIGlkZW50aXR5Sm9iOiBKb2I/ID0gbnVsbAogICAgcHJpdmF0ZSB2YXIgcHJlZmVyZW5jZXNKb2I6IEpvYj8gPSBudWxsCiAgICBwcml2YXRlIHZhciBwZW5kaW5nUHVzaDogSm9iPyA9IG51bGwKICAgIHByaXZhdGUgdmFyIGFwcGx5aW5nID0gZmFsc2UKCiAgICBwcml2YXRlIGZ1biBjdXJyZW50U2NvcGUoKTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZT8gewogICAgICAgIHZhbCBhdXRoID0gQXV0aFJlcG9zaXRvcnkuc3RhdGUudmFsdWUgYXM/IEF1dGhTdGF0ZS5BdXRoZW50aWNhdGVkID86IHJldHVybiBudWxsCiAgICAgICAgaWYgKGF1dGguaXNBbm9ueW1vdXMgfHwgIVByb2ZpbGVSZXBvc2l0b3J5LnN0YXRlLnZhbHVlLmlzTG9hZGVkKSByZXR1cm4gbnVsbAogICAgICAgIHJldHVybiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlKGF1dGgudXNlcklkLCBQcm9maWxlUmVwb3NpdG9yeS5hY3RpdmVQcm9maWxlSWQpCiAgICB9CgogICAgcHJpdmF0ZSB2YWwgZGV2aWNlID0gb2JqZWN0IDogU2hhcmVkUHJlZmVyZW5jZXNEZXZpY2UgewogICAgICAgIG92ZXJyaWRlIHZhbCBzdXBwb3J0ZWRLZXlzID0gc2V0T2YoImNvbnRpbnVlV2F0Y2hpbmdWaXNpYmxlIiwgImhlcm9FbmFibGVkIiwgImhpZGVVbnJlbGVhc2VkQ29udGVudCIsICJhdWRpb0xhbmd1YWdlIiwgInN1YnRpdGxlTGFuZ3VhZ2UiLCAiaG9tZUNhdGFsb2dzIikKICAgICAgICBvdmVycmlkZSBmdW4gY3VycmVudFNjb3BlKCkgPSBPbW5pYVByZWZlcmVuY2VzU3luYy5jdXJyZW50U2NvcGUoKQoKICAgICAgICBvdmVycmlkZSBzdXNwZW5kIGZ1biBleHBvcnQoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUpOiBKc29uT2JqZWN0ID0gd2l0aENvbnRleHQoRGlzcGF0Y2hlcnMuTWFpbi5pbW1lZGlhdGUpIHsKICAgICAgICAgICAgY2hlY2soY3VycmVudFNjb3BlKCkgPT0gc2NvcGUpIHsgIkFjY291bnQgb3IgcHJvZmlsZSBjaGFuZ2VkIiB9CiAgICAgICAgICAgIENvbnRpbnVlV2F0Y2hpbmdQcmVmZXJlbmNlc1JlcG9zaXRvcnkuZW5zdXJlTG9hZGVkKCkKICAgICAgICAgICAgUGxheWVyU2V0dGluZ3NSZXBvc2l0b3J5LmVuc3VyZUxvYWRlZCgpCiAgICAgICAgICAgIHZhbCBjYXRhbG9ncyA9IEhvbWVDYXRhbG9nU2V0dGluZ3NSZXBvc2l0b3J5LmV4cG9ydFRvU3luY1BheWxvYWQoa25vd25Pbmx5ID0gdHJ1ZSkKICAgICAgICAgICAgdmFsIGhvbWUgPSBIb21lQ2F0YWxvZ1NldHRpbmdzUmVwb3NpdG9yeS51aVN0YXRlLnZhbHVlCiAgICAgICAgICAgIHZhbCBwbGF5ZXIgPSBQbGF5ZXJTZXR0aW5nc1JlcG9zaXRvcnkudWlTdGF0ZS52YWx1ZQogICAgICAgICAgICBidWlsZEpzb25PYmplY3QgewogICAgICAgICAgICAgICAgcHV0KCJjb250aW51ZVdhdGNoaW5nVmlzaWJsZSIsIENvbnRpbnVlV2F0Y2hpbmdQcmVmZXJlbmNlc1JlcG9zaXRvcnkudWlTdGF0ZS52YWx1ZS5pc1Zpc2libGUpCiAgICAgICAgICAgICAgICBwdXQoImhlcm9FbmFibGVkIiwgaG9tZS5oZXJvRW5hYmxlZCkKICAgICAgICAgICAgICAgIHB1dCgiaGlkZVVucmVsZWFzZWRDb250ZW50IiwgaG9tZS5oaWRlVW5yZWxlYXNlZENvbnRlbnQpCiAgICAgICAgICAgICAgICBwdXQoImF1ZGlvTGFuZ3VhZ2UiLCBwbGF5ZXIucHJlZmVycmVkQXVkaW9MYW5ndWFnZSkKICAgICAgICAgICAgICAgIHB1dCgic3VidGl0bGVMYW5ndWFnZSIsIHBsYXllci5wcmVmZXJyZWRTdWJ0aXRsZUxhbmd1YWdlKQogICAgICAgICAgICAgICAgcHV0KCJob21lQ2F0YWxvZ3MiLCBKc29uQXJyYXkoY2F0YWxvZ3MuaXRlbXMuZmlsdGVyIHsgcm93IC0+CiAgICAgICAgICAgICAgICAgICAgaWYgKHJvdy5pc0NvbGxlY3Rpb24pIGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KHJvdy5jb2xsZWN0aW9uSWQsIDEyOCkKICAgICAgICAgICAgICAgICAgICBlbHNlIGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KHJvdy5hZGRvbklkLCA1MTIpICYmCiAgICAgICAgICAgICAgICAgICAgICAgIGlzU2hhcmVhYmxlQ2F0YWxvZ0lkZW50aXR5KHJvdy50eXBlLCA2NCkgJiYKICAgICAgICAgICAgICAgICAgICAgICAgaXNTaGFyZWFibGVDYXRhbG9nSWRlbnRpdHkocm93LmNhdGFsb2dJZCwgMTAyNCkKICAgICAgICAgICAgICAgIH0ubWFwIHsgcm93IC0+IEpzb25PYmplY3QoanNvbi5lbmNvZGVUb0pzb25FbGVtZW50KFN5bmNDYXRhbG9nSXRlbS5zZXJpYWxpemVyKCksIHJvdykuanNvbk9iamVjdCAtICJrZXkiKSB9KSkKICAgICAgICAgICAgfQogICAgICAgIH0KCiAgICAgICAgb3ZlcnJpZGUgc3VzcGVuZCBmdW4gYXBwbHkoc2NvcGU6IFNoYXJlZFByZWZlcmVuY2VzU2NvcGUsIHByZWZlcmVuY2VzOiBKc29uT2JqZWN0LCBzdGlsbEN1cnJlbnQ6ICgpIC0+IEJvb2xlYW4pID0gd2l0aENvbnRleHQoRGlzcGF0Y2hlcnMuTWFpbi5pbW1lZGlhdGUpIHsKICAgICAgICAgICAgZnVuIGd1YXJkKCkgeyBjaGVjayhzdGlsbEN1cnJlbnQoKSAmJiBjdXJyZW50U2NvcGUoKSA9PSBzY29wZSkgeyAiQWNjb3VudCwgcHJvZmlsZSBvciBzeW5jIGNob2ljZSBjaGFuZ2VkIiB9IH0KICAgICAgICAgICAgZ3VhcmQoKQogICAgICAgICAgICAvLyBBbGwgcmVwb3NpdG9yeSB3cml0ZXMgYmVsb3cgYXJlIHN5bmNocm9ub3VzOyBlYWNoIGNoZWNrcyB0aGUgcmVxdWVzdCBndWFyZC4KICAgICAgICAgICAgLy8gTm8gc3VzcGVuZGVkIG5ldHdvcmsgb3Igc3RvcmFnZSBvcGVyYXRpb24gY2FuIHJlc3VtZSBpbnRvIGEgZGlmZmVyZW50IHByb2ZpbGUuCiAgICAgICAgICAgIGFwcGx5aW5nID0gdHJ1ZQogICAgICAgICAgICB0cnkgewogICAgICAgICAgICAgICAgcHJlZmVyZW5jZXNbImhvbWVDYXRhbG9ncyJdPy5sZXQgeyByb3dzIC0+CiAgICAgICAgICAgICAgICAgICAgdmFsIGl0ZW1zID0gKHJvd3MgYXMgSnNvbkFycmF5KS5tYXAgeyBqc29uLmRlY29kZUZyb21Kc29uRWxlbWVudChTeW5jQ2F0YWxvZ0l0ZW0uc2VyaWFsaXplcigpLCBpdCkgfQogICAgICAgICAgICAgICAgICAgIHZhbCBsb2NhbCA9IEhvbWVDYXRhbG9nU2V0dGluZ3NSZXBvc2l0b3J5LmV4cG9ydFRvU3luY1BheWxvYWQoKQogICAgICAgICAgICAgICAgICAgIGd1YXJkKCk7IEhvbWVDYXRhbG9nU2V0dGluZ3NSZXBvc2l0b3J5LmFwcGx5RnJvbVJlbW90ZShsb2NhbC5jb3B5KGl0ZW1zID0gaXRlbXMpKQogICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgcHJlZmVyZW5jZXNbImNvbnRpbnVlV2F0Y2hpbmdWaXNpYmxlIl0/Lmpzb25QcmltaXRpdmU/LmJvb2xlYW5Pck51bGw/LmxldCB7IGd1YXJkKCk7IENvbnRpbnVlV2F0Y2hpbmdQcmVmZXJlbmNlc1JlcG9zaXRvcnkuc2V0VmlzaWJsZShpdCkgfQogICAgICAgICAgICAgICAgcHJlZmVyZW5jZXNbImhlcm9FbmFibGVkIl0/Lmpzb25QcmltaXRpdmU/LmJvb2xlYW5Pck51bGw/LmxldCB7IGd1YXJkKCk7IEhvbWVDYXRhbG9nU2V0dGluZ3NSZXBvc2l0b3J5LnNldEhlcm9FbmFibGVkKGl0KSB9CiAgICAgICAgICAgICAgICBwcmVmZXJlbmNlc1siaGlkZVVucmVsZWFzZWRDb250ZW50Il0/Lmpzb25QcmltaXRpdmU/LmJvb2xlYW5Pck51bGw/LmxldCB7IGd1YXJkKCk7IEhvbWVDYXRhbG9nU2V0dGluZ3NSZXBvc2l0b3J5LnNldEhpZGVVbnJlbGVhc2VkQ29udGVudChpdCkgfQogICAgICAgICAgICAgICAgcHJlZmVyZW5jZXNbImF1ZGlvTGFuZ3VhZ2UiXT8uanNvblByaW1pdGl2ZT8uY29udGVudE9yTnVsbD8ubGV0IHsgZ3VhcmQoKTsgUGxheWVyU2V0dGluZ3NSZXBvc2l0b3J5LnNldFByZWZlcnJlZEF1ZGlvTGFuZ3VhZ2UoaXQpIH0KICAgICAgICAgICAgICAgIHByZWZlcmVuY2VzWyJzdWJ0aXRsZUxhbmd1YWdlIl0/Lmpzb25QcmltaXRpdmU/LmNvbnRlbnRPck51bGw/LmxldCB7IGd1YXJkKCk7IFBsYXllclNldHRpbmdzUmVwb3NpdG9yeS5zZXRQcmVmZXJyZWRTdWJ0aXRsZUxhbmd1YWdlKGl0KSB9CiAgICAgICAgICAgICAgICBndWFyZCgpCiAgICAgICAgICAgIH0gZmluYWxseSB7IGFwcGx5aW5nID0gZmFsc2UgfQogICAgICAgIH0KICAgIH0KCiAgICBwcml2YXRlIGZ1biBKc29uT2JqZWN0LnNuYXBzaG90KCk6IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QgPSBTaGFyZWRQcmVmZXJlbmNlc1NuYXBzaG90KAogICAgICAgIHJlcXVpcmVOb3ROdWxsKHRoaXNbInJldmlzaW9uIl0/Lmpzb25QcmltaXRpdmU/LmxvbmdPck51bGwpLAogICAgICAgIHRoaXNbInByZWZlcmVuY2VzIl0gYXM/IEpzb25PYmplY3QgPzogZXJyb3IoIkludmFsaWQgc2F2ZWQgcHJlZmVyZW5jZXMiKSwKICAgICAgICByZXF1aXJlTm90TnVsbCh0aGlzWyJwcm9maWxlX2luc3RhbmNlIl0/Lmpzb25QcmltaXRpdmU/LmNvbnRlbnRPck51bGwpLmFsc28geyByZXF1aXJlKGl0LmlzTm90QmxhbmsoKSkgfSwKICAgICkKCiAgICBwcml2YXRlIHZhbCB0cmFuc3BvcnQgPSBvYmplY3QgOiBTaGFyZWRQcmVmZXJlbmNlc1RyYW5zcG9ydCB7CiAgICAgICAgb3ZlcnJpZGUgc3VzcGVuZCBmdW4gcHVsbChzY29wZTogU2hhcmVkUHJlZmVyZW5jZXNTY29wZSk6IFNoYXJlZFByZWZlcmVuY2VzU25hcHNob3QgPQogICAgICAgICAgICBTdXBhYmFzZVByb3ZpZGVyLmNsaWVudC5wb3N0Z3Jlc3QucnBjKCJvbW5pYV9wdWxsX3ByZWZlcmVuY2VzX3YxIiwgYnVpbGRKc29uT2JqZWN0IHsKICAgICAgICAgICAgICAgIHB1dCgicF9leHBlY3RlZF9vd25lciIsIHNjb3BlLm93bmVyKTsgcHV0KCJwX3Byb2ZpbGVfaWQiLCBzY29wZS5wcm9maWxlSWQpCiAgICAgICAgICAgIH0pLmRlY29kZUFzPEpzb25PYmplY3Q+KCkuc25hcHNob3QoKQoKICAgICAgICBvdmVycmlkZSBzdXNwZW5kIGZ1biBwdXNoKHNjb3BlOiBTaGFyZWRQcmVmZXJlbmNlc1Njb3BlLCBleHBlY3RlZFJldmlzaW9uOiBMb25nLCBwcmVmZXJlbmNlczogSnNvbk9iamVjdCwgZXhwZWN0ZWRQcm9maWxlSW5zdGFuY2U6IFN0cmluZz8pOiBTaGFyZWRQcmVmZXJlbmNlc1B1c2hSZXN1bHQgewogICAgICAgICAgICB2YWwgcmVzcG9uc2UgPSBTdXBhYmFzZVByb3ZpZGVyLmNsaWVudC5wb3N0Z3Jlc3QucnBjKCJvbW5pYV9wdXNoX3ByZWZlcmVuY2VzX3YxIiwgYnVpbGRKc29uT2JqZWN0IHsKICAgICAgICAgICAgICAgIHB1dCgicF9leHBlY3RlZF9vd25lciIsIHNjb3BlLm93bmVyKTsgcHV0KCJwX3Byb2ZpbGVfaWQiLCBzY29wZS5wcm9maWxlSWQpCiAgICAgICAgICAgICAgICBwdXQoInBfZXhwZWN0ZWRfcmV2aXNpb24iLCBleHBlY3RlZFJldmlzaW9uKTsgcHV0KCJwX3ByZWZlcmVuY2VzIiwgcHJlZmVyZW5jZXMpCiAgICAgICAgICAgICAgICBwdXQoInBfZXhwZWN0ZWRfcHJvZmlsZV9pbnN0YW5jZSIsIHJlcXVpcmVOb3ROdWxsKGV4cGVjdGVkUHJvZmlsZUluc3RhbmNlKSkKICAgICAgICAgICAgfSkuZGVjb2RlQXM8SnNvbk9iamVjdD4oKQogICAgICAgICAgICByZXR1cm4gU2hhcmVkUHJlZmVyZW5jZXNQdXNoUmVzdWx0KAogICAgICAgICAgICAgICAgcmVxdWlyZU5vdE51bGwocmVzcG9uc2VbImNvbmZsaWN0Il0/Lmpzb25QcmltaXRpdmU/LmJvb2xlYW5Pck51bGwpLAogICAgICAgICAgICAgICAgcmVxdWlyZU5vdE51bGwocmVzcG9uc2VbInNuYXBzaG90Il0gYXM/IEpzb25PYmplY3QpLnNuYXBzaG90KCksCiAgICAgICAgICAgICkKICAgICAgICB9CiAgICB9CgogICAgcHJpdmF0ZSB2YWwgcmVjb3JkcyA9IE9tbmlhUHJlZmVyZW5jZXNTeW5jUmVjb3JkU3RvcmUoT21uaWFQcmVmZXJlbmNlc1N5bmNTdG9yYWdlOjpsb2FkLCBPbW5pYVByZWZlcmVuY2VzU3luY1N0b3JhZ2U6OnNhdmUpCiAgICBwcml2YXRlIHZhbCBlbmdpbmUgPSBPbW5pYVNoYXJlZFByZWZlcmVuY2VzRW5naW5lKGRldmljZSwgcmVjb3JkcywgdHJhbnNwb3J0KQogICAgdmFsIHN0YXRlID0gZW5naW5lLnN0YXRlCgogICAgZnVuIHN0YXJ0T2JzZXJ2aW5nKCkgewogICAgICAgIGlmIChpZGVudGl0eUpvYj8uaXNBY3RpdmUgPT0gdHJ1ZSkgcmV0dXJuCiAgICAgICAgZW5naW5lLnJlZnJlc2hMb2NhbFN0YXRlKCkKICAgICAgICBpZGVudGl0eUpvYiA9IHNjb3BlLmxhdW5jaCB7CiAgICAgICAgICAgIGNvbWJpbmUoQXV0aFJlcG9zaXRvcnkuc3RhdGUsIFByb2ZpbGVSZXBvc2l0b3J5LnN0YXRlKSB7IF8sIF8gLT4gY3VycmVudFNjb3BlKCkgfQogICAgICAgICAgICAgICAgLmRpc3RpbmN0VW50aWxDaGFuZ2VkKCkuY29sbGVjdCB7CiAgICAgICAgICAgICAgICAgICAgcGVuZGluZ1B1c2g/LmNhbmNlbCgpOyBlbmdpbmUucmVmcmVzaExvY2FsU3RhdGUoKQogICAgICAgICAgICAgICAgICAgIHJlcXVlc3RTeW5jKCkKICAgICAgICAgICAgICAgIH0KICAgICAgICB9CiAgICAgICAgcHJlZmVyZW5jZXNKb2IgPSBzY29wZS5sYXVuY2ggewogICAgICAgICAgICBjb21iaW5lKENvbnRpbnVlV2F0Y2hpbmdQcmVmZXJlbmNlc1JlcG9zaXRvcnkudWlTdGF0ZSwgSG9tZUNhdGFsb2dTZXR0aW5nc1JlcG9zaXRvcnkudWlTdGF0ZSwgUGxheWVyU2V0dGluZ3NSZXBvc2l0b3J5LnVpU3RhdGUpIHsgXywgXywgXyAtPgogICAgICAgICAgICAgICAgY3VycmVudFNjb3BlKCk/LmxldCB7IGRldmljZS5leHBvcnQoaXQpLnRvU3RyaW5nKCkgfQogICAgICAgICAgICB9LmRpc3RpbmN0VW50aWxDaGFuZ2VkKCkuZHJvcCgxKS5jb2xsZWN0IHsgcmVxdWVzdFN5bmMoKSB9CiAgICAgICAgfQogICAgfQoKICAgIC8qKiBDYWxsIGJlZm9yZSBwcm9maWxlL2FjY291bnQgdHJhbnNpdGlvbiwgZXZlbiBpZiBhbiBB4oaSQuKGkkEgZmxvdyBlbWlzc2lvbiBpcyBjb25mbGF0ZWQuICovCiAgICBmdW4gaW52YWxpZGF0ZVJlcXVlc3RzKCkgewogICAgICAgIHBlbmRpbmdQdXNoPy5jYW5jZWwoKQogICAgICAgIGVuZ2luZS5yZWZyZXNoTG9jYWxTdGF0ZSgpCiAgICB9CgogICAgZnVuIG9uUHJvZmlsZUNoYW5nZWQoKSB7IGludmFsaWRhdGVSZXF1ZXN0cygpOyByZXF1ZXN0U3luYygpIH0KCiAgICBmdW4gY2xlYXJBY2NvdW50U3RhdGUoKSB7CiAgICAgICAgaW52YWxpZGF0ZVJlcXVlc3RzKCkKICAgICAgICBpZGVudGl0eUpvYj8uY2FuY2VsKCk7IGlkZW50aXR5Sm9iID0gbnVsbAogICAgICAgIHByZWZlcmVuY2VzSm9iPy5jYW5jZWwoKTsgcHJlZmVyZW5jZXNKb2IgPSBudWxsCiAgICAgICAgT21uaWFQcmVmZXJlbmNlc1N5bmNTdG9yYWdlLmNsZWFyKCkKICAgICAgICBlbmdpbmUucmVmcmVzaExvY2FsU3RhdGUoKQogICAgfQoKICAgIGZ1biByZXF1ZXN0U3luYygpIHsKICAgICAgICBpZiAoYXBwbHlpbmcgfHwgIXN0YXRlLnZhbHVlLmVuYWJsZWQpIHJldHVybgogICAgICAgIHZhbCBleHBlY3RlZCA9IGN1cnJlbnRTY29wZSgpID86IHJldHVybgogICAgICAgIHBlbmRpbmdQdXNoPy5jYW5jZWwoKQogICAgICAgIHBlbmRpbmdQdXNoID0gc2NvcGUubGF1bmNoIHsKICAgICAgICAgICAgZGVsYXkoNzUwKQogICAgICAgICAgICBpZiAoY3VycmVudFNjb3BlKCkgPT0gZXhwZWN0ZWQpIGVuZ2luZS5zeW5jaHJvbml6ZSgpCiAgICAgICAgfQogICAgfQoKICAgIHN1c3BlbmQgZnVuIHN5bmNocm9uaXplKHByb2ZpbGVJZDogSW50ID0gUHJvZmlsZVJlcG9zaXRvcnkuYWN0aXZlUHJvZmlsZUlkKTogU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzIHsKICAgICAgICBpZiAoY3VycmVudFNjb3BlKCk/LnByb2ZpbGVJZCAhPSBwcm9maWxlSWQpIHJldHVybiBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU2lnbkluUmVxdWlyZWQKICAgICAgICByZXR1cm4gZW5naW5lLnN5bmNocm9uaXplKCkKICAgIH0KCiAgICBzdXNwZW5kIGZ1biBlbmFibGUoY2hvaWNlOiBTaGFyZWRQcmVmZXJlbmNlc0luaXRpYWxDaG9pY2U/ID0gbnVsbCkgPSBlbmdpbmUuZW5hYmxlKGNob2ljZSkKICAgIHN1c3BlbmQgZnVuIGRpc2FibGUoKSA9IGVuZ2luZS5kaXNhYmxlKCkKICAgIGZ1biBjYW5jZWxJbml0aWFsQ2hvaWNlKCkgPSBlbmdpbmUucmVmcmVzaExvY2FsU3RhdGUoKQp9Cg==', 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/OmniaPreferencesSyncSettings.kt': 'cGFja2FnZSBjb20ubnV2aW8uYXBwLmZlYXR1cmVzLnNldHRpbmdzCgppbXBvcnQgYW5kcm9pZHguY29tcG9zZS5mb3VuZGF0aW9uLmxheW91dC5BcnJhbmdlbWVudAppbXBvcnQgYW5kcm9pZHguY29tcG9zZS5mb3VuZGF0aW9uLmxheW91dC5Db2x1bW4KaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UuZm91bmRhdGlvbi5sYXlvdXQuU3BhY2VyCmltcG9ydCBhbmRyb2lkeC5jb21wb3NlLmZvdW5kYXRpb24ubGF5b3V0LmhlaWdodAppbXBvcnQgYW5kcm9pZHguY29tcG9zZS5tYXRlcmlhbDMuQWxlcnREaWFsb2cKaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UubWF0ZXJpYWwzLk1hdGVyaWFsVGhlbWUKaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UubWF0ZXJpYWwzLlRleHQKaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UubWF0ZXJpYWwzLlRleHRCdXR0b24KaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UucnVudGltZS5Db21wb3NhYmxlCmltcG9ydCBhbmRyb2lkeC5jb21wb3NlLnJ1bnRpbWUuTGF1bmNoZWRFZmZlY3QKaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UucnVudGltZS5nZXRWYWx1ZQppbXBvcnQgYW5kcm9pZHguY29tcG9zZS5ydW50aW1lLnJlbWVtYmVyQ29yb3V0aW5lU2NvcGUKaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UudWkuTW9kaWZpZXIKaW1wb3J0IGFuZHJvaWR4LmNvbXBvc2UudWkudW5pdC5kcAppbXBvcnQgYW5kcm9pZHgubGlmZWN5Y2xlLmNvbXBvc2UuY29sbGVjdEFzU3RhdGVXaXRoTGlmZWN5Y2xlCmltcG9ydCBjb20ubnV2aW8uYXBwLmNvcmUuYXV0aC5BdXRoUmVwb3NpdG9yeQppbXBvcnQgY29tLm51dmlvLmFwcC5jb3JlLmF1dGguQXV0aFN0YXRlCmltcG9ydCBjb20ubnV2aW8uYXBwLmNvcmUuc3luYy5PbW5pYVByZWZlcmVuY2VzU3luYwppbXBvcnQgY29tLm51dmlvLmFwcC5jb3JlLnN5bmMuU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlCmltcG9ydCBjb20ubnV2aW8uYXBwLmNvcmUuc3luYy5TaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMKaW1wb3J0IGtvdGxpbnguY29yb3V0aW5lcy5sYXVuY2gKCkBDb21wb3NhYmxlCmludGVybmFsIGZ1biBPbW5pYVByZWZlcmVuY2VzU3luY1NldHRpbmdzKGlzVGFibGV0OiBCb29sZWFuKSB7CiAgICB2YWwgc3RhdGUgYnkgT21uaWFQcmVmZXJlbmNlc1N5bmMuc3RhdGUuY29sbGVjdEFzU3RhdGVXaXRoTGlmZWN5Y2xlKCkKICAgIHZhbCBhdXRoIGJ5IEF1dGhSZXBvc2l0b3J5LnN0YXRlLmNvbGxlY3RBc1N0YXRlV2l0aExpZmVjeWNsZSgpCiAgICB2YWwgc2NvcGUgPSByZW1lbWJlckNvcm91dGluZVNjb3BlKCkKICAgIHZhbCBzaWduZWRJbiA9IChhdXRoIGFzPyBBdXRoU3RhdGUuQXV0aGVudGljYXRlZCk/LmlzQW5vbnltb3VzID09IGZhbHNlCiAgICBMYXVuY2hlZEVmZmVjdChVbml0KSB7IE9tbmlhUHJlZmVyZW5jZXNTeW5jLnN0YXJ0T2JzZXJ2aW5nKCkgfQogICAgU2V0dGluZ3NHcm91cChpc1RhYmxldCA9IGlzVGFibGV0KSB7CiAgICAgICAgU2V0dGluZ3NTd2l0Y2hSb3coCiAgICAgICAgICAgIHRpdGxlID0gIlN5bmMgc2V0dGluZ3MgYWNyb3NzIGRldmljZXMiLAogICAgICAgICAgICBkZXNjcmlwdGlvbiA9ICJTaGFyZSBjb21wYXRpYmxlIEhvbWUgYW5kIGxhbmd1YWdlIHByZWZlcmVuY2VzIHdpdGggdGhpcyBhY2NvdW50IGFuZCBwcm9maWxlLiBPZmYga2VlcHMgdGhpcyBkZXZpY2XigJlzIGN1cnJlbnQgc2V0dGluZ3Mgc2VwYXJhdGUuIEFkZC1vbnMsIGxpYnJhcnkgYW5kIGhpc3Rvcnkgc3luYyBzZXBhcmF0ZWx5LiIsCiAgICAgICAgICAgIGNoZWNrZWQgPSBzdGF0ZS5lbmFibGVkLAogICAgICAgICAgICBlbmFibGVkID0gc2lnbmVkSW4gJiYgKHN0YXRlLmVuYWJsZWQgfHwgc3RhdGUuc3RhdHVzICE9IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jaW5nKSwKICAgICAgICAgICAgaXNUYWJsZXQgPSBpc1RhYmxldCwKICAgICAgICAgICAgb25DaGVja2VkQ2hhbmdlID0geyBlbmFibGVkIC0+IHNjb3BlLmxhdW5jaCB7CiAgICAgICAgICAgICAgICBpZiAoZW5hYmxlZCkgT21uaWFQcmVmZXJlbmNlc1N5bmMuZW5hYmxlKCkgZWxzZSBPbW5pYVByZWZlcmVuY2VzU3luYy5kaXNhYmxlKCkKICAgICAgICAgICAgfSB9LAogICAgICAgICkKICAgICAgICBDb2x1bW4odmVydGljYWxBcnJhbmdlbWVudCA9IEFycmFuZ2VtZW50LnNwYWNlZEJ5KDguZHApKSB7CiAgICAgICAgICAgIFRleHQod2hlbiB7CiAgICAgICAgICAgICAgICAhc2lnbmVkSW4gLT4gIlNpZ24gaW4gdG8gc2hhcmUgc2V0dGluZ3MuIgogICAgICAgICAgICAgICAgZWxzZSAtPiB3aGVuKHN0YXRlLnN0YXR1cykgewogICAgICAgICAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5PZmYgLT4gIk9mZiDCtyBUaGlzIGRldmljZSBrZWVwcyBpdHMgb3duIHNldHRpbmdzLiIKICAgICAgICAgICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuUmVhZHkgLT4gIk9uIMK3IFJlYWR5IHRvIHN5bmMuIgogICAgICAgICAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MgLT4gIkNob29zZSB3aGljaCBzZXR0aW5ncyB0byB1c2UuIgogICAgICAgICAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jaW5nIC0+ICJTeW5jaW5nIHNldHRpbmdz4oCmIgogICAgICAgICAgICAgICAgICAgIFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5TeW5jZWQgLT4gIlNldHRpbmdzIHN5bmNlZC4iCiAgICAgICAgICAgICAgICAgICAgU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlNpZ25JblJlcXVpcmVkIC0+ICJTaWduIGluIHRvIHNoYXJlIHNldHRpbmdzLiIKICAgICAgICAgICAgICAgICAgICBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuRXJyb3IgLT4gIlNldHRpbmdzIGNvdWxkIG5vdCBzeW5jLiBZb3VyIGxvY2FsIHByZWZlcmVuY2VzIGFyZSBrZXB0LiBUcnkgYWdhaW4uIgogICAgICAgICAgICAgICAgfQogICAgICAgICAgICB9LCBzdHlsZSA9IE1hdGVyaWFsVGhlbWUudHlwb2dyYXBoeS5ib2R5TWVkaXVtKQogICAgICAgICAgICBUZXh0KCJTaGFyZXMgSG9tZSBjYXRhbG9nIG9yZGVyLCB2aXNpYmlsaXR5IGFuZCBuYW1lczsgQ29udGludWUgV2F0Y2hpbmcgdmlzaWJpbGl0eTsgaGVybyB2aXNpYmlsaXR5OyB1bnJlbGVhc2VkLWNvbnRlbnQgZmlsdGVyaW5nOyBhbmQgYXVkaW8vc3VidGl0bGUgbGFuZ3VhZ2UuIERldmljZSBwbGF5YmFjayB0dW5pbmcgc3RheXMgbG9jYWwuIFVwZGF0ZXMgd2hlbiB5b3Ugb3BlbiBPbW5pYSwgY2hhbmdlIGEgc2hhcmVkIHByZWZlcmVuY2UsIG9yIHNlbGVjdCBTeW5jIG5vdy4iLCBzdHlsZSA9IE1hdGVyaWFsVGhlbWUudHlwb2dyYXBoeS5ib2R5U21hbGwsIGNvbG9yID0gTWF0ZXJpYWxUaGVtZS5jb2xvclNjaGVtZS5vblN1cmZhY2VWYXJpYW50KQogICAgICAgICAgICBpZiAoc3RhdGUuZW5hYmxlZCAmJiBzdGF0ZS5zdGF0dXMgIT0gU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLlN5bmNpbmcpIHsKICAgICAgICAgICAgICAgIFRleHRCdXR0b24ob25DbGljayA9IHsgc2NvcGUubGF1bmNoIHsgT21uaWFQcmVmZXJlbmNlc1N5bmMuc3luY2hyb25pemUoKSB9IH0pIHsgVGV4dCgiU3luYyBzZXR0aW5ncyBub3ciKSB9CiAgICAgICAgICAgIH0KICAgICAgICAgICAgaWYgKCFzdGF0ZS5lbmFibGVkICYmIHN0YXRlLnN0YXR1cyA9PSBTaGFyZWRQcmVmZXJlbmNlc1N5bmNTdGF0dXMuU3luY2luZykgewogICAgICAgICAgICAgICAgVGV4dEJ1dHRvbihvbkNsaWNrID0geyBzY29wZS5sYXVuY2ggeyBPbW5pYVByZWZlcmVuY2VzU3luYy5kaXNhYmxlKCkgfSB9KSB7IFRleHQoIkNhbmNlbCBlbmFibGluZyBzeW5jIikgfQogICAgICAgICAgICB9CiAgICAgICAgICAgIGlmICghc3RhdGUuZW5hYmxlZCAmJiBzdGF0ZS5zdGF0dXMgPT0gU2hhcmVkUHJlZmVyZW5jZXNTeW5jU3RhdHVzLkVycm9yKSB7CiAgICAgICAgICAgICAgICBUZXh0QnV0dG9uKG9uQ2xpY2sgPSB7IHNjb3BlLmxhdW5jaCB7IE9tbmlhUHJlZmVyZW5jZXNTeW5jLmVuYWJsZSgpIH0gfSkgeyBUZXh0KCJUcnkgZW5hYmxpbmcgYWdhaW4iKSB9CiAgICAgICAgICAgIH0KICAgICAgICB9CiAgICB9CiAgICBpZiAoc3RhdGUuc3RhdHVzID09IFNoYXJlZFByZWZlcmVuY2VzU3luY1N0YXR1cy5DaG9vc2VJbml0aWFsU2V0dGluZ3MpIHsKICAgICAgICBBbGVydERpYWxvZygKICAgICAgICAgICAgb25EaXNtaXNzUmVxdWVzdCA9IE9tbmlhUHJlZmVyZW5jZXNTeW5jOjpjYW5jZWxJbml0aWFsQ2hvaWNlLAogICAgICAgICAgICB0aXRsZSA9IHsgVGV4dCgiV2hpY2ggc2V0dGluZ3Mgc2hvdWxkIHdlIHVzZT8iKSB9LAogICAgICAgICAgICB0ZXh0ID0geyBUZXh0KCJTYXZlZCBzZXR0aW5ncyBhbHJlYWR5IGV4aXN0IGZvciB0aGlzIHByb2ZpbGUuIENob29zZSB0aGUgc3RhcnRpbmcgc2V0dGluZ3MgZm9yIHRoaXMgZGV2aWNlLiBQbGF5YmFjayB0dW5pbmcsIGFkZC1vbnMsIGxpYnJhcnkgYW5kIGhpc3RvcnkgYXJlIHVuYWZmZWN0ZWQuIikgfSwKICAgICAgICAgICAgY29uZmlybUJ1dHRvbiA9IHsgQ29sdW1uIHsKICAgICAgICAgICAgICAgIFRleHRCdXR0b24ob25DbGljayA9IHsgc2NvcGUubGF1bmNoIHsgT21uaWFQcmVmZXJlbmNlc1N5bmMuZW5hYmxlKFNoYXJlZFByZWZlcmVuY2VzSW5pdGlhbENob2ljZS5Vc2VTYXZlZFNldHRpbmdzKSB9IH0pIHsgVGV4dCgiVXNlIHNhdmVkIHNldHRpbmdzIikgfQogICAgICAgICAgICAgICAgVGV4dEJ1dHRvbihvbkNsaWNrID0geyBzY29wZS5sYXVuY2ggeyBPbW5pYVByZWZlcmVuY2VzU3luYy5lbmFibGUoU2hhcmVkUHJlZmVyZW5jZXNJbml0aWFsQ2hvaWNlLlVzZVRoaXNEZXZpY2UpIH0gfSkgeyBUZXh0KCJVc2UgdGhpcyBkZXZpY2XigJlzIHNldHRpbmdzIikgfQogICAgICAgICAgICB9IH0sCiAgICAgICAgICAgIGRpc21pc3NCdXR0b24gPSB7IFRleHRCdXR0b24ob25DbGljayA9IE9tbmlhUHJlZmVyZW5jZXNTeW5jOjpjYW5jZWxJbml0aWFsQ2hvaWNlKSB7IFRleHQoIkNhbmNlbCIpIH0gfSwKICAgICAgICApCiAgICB9Cn0K'}.items():
        path=ROOT/rel;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(base64.b64decode(encoded))
    prefix='composeApp/src/commonMain/kotlin/com/nuvio/app/'
    profile=ROOT/(prefix+'core/sync/ProfileSettingsSync.kt')
    code=profile.read_text();imports=code.split('object ProfileSettingsSync {',1)[0]
    start=code.index('    private fun ensureRepositoriesLoaded() {')
    end=code.index('\n    }',start)+len('\n    }')
    ensure=code[start:end]
    body="""object ProfileSettingsSync {
    fun startObserving() {
        ensureRepositoriesLoaded()
        ProviderCredentialSync.startObserving()
        MediaServerSync.startObserving()
        OmniaPreferencesSync.startObserving()
    }
    fun clearAccountState() {
        OmniaPreferencesSync.clearAccountState()
        ProviderCredentialSync.clearAccountState()
        MediaServerSync.clearAccountState()
    }
    fun onProfileChanged() {
        OmniaPreferencesSync.onProfileChanged()
        ProviderCredentialSync.onProfileChanged()
    }
    suspend fun pull(profileId: Int): Boolean {
        ensureRepositoriesLoaded()
        return OmniaPreferencesSync.synchronize(profileId) == SharedPreferencesSyncStatus.Synced
    }
    suspend fun pushCurrentProfileToRemote(): Boolean =
        OmniaPreferencesSync.synchronize() == SharedPreferencesSyncStatus.Synced
ENSURE
}
""".replace('ENSURE',ensure)
    profile.write_text(imports+body,encoding='utf8',newline='\n')
    home=ROOT/(prefix+'features/home/HomeCatalogSettingsSyncService.kt')
    code=home.read_text().split('object HomeCatalogSettingsSyncService {',1)[0]
    code+='object HomeCatalogSettingsSyncService {\n    suspend fun pullFromServer(profileId: Int) {\n        com.nuvio.app.core.sync.OmniaPreferencesSync.synchronize(profileId)\n    }\n    fun triggerPush() = com.nuvio.app.core.sync.OmniaPreferencesSync.requestSync()\n}\n'
    home.write_text(code,encoding='utf8',newline='\n')
    catalog=ROOT/(prefix+'features/home/HomeCatalogSettingsRepository.kt')
    code=catalog.read_text().replace('fun exportToSyncPayload(): SyncHomeCatalogPayload', 'fun exportToSyncPayload(knownOnly: Boolean = false): SyncHomeCatalogPayload')
    anchor='val items = preferences.values.filterNot { ServerCatalog.isServerKey(it.key) }'
    replacement='val items = preferences.values.filter { !knownOnly || it.key in catalogDefinitionsByKey || it.key in collectionDefinitionsByKey }.filterNot { ServerCatalog.isServerKey(it.key) }'
    if replacement not in code:
        assert anchor in code
        code=code.replace(anchor,replacement,1)
    catalog.write_text(code,encoding='utf8',newline='\n')
    def insert_once(rel,anchor,addition):
        p=ROOT/rel;s=p.read_text()
        if addition not in s:
            assert anchor in s,(rel,anchor)
            s=s.replace(anchor,anchor+addition,1)
        p.write_text(s,encoding='utf8',newline='\n')
    insert_once(prefix+'features/profiles/ProfileRepository.kt','    fun selectProfile(profileIndex: Int) {\n','        com.nuvio.app.core.sync.OmniaPreferencesSync.invalidateRequests()\n')
    insert_once(prefix+'features/settings/AccountSettingsPage.kt','    item { AccountSettingsBody(isTablet = isTablet) }\n','    item { OmniaPreferencesSyncSettings(isTablet = isTablet) }\n')
    insert_once(prefix+'core/sync/SyncManager.kt','    fun requestForegroundPull(profileId: Int, force: Boolean = false) {\n','        if (ProfileRepository.activeProfileId == profileId) OmniaPreferencesSync.requestSync()\n')
    insert_once('composeApp/src/androidMain/kotlin/com/nuvio/app/features/settings/ThemeSettingsStorage.android.kt','    fun initialize(context: Context) {\n','        com.nuvio.app.core.sync.OmniaPreferencesSyncStorage.initialize(context)\n')
    for p in [profile,home]:
        assert 'rpc("sync_push_profile_settings_blob"' not in p.read_text()
        assert 'rpc("sync_pull_profile_settings_blob"' not in p.read_text()
        assert 'rpc("sync_push_home_catalog_settings"' not in p.read_text()
        assert 'rpc("sync_pull_home_catalog_settings"' not in p.read_text()
    (ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=26\nMARKETING_VERSION=0.4.18\n',encoding='utf8',newline='\n')
    ios_tests=ROOT/'prepare_omnia_ios_tests.py'
    ios_tests.write_text(ios_tests.read_text().replace('Version 0.4.17 (25)','Version 0.4.18 (26)'),encoding='utf8',newline='\n')
    print('Prepared optional common preferences client and removed legacy automatic Home/platform-blob transport. Build and runtime checks still required.')

# Priority storage release: account/media storage and catalog defaults stay unchanged.
exec(compile('"""Bound browsing caches and remove obsolete installers without touching account/media data."""\nfrom pathlib import Path\nimport re\n\nmobile=(ROOT/\'composeApp\').is_dir()\npackage=\'com.nuvio.app.features.updater\' if mobile else \'com.nuvio.tv.updater\'\nbase=\'composeApp/src/androidMain/kotlin/com/nuvio/app/features/updater/\' if mobile else \'app/src/main/java/com/nuvio/tv/updater/\'\n\ndef write(relative,text):\n p=ROOT/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n\ndef replace(relative,old,new):\n p=ROOT/relative;s=p.read_text()\n if new in s:\n  p.write_text(s,encoding=\'utf-8\',newline=\'\\n\');return\n assert s.count(old)==1,(relative,old[:80],s.count(old))\n p.write_text(s.replace(old,new,1),encoding=\'utf-8\',newline=\'\\n\')\n\nutility=\'\'\'package PACKAGE\n\nimport java.io.File\n\n/** Operates on direct installer files in the app-owned updates directory only. */\ninternal object OmniaUpdateFiles {\n    private fun managed(directory: File): List<File> = directory.listFiles().orEmpty().filter {\n        it.isFile && it.canonicalFile.parentFile == directory.canonicalFile &&\n            (it.name.endsWith(".apk") || it.name.endsWith(".apk.part") || it.name == "update.dm")\n    }\n\n    fun prune(directory: File, keep: File? = null) {\n        require(keep == null || keep.canonicalFile.parentFile == directory.canonicalFile)\n        managed(directory).filter { it != keep }.forEach { it.delete() }\n    }\n\n    fun removeInstalled(directory: File, installedCode: Long, archiveCode: (File) -> Long?) {\n        managed(directory).forEach { file ->\n            val code = if (file.name.endsWith(".apk")) archiveCode(file) else null\n            if (code == null || code <= installedCode) file.delete()\n        }\n    }\n}\n\'\'\'.replace(\'PACKAGE\',package)\nwrite(base+\'OmniaUpdateFiles.kt\',utility)\n\ntests=\'\'\'package PACKAGE\n\nimport java.nio.file.Files\nimport org.junit.Assert.*\nimport org.junit.Test\n\nclass OmniaUpdateFilesTest {\n    @Test fun upgradeRemovesInstalledAndCorruptFilesButKeepsPendingUpdateAndUserFiles() {\n        val root = Files.createTempDirectory("omnia-update-cleanup").toFile()\n        try {\n            val names = listOf("old.apk", "current.apk", "future.apk", "corrupt.apk", "future.apk.part", "update.dm", "notes.txt")\n            names.forEach { root.resolve(it).writeText(it) }\n            val versions = mapOf("old.apk" to 1L, "current.apk" to 2L, "future.apk" to 3L)\n            OmniaUpdateFiles.removeInstalled(root, 2) { versions[it.name] }\n            assertEquals(setOf("future.apk", "notes.txt"), root.list()!!.toSet())\n            OmniaUpdateFiles.removeInstalled(root, 3) { versions[it.name] }\n            assertEquals(setOf("notes.txt"), root.list()!!.toSet())\n        } finally { root.deleteRecursively() }\n    }\n\n    @Test fun nextDownloadReclaimsOldInstallersWithoutRecursingIntoOtherData() {\n        val root = Files.createTempDirectory("omnia-update-prune").toFile()\n        try {\n            val pending = root.resolve("new.apk").apply { writeText("new") }\n            root.resolve("old.apk").writeText("old")\n            root.resolve("failed.apk.part").writeText("partial")\n            val unrelated = root.resolve("nested").apply { mkdir() }.resolve("saved.apk").apply { writeText("saved") }\n            OmniaUpdateFiles.prune(root, pending)\n            assertTrue(pending.exists());assertTrue(unrelated.exists())\n            assertFalse(root.resolve("old.apk").exists());assertFalse(root.resolve("failed.apk.part").exists())\n        } finally { root.deleteRecursively() }\n    }\n\n    @Test fun anOutsideKeepPathIsRejected() {\n        val root = Files.createTempDirectory("omnia-update-boundary").toFile()\n        try {\n            assertThrows(IllegalArgumentException::class.java) { OmniaUpdateFiles.prune(root, root.parentFile.resolve("outside.apk")) }\n        } finally { root.deleteRecursively() }\n    }\n\n    @Test fun symlinksCannotDeleteOutsideTheInstallerDirectory() {\n        val root = Files.createTempDirectory("omnia-update-symlink").toFile()\n        val outside = Files.createTempFile("omnia-preserved", ".apk").toFile()\n        try {\n            outside.writeText("preserved")\n            Files.createSymbolicLink(root.resolve("linked.apk").toPath(), outside.toPath())\n            OmniaUpdateFiles.prune(root)\n            assertEquals("preserved", outside.readText())\n        } finally { root.deleteRecursively();outside.delete() }\n    }\n}\n\'\'\'.replace(\'PACKAGE\',package)\ntestbase=\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/updater/\' if mobile else \'app/src/test/java/com/nuvio/tv/updater/\'\nwrite(testbase+\'OmniaUpdateFilesTest.kt\',tests)\n\ntransfer_tests=\'\'\'package PACKAGE\n\nimport java.io.File\nimport java.nio.file.Files\nimport java.util.concurrent.TimeUnit\nimport kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.runBlocking\nimport okhttp3.OkHttpClient\nimport okhttp3.mockwebserver.MockResponse\nimport okhttp3.mockwebserver.MockWebServer\nimport okhttp3.mockwebserver.SocketPolicy\nimport okio.Buffer\nimport org.junit.Assert.*\nimport org.junit.Test\nPLATFORM_IMPORTS\nPLATFORM_ANNOTATIONS\nclass OmniaDownloadTransferTest {\n    private fun directory(): File { PLATFORM_DIRECTORY }\n    private suspend fun download(server: MockWebServer, root: File, progress: (Long, Long?) -> Unit = { _, _ -> }): Result<File> {\n        PLATFORM_DOWNLOAD\n    }\n\n    @Test fun completeDownloadIsAtomicAndDoesNotEnterTheHttpCache() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            val data = ByteArray(16384) { (it % 255).toByte() }\n            server.enqueue(MockResponse().setBody(Buffer().write(data)))\n            val file = download(server, root).getOrThrow()\n            assertArrayEquals(data, file.readBytes())\n            assertFalse(root.resolve("candidate.apk.part").exists())\n            assertEquals("no-store", server.takeRequest().getHeader("Cache-Control"))\n        } } finally { root.deleteRecursively() }\n    } }\n\n    @Test fun httpFailureLeavesNoInstallerOrPartialFile() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            server.enqueue(MockResponse().setResponseCode(503).setBody("Unavailable"))\n            assertTrue(download(server, root).isFailure)\n            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())\n        } } finally { root.deleteRecursively() }\n    } }\n\n    @Test fun truncatedDownloadCannotBecomeAnInstallableFile() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            server.enqueue(MockResponse().setBody("short").setHeader("Content-Length", 4096).setSocketPolicy(SocketPolicy.DISCONNECT_AT_END))\n            assertTrue(download(server, root).isFailure)\n            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())\n        } } finally { root.deleteRecursively() }\n    } }\n\n    @Test fun cancellationIsPropagatedAndReclaimsThePartialDownload() { runBlocking {\n        val root = directory()\n        try { MockWebServer().use { server ->\n            server.enqueue(MockResponse().setBody("candidate bytes"))\n            var cancelled = false\n            try { download(server, root) { _, _ -> throw CancellationException("cancelled by test") } }\n            catch (_: CancellationException) { cancelled = true }\n            assertTrue(cancelled)\n            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())\n        } } finally { root.deleteRecursively() }\n    } }\n}\n\'\'\'.replace(\'PACKAGE\',package)\nif mobile:\n transfer_tests=transfer_tests.replace(\'PLATFORM_IMPORTS\',\'import android.app.Application\\nimport org.junit.runner.RunWith\\nimport org.robolectric.RobolectricTestRunner\\nimport org.robolectric.RuntimeEnvironment\\nimport org.robolectric.annotation.Config\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_ANNOTATIONS\',\'@RunWith(RobolectricTestRunner::class)\\n@Config(sdk = [34], application = Application::class)\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DIRECTORY\',\'val context = RuntimeEnvironment.getApplication(); AndroidAppUpdaterPlatform.initialize(context); return File(context.cacheDir, "updates").apply { mkdirs() }\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DOWNLOAD\',\'return AndroidAppUpdaterPlatform.downloadApk(server.url("/candidate.apk").toString(), "candidate.apk", progress).map { File(it) }\')\n write(\'composeApp/src/androidFullHostTest/kotlin/com/nuvio/app/features/updater/OmniaDownloadTransferTest.kt\',transfer_tests)\nelse:\n transfer_tests=transfer_tests.replace(\'PLATFORM_IMPORTS\',\'\').replace(\'PLATFORM_ANNOTATIONS\',\'\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DIRECTORY\',\'return Files.createTempDirectory("omnia-transfer").toFile()\')\n transfer_tests=transfer_tests.replace(\'PLATFORM_DOWNLOAD\',\'return ApkDownloader(OkHttpClient.Builder().readTimeout(2, TimeUnit.SECONDS).build()).download(server.url("/candidate.apk").toString(), root.resolve("candidate.apk"), progress)\')\n write(testbase+\'OmniaDownloadTransferTest.kt\',transfer_tests)\n\nif mobile:\n updater=\'composeApp/src/androidFull/kotlin/com/nuvio/app/features/updater/AndroidAppUpdaterPlatform.kt\'\n replace(updater,\'import kotlinx.coroutines.Dispatchers\',\'\'\'import kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.CoroutineScope\nimport kotlinx.coroutines.SupervisorJob\nimport kotlinx.coroutines.launch\nimport kotlinx.coroutines.sync.Mutex\nimport kotlinx.coroutines.sync.withLock\nimport kotlinx.coroutines.Dispatchers\'\'\')\n replace(updater,\'    private var appContext: Context? = null\',\'\'\'    private var appContext: Context? = null\n    private val downloadMutex = Mutex()\n    private val maintenanceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)\n    private var cleanupScheduled = false\'\'\')\n replace(updater,\'\'\'        appContext = context.applicationContext\n    }\n\'\'\',\'\'\'        appContext = context.applicationContext\n        val schedule = synchronized(this) {\n            if (cleanupScheduled) false else { cleanupScheduled = true; true }\n        }\n        if (schedule) maintenanceScope.launch {\n            downloadMutex.withLock {\n                runCatching {\n                    val current = context.packageManager.getPackageInfo(context.packageName, 0)\n                    val code = if (Build.VERSION.SDK_INT >= 28) current.longVersionCode else current.versionCode.toLong()\n                    listOf(File(context.cacheDir, "updates"), File(context.filesDir, "updates")).forEach { directory ->\n                    OmniaUpdateFiles.removeInstalled(directory, code) { file ->\n                        context.packageManager.getPackageArchiveInfo(file.path, 0)?.takeIf { it.packageName == context.packageName }?.let {\n                            if (Build.VERSION.SDK_INT >= 28) it.longVersionCode else it.versionCode.toLong()\n                        }\n                    }\n                    }\n                }\n            }\n        }\n    }\n\'\'\')\n p=ROOT/updater;s=p.read_text();start=s.index(\'    suspend fun downloadApk(\');end=s.index(\'    fun canRequestPackageInstalls()\',start)\n s=s[:start]+\'\'\'    suspend fun downloadApk(\n        assetUrl: String,\n        assetName: String,\n        onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,\n    ): Result<String> = withContext(Dispatchers.IO) {\n        downloadMutex.withLock {\n            val context = requireContext()\n            val safeName = assetName.replace(Regex("[^a-zA-Z0-9._-]"), "_")\n            val directory = File(context.cacheDir, "updates").apply { mkdirs() }\n            val destination = File(directory, safeName)\n            val partial = File(directory, "$safeName.part")\n            try {\n                require(safeName.endsWith(".apk")) { "Invalid update filename" }\n                OmniaUpdateFiles.prune(directory)\n                val request = Request.Builder().url(assetUrl).header("Cache-Control", "no-store").build()\n                httpClient.newCall(request).execute().use { response ->\n                    check(response.isSuccessful) { "Download failed: HTTP ${response.code}" }\n                    val body = checkNotNull(response.body) { "Empty update download" }\n                    val totalBytes = body.contentLength().takeIf { it > 0L }\n                    var received = 0L\n                    body.byteStream().use { input ->\n                        FileOutputStream(partial).use { output ->\n                            val buffer = ByteArray(64 * 1024)\n                            while (true) {\n                                currentCoroutineContext().ensureActive()\n                                val read = input.read(buffer)\n                                if (read < 0) break\n                                if (read == 0) continue\n                                output.write(buffer, 0, read);received += read\n                                onProgress(received, totalBytes)\n                            }\n                            output.fd.sync()\n                        }\n                    }\n                    check(received > 0L && (totalBytes == null || received == totalBytes)) { "Incomplete update download. Please retry." }\n                }\n                currentCoroutineContext().ensureActive()\n                check(partial.renameTo(destination)) { "Could not save update. Check free storage." }\n                Result.success(destination.absolutePath)\n            } catch (cancelled: CancellationException) {\n                throw cancelled\n            } catch (error: Exception) {\n                Result.failure(error)\n            } finally {\n                partial.delete()\n            }\n        }\n    }\n\n\'\'\'+s[end:];p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n replace(updater,\'\'\'        check(apkFile.exists()) { runBlocking { getString(Res.string.updates_downloaded_file_missing) } }\n\'\'\',\'\'\'        check(apkFile.exists()) { runBlocking { getString(Res.string.updates_downloaded_file_missing) } }\n        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)\n        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }\n\'\'\')\n app=\'composeApp/src/androidMain/kotlin/com/nuvio/app/NuvioApplication.kt\'\n replace(app,\'import coil3.ImageLoader\',\'import coil3.disk.DiskCache\\nimport okio.Path.Companion.toOkioPath\\nimport coil3.ImageLoader\')\n replace(app,\'            .diskCachePolicy(CachePolicy.ENABLED)\',\'\'\'            .diskCachePolicy(CachePolicy.ENABLED)\n            .diskCache {\n                DiskCache.Builder()\n                    .directory(context.cacheDir.resolve("image_cache").toOkioPath())\n                    .maxSizeBytes(96L * 1024 * 1024)\n                    .build()\n            }\'\'\')\n badge=\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/BadgeImageLoader.kt\'\n replace(badge,\'import coil3.ImageLoader\',\'import coil3.SingletonImageLoader\\nimport coil3.ImageLoader\')\n replace(badge,\'                .diskCachePolicy(CachePolicy.ENABLED)\',\'\'\'                .diskCachePolicy(CachePolicy.ENABLED)\n                .diskCache { SingletonImageLoader.get(context).diskCache }\'\'\')\n ios=\'composeApp/src/iosMain/kotlin/com/nuvio/app/core/ui/PlatformImageLoader.ios.kt\'\n write(ios,\'\'\'package com.nuvio.app.core.ui\n\nimport coil3.ImageLoader\nimport coil3.disk.DiskCache\nimport okio.Path.Companion.toPath\nimport platform.Foundation.NSCachesDirectory\nimport platform.Foundation.NSSearchPathForDirectoriesInDomains\nimport platform.Foundation.NSUserDomainMask\n\ninternal actual fun ImageLoader.Builder.configurePlatformImageLoader(): ImageLoader.Builder = diskCache {\n    val root = NSSearchPathForDirectoriesInDomains(NSCachesDirectory, NSUserDomainMask, true).first() as String\n    DiskCache.Builder()\n        .directory((root + "/image_cache").toPath())\n        .maxSizeBytes(96L * 1024 * 1024)\n        .build()\n}\n\ninternal actual val platformProvidesImageLoader: Boolean = false\n\'\'\')\n replace(\'composeApp/src/androidMain/kotlin/com/nuvio/app/features/addons/AddonPlatform.android.kt\',\'private const val cacheSizeBytes = 50L * 1024L * 1024L\',\'private const val cacheSizeBytes = 32L * 1024L * 1024L\')\n # Independent platform versions retain installed identity and release-channel matching.\n write(\'iosApp/Configuration/Version.xcconfig\',\'CURRENT_PROJECT_VERSION=27\\nMARKETING_VERSION=0.4.19\\n\')\n p=ROOT/\'prepare_omnia_ios_tests.py\';s=p.read_text().replace(\'Version 0.4.18 (26)\',\'Version 0.4.19 (27)\');p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\nelse:\n app=\'app/src/main/java/com/nuvio/tv/NuvioApplication.kt\'\n replace(app,\'.maxSizeBytes(200L * 1024 * 1024)\',\'.maxSizeBytes(96L * 1024 * 1024)\')\n badge=\'app/src/main/java/com/nuvio/tv/ui/components/StreamBadgeChips.kt\'\n replace(badge,\'.maxSizeBytes(50L * 1024 * 1024)\',\'.maxSizeBytes(8L * 1024 * 1024)\')\n net=\'app/src/main/java/com/nuvio/tv/core/di/NetworkModule.kt\';p=ROOT/net;s=p.read_text().replace(\'50L * 1024 * 1024\',\'32L * 1024 * 1024\').replace(\'// 50 MB disk cache\',\'// 32 MB disk cache\');p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n hooks=\'app/src/full/java/com/nuvio/tv/core/runtime/PluginRuntimeHooks.kt\';p=ROOT/hooks;s=p.read_text().replace(\'50L * 1024L * 1024L\',\'32L * 1024L * 1024L\');p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n store=\'app/src/full/java/com/nuvio/tv/updater/UpdateDownloadStore.kt\'\n replace(store,\'        val destination = destinationFor(update)\\n\',\'        val destination = destinationFor(update)\\n        OmniaUpdateFiles.prune(updatesDir)\\n\')\n replace(store,\'import kotlinx.coroutines.flow.first\',\'import kotlinx.coroutines.Dispatchers\\nimport kotlinx.coroutines.withContext\\nimport kotlinx.coroutines.flow.first\')\n p=ROOT/store;s=p.read_text();start=s.index(\'    suspend fun clearIfInstalled()\');end=s.index(\'\\n    }\',start)+len(\'\\n    }\')\n s=s[:start]+\'\'\'    suspend fun clearIfInstalled() = withContext(Dispatchers.IO) {\n        downloadMutex.withLock {\n            // Includes orphan installers and the cache location used by older releases.\n            listOf(File(context.cacheDir, "updates"), updatesDir).forEach { directory ->\n                OmniaUpdateFiles.removeInstalled(directory, BuildConfig.VERSION_CODE.toLong()) { file ->\n                    runCatching {\n                        context.packageManager.getPackageArchiveInfo(file.path, 0)?.takeIf { it.packageName == context.packageName }?.let {\n                            if (android.os.Build.VERSION.SDK_INT >= 28) it.longVersionCode else it.versionCode.toLong()\n                        }\n                    }.getOrNull()\n                }\n            }\n            val pending = updatePreferences.downloadedUpdate.first()\n            if (pending != null && !VersionUtils.isRemoteNewer(pending.first, BuildConfig.VERSION_NAME)) clear()\n        }\n    }\'\'\'+s[end:];p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n installer=\'app/src/full/java/com/nuvio/tv/updater/ApkInstaller.kt\'\n replace(installer,\'        val packageInstaller = context.packageManager.packageInstaller\',\'\'\'        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)\n        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }\n        val packageInstaller = context.packageManager.packageInstaller\'\'\')\n replace(installer,\'        val authority = "${BuildConfig.APPLICATION_ID}.fileprovider"\',\'\'\'        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)\n        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }\n        val authority = "${BuildConfig.APPLICATION_ID}.fileprovider"\'\'\')\n write(\'app/src/full/java/com/nuvio/tv/updater/ApkDownloader.kt\',\'\'\'package com.nuvio.tv.updater\n\nimport kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.currentCoroutineContext\nimport kotlinx.coroutines.ensureActive\nimport kotlinx.coroutines.withContext\nimport okhttp3.OkHttpClient\nimport okhttp3.Request\nimport java.io.File\nimport java.io.FileOutputStream\nimport javax.inject.Inject\nimport javax.inject.Singleton\n\n@Singleton\nclass ApkDownloader @Inject constructor(private val okHttpClient: OkHttpClient) {\n    suspend fun download(\n        url: String,\n        destinationFile: File,\n        onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit\n    ): Result<File> = withContext(Dispatchers.IO) {\n        val partial = File(destinationFile.parentFile, "${destinationFile.name}.part")\n        try {\n            destinationFile.parentFile?.mkdirs()\n            if (destinationFile.exists()) check(destinationFile.delete()) { "Could not replace the saved update" }\n            val request = Request.Builder().url(url).header("Cache-Control", "no-store").build()\n            okHttpClient.newCall(request).execute().use { response ->\n                check(response.isSuccessful) { "Download failed: HTTP ${response.code}" }\n                val body = checkNotNull(response.body) { "Empty update download" }\n                val total = body.contentLength().takeIf { it > 0 }\n                var received = 0L\n                body.byteStream().use { input ->\n                    FileOutputStream(partial).use { output ->\n                        val buffer = ByteArray(64 * 1024)\n                        while (true) {\n                            currentCoroutineContext().ensureActive()\n                            val read = input.read(buffer)\n                            if (read < 0) break\n                            if (read == 0) continue\n                            output.write(buffer, 0, read);received += read\n                            onProgress(received, total)\n                        }\n                        output.fd.sync()\n                    }\n                }\n                check(received > 0L && (total == null || received == total)) { "Incomplete update download. Please retry." }\n            }\n            currentCoroutineContext().ensureActive()\n            check(partial.renameTo(destinationFile)) { "Could not save update. Check free storage." }\n            Result.success(destinationFile)\n        } catch (cancelled: CancellationException) {\n            throw cancelled\n        } catch (error: Exception) {\n            Result.failure(error)\n        } finally {\n            partial.delete()\n        }\n    }\n}\n\'\'\')\n p=ROOT/\'app/build.gradle.kts\';s=p.read_text();s,n=re.subn(r\'versionCode = \\d+\',\'versionCode = 26\',s,count=1);assert n==1;s,n=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.20"\',s,count=1);assert n==1;p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n\n# Display labels are independent of the technical tags consumed by installed updaters.\npaths=([\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/updater/VersionUtils.kt\',\n        \'composeApp/src/commonMain/kotlin/com/nuvio/app/features/updater/AppUpdaterBanner.kt\'] if mobile else\n       [\'app/src/main/java/com/nuvio/tv/updater/VersionUtils.kt\',\n        \'app/src/full/java/com/nuvio/tv/updater/ui/UpdateBanner.kt\'])\np=ROOT/paths[0];s=p.read_text()\nif \'fun displayLabel(\' not in s:\n anchor=\'    fun parse(raw: String?): SemanticVersion? {\'\n assert s.count(anchor)==1\n s=s.replace(anchor,"    fun displayLabel(raw: String?): String {\\n        val normalized = normalize(raw)\\n        return if (parse(normalized) != null) normalized.substringBefore(\'+\') else normalized\\n    }\\n\\n"+anchor,1)\np.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\nif not mobile:\n p=ROOT/paths[1];s=p.read_text()\n if \'import com.nuvio.tv.updater.VersionUtils\' not in s:s=s.replace(\'import com.nuvio.tv.updater.UpdateUiState\',\'import com.nuvio.tv.updater.VersionUtils\\nimport com.nuvio.tv.updater.UpdateUiState\',1)\n p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\nreplace(paths[1],\'        update.tag,\\n\',\'        VersionUtils.displayLabel(update.tag),\\n\')\n\nprint(\'Prepared bounded browsing caches, obsolete installer cleanup and same-package install guard; account/media storage unchanged.\')\n', "omnia-storage-update-overlay", "exec"))

exec(compile('"""Fresh-profile catalog defaults and display-only version labels; no stored-list rewrite."""\nCORE_URL=\'https://omnia.161.97.128.244.sslip.io/catalogs/core/manifest.json\'\nif (ROOT/\'composeApp\').exists():\n    prefix=\'composeApp/src/commonMain/kotlin/com/nuvio/app/\'\n    p=ROOT/prefix/\'features/addons/OmniaAddonDefaults.kt\'\n    p.write_text(\'\'\'package com.nuvio.app.features.addons\n\n// Fallback for a profile with no saved local list. Explicitly empty lists and\n// existing configured add-ons are preserved by the platform storage readers.\ninternal val omniaDefaultAddonUrls = listOf(\n    "\'\'\'+CORE_URL+\'\'\'",\n    "https://opensubtitles-v3.strem.io/manifest.json",\n)\n\'\'\',encoding=\'utf-8\',newline=\'\\n\')\n    version=ROOT/\'iosApp/Configuration/Version.xcconfig\'\n    version.write_text(\'CURRENT_PROJECT_VERSION=27\\nMARKETING_VERSION=0.4.19\\n\',encoding=\'utf-8\',newline=\'\\n\')\n    p=ROOT/\'prepare_omnia_ios_tests.py\'\n    p.write_text(p.read_text().replace(\'Version 0.4.18 (26)\',\'Version 0.4.19 (27)\'),encoding=\'utf-8\',newline=\'\\n\')\n    paths=[prefix+\'features/updater/VersionUtils.kt\',prefix+\'features/updater/AppUpdaterBanner.kt\']\nelse:\n    p=ROOT/\'app/src/main/java/com/nuvio/tv/data/local/AddonPreferences.kt\';s=p.read_text()\n    pattern=r\'private fun getDefaultAddons\\(\\): Set<String> = setOf\\(.*?\\n    \\)\'\n    new=\'private fun getDefaultAddons(): Set<String> = setOf(\\n        "\'+CORE_URL+\'",\\n        "https://opensubtitles-v3.strem.io"\\n    )\'\n    assert len(re.findall(pattern,s,re.S))==1\n    p.write_text(re.sub(pattern,lambda _:new,s,count=1,flags=re.S),encoding=\'utf-8\',newline=\'\\n\')\n    p=ROOT/\'app/build.gradle.kts\';s=p.read_text()\n    s,count=re.subn(r\'versionCode = \\d+\',\'versionCode = 26\',s,count=1);assert count==1\n    s,count=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.20"\',s,count=1);assert count==1\n    p.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n    paths=[\'app/src/main/java/com/nuvio/tv/updater/VersionUtils.kt\',\'app/src/full/java/com/nuvio/tv/updater/ui/UpdateBanner.kt\']\n    banner=ROOT/paths[1];s=banner.read_text()\n    if \'import com.nuvio.tv.updater.VersionUtils\' not in s:s=s.replace(\'import com.nuvio.tv.updater.UpdateUiState\',\'import com.nuvio.tv.updater.VersionUtils\\nimport com.nuvio.tv.updater.UpdateUiState\',1)\n    banner.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n\np=ROOT/paths[0];s=p.read_text();anchor=\'    fun parse(raw: String?): SemanticVersion? {\'\naddition=\'\'\'    /** Keep technical release tags intact for comparison, downloads and ignored updates. */\n    fun displayLabel(raw: String?): String {\n        val normalized = normalize(raw)\n        return if (parse(normalized) != null) normalized.substringBefore(\'+\') else normalized\n    }\n\n\'\'\'\nif \'fun displayLabel(\' not in s:\n    assert s.count(anchor)==1;s=s.replace(anchor,addition+anchor,1)\np.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\np=ROOT/paths[1];s=p.read_text();old=\'        update.tag,\\n\';new=\'        VersionUtils.displayLabel(update.tag),\\n\'\nif new not in s:\n    assert s.count(old)==1;s=s.replace(old,new,1)\np.write_text(s,encoding=\'utf-8\',newline=\'\\n\')\n\n# This deliberately does not replace values in saved addon lists, sync envelopes,\n# Home catalog records or release models. A configured profile keeps its choices.\nprint(\'Prepared fresh-profile Omnia Catalog default and clean display-only version labels. Build/native rollout still gated.\')\n', "omnia-core-defaults-overlay", "exec"))
exec(compile('"""Catalog/hero follow-up on top of the preserved storage candidates."""\nfrom pathlib import Path\nimport re\n\nmobile=(ROOT/\'composeApp\').is_dir()\ndef write(path,text):\n    dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True)\n    dest.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n\nif mobile:\n    prefix=\'composeApp/src/commonMain/kotlin/com/nuvio/app/\'\n    path=prefix+\'features/details/MetaScreenSettingsRepository.kt\'\n    text=(ROOT/path).read_text()\n    # Missing/default values become on; explicitly stored false remains false.\n    text=text.replace(\'heroTrailerPlayback: Boolean = false\',\'heroTrailerPlayback: Boolean = true\')\n    text=text.replace(\'heroTrailerPlayback = false\',\'heroTrailerPlayback = true\')\n    write(path,text)\n    path=prefix+\'features/details/HeroTrailerAudioState.kt\'\n    text=(ROOT/path).read_text().replace(\'MutableStateFlow(true)\',\'MutableStateFlow(false)\')\n    write(path,text)\n    path=prefix+\'features/home/HomeCatalogSettingsRepository.kt\'\n    text=(ROOT/path).read_text().replace(\'const val HERO_SOURCE_SELECTION_LIMIT = 6\',\'const val HERO_SOURCE_SELECTION_LIMIT = 12\')\n    write(path,text)\n    path=prefix+\'features/home/HomeRepository.kt\'\n    text=(ROOT/path).read_text().replace(\'private const val HOME_COLLECTION_HERO_SOURCE_LIMIT = 6\',\'private const val HOME_COLLECTION_HERO_SOURCE_LIMIT = HomeCatalogSettingsRepository.HERO_SOURCE_SELECTION_LIMIT\')\n    write(path,text)\n    path=\'composeApp/src/iosMain/kotlin/com/nuvio/app/core/ui/PlatformImageLoader.ios.kt\'\n    text=(ROOT/path).read_text()\n    if not text.startswith(\'@file:OptIn(\'):text=\'@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)\\n\\n\'+text\n    write(path,text)\n    path=\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/home/HomeCatalogSettingsRepositoryTest.kt\'\n    text=(ROOT/path).read_text()\n    text=text.replace(\'omniaAllowsSixHeroCatalogsAndReplacingASelection\',\'omniaAllowsTwelveHeroCatalogsAndReplacingASelection\')\n    start=text.index(\'    fun omniaAllowsTwelveHeroCatalogsAndReplacingASelection()\')\n    end=text.index(\'    private fun addon()\',start)\n    # Replace the whole test deterministically; replay must not append assertions.\n    block=\'\'\'    fun omniaAllowsTwelveHeroCatalogsAndReplacingASelection() {\n        val base = addon()\n        val manifest = requireNotNull(base.manifest)\n        val catalogs = listOf(base.copy(\n            manifest = manifest.copy(catalogs = (1..13).map {\n                AddonCatalog(type = "movie", id = "catalog$it", name = "Catalog $it")\n            }),\n        ))\n        HomeCatalogSettingsRepository.syncCatalogs(catalogs)\n        val keys = HomeCatalogSettingsRepository.uiState.value.items.map { it.key }\n        assertEquals(12, HomeCatalogSettingsRepository.HERO_SOURCE_SELECTION_LIMIT)\n        keys.forEach { HomeCatalogSettingsRepository.setHeroSourceEnabled(it, false) }\n        keys.take(12).forEach { HomeCatalogSettingsRepository.setHeroSourceEnabled(it, true) }\n        HomeCatalogSettingsRepository.setHeroSourceEnabled(keys.last(), true)\n        assertEquals(12, HomeCatalogSettingsRepository.uiState.value.items.count { it.heroSourceEnabled })\n        assertTrue(!HomeCatalogSettingsRepository.uiState.value.items.last().heroSourceEnabled)\n        HomeCatalogSettingsRepository.setHeroSourceEnabled(keys.first(), false)\n        HomeCatalogSettingsRepository.setHeroSourceEnabled(keys.last(), true)\n        assertEquals(12, HomeCatalogSettingsRepository.uiState.value.items.count { it.heroSourceEnabled })\n        assertTrue(HomeCatalogSettingsRepository.uiState.value.items.last().heroSourceEnabled)\n        HomeCatalogSettingsRepository.onProfileChanged()\n        HomeCatalogSettingsRepository.syncCatalogs(catalogs)\n        assertEquals(12, HomeCatalogSettingsRepository.uiState.value.items.count { it.heroSourceEnabled })\n        assertTrue(!HomeCatalogSettingsRepository.uiState.value.items.first().heroSourceEnabled)\n        assertTrue(HomeCatalogSettingsRepository.uiState.value.items.last().heroSourceEnabled)\n    }\n\n\'\'\'\n    write(path,text[:start]+block+text[end:])\n    write(\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/details/OmniaHeroDefaultsTest.kt\',\'\'\'package com.nuvio.app.features.details\n\nimport android.app.Application\nimport android.content.Context\nimport org.junit.Before\nimport org.junit.After\nimport org.junit.Test\nimport org.junit.Assert.*\nimport org.junit.runner.RunWith\nimport org.robolectric.RobolectricTestRunner\nimport org.robolectric.RuntimeEnvironment\nimport org.robolectric.annotation.Config\n\n@RunWith(RobolectricTestRunner::class)\n@Config(sdk = [34], application = Application::class)\nclass OmniaHeroDefaultsTest {\n    @Before fun initialize() {\n        val context = RuntimeEnvironment.getApplication()\n        context.getSharedPreferences("nuvio_meta_screen_settings", Context.MODE_PRIVATE).edit().clear().commit()\n        MetaScreenSettingsStorage.initialize(context)\n        MetaScreenSettingsRepository.clearLocalState()\n    }\n    @After fun finish() { MetaScreenSettingsRepository.clearLocalState() }\n\n    @Test fun freshProfileEnablesTrailers() {\n        MetaScreenSettingsRepository.ensureLoaded()\n        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        assertTrue(MetaScreenSettingsStorage.loadPayload()!!.contains("\\\\"hero_trailer_playback\\\\":true"))\n    }\n    @Test fun olderPayloadWithoutTrailerSettingUsesDefaultAndKeepsOtherChoices() {\n        MetaScreenSettingsStorage.savePayload("""{"blur_unwatched_episodes":true}""")\n        MetaScreenSettingsRepository.onProfileChanged()\n        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        assertTrue(MetaScreenSettingsRepository.uiState.value.blurUnwatchedEpisodes)\n    }\n    @Test fun explicitOffSurvivesProfileReloadAndUnrelatedChanges() {\n        MetaScreenSettingsRepository.setHeroTrailerPlayback(false)\n        MetaScreenSettingsRepository.setShowOverallRatings(false)\n        MetaScreenSettingsRepository.onProfileChanged()\n        assertFalse(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        assertFalse(MetaScreenSettingsRepository.uiState.value.showOverallRatings)\n    }\n    @Test fun resetRestoresDefaultButDoesNotChangeRetainedPayload() {\n        MetaScreenSettingsRepository.setHeroTrailerPlayback(false)\n        val before = MetaScreenSettingsStorage.loadPayload()!!\n        MetaScreenSettingsRepository.resetToDefaults()\n        assertTrue(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n        MetaScreenSettingsStorage.savePayload(before)\n        MetaScreenSettingsRepository.onProfileChanged()\n        assertFalse(MetaScreenSettingsRepository.uiState.value.heroTrailerPlayback)\n    }\n}\n\'\'\')\n    write(\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/details/OmniaHeroAudioStateTest.kt\',\'\'\'package com.nuvio.app.features.details\n\nimport kotlin.test.Test\nimport kotlin.test.assertFalse\nimport kotlin.test.assertTrue\n\nclass OmniaHeroAudioStateTest {\n    @Test fun defaultIsAudibleAndExplicitMuteCanBeToggledBack() {\n        assertFalse(HeroTrailerAudioState.muted.value)\n        HeroTrailerAudioState.toggleMuted()\n        try { assertTrue(HeroTrailerAudioState.muted.value) }\n        finally { HeroTrailerAudioState.toggleMuted() }\n        assertFalse(HeroTrailerAudioState.muted.value)\n    }\n}\n\'\'\')\n    write(\'iosApp/Configuration/Version.xcconfig\',\'CURRENT_PROJECT_VERSION=28\\nMARKETING_VERSION=0.4.20\\n\')\n    path=\'prepare_omnia_ios_tests.py\'\n    text=(ROOT/path).read_text().replace(\'Version 0.4.19 (27)\',\'Version 0.4.20 (28)\').replace(\'Version 0.4.18 (26)\',\'Version 0.4.20 (28)\')\n    write(path,text)\nelse:\n    path=\'app/src/main/java/com/nuvio/tv/data/local/LayoutPreferenceDataStore.kt\'\n    text=(ROOT/path).read_text()\n    # Playback enablement and the user\'s audio choice are independent preferences.\n    text=text.replace(\'                prefs[focusedPosterBackdropTrailerMutedKey] = true\\n\',\'\')\n    write(path,text)\n    write(\'app/src/test/java/com/nuvio/tv/data/local/OmniaHeroPreferencesTest.kt\',\'\'\'package com.nuvio.tv.data.local\n\nimport androidx.datastore.preferences.core.booleanPreferencesKey\nimport com.nuvio.tv.TestPreferencesStore\nimport com.nuvio.tv.core.profile.ProfileManager\nimport io.mockk.every\nimport io.mockk.mockk\nimport kotlinx.coroutines.flow.MutableStateFlow\nimport kotlinx.coroutines.flow.first\nimport kotlinx.coroutines.runBlocking\nimport org.junit.Assert.*\nimport org.junit.Test\n\nclass OmniaHeroPreferencesTest {\n    private fun preferences(): Pair<LayoutPreferenceDataStore, TestPreferencesStore> {\n        val store = TestPreferencesStore()\n        val profiles = mockk<ProfileManager>()\n        every { profiles.activeProfileId } returns MutableStateFlow(1)\n        every { profiles.profiles } returns MutableStateFlow(emptyList())\n        val factory = mockk<ProfileDataStoreFactory>()\n        every { factory.get(1, "layout_settings") } returns store\n        return LayoutPreferenceDataStore(factory, profiles) to store\n    }\n    @Test fun freshProfilePlaysHeroTrailersWithAudio() = runBlocking {\n        val (prefs, _) = preferences()\n        assertTrue(prefs.focusedPosterBackdropTrailerEnabled.first())\n        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())\n    }\n    @Test fun disablingAndReenablingTrailersKeepsAnAudibleChoice() = runBlocking {\n        val (prefs, store) = preferences()\n        prefs.setFocusedPosterBackdropTrailerMuted(false)\n        prefs.setFocusedPosterBackdropTrailerEnabled(false)\n        prefs.setFocusedPosterBackdropTrailerEnabled(true)\n        assertTrue(prefs.focusedPosterBackdropTrailerEnabled.first())\n        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())\n        assertFalse(store.value[booleanPreferencesKey("focused_poster_backdrop_trailer_muted")]!!)\n    }\n    @Test fun explicitMuteSurvivesTrailerAndExpansionToggles() = runBlocking {\n        val (prefs, _) = preferences()\n        prefs.setFocusedPosterBackdropTrailerMuted(true)\n        prefs.setFocusedPosterBackdropTrailerEnabled(false)\n        prefs.setFocusedPosterBackdropTrailerEnabled(true)\n        prefs.setFocusedPosterBackdropExpandEnabled(false)\n        prefs.setFocusedPosterBackdropExpandEnabled(true)\n        assertTrue(prefs.focusedPosterBackdropTrailerMuted.first())\n    }\n    @Test fun disablingExpansionDoesNotOverwriteAnAudibleChoice() = runBlocking {\n        val (prefs, _) = preferences()\n        prefs.setFocusedPosterBackdropTrailerMuted(false)\n        prefs.setFocusedPosterBackdropExpandEnabled(false)\n        assertFalse(prefs.focusedPosterBackdropTrailerMuted.first())\n    }\n}\n\'\'\')\n    path=\'app/build.gradle.kts\';text=(ROOT/path).read_text()\n    text,n=re.subn(r\'versionCode = \\d+\',\'versionCode = 27\',text,count=1);assert n==1\n    text,n=re.subn(r\'versionName = "[^"]+"\',\'versionName = "0.3.21"\',text,count=1);assert n==1\n    write(path,text)\n\nprint(\'Prepared next catalog/hero candidate with saved-choice preservation; compilation/runtime/release remain gated.\')\n', "omnia-major-catalog-hero-overlay", "exec"))
exec(compile('"""Use the existing Omnia account portal without duplicating account storage."""\nmobile=(ROOT/\'composeApp\').is_dir()\ndef write(path,text):\n    path=ROOT/path;path.parent.mkdir(parents=True,exist_ok=True)\n    path.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n\npackage=\'com.nuvio.app.features.auth\' if mobile else \'com.nuvio.tv.ui.screens.account\'\npolicy=\'\'\'package PACKAGE\n\n/** Fixed public account entry points. Never carries app credentials or session tokens. */\ninternal object OmniaAccountPortal {\n    const val ORIGIN = "https://omnia.161.97.128.244.sslip.io"\n    const val ACCOUNT_URL = "$ORIGIN/discord-account/"\n    const val SIGNUP_URL = "$ORIGIN/account/signup"\n    const val RECOVERY_URL = "$ORIGIN/account/recover"\n\n    fun availableFor(backendUrl: String): Boolean =\n        backendUrl.trim().trimEnd(\'/\').equals(ORIGIN, ignoreCase = true)\n}\n\'\'\'.replace(\'PACKAGE\',package)\npath=(\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/auth/\' if mobile else \'app/src/main/java/com/nuvio/tv/ui/screens/account/\')\nwrite(path+\'OmniaAccountPortal.kt\',policy)\n\nif mobile:\n    file=path+\'AuthScreen.kt\';text=(ROOT/file).read_text()\n    old=\'\'\'        // Omnia currently uses a single pre-provisioned private account.\n        // Public signup is disabled on the server and is not offered here.\'\'\'\n    if \'        OmniaAccountPortalLinks(enabled = !isLoading)\' not in text:\n        assert text.count(old)==1\n        text=text.replace(old,\'        OmniaAccountPortalLinks(enabled = !isLoading)\',1)\n    write(file,text)\n    write(path+\'OmniaAccountPortalLinks.kt\',\'\'\'package com.nuvio.app.features.auth\n\nimport androidx.compose.foundation.layout.Arrangement\nimport androidx.compose.foundation.layout.Column\nimport androidx.compose.foundation.layout.Row\nimport androidx.compose.foundation.layout.fillMaxWidth\nimport androidx.compose.foundation.layout.padding\nimport androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.Text\nimport androidx.compose.material3.TextButton\nimport androidx.compose.runtime.Composable\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.setValue\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.platform.LocalUriHandler\nimport androidx.compose.ui.unit.dp\nimport androidx.lifecycle.compose.collectAsStateWithLifecycle\nimport com.nuvio.app.core.network.ServerConfigurationRepository\n\n@Composable\ninternal fun OmniaAccountPortalLinks(enabled: Boolean) {\n    val server by ServerConfigurationRepository.active.collectAsStateWithLifecycle()\n    if (!OmniaAccountPortal.availableFor(server.backendUrl)) return\n    val handler = LocalUriHandler.current\n    var fallbackUrl by remember { mutableStateOf<String?>(null) }\n    fun open(url: String) {\n        fallbackUrl = if (runCatching { handler.openUri(url) }.isSuccess) null else url\n    }\n    Column(modifier = Modifier.fillMaxWidth()) {\n        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {\n            TextButton(enabled = enabled, onClick = { open(OmniaAccountPortal.SIGNUP_URL) }) { Text("Create account") }\n            TextButton(enabled = enabled, onClick = { open(OmniaAccountPortal.RECOVERY_URL) }) { Text("Forgot password?") }\n        }\n        TextButton(enabled = enabled, onClick = { open(OmniaAccountPortal.ACCOUNT_URL) }) { Text("Google or Discord account") }\n        Text(\n            "Set an Omnia app password in Account, then use the same email and password on every device.",\n            modifier = Modifier.padding(horizontal = 12.dp),\n            style = MaterialTheme.typography.bodySmall,\n            color = MaterialTheme.colorScheme.onSurfaceVariant,\n        )\n        fallbackUrl?.let { url ->\n            Text("Open in a browser: $url", style = MaterialTheme.typography.bodySmall)\n        }\n    }\n}\n\'\'\')\nelse:\n    file=path+\'AccountViewModel.kt\';text=(ROOT/file).read_text()\n    anchor=\'    internal val preferencesSyncState = omniaPreferences.state\'\n    if \'internal val hasOmniaAccountPortal:\' not in text:\n        assert text.count(anchor)==1\n        text=text.replace(anchor,\'    internal val hasOmniaAccountPortal: Boolean = OmniaAccountPortal.availableFor(serverConfiguration.backendUrl)\\n\\n\'+anchor,1)\n    write(file,text)\n    file=path+\'AuthQrSignInScreen.kt\';text=(ROOT/file).read_text()\n    for imp in [\'import androidx.compose.foundation.rememberScrollState\',\'import androidx.compose.foundation.verticalScroll\']:\n        if imp not in text:text=text.replace(\'import androidx.compose.runtime.Composable\',imp+\'\\nimport androidx.compose.runtime.Composable\',1)\n    if \'                hasOmniaAccountPortal = viewModel.hasOmniaAccountPortal,\' not in text:\n        anchor=\'                onSignIn = viewModel::signIn,\';assert text.count(anchor)==1\n        text=text.replace(anchor,\'                hasOmniaAccountPortal = viewModel.hasOmniaAccountPortal,\\n\'+anchor,1)\n    anchor=\'    useEmailLogin: Boolean,\\n    needsServer: Boolean,\\n\'\n    if \'    hasOmniaAccountPortal: Boolean,\\n\' not in text:\n        assert text.count(anchor)==1;text=text.replace(anchor,anchor+\'    hasOmniaAccountPortal: Boolean,\\n\',1)\n    text=text.replace(\'modifier = modifier.padding(horizontal = 48.dp),\',\'modifier = modifier.verticalScroll(rememberScrollState()).padding(horizontal = 48.dp, vertical = 24.dp),\',1)\n    anchor=\'\'\'                initialFocusRequester = initialFocusRequester\n            )\n        } else {\n            AuthQrCodeBlock(uiState = uiState)\'\'\'\n    replacement=\'\'\'                initialFocusRequester = initialFocusRequester\n            )\n            if (hasOmniaAccountPortal) OmniaTvAccountPortalLink(enabled = !uiState.isLoading)\n        } else {\n            AuthQrCodeBlock(uiState = uiState)\'\'\'\n    if replacement not in text:\n        assert text.count(anchor)==1;text=text.replace(anchor,replacement,1)\n    write(file,text)\n    write(path+\'OmniaTvAccountPortalLink.kt\',\'\'\'@file:OptIn(androidx.tv.material3.ExperimentalTvMaterial3Api::class)\n\npackage com.nuvio.tv.ui.screens.account\n\nimport androidx.compose.foundation.layout.Column\nimport androidx.compose.foundation.layout.Spacer\nimport androidx.compose.foundation.layout.fillMaxWidth\nimport androidx.compose.foundation.layout.height\nimport androidx.tv.material3.MaterialTheme\nimport androidx.tv.material3.Text\nimport androidx.compose.runtime.Composable\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.setValue\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.graphics.Color\nimport androidx.compose.ui.platform.LocalUriHandler\nimport androidx.compose.ui.unit.dp\nimport androidx.tv.material3.Button\n\n@Composable\ninternal fun OmniaTvAccountPortalLink(enabled: Boolean) {\n    val handler = LocalUriHandler.current\n    var browserUnavailable by remember { mutableStateOf(false) }\n    Column {\n        Spacer(Modifier.height(10.dp))\n        Button(\n            enabled = enabled,\n            modifier = Modifier.fillMaxWidth(),\n            onClick = { browserUnavailable = runCatching { handler.openUri(OmniaAccountPortal.ACCOUNT_URL) }.isFailure },\n        ) { Text("Account options") }\n        Spacer(Modifier.height(6.dp))\n        Text(\n            "Create an account, reset your password, or set an app password for a linked Google or Discord account.",\n            style = MaterialTheme.typography.bodySmall,\n            color = Color(0xFF969CA3),\n        )\n        if (browserUnavailable) Text(\n            "Open in a browser: ${OmniaAccountPortal.ACCOUNT_URL}",\n            style = MaterialTheme.typography.bodySmall,\n            color = Color(0xFF969CA3),\n        )\n    }\n}\n\'\'\')\n\ntests=\'\'\'package PACKAGE\n\nIMPORTS\n\nclass OmniaAccountPortalTest {\n    @Test fun acceptsOnlyTheExactOmniaBackend() {\n        assertTrue(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN))\n        assertTrue(OmniaAccountPortal.availableFor("  " + OmniaAccountPortal.ORIGIN + "/  "))\n        assertFalse(OmniaAccountPortal.availableFor("http://omnia.161.97.128.244.sslip.io"))\n        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + ".example.com"))\n        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + "@example.com"))\n        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + "?redirect=example.com"))\n        assertFalse(OmniaAccountPortal.availableFor("https://custom.example.com"))\n    }\n    @Test fun accountLinksHaveNoCredentialsOrSessionParameters() {\n        assertTrue(OmniaAccountPortal.ACCOUNT_URL == OmniaAccountPortal.ORIGIN + "/discord-account/")\n        assertTrue(OmniaAccountPortal.SIGNUP_URL == OmniaAccountPortal.ORIGIN + "/account/signup")\n        assertTrue(OmniaAccountPortal.RECOVERY_URL == OmniaAccountPortal.ORIGIN + "/account/recover")\n        listOf(OmniaAccountPortal.ACCOUNT_URL, OmniaAccountPortal.SIGNUP_URL, OmniaAccountPortal.RECOVERY_URL).forEach {\n            assertFalse(\'?\' in it || \'#\' in it || \'@\' in it)\n        }\n    }\n}\n\'\'\'.replace(\'PACKAGE\',package)\nif mobile:\n    tests=tests.replace(\'IMPORTS\',\'import kotlin.test.Test\\nimport kotlin.test.assertTrue\\nimport kotlin.test.assertFalse\')\n    write(\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/auth/OmniaAccountPortalTest.kt\',tests)\nelse:\n    tests=tests.replace(\'IMPORTS\',\'import org.junit.Test\\nimport org.junit.Assert.assertTrue\\nimport org.junit.Assert.assertFalse\')\n    write(\'app/src/test/java/com/nuvio/tv/ui/screens/account/OmniaAccountPortalTest.kt\',tests)\nprint(\'Prepared shared-account registration/recovery entry points; existing native sessions and authentication backend unchanged.\')\n', "omnia-account-entrypoints-overlay", "exec"))
exec(compile('"""Keep remote focus in Account when temporary sync actions disappear."""\nif not (ROOT/\'composeApp\').is_dir():\n    path=ROOT/\'app/src/main/java/com/nuvio/tv/ui/screens/account/AccountSettingsContent.kt\'\n    text=path.read_text()\n    start=text.index(\'private fun OmniaPreferencesSyncSettings(viewModel: AccountViewModel) {\')\n    before,block=text[:start],text[start:]\n    anchor=\'    val state by viewModel.preferencesSyncState.collectAsStateWithLifecycle()\\n\'\n    if \'val syncControlFocus = remember { FocusRequester() }\' not in block:\n        assert block.count(anchor)==1\n        block=block.replace(anchor,anchor+\'\'\'    val syncControlFocus = remember { FocusRequester() }\n    fun fromStableControl(action: () -> Unit) {\n        // The clicked choice/manual action is removed during synchronization.\n        // Move focus before it leaves the tree, keeping DPAD navigation in this panel.\n        syncControlFocus.requestFocus()\n        action()\n    }\n\'\'\',1)\n    anchor=\'            onClick = { if (state.enabled) viewModel.disablePreferencesSync() else if (state.status != SharedPreferencesSyncStatus.Syncing) viewModel.enablePreferencesSync() },\\n\'\n    if \'            modifier = Modifier.focusRequester(syncControlFocus),\' not in block:\n        assert block.count(anchor)==1\n        block=block.replace(anchor,anchor+\'            modifier = Modifier.focusRequester(syncControlFocus),\\n\',1)\n    for choice in [\'UseSavedSettings\',\'UseThisDevice\']:\n        old=\'{ viewModel.enablePreferencesSync(SharedPreferencesInitialChoice.\'+choice+\') }\'\n        new=\'{ fromStableControl { viewModel.enablePreferencesSync(SharedPreferencesInitialChoice.\'+choice+\') } }\'\n        if new not in block:\n            assert block.count(old)==1;block=block.replace(old,new,1)\n    for method in [\'cancelPreferencesChoice\',\'synchronizePreferences\']:\n        old=\'viewModel::\'+method+\')\';new=\'{ fromStableControl(viewModel::\'+method+\') })\'\n        if new not in block:\n            assert block.count(old)==1;block=block.replace(old,new,1)\n    old=\'"Keep this device’s settings separate.", viewModel::disablePreferencesSync)\'\n    new=\'"Keep this device’s settings separate.", { fromStableControl(viewModel::disablePreferencesSync) })\'\n    if new not in block:\n        assert block.count(old)==1;block=block.replace(old,new,1)\n    path.write_text(before+block,encoding=\'utf-8\',newline=\'\\n\')\n    print(\'Prepared stable TV account-sync focus before temporary action removal; native recheck required.\')\n', "omnia-tv-account-focus-overlay", "exec"))

exec(compile('"""Align existing provider regression tests with the requested Omnia feature set."""\npath=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/debrid/DebridSettingsTest.kt\'\ntext=path.read_text()\ntext=text.replace(\'assertEquals(listOf(DebridProviders.TORBOX_ID, DebridProviders.PREMIUMIZE_ID), services.map { it.provider.id })\',\'assertEquals(listOf(DebridProviders.TORBOX_ID, DebridProviders.PREMIUMIZE_ID, DebridProviders.REAL_DEBRID_ID), services.map { it.provider.id })\')\ntext=text.replace(\'assertEquals(listOf("tb_key", "pm_key"), services.map { it.apiKey })\',\'assertEquals(listOf("tb_key", "pm_key", "rd_key"), services.map { it.apiKey })\')\ntext=text.replace(\'assertFalse(DebridProviders.isVisible(DebridProviders.REAL_DEBRID_ID))\',\'assertTrue(DebridProviders.isVisible(DebridProviders.REAL_DEBRID_ID))\')\ntext=text.replace(\'fun `cloud library and link resolving capabilities are independent`()\',\'fun `legacy cloud library preference cannot activate a removed capability`()\')\ntext=text.replace(\'assertTrue(settings.canUseCloudLibrary)\',\'assertFalse(settings.canUseCloudLibrary)\')\nanchor=\'    @Test\\n    fun `normalizes provider ids when reading api keys`() {\'\nif \'fun `Premiumize uses its available API key setup`\' not in text:\n    assert text.count(anchor)==1\n    text=text.replace(anchor,\'\'\'    @Test\n    fun `Premiumize uses its available API key setup`() {\n        assertEquals(DebridProviderAuthMethod.ApiKey, DebridProviders.Premiumize.authMethod)\n        assertTrue(DebridProviders.isVisible(DebridProviders.PREMIUMIZE_ID))\n    }\n\n    @Test\n    fun `Real Debrid can be the only connected resolver`() {\n        val settings = DebridSettings(\n            enabled = true,\n            providerApiKeys = mapOf(DebridProviders.REAL_DEBRID_ID to "rd_key"),\n            preferredResolverProviderId = DebridProviders.REAL_DEBRID_ID,\n        )\n        assertEquals(DebridProviders.REAL_DEBRID_ID, settings.activeResolverProviderId)\n        assertEquals("rd_key", settings.activeResolverCredential?.apiKey)\n        assertTrue(settings.canResolvePlayableLinks)\n        assertFalse(settings.canUseCloudLibrary)\n        assertFalse(settings.copy(enabled = false).canResolvePlayableLinks)\n    }\n\n    @Test\n    fun `unknown provider credentials cannot activate an integration`() {\n        val settings = DebridSettings(enabled = true, providerApiKeys = mapOf("unknown" to "key"))\n        assertTrue(DebridProviders.configuredServices(settings).isEmpty())\n        assertFalse(settings.hasAnyApiKey)\n        assertFalse(settings.canResolvePlayableLinks)\n        assertFalse(settings.canUseCloudLibrary)\n    }\n\n\'\'\'+anchor,1)\npath.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\nprint(\'Prepared provider-setting regressions for visible Real-Debrid, Premiumize API-key entry and removed cloud-library capabilities; application implementation unchanged.\')\n', "omnia-provider-settings-test-review-overlay", "exec"))

exec(compile('"""Keep an un-cancellable UIKit icon request paired with its own callback."""\nif (ROOT/\'composeApp\').is_dir():\n    path=ROOT/\'composeApp/src/iosMain/kotlin/com/nuvio/app/features/settings/AppIconPlatform.ios.kt\'\n    text=path.read_text()\n    old=\'\'\'            pendingChange = continuation\n            continuation.invokeOnCancellation {\n                if (pendingChange === continuation) {\n                    pendingChange = null\n                }\n            }\n\'\'\'\n    new=\'\'\'            // UIKit\'s icon request continues after the calling coroutine is cancelled.\n            // Keep its slot until the native callback arrives; otherwise that callback\n            // could complete a newer request with the previous request\'s result.\n            pendingChange = continuation\n\'\'\'\n    if new not in text:\n        assert text.count(old)==1\n        text=text.replace(old,new,1)\n    path.write_text(text,encoding=\'utf-8\',newline=\'\\n\')\n    print(\'Prepared iOS icon-request cancellation fix; native callback keeps ownership until completion.\')\n', "omnia-ios-icon-callback-overlay", "exec"))

exec(compile('"""Preserve resolver coverage while testing the requested connected-service scope."""\nif (ROOT/\'composeApp\').is_dir():\n    path=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/debrid/DebridProviderTest.kt\'\n    text=path.read_text()\n    text=text.replace(\'assertTrue(DebridProviders.Torbox.supports(DebridProviderCapability.CloudLibrary))\',\'assertFalse(DebridProviders.Torbox.supports(DebridProviderCapability.CloudLibrary))\')\n    text=text.replace(\'fun `premiumize exposes oauth and cloud service capabilities`()\',\'fun `premiumize exposes API key resolver capabilities without cloud library`()\')\n    text=text.replace(\'assertTrue(DebridProviders.Premiumize.authMethod == DebridProviderAuthMethod.DeviceCode)\',\'assertTrue(DebridProviders.Premiumize.authMethod == DebridProviderAuthMethod.ApiKey)\')\n    text=text.replace(\'assertTrue(DebridProviders.Premiumize.supports(DebridProviderCapability.CloudLibrary))\',\'assertFalse(DebridProviders.Premiumize.supports(DebridProviderCapability.CloudLibrary))\')\n    text=text.replace(\'fun `real debrid stays hidden from local addon capability paths`()\',\'fun `real debrid is visible for client resolution without local torrent capabilities`()\')\n    text=text.replace(\'assertFalse(DebridProviders.RealDebrid.visibleInUi)\',\'assertTrue(DebridProviders.RealDebrid.visibleInUi)\')\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/library/LibraryRepositoryTest.kt\'\n    text=path.read_text().replace(\'library tabs include local Nuvio library before Trakt tabs\',\'library tabs include local Omnia library before Trakt tabs\').replace(\'assertEquals("Nuvio Library", tabs.first().title)\',\'assertEquals("Omnia Library", tabs.first().title)\')\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/membership/ThemeAccessTest.kt\'\n    text=path.read_text().replace(\'unavailableSupporterThemeFallsBackToWhite\',\'unavailableSupporterThemeFallsBackToOmniaCrimson\')\n    text=text.replace(\'\'\'            AppTheme.WHITE,\n            resolveAppTheme(AppTheme.JADE, CosmeticEntitlements.None),\'\'\',\'\'\'            AppTheme.CRIMSON,\n            resolveAppTheme(AppTheme.JADE, CosmeticEntitlements.None),\'\'\')\n    text=text.replace(\'assertEquals(AppTheme.WHITE, resolveAppTheme(null, CosmeticEntitlements.None))\',\'assertEquals(AppTheme.CRIMSON, resolveAppTheme(null, CosmeticEntitlements.None))\')\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    print(\'Provider capability regressions retain resolver/local-torrent checks and reflect removed cloud library plus Premiumize API-key UI.\')\n    path=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/servers/mediabrowser/MediaBrowserRequestTest.kt\'\n    text=path.read_text().replace(\'header.startsWith("MediaBrowser Client=\\\\"Nuvio\\\\"")\',\'header.startsWith("MediaBrowser Client=\\\\"Omnia\\\\"")\')\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/settings/AppIconOptionTest.kt\'\n    text=path.read_text().replace(\'import nuvio.composeapp.generated.resources.app_logo_wordmark_gold\',\'import nuvio.composeapp.generated.resources.omnia_wordmark\').replace(\'fun goldThemeUsesGoldWordmark()\', \'fun goldThemeUsesOmniaWordmark()\').replace(\'Res.drawable.app_logo_wordmark_gold\',\'Res.drawable.omnia_wordmark\')\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/settings/SettingsPagesTest.kt\'\n    text=path.read_text().replace(\'fun layoutKeepsItsChildPagesAndMobileNavigationControls()\', \'fun layoutKeepsVisualPagesAndMobileNavigationControls()\')\n    text=text.replace(\'            "Collections" to "collections",\\n\',\'\')\n    anchor=\'        compose.onNode(hasText("Navigation Bar") and hasClickAction()).performScrollTo().performClick()\'\n    if \'        compose.onNodeWithText("Collections").assertDoesNotExist()\\n\'+anchor not in text:\n        assert text.count(anchor)==1;text=text.replace(anchor,\'        compose.onNodeWithText("Collections").assertDoesNotExist()\\n\'+anchor,1)\n    text=text.replace(\'assertEquals("Services", entries.single { it.key == "tracking" }.category)\',\'assertEquals("Providers & tracking", entries.single { it.key == "tracking" }.category)\')\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/commonTest/kotlin/com/nuvio/app/features/watchprogress/WatchProgressIdentityTest.kt\'\n    text=path.read_text()\n    start=text.index(\'    fun `legacy payload derives episode progress key and preserves completed position`()\')\n    end=text.index(\'    @Test\',start)\n    block=text[start:end].replace(\'"lastPositionMs": 940,\',\'"lastPositionMs": 940000,\').replace(\'"durationMs": 1000,\',\'"durationMs": 1000000,\').replace(\'assertEquals(940L, decoded.single().lastPositionMs)\',\'assertEquals(940000L, decoded.single().lastPositionMs)\')\n    text=text[:start]+block+text[end:]\n    if \'fun `short placeholder payload cannot complete an episode`\' not in text:\n        anchor=\'    @Test\\n    fun `custom progress key round trips byte for byte`()\'\n        assert text.count(anchor)==1\n        text=text.replace(anchor,\'\'\'    @Test\n    fun `short placeholder payload cannot complete an episode`() {\n        val placeholder = entry().copy(lastPositionMs = 940L, durationMs = 1000L, isCompleted = false, progressPercent = null)\n        val decoded = WatchProgressCodec.decodeEntries(WatchProgressCodec.encodeEntries(listOf(placeholder))).single()\n        assertEquals(940L, decoded.lastPositionMs)\n        assertTrue(!decoded.isCompleted)\n    }\n\n\'\'\'+anchor,1)\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/androidFullHostTest/kotlin/com/nuvio/app/features/plugins/PluginSyncTest.kt\'\n    text=path.read_text()\n    old=\'\'\'    @Test\n    fun emptyRemoteRemovesCachedAddonsWithoutUploadingAndStaysEmptyAfterReload(): Unit = runBlocking {\n        AddonStorage.saveInstalledAddonUrls(1, listOf(manifestUrl))\n        AddonStorage.saveAddonEnabledStates(1, mapOf(manifestUrl to false))\n        AddonRepository.initialize()\n        assertEquals(1, AddonRepository.uiState.value.addons.size)\n        respond("[]")\n\n        AddonRepository.pullFromServer(1)\n\n        assertTrue(AddonRepository.uiState.value.addons.isEmpty())\n        assertTrue(AddonStorage.loadInstalledAddonUrls(1).isEmpty())\n        assertTrue(AddonStorage.loadAddonEnabledStates(1).isEmpty())\n        AddonRepository.clearLocalState()\n        AddonRepository.initialize()\n        respond("[]")\n        AddonRepository.pullFromServer(1)\n\n        assertTrue(AddonRepository.uiState.value.addons.isEmpty())\n        assertPullsOnly("addons", count = 2)\n    }\'\'\'\n    new=\'\'\'    @Test\n    fun signedOutAddonPullPreservesCachedDisabledAddonsWithoutRequestingAccountData(): Unit = runBlocking {\n        AddonStorage.saveInstalledAddonUrls(1, listOf(manifestUrl))\n        AddonStorage.saveAddonEnabledStates(1, mapOf(manifestUrl to false))\n        AddonRepository.initialize()\n\n        repeat(2) {\n            AddonRepository.pullFromServer(1)\n            assertEquals(listOf(manifestUrl), AddonRepository.uiState.value.addons.map { addon -> addon.manifestUrl })\n            assertEquals(listOf(manifestUrl), AddonStorage.loadInstalledAddonUrls(1))\n            assertEquals(mapOf(manifestUrl to false), AddonStorage.loadAddonEnabledStates(1))\n            assertEquals(com.nuvio.app.features.addons.OmniaAddonSyncStatus.SignIn, AddonRepository.syncStatus.value)\n            AddonRepository.clearLocalState()\n            AddonRepository.initialize()\n        }\n        assertNull(server.takeRequest(750, TimeUnit.MILLISECONDS))\n    }\'\'\'\n    if new not in text:\n        assert text.count(old)==1;text=text.replace(old,new,1)\n    path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    print(\'Prepared current Omnia labels/navigation and owner-required add-on sync regressions; no application implementation modified.\')\n', "omnia-provider-capabilities-test-review-overlay", "exec"))
HERO_IOS_SOURCE='package com.nuvio.app.features.details.components\n\nimport androidx.compose.runtime.Composable\nimport androidx.compose.runtime.DisposableEffect\nimport androidx.compose.runtime.LaunchedEffect\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.remember\nimport androidx.compose.runtime.rememberUpdatedState\nimport androidx.compose.runtime.setValue\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.draw.clipToBounds\nimport androidx.compose.ui.interop.UIKitViewController\nimport androidx.lifecycle.Lifecycle\nimport androidx.lifecycle.LifecycleEventObserver\nimport androidx.lifecycle.compose.LocalLifecycleOwner\nimport com.nuvio.app.core.ui.LocalScreenActive\nimport com.nuvio.app.features.player.NuvioPlayerBridgeFactory\nimport kotlinx.cinterop.ExperimentalForeignApi\nimport kotlinx.cinterop.useContents\nimport kotlinx.coroutines.delay\nimport kotlinx.coroutines.isActive\n\n@OptIn(ExperimentalForeignApi::class)\n@Composable\nactual fun HeroTrailerPlayerSurface(\n    sourceUrl: String,\n    sourceAudioUrl: String?,\n    playWhenReady: Boolean,\n    muted: Boolean,\n    modifier: Modifier,\n    onReady: () -> Unit,\n    onEnded: () -> Unit,\n    onError: () -> Unit,\n) {\n    val latestReady = rememberUpdatedState(onReady)\n    val latestEnded = rememberUpdatedState(onEnded)\n    val latestError = rememberUpdatedState(onError)\n    val owner = LocalLifecycleOwner.current\n    val screenActive = LocalScreenActive.current\n    var foreground by remember(owner) {\n        mutableStateOf(owner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED))\n    }\n    val bridge = remember(sourceUrl, sourceAudioUrl) {\n        NuvioPlayerBridgeFactory.create()?.apply { configureHeroPreview(muted) }\n    }\n    if (bridge == null) {\n        LaunchedEffect(sourceUrl, sourceAudioUrl) { latestError.value() }\n        return\n    }\n    val controller = remember(bridge) { bridge.createPlayerViewController() }\n\n    DisposableEffect(owner) {\n        val observer = LifecycleEventObserver { _, _ ->\n            foreground = owner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)\n        }\n        owner.lifecycle.addObserver(observer)\n        onDispose { owner.lifecycle.removeObserver(observer) }\n    }\n    DisposableEffect(bridge) {\n        onDispose {\n            bridge.pause()\n            bridge.destroy()\n        }\n    }\n    LaunchedEffect(bridge, muted) { bridge.setMuted(muted) }\n    LaunchedEffect(bridge, playWhenReady, foreground, screenActive) {\n        if (playWhenReady && foreground && screenActive) bridge.play() else bridge.pause()\n    }\n    LaunchedEffect(bridge) {\n        bridge.loadFileWithAudio(sourceUrl, sourceAudioUrl, null, null)\n        var ready = false\n        var loadingTicks = 0\n        while (isActive) {\n            val loading = bridge.getIsLoading()\n            if (bridge.getErrorMessage().isNotBlank()) {\n                bridge.pause()\n                latestError.value()\n                break\n            }\n            if (bridge.getIsEnded()) {\n                bridge.pause()\n                latestEnded.value()\n                break\n            }\n            if (!ready && !loading && (bridge.getIsPlaying() || bridge.getDurationMs() > 0L)) {\n                ready = true\n                latestReady.value()\n            }\n            if (!ready && ++loadingTicks >= 180) {\n                bridge.pause()\n                latestError.value()\n                break\n            }\n            delay(250L)\n        }\n    }\n    UIKitViewController(\n        factory = { controller },\n        modifier = modifier.clipToBounds(),\n        interactive = false,\n        onResize = { viewController, rect ->\n            viewController.view.setFrame(rect)\n            rect.useContents {\n                bridge.syncVideoSurfaceLayout(width = size.width, height = size.height)\n            }\n        },\n    )\n}\n'
exec(compile('"""An actual full-distribution iOS inline preview, separate from full-screen controls."""\nif (ROOT/\'composeApp\').is_dir():\n    def replace_ios(relative,old,new):\n        path=ROOT/relative;text=path.read_text()\n        if new not in text:\n            assert text.count(old)==1,(relative,old[:80])\n            text=text.replace(old,new,1)\n        path.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    path=ROOT/\'composeApp/src/iosFull/kotlin/com/nuvio/app/features/details/components/HeroTrailerPlayerSurface.ios.kt\'\n    path.write_text(HERO_IOS_SOURCE,encoding=\'utf8\',newline=\'\\n\')\n    replace_ios(\'composeApp/src/iosFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.ios.kt\',\'actual val heroTrailerPlaybackSupported: Boolean = false\',\'actual val heroTrailerPlaybackSupported: Boolean = true\')\n    replace_ios(\'composeApp/src/iosMain/kotlin/com/nuvio/app/features/player/PlayerBridge.kt\',\'    fun createPlayerViewController(): UIViewController\',\'    fun createPlayerViewController(): UIViewController\\n    fun configureHeroPreview(muted: Boolean)\')\n    swift=\'iosApp/iosApp/Player/MPVPlayerBridge.swift\'\n    replace_ios(swift,\'    func loadFile(url: String) { ensurePlayerViewController().loadFile(url) }\',\'    func configureHeroPreview(muted: Bool) { ensurePlayerViewController().configureHeroPreview(muted) }\\n\\n    func loadFile(url: String) { ensurePlayerViewController().loadFile(url) }\')\n    replace_ios(swift,\'    private static let defaultAudioOutput = "audiounit"\',\'\'\'    private static let defaultAudioOutput = "audiounit"\n    private var isHeroPreview = false\n    private var heroPreviewMuted = false\n    private var heroPreviewWantsToPlay = false\n\n    func configureHeroPreview(_ muted: Bool) {\n        isHeroPreview = true\n        heroPreviewMuted = muted\n        if mpv != nil { setFlag("mute", muted) }\n    }\'\'\')\n    replace_ios(swift,\'\'\'    override var canBecomeFirstResponder: Bool {\n        true\n    }\'\'\',\'\'\'    override var canBecomeFirstResponder: Bool {\n        !isHeroPreview\n    }\'\'\')\n    replace_ios(swift,\'\'\'    override var prefersHomeIndicatorAutoHidden: Bool {\n        true\n    }\'\'\',\'\'\'    override var prefersHomeIndicatorAutoHidden: Bool {\n        !isHeroPreview\n    }\'\'\')\n    replace_ios(swift,\'\'\'    override var preferredScreenEdgesDeferringSystemGestures: UIRectEdge {\n        [.bottom, .left, .right]\n    }\'\'\',\'\'\'    override var preferredScreenEdgesDeferringSystemGestures: UIRectEdge {\n        isHeroPreview ? [] : [.bottom, .left, .right]\n    }\'\'\')\n    replace_ios(swift,\'\'\'    override var prefersStatusBarHidden: Bool {\n        true\n    }\'\'\',\'\'\'    override var prefersStatusBarHidden: Bool {\n        !isHeroPreview\n    }\'\'\')\n    replace_ios(swift,\'\'\'        let pip = PlayerPictureInPictureController(owner: self, metalLayer: metalLayer)\n        pictureInPictureController = pip\n        view.layer.addSublayer(pip.displayLayer)\'\'\',\'\'\'        if !isHeroPreview {\n            let pip = PlayerPictureInPictureController(owner: self, metalLayer: metalLayer)\n            pictureInPictureController = pip\n            view.layer.addSublayer(pip.displayLayer)\n        }\'\'\')\n    replace_ios(swift,\'\'\'        SystemUI.shared.playerDidBecomeVisible(self)\n        refreshImmersiveSystemUI()\n        becomeFirstResponder()\n        UIApplication.shared.beginReceivingRemoteControlEvents()\n        publishCachedNowPlayingInfoIfNeeded()\'\'\',\'\'\'        if !isHeroPreview {\n            SystemUI.shared.playerDidBecomeVisible(self)\n            refreshImmersiveSystemUI()\n            becomeFirstResponder()\n            UIApplication.shared.beginReceivingRemoteControlEvents()\n            publishCachedNowPlayingInfoIfNeeded()\n        }\'\'\')\n    replace_ios(swift,\'\'\'        SystemUI.shared.playerDidBecomeHidden(self)\n        super.viewWillDisappear(animated)\'\'\',\'\'\'        if !isHeroPreview { SystemUI.shared.playerDidBecomeHidden(self) }\n        super.viewWillDisappear(animated)\'\'\')\n    replace_ios(swift,\'\'\'        if parent == nil {\n            SystemUI.shared.playerDidBecomeHidden(self)\n        }\'\'\',\'\'\'        if parent == nil && !isHeroPreview {\n            SystemUI.shared.playerDidBecomeHidden(self)\n        }\'\'\')\n    replace_ios(swift,\'\'\'        checkError(mpv_initialize(mpv))\n        applyAudioLanguagePreferences(preferredAudioLanguages)\'\'\',\'\'\'        if isHeroPreview {\n            checkError(mpv_set_option_string(mpv, "demuxer-max-bytes", "8388608"))\n            checkError(mpv_set_option_string(mpv, "demuxer-max-back-bytes", "0"))\n        }\n        checkError(mpv_initialize(mpv))\n        if isHeroPreview {\n            setFlag("mute", heroPreviewMuted)\n            setFlag("pause", !heroPreviewWantsToPlay)\n        }\n        applyAudioLanguagePreferences(preferredAudioLanguages)\'\'\')\n    replace_ios(swift,\'\'\'        restoreBackgroundVideo()\n        playPlayback()\'\'\',\'\'\'        restoreBackgroundVideo()\n        // Inline previews resume only when Compose\'s current screen/lifecycle asks.\n        if !isHeroPreview { playPlayback() }\'\'\')\n    replace_ios(swift,\'\'\'    func playPlayback() {\n        guard mpv != nil else { return }\'\'\',\'\'\'    func playPlayback() {\n        if isHeroPreview { heroPreviewWantsToPlay = true }\n        guard mpv != nil else { return }\'\'\')\n    replace_ios(swift,\'\'\'    func pausePlayback() {\n        guard mpv != nil else { return }\'\'\',\'\'\'    func pausePlayback() {\n        if isHeroPreview { heroPreviewWantsToPlay = false }\n        guard mpv != nil else { return }\'\'\')\n    replace_ios(swift,\'\'\'    func setMuted(_ muted: Bool) {\n        guard mpv != nil else { return }\'\'\',\'\'\'    func setMuted(_ muted: Bool) {\n        if isHeroPreview { heroPreviewMuted = muted }\n        guard mpv != nil else { return }\'\'\')\n    replace_ios(swift,\'\'\'        UIApplication.shared.endReceivingRemoteControlEvents()\n        resignFirstResponder()\'\'\',\'\'\'        if !isHeroPreview {\n            UIApplication.shared.endReceivingRemoteControlEvents()\n            resignFirstResponder()\n        }\'\'\')\n    replace_ios(swift,\'\'\'        nowPlayingController.invalidate()\n        clearPlaybackError()\'\'\',\'\'\'        if !isHeroPreview { nowPlayingController.invalidate() }\n        clearPlaybackError()\'\'\')\n    replace_ios(swift,\'\'\'    private func syncNowPlayingPlaybackState(isPlaying: Bool) {\n        pictureInPictureController?.updatePlaybackState()\'\'\',\'\'\'    private func syncNowPlayingPlaybackState(isPlaying: Bool) {\n        guard !isHeroPreview else { return }\n        pictureInPictureController?.updatePlaybackState()\'\'\')\n    replace_ios(swift,\'\'\'    private func publishNowPlayingForPlaybackSession() {\n        activateAudioSessionForPlayback()\'\'\',\'\'\'    private func publishNowPlayingForPlaybackSession() {\n        activateAudioSessionForPlayback()\n        guard !isHeroPreview else { return }\'\'\')\n    replace_ios(swift,\'\'\'    private func refreshImmersiveSystemUI() {\n        setNeedsUpdateOfHomeIndicatorAutoHidden()\'\'\',\'\'\'    private func refreshImmersiveSystemUI() {\n        guard !isHeroPreview else { return }\n        setNeedsUpdateOfHomeIndicatorAutoHidden()\'\'\')\n    audio=\'iosApp/iosApp/Player/PlayerAudioSessionController.swift\'\n    replace_ios(audio,\'\'\'    private var isActive = false\'\'\',\'\'\'    // Only audioQueue reads/writes this set. Closing a preview must not deactivate\n    // the shared audio session underneath a newly opened full-screen player.\n    private static var activeOwners = Set<UUID>()\n    private let audioOwner = UUID()\n    private var isActive = false\'\'\')\n    replace_ios(audio,\'\'\'        isActive = false\n        generation &+= 1\'\'\',\'\'\'        guard isActive else { return }\n        isActive = false\n        generation &+= 1\'\'\')\n    replace_ios(audio,\'\'\'        Self.audioQueue.async {\n            do {\n                try AVAudioSession.sharedInstance().setActive(false\'\'\',\'\'\'        let owner = audioOwner\n        Self.audioQueue.async {\n            Self.activeOwners.remove(owner)\n            guard Self.activeOwners.isEmpty else { return }\n            do {\n                try AVAudioSession.sharedInstance().setActive(false\'\'\')\n    replace_ios(audio,\'\'\'        Self.audioQueue.async { [weak self] in\n            let session = AVAudioSession.sharedInstance()\'\'\',\'\'\'        let owner = audioOwner\n        Self.audioQueue.async { [weak self] in\n            Self.activeOwners.insert(owner)\n            let session = AVAudioSession.sharedInstance()\'\'\')\n    print(\'Prepared a real full-iOS inline trailer surface with lifecycle/mute control, bounded preview buffering, no PiP/remote-control takeover and shared audio-session ownership.\')\n', "omnia-ios-hero-preview-overlay", "exec"))

exec(compile('if (ROOT/\'composeApp\').is_dir():\n    panel=ROOT/\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/addons/AddonHealthPanel.kt\'\n    text=panel.read_text(encoding=\'utf8\')\n    if \'import androidx.compose.material3.LocalContentColor\' not in text:\n        text=text.replace(\'import androidx.compose.material3.MaterialTheme\',\'import androidx.compose.material3.LocalContentColor\\nimport androidx.compose.material3.MaterialTheme\',1)\n    start=\'    Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {\'\n    replacement=\'    CompositionLocalProvider(LocalContentColor provides MaterialTheme.colorScheme.onSurface) {\\n\'+start\n    if replacement not in text:\n        assert text.count(start)==1\n        text=text.replace(start,replacement,1)\n        end=\'    }\\n}\\n}\\n\\n@Composable\\ninternal fun OmniaAddonDiagnostics()\'\n        assert text.count(end)==1\n        text=text.replace(end,\'    }\\n    }\\n}\\n}\\n\\n@Composable\\ninternal fun OmniaAddonDiagnostics()\',1)\n    panel.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    strings=ROOT/\'composeApp/src/commonMain/composeResources/values/strings.xml\'\n    text=strings.read_text(encoding=\'utf8\')\n    import re\n    text,n=re.subn(r\'(<string name="compose_settings_root_advanced_description">).*?(</string>)\',r\'\\1Provider diagnostics, startup and cache.\\2\',text,count=1)\n    assert n==1\n    strings.write_text(text,encoding=\'utf8\',newline=\'\\n\')\n    print(\'Prepared readable shared Android/iOS provider diagnostics; existing settings and actions are retained.\')\n', "omnia-mobile-diagnostics-contrast-overlay", "exec"))

exec(compile("# Security transport and shared mobile tools, reviewed as a single prepared candidate.\n# Each file is captured from the tested source tree; this preserves existing player/settings behavior.\nimport base64,gzip\n_omnia_security_files = {'composeApp/build.gradle.kts': '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', 'composeApp/src/androidFull/kotlin/com/nuvio/app/features/details/components/HeroTrailerPlayerSurface.android.kt': 'H4sIAAAAAAACCq0aXXPbuPFdvwJ3DzdkR2WSttOZai7xKbZ8yYwdeSwlufTFA5GghZoiWBD0R3P+712ABAmAIEW3pxdRwO5id7HfVIHjO3xLUMwOUV7dUxbhoohSgkXFSRklRGCalRFsFywnuShnMwqPXCCcJ5zRBLZyARvRqfx+FO72LcfFnsZldIkFp4/u9j0lD9EW8OC4L/Ds7j/Q5JaI6JzjA7nAT6wSXgoS9VfOqiKqga4wIMCZy+3ph5ur5fXq09bBe6xlKkmEc3rAgrIcVrj+Sc4zhsWy3Ah4nooqHgjJB4F5lQt6IKAo+RvvMnIU9IyWDegqTUksjiJc4CqP9ySZCM7JgRx2hE8G/FwkoI9kXCsaCS7uC86q44CHSkgZlcoV6XU6FWcqeHmMl4pGlyyhKR3RBsAkHD9EcUaLLXvPqjwpx4Bb29cPYJzj5IsMi5TxQ3TBYpz5XcpCkNZPAYqzIlrW+x43eowyCgbxFGdgIvppCszqHlx7vSsJv/cw3iFojhTbLfb6IfdgHUhC8V8lygEc51L++ijI4QjcVYafdhCsVo8xKaTLTYA/evgXmhC2of8hR+AqQbPoc14qk1sWdAicPLJCnRutHtk4Bx1oySoeg6+TFFeZUPrYqKVzHAvGnyZTuCT8lua3BgWNOhDdG/Srxui0is+w8HMwQEZwyBFA54IIMMQdezwjgkjEl+Jt8KHIyIvRthyY7tDumMhoLr0EEoKguUpjINps9kurQpznTNSRe12Ij3lgXO5iEWe4LMPZL0akBkVUOENplaMP4Gzbmof6ijcVT3FMghmCT30Xn3m2QBtIePnt3FheVgllxt5JvSnv4eue5NcEJ08L9J6xjOC83oM4RxJ3rQlUC6RDVr3ONIUgRH9+hz7nVOiNVZ5IMp4Nzhm3N0L0XW3eg8BxHYLQW2RGpCiuOIfI0IJllstraDsQ9JEgdJfiyhQeMH2pJrA0FDoU1uO4bAhL6WQYS217sKTCRrDktsbiqHYxqTZMpWZ2Ty0i+o7sJPazYVlNSdQinrwL8irLQvQ8azlKXD81uAqai5t3BqmvVX6OunwUcyIFajHkpzMGTd3abk8CgPbZBknqIHdN/l2BMj/AvRBeAjg5FOLpEhdBOAAPdVBekuMIVUm+gddXO3K6r/I7kmgJAUfwinTQ9R09t9okOmKbWuzEcDx43te+qV9J8NCL5EB5MMoHfXottTaZRO8rmiXd7YaW7LLI8RDu8+Gg7STRwFmEkJs9GRLpD01R8IOti4iWn8A21/x9hvO7IAw9aMo+LPYCL4z89PPYMKwKhz0BG+s1KbR1RpRydvjMaXe3oWNDfyh9raSxQwa2wt7qMyJZSY6oVzIxLm6fbm+FkwIkhPRCwGgb47teXa2W25vL9dnqZn1+3sO5Z1l1kPDSRlTeCtHrtGb5TdoDL+AMzIljeM+WW3K0x+U1gUjMSXJOeSlUJ2iG0aB13LAXUYMUw+GhQS7TRcM/GTscJWN2JMGbNDTChUVIgYDgnt6xM12Bue6IANTC7+6/7Sg3BYllzJItZZBUXC1e0iyjMvz97fVrw2gyvCMy6P647xLIhUn/xxo2rHOH21V2os+dRG56six95Dgg3tdVc1P0uM7uJLyTqMap6RtKHkfCWbHHINHrzmyaxNdVHKUgda3Bdv8CKdBC2+mF3nI44/ReXpM0Ay4rgmsi60VVAig7GYSW9pf0oC1wBv0RB70oNbFcZx1lAqd7nN+SRBUx7eICfcyFL1I+QJmDbNihgNrIu9kut6ub69Xy7Jss4r4PxhkVuy3RwxHoOgzYepIpdBTBqsiie2nsQTiI8TybvmoJu/p0tjqbIKx1c8eEda95srCqUvxDhVUxsynIj0Tr51FDbDtcbYT3emGB2j2fYnouKScoGqGjEr6Al34cD3wn+yO+5zqej7og4aocD0jd5PRmCL7jfTFuNnjzkrD35p9n/ScZt1gzTJE9knfKAtnnZo6IXAILmPVDg9rycd7SixTBaP3pBrzlejvsJ9JHPF1YLRD66aeuKI6sgIR+eOvxxzH/6kd4cTwtTEoRnsqi9SKL+wHXfJ5QDXk1u74aVqxxMoaWZODoSabW52YwOPhsruMEJ4nOjIHOnt1xduI3RnuApk0z0MbbobG8ribconSQHNRb4KgjFG2ma/ARvifpsaNXClYEw4dlBPduy23h3yLZic/cglV92fN3s7CyJxiGtqQPDrnZ2yluxomoeP6LM/ofs4TCGblYvy3GBrn+n316qh8P+q63Bxr2t4nX07Qr3z3amtDWHCXvzWnmcXZfYmlDFTIDBMbvXuYbUQ9HZbpx5qWGkiRgWQ9fTcBmHmsACu7OBB720G2gQCZnfzaVt9ebDEeb5eXVxerm46ft6vrL8uLmchN6Rw19TFrWbH2lecIe1vemqekR4xUrqczvc+MadQ8VhmgHZe2df7LRwdNSPtD8NlTTLpp7ikGl4O7lZeNKlnmb2yeLcVI7LNXfXERUfwcGgXCUgmtCzc1H0EvWlID8OIW+XoyMglKa46w3E9Lc9mOn5XnGu6muI9ZzbGBWP9pDKPNFmzugst6peSyvjHFGfnM7bRVX6/rGj/FtKsZz13+n7XjvO5Iv5JopuVu+jYx3AwMtHJy9Zca7bTVtOPoGPDDfgM+R+avvb1NLsn5CFHtaDtlNp6ZKTcqVluIW2dFRn3YLOnOddTQ56Xm1Qp2UmXo8hzMwXj0HUO+ERq9wZozIF+hUT8hDtEDG3xfa0a3xksUOIca/Iew5bzeSaFGAl7yUg3zAq/9gEbiwHKlmbVkWED+vZQiU6eXvKXqF/pH2YGtF1WNz+YKpHT2f6LpHoVAoPQ2FSz89hUSQQPB1O7Xah6+gjIRY6m7S8pzFlZpF9aYwgGGHC5WAOuXYQ9OpVu++AHCIRmMc2XCnGY3venBNvJM9qGV0hatQtwa0NQ+ln04mOsvPbD/VkCcQJQnmqvo1TcfMGwOobb6a2e7X9vqj9AxJrRnf/yOpr8B8iXxeGYfLdcm7f64xMB2R7Lcw8s9JYo9+foteo99/R936ntDbvVAbvcvzOKNL8E/GSkEfSfZVLn9QRGucV73DnCC7dcJDYF2ZMykxx0OKAzWbhKJVUW5+sCz5auzBzw/dtqmisirqosOlqgl2tAwy4YsE0BFL8j8E77yNk0lSHQoKV+xEgqk5vVMGS7iaJQCsGfZA1nagKcqLTmsTaJGNNefC1U5rF73DXdvQh7wyqLsRqRUbyjCwZw+jJtV3PZ5cx1P9gK6GXPRXPXRfhO5YAoY2klbwJp03VOeWXH9J56bm5MKRdq/l7zftPi6DFssT+aspztGb9CX8ebMD0OxM0T1Rm/Lz7L8Sr+ERfikAAA==', 'composeApp/src/androidFull/kotlin/com/nuvio/app/features/player/PlatformPlaybackDataSourceFactory.android.kt': 'H4sIAAAAAAACCo1UPW/bMBDd9Ss4yoDBpZuRZGjaIEPaBnE7dKSlk8NaIlny6MYI/N97+hZN2TEXUrrP9+6RRmQ7sQWW6Yorv5eaC2N4AQK9BcdNKQ5gk0RWRltkQuVWy5xnWiEo5Pf1/oYn5jdeQS7FJ54LFE57mwH/Qsd1c7zGGQrhS4xjznSJVsgSLP+tPfoN3L96tYN8DH8QGWp7IBjUrlWiZHrzBzJkz6XAQtuK9sOGmIhC2HvCaBVescxSOUib73plLfYV60hYDpYWxS9brtgarVTb0ZS3yF7grweHjyBysG7Fvglz07l2IXczMc5o5eC6IO8gZKOHuGKftS5BqMD3SavtCyX+KSugsMGJ3bJClA5GZ0LaULj2G5RYAjXyJB3enBmNQ6Ktcnzd7H3QHeWFyuChDk0XbfbFio3883AA9drT3BTgP213nXE24JbJgqVn8S8mGev1gWbS2YlRkdn/iyH1kQHRdlLrublNfSffWyw0N95q6xHRxA0EGc5qaBm5xVONfQalEqDhHLvRIBvjiD5SARfO6UwSCvbOJHJPOVHXp9c2iGv7tZ54umDHsMKEtGDWrsvdVh3H29cMCPiAN29aIY5ZQiWFHUXo5hAncf911xvh4LI8o9ett6Xdk7Kchz7WsUCXSzU6n38cuHQd2adyn7R3Wathxh97sFbmpNUrBBqTPam6PK/nAML0igWGy+I5JsfkP+vj/kPUBgAA', 'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/player/OmniaMediaDataSourceSecurityTest.kt': 'H4sIAAAAAAACCsVWbW/bNhD+7l8h6BM12ExaF13RwEVip0WLLWlhu0uBYR9o6SRzlkiVL069wv+9R71EkuW8FMMwAjZE8Xh87rmHd8pZuGEJeKHMqLBbLinLcxoDM1aBpnnKdqAGA57lUhmPiUhJHlEBhn5W/OD1N5pBxNmYRswwLa0KgV7i4yKHsDaVm7Ux+ZhmMtzcwkqD2oKiVzibg86l0PC45Q2sFsXszlQl9G8ruKEXGu0M/aW/sgRt+m+VFQK9zq244WbdXldyJVMIjeIhnTfPzs282HSfMRNCGma4FHQmRcyTweC88k+OOnr9OkyZ1sHgvLQnOtp4E+/P56/+CgbFkvcxE5xdOXILPgtqFxBaxc3OOfK+Dzwc58VzbIXHQmNZWuwYv8OJVLtLCfpamndS3TIVXTHBY7R+DywCpZfyg4ggB/wTZhaJ2ZqnkQJBgsq1Gx3uSUCtBu87xs8TLrzRm3vWw8gt3jlxo9xCtWHKkOAMLernjtmWpV5cgp98KoTo/leo2Gswt1JtuEhoqFCr8B6l0lBTRUw63tzIWP4xJv6FNWvE8E+RJd8z0vOnwBQozyAl/tDzZ1JuOJRL7t0kV3yL57i1L6OZ1UZmo99g11j4wbB3XHkHPqt0UkVsVUr8k6zinmZ55AfUyAUKQiTkwEOXjFgqkjOz9pDrlGvj4jjRkGSYMJq90A7ZibYrw00KdGsQUDt39XBcg/hqwQJp3zpMlwYzldGO+DH/5m4/OuhtdymJ9KTKSkV+Qzzp7zBqdwSGG5GmEhVH6hJBpxZFVygHoWB5IfijOVOIzsF25DkG2owFAV25XeQIVjdYUQ+WCqPF4xBtRKY7AxdKsR15+SIYng7x/81pf/fei7lgaYroHdIwlY4kb3+UEgXIKKrEwTRsA/NyfoQOl8Z1cefaiewKcljLb9jVGia0jOfapimpzqQJVJe48nvAxP7YzbtfAfVsJiMgz09fBpRFUeUfYQmDchvNmUgcuhVSqb1no/HJr35LPyifQ+38nG4KzfyUPjr3K5UhS4s7cSAV3PZJau5IJs+K6e8gEqzL4wdk5KCvbByDmjTSGQdnZSrefsU6q8l4WMurNEVdjYMDm4KXYQWnNDvM1VM05/AUEdZFpSO4gyOLDE0wQ/6wZKVRi19msYeyUwl7m7pKbeHfVzD3g4NWpAFThNleVLVppsA1GY6HzQG/L7CTGWQuu4SY2dToD2K5xnhYWlfxf9+C6rKoH2lEd3b3tqPawtX0xrqUnbwVZd1tie7/7me6oHZUt7Uvo5LrpnW1DZ7ewbY8AvlA63IDPx+LzdUXxqTE2iLQnf94AJV9hfDBFtkk5LEOd/N2+sdy+V8UqVZNaoUa3N2yJ7Sip5eBuu00gT9UC44yOuy3kd4dP3uw63RFdbQi7Ac/AK+zlGRnDAAA', 'composeApp/src/androidHostTest/kotlin/com/nuvio/app/features/player/OmniaPlaybackSecurityTest.kt': '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', 'composeApp/src/androidMain/kotlin/com/nuvio/app/core/network/OmniaHttpSecurity.kt': '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', 'composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlayerEngine.android.kt': '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', 'composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlayerPlaybackNetworking.kt': 'H4sIAAAAAAACCuVX31PbOBB+z1+hy5M9dUUpR5lJj3YChNKBAJPA3cPNDaPYm0SNLPlkmRBa/vdb2U78k1Du8c7MYMfaXe3u9+16FTF/wWZAfBVSmdxzRVkU0Skwk2iIaSTYCnSnw8NIaUOYDLTiAfWVNCANPbb3B1NbfqAhBJzt0YAZFqtE+0BP8HGcPv6MMExZIsyrdNRibkxErxZneGtqVuPzlQaKFmZSxYb7MR1jNHp1CWap9OJIAwt8nYSTrxgeGomM0lsMyUyNfr2+//WU69icyPgnxK9CyZn1dgx+orlZrXWyUPbyWI4FR+fWa9/YPbMWqF26HV0gAhJ8w5WsSCSGC4sSGtYWqBsewq3kBpG0IUkmiJp8Q0VynSJs/0+QCnkGuJyR7x2C10YcjcWG3OPTyeC0f3txc3c7Hozu+l8GlzfkMJW1V3eoHrkQbGefviPOBZfJw0fSz2Aju3sfyTV/AEEOXNKPIgF/wOScm539vQO694F0yZuNodSYc352M7zwiOALIF/AXyiXHM+1CmFn9/07mv6RoZpwAWTMpkzz3FS3kxqKNL9nBipuj29Gg/7w7mzQPxmMxuSQhCy6mjpFBLcx6Lf9GaatS4xqCddLZd1ONUF2jyhPY4Fbj5RRJJMVEexxlSfXXuVlepRwEYB23EoaaCBjp0wux60J+BkLLMoqMc7uvkfWiNPx4Pjq8mRc07AUf4X4EvkJr5CfKiHUcoRVqtGv2DE6gVaRcSy2SmnAurySBc1PGRfYmtpkWRCUCtZ5uaYbeRRgnEZZ9nqRVgZ3rwlPLFg5VE9NvgmlIsuF69dzokkjLPnlM+SoRk2+E3/OuCRvP1XE7GW90vB3AljIh5kYzX/XjNakj1OLh4RPicPjizywM+ydTi5BEy3oHF+4bimO8pVtt+RmPipR78OLVEqzS0DEsM1wU6XxphwLRUR9gGDtfnXLpxdxniaS+MgoAwVERQcJss/XGcYJOu6RIYt+GxuNTdUj2f0TJhPCyKxwyXG9jWYSw4WSs1KGeuRIKQHMpn/KMAuFcPbhu9Wil1v9jDIyEaIQwU94KtTqSotbbX65NboWKFiGTBgCkzGj6by7pQgySJtML/mOI4gkjXKksa8icOzGlarwioTgI0NC8cd14E4VEpStZcZ9GeVipjhlPlba6j8MeBErzYOtwZ7XTb4NGnkh4RVlPyPAYbOEqma9lvRUUK6D2GmQpzYNrqNxMhdcO5SJVa2xxGDyAXSUuXOtkXDacIhrDlbbhq2B6jqdp/ffmUjAKc8VLjnMkGvrlri/FU0lneb08Vyvemqn7hba+tn03iP5GO/9Twmdk6Vx6qCNjJWy5lVfbmkT1WS+mtTFRo3mhLQsTUaFm0mR0UJ7vgXMQioEM1dBU7s6YQ7RDA4dZZg2wTTXmJxBO8KITOMcU+s0IegZBKiV+0+NGiaGTQSkCHfK1ZfJ0gWsYiqVxImB4FiBJYm0q9SfR9LxkTy5uf0/y6t/4W7Nunv5w1SDI7FoZua9PK9eI49eNXVelq3WodIiXm+z20B1n6nbOiMoHoAulblEVDBhjmbLc1hZR5Zp43Lro6RFBVOMScpEKRoOawPkfXYgSiCTSg21yVnU0Bbl8ZFgcuG45MePTLH6ysqscRzZDCGEHE/vGo6zASTFs62bWrJ1fmqYtDHheS/d/bkea9mX0q6BTG0utrPwmvNuuQUu5yBJukzx+INjO/rvVDzv7r4/SI+2uxhkVyifCStuf/R6u12EI412I5+Ggy/T5voccezgnTe44uPyL9hTLc41HYOWCWBe/0ZarDcKWz6Nv6w/jXmhbXQaDbv9RP+mptGSjZbIKg5JFkIJvU3rKnKOR0ucB+jUnsiv9Lp2FrZw7mzFlBlrrbXRlTx9phnbnjr/APNJ3MuIEwAA', 'composeApp/src/androidPlaystore/kotlin/com/nuvio/app/features/player/PlatformPlaybackDataSourceFactory.android.kt': 'H4sIAAAAAAACCo1Ty27bMBC86yv2KAEGL70JcQ5NW+SQPhC3hx4paWWzlkiVXLoxAv97V2/JkpHwYFLe2cfMkJVMj3KPkJpSaH9SRsiqEjlK8hadqAp5RhsEqqyMJZA6s0ZlIjWaUJN4qPcXugq/iBIzJT+ITJJ0xtsUxSc+7prje8CYS1/QJCdQ3MhqWYBJ/mBK8KOQlBtb8n5OmMOI/SJTMvYMrwHwyr2G1DIdDJvveqXt1DF042+GSNv/ly1i2JFVej+GsnamZ/zr0dEjygyti+GrrO46aJdyv5LjKqMdvi/JO/xtPPkEHw5eHzHrKcbw0ZgCpZ5hn4zeP3Phn6pEThtAsIVcFg5HMDNtJNz5hBQVyIM8KUd3N6x3xLKVTuyavU+657pYVnSuU8OorR7FMOov5gbU68S+HYiqPrKt7eN71TP7hvTP2CPrIFqvHhm8cHQ08KYfmxlkqc48PrjNAw3nOYSFaAJd/Zr8tYpCOmdSxVPDKygSnuuRqU+HNkkY+7lWLIzgMlaPZuq4rlrbZ9Sp7zKj+YYyvmqtG6tMtJ/TW5BZI3hj5ES6vv+q/VtYPOM+FnYvcLPOe+xjke+iBpVDuP6WhHKdttHkvtVrMt7w/wWQX8QVcF7x+wmtVRlfxTdUXld60nWzgK9T4Kz1wLzAKMolaH8vwX8FF6tGvQUAAA==', 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/AdvancedSettingsPage.kt': 'H4sIAAAAAAACCsVX3W7aMBS+5ym8XiVSlweo1AtG22kSWiuotktk7JPgkdiR7YR1Fe++4/xAAoRASzdfVIl7znd+v5NDStmSRkCYSgKZ5UIFNE2DEKjNNJjAgLVCRmYwEEmqtCVUcq0E/x2gQqoMBKHKJKdWKBnE9M9LMMY/Y2HslKkUOrV0Jq1IIEgyS+cxTC218Bj2ikdgf9A468c1pwpqSCCZgx4prTIMFU7z29AcnOMb/Wl1UWt25DPVKhQxPjyVDxNAWGGVfulRXFHLFqgd4YsJRgrdkBn8dLdYn3upBVskIO2IsgWchVVgPFVv+/4slY2FdBmoEmSwzplki1qgNFAlyNmJQILGenJMjlGZZqgyAXOWfN13M8pzKhnwGYuB6hlbzVgzwouAzbiSF0Y02dwKG78Xte6uWUyNnVXN8xGYMw6GaZE6Hr8T3wBzKBepU41lLNU2S2s0paPgF9i5pkKaLTe3QFYjzqR6x9klLWhJYxJmkrQGVFCbmla2HbOQRt6A4BHm2XHa3pAvSmGB5XVxXWdwjAmseHwvnSBvCPrktcSwkJBX8phIQRFclhE9o5jxanyfrBuyxaM7tU/TUscrOorckqsh55+VJFzQSCpjBTNX1xtnUWCLuwVzp2MeUI4EMEHh4tA9322BPX+DUPp4kqctq7Xb7ap4k02h+gvvX7cQD4S6FdgNuvbtK86v1DshS62AVgKn40StvD2Rt4Z2kH87AdanwcpLWGmyvMMicpYtgaO17i4/rHm0KM2j5Kg0MlpQGbn07X0Mb24woskZDvitm/V/7dli8P3zji3Zq+1K6WWxBAzLsDY6nT1emLkTueCgj4jnOD+Nm5mN3mhvTd4hJU2KTyO21PyF7G5LOBjbG6AX0tiA36jgrrffaS6iYt+8KCvb3++T6ChC4lWxHSpIfd7uRbGX+AeB1wQwTx9jtd5dOiy/n/2xYEuU63beZfbTCal1p2cVDgqYYRx7e0MmoMiQHKr7b9w/aqfu4ltiNf6uOCZasKTaknu8d6djAS89HytG46HkDwrLOJU0NQuFkzFE2cWDVskUdI607TXiTm8GrnthjudoPTjvP+vzB/l6MPgLSoc0sbMOAAA=', 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/OmniaAdvancedTools.kt': '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', 'composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/SettingsSearch.kt': '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', 'composeApp/src/commonTest/kotlin/com/nuvio/app/features/settings/OmniaConnectionToolsTest.kt': 'H4sIAAAAAAACCq1UXW/aMBR951e4fqiSNU27bnuhgNYiqiFtawVMfZimyU0uxMLYmX1D6Sr++66TUAYD+rI8xInv1znn+joXyVRMgCVmFutiLk0s8jweg8DCgosdIEo9cY2GnOXG4j4/kaZGu3ggHj8h5gNwOf3CKmhqUEm9iBNjTUH5KKArdAJKCZRG9xYJ5P7jgD+Cw9gWekTrpltletNoJEo4x25nWoqu0RoSn3JkjHI+iD03GD25lXOBwMaFZraGGTgkGq7J+hoj9mDSpyYboiXerM04D+m9RayOiLivzSOekc01z85gIWa5grja9pkimOX49EXkQRiWAD6WYHz5uVAypZJgNeCVTrsChTKTVQ13R3QCX7ymXTPwD4WywirXnhUoHhR8lg5vx60KdCcINxyJZqHQtZMMkumWPI49+0TstFPmO2nT+5LJcUBrDDp19xKzgE9AgyXZfl6cv+dhuFaO/kMGysHfW+cR5/yZJxUfx5vffyy513H5gouogcXer0IoF1xENcTYyd8QXlbGkS0gWBmEUoRUYpx7Y8qWG14e+tqFemOxBr5qjC9eqbLc6kIi6OjN4Y4OlFC39tqaKei6FX331eAwM4/6ytWaQXqgJa8pvalRK8OZ6gzlRDOpGRp2L09vZOus3N6h1oYg2mg4oMg/uqWAQiqaKE2rdgH/pmGRl4ReYO0XifLOwfasNbbvBuCnD1KvMI1nL8kMnbo+urtqtl6G5D8I9eH8XcRXM5tKMdHGoUxILerSaxpV5I/WGh0f75SCilAqMh7tstbVD52g9VU2RJO7UQZdT2wgMAM7yoS+Bro3SaSrNc1SzL0SWcqqaL7Pt/jdELbyaLd2XqAd4rtP0zLhycklZtY8sp3hAXeE3zPdN6pvozLNSohl4w/5LQt6QAYAAA=='}\nfor _name,_encoded in _omnia_security_files.items():\n    _target=ROOT/_name\n    _target.parent.mkdir(parents=True,exist_ok=True)\n    _target.write_bytes(gzip.decompress(base64.b64decode(_encoded)))\nprint('Prepared strict TLS, provider-origin credential scope and tested settings tools.')\n", "omnia-security-tools-candidate-overlay", "exec"))

exec(compile("import re\n(ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=29\\nMARKETING_VERSION=0.4.21\\n',encoding='utf8',newline='\\n')\np=ROOT/'prepare_omnia_ios_tests.py';s=p.read_text()\ns,n=re.subn(r'Version 0\\.4\\.\\d+ \\(\\d+\\)','Version 0.4.21 (29)',s);assert n>=1\np.write_text(s,encoding='utf8',newline='\\n')\n", "omnia-security-release-version", "exec"))

exec(compile("import base64,gzip,sys,subprocess,re\nfrom pathlib import Path\n_omnia_device_files={'apply_native_signin.py': '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', 'native/mobile/OmniaAccountPortalLinks.kt': 'H4sIAAAAAAACCsVVwW7bMAy95yvYYgcHKHTZbVjXpVm7DWiXIlk67DQwMp0IkUVDltJmRf99lN2sSZc2zWk62ckjnx75SFeo5zgl0FwqFxeGFVaVKghD9FQrjGHW6ZiyYh8AXe7Z5LdKwBXXpAqOLsdg2CmLS45B9bxHN6WSXNgjqs82lm6PgCHf7IEujLWXePvD5CLmubASA3mD9q36TrfhlbDTGAI/f3EfXTAlib70jhNLO6GarSUdevUoCNNO+JTCNdq4G1jGkPibrINiJ9xLC8sJ+Z3AetcFolGXnJvCvJBMMJXFULAv1QVrtGNvvgjKPsZs+lOzp8ab6hMtjKYL4+Y9eR2S5DOB/XK/uI1ibwlxFG7Yz9WI/IJ8n11hptE3Jluj7Hxcb7QTozi0UEQHg9IZ7Gkt1gxXwoE2MdcZuYTN38EpsyV0XbjrgJyFxNUNF0yW8CKrQh3M4qlxsm6TxxSQHfxLrnCBxibqc/ZZS6QmsgnI5WNvu13wJPPv/t5l1jYDjuFJe5SO3qdhb5EeCrQ2ZZI06eorH8EdbDrw/Sh446YnHzIXre3CfZOhXQRZ+WAY4Vt5Z2OIs+6qUOnIMshm7M1vdqJtbQNJ+NqbGlWo6VQ6SeSOYD+OdB4HftU3iX14OgJ2fWv0XH662yjCcdMEGZc+Bj0TyfL/QzkVV+SkltmWDo2+fv42vvo1Hl5IbZSpz6VhspG78CIWyNYEqaJwL9dvrpwd9r2scwJsgw6PxOGWk/Bk/QS58qZEv1x14b8IHp71B9dnw5+vk7yO3i5anD3lABXWtYxufvI62Y9PScS6rINjaJ3aph+IEnizDjAOECaeb2Se1Ba2EWmWD5PwdVqm+84fv7DwvH0HAAA=', 'native/mobile/OmniaBrowserSignIn.kt': 'H4sIAAAAAAACCpVW227bRhB911eMhSCgAGVf+pbWcWO5aQs4cFDFzfOKHEoDL3eJ5a5sQRGQ3+gP9MP6JZ0hRUmUJUvmg8DLmTMzZy6rUqcPeoqQukLZOCendFmqHHWIHiulY5j1elSUzgfQNvOOsifF4NJVqHIXbaYDOauMXrgY1MiZWNhXGORkzGf99I0ydnTMrNABPWnzk7qLwZDF7DqG4OwZBl/xKRyF+WgDFchRy7OeGDwJvaFqDf0tzzE9zX2ro01nmJ0JT50xjPtYjQPncBI+xfC3NvE0sIhBgq5Z7/KTcI8FFhP0J4HVqQAiqc8uo5xeIGNMaXTInS/UrUu1uff0B6PM1qbbn6nzWPemusE5pXhL9uEjP/6FzEfB+cXr7Bqxe7/uNoLlFrLaQB4t3BWW9LV3jxX6MU3tnzZBK7DsPVw7Z1DbASx7wNecTSqhg8kCjkWnasResZPBhmDWJA+XsCeHSqP3aMMa6cGVyOMgvtqSwRK6xf5lHDzZ6dWHxEZjBrDqGH/SZE4QJLk2FW4NDTxqCkzJ8TWp6uoKDiiqvjW4jd0kVouNEVUHbfjX1+Tfv2/8XFyCxF7zSD0k8CR68x6a3Fj83WQugdtzpEM6E+NlK6cSCGsplpyNokrwvOfWmXVHNVk7v1Jz3iU5pfXeuhfTptJtUszGHo+hN1DKQRy3ucDbt23x+I184BcbEqqkFQ222QcfsU2yTpANft7I0Jam+d1fUcm9pVAb2+YT8v3Rzky1TdEkTLmma1Z6UqyHmH2389xZ3slgVxceZUiS0rs5ZeiHYPQEOUyyYKgK3FL9qXNTg30IDvq/N/dD6GdU8Yxmzeub9UOHWa7uKZB0vsm1nk0Otb1jbS+k+YbPsKfzem7j7MhQ+sAmyxdH3IeNBKxnl0cKIodT0h85XqU2IjxSmMGbWirWgpeDk6iEVoBfPBXaL9pab+st1+MMLST1XO2L9eKMvfuwDuKLx1LLKEGFqYxExWvuHdn/fvx7IJYxpo4Pco6m4+rIRK+ncuNr3FBDRhnz/xMgJ0vVTMFXvwA91fyJvUXuU/6L4JvlC1gwixwdUOqqeuS+UOcHhry/xL9MwgH1ZDT3Vs2+inXkO7jOhA6g/6lOodZvK1zjVwqcky842AzhzbJlkMeVjESd5aQ5XYYQpJQe+f+XlSmos39FqhLjxeEgl88aeW+Qdvu63i0tz7MNuBrCWQthq9t2PbNaUmh5IXpxvm3yTfFb2e4Y0KrJRZ/ieUNxRm5nLL9X5dcf1XZtsOfHuT/Kq96q9z/LxHUCkgsAAA==', 'native/mobile/OmniaDeviceLoginUrl.kt': 'H4sIAAAAAAACCmVRXW/TQBB8969YnSJqh+RMqqrQSFbVlgpFQkRq4QXEw+W8tY9e7sx9uKA0/521E0e0uQf7tLMzO7fTCPkoKgRp19zEVlkumoZL65CLGOokycdjWBr9F0KN0MSVVhJ8bV0gSkk8Z71HD8oECwJWzj55dBy+UneJrZIIxpruiy06KC16DuM8oX50Rmiwq18oAyzXRomPPeGzrZT55jRsEqAjrfEBWmpd3i0+Lb5AAawOofHzPLcdi8/OZ/ziPZ+dfuCnZ2fce60arix7Rb++ur/tyKOdTl4qT+8sp0JKG03ItTKPO85DNKB8byld0YLQlHO4D06ZKpvDtbUahSGpPcYJWadZ/7s1ZXqSn2Qcf0ehfbqbNQFVGdrpjfBIvOAiZodJ0qEImEba2w2tdJg0gcbZVpXohsplNtz2q+lO97I+iQIGBR6bBp2kWWTKYaOFxJRN2QQYyw5ERw6Vw/QOK/yTsh9X0+/vphc/N+dblvG1CLJGn3bKWQYbYAtDk1Q5hNoBDLZHaoNnKAowUWt4fob/a6yyttJEfV3fp3EM4FoozV54GPCXBkJ0htLtYr7s7BWjncm3oB7gyFhGywDUlAd7M2DF6KDc626TbfIPbTDSLCEDAAA=', 'native/mobile/OmniaDeviceLoginUrlTest.kt': 'H4sIAAAAAAACCq1UTY/TMBC951dYOVStAFeCcqko0C0FVVrRqlvE2etMkyGOHWynW7Tqf2fctCgK2WVF11KixPPx3vjNuBQyFykwaQquqx0aLsqSS2OBi8pnUYRFaaxnufEKNffgPN/Qq2tfOAfWz39WQrmH7Z/JCo+ZUbnvSNAPumxsBVEkFf2xZaFRfIIdSrg2KepvVgV67D5itD4ev7eVZrfW3FHsGiTgDtxSq1+bDG4yQpiZBKY6mSpl7hQ6D8nKmh0mYPuDU56wmtX1O2D51fRmzl6w+IOkhJPp1ez1m1GvPKWapMakCuKXXYy5tCA89GNxK19RFHnFJ//B4LkIJOhI1uQfDOqoQODs/3wMoCBtn4xfe1+K/lQ4XSnVwNoay/ohDUPNQlMst2fnnjZawsQB5fCBaOZ96cbDISEojnonFIZTjsNTh7ylMlirvd8tlIJUqKlNqwK0n+8llB6Nfs/uH6McSDXagx1a53MxQEOCGqRnIUEL0k9ChX8gD60JMxYp0SwDma/hB7m7a2NyOowc3IrGzNGMzffeipXwmesYrTDWnbqiO+522pbrxZfF16D6MG7r56rtFvdNBXlbo/FodKx0CIFZUya6pP6fTI38V+9ekpVbKJWQpE/db+fOGxPpwUmQQ/QbqxxWVs8FAAA='}\nfor _name,_encoded in _omnia_device_files.items():\n    _target=ROOT/'scripts/omnia-device-signin'/_name\n    _target.parent.mkdir(parents=True,exist_ok=True)\n    _target.write_bytes(gzip.decompress(base64.b64decode(_encoded)))\nsubprocess.run([sys.executable,str(ROOT/'scripts/omnia-device-signin/apply_native_signin.py'),'--root',str(ROOT),'--platform','mobile'],check=True)\n(ROOT/'iosApp/Configuration/Version.xcconfig').write_text('CURRENT_PROJECT_VERSION=32\\nMARKETING_VERSION=0.4.24\\n',encoding='utf8',newline='\\n')\n_p=ROOT/'prepare_omnia_ios_tests.py';_s=_p.read_text();_s,_n=re.subn(r'Version 0\\.4\\.\\d+ \\(\\d+\\)','Version 0.4.24 (30)',_s);assert _n>=1;_p.write_text(_s,encoding='utf8',newline='\\n')\n","omnia-native-device-signin-overlay","exec"))

exec(compile('\nfrom pathlib import Path\nimport base64,gzip\ndef layout_replace(path,old,new):\n p=Path(path);s=p.read_text(encoding=\'utf-8\')\n if new in s:return\n if s.count(old)!=1:raise ValueError(\'Login layout source anchor changed: \'+str(p))\n p.write_text(s.replace(old,new,1),encoding=\'utf-8\')\nif \'mobile\'==\'tv\':\n screen=\'app/src/main/java/com/nuvio/tv/ui/screens/account/AuthQrSignInScreen.kt\'\n layout_replace(screen,\'if (BuildConfig.FEATURE_CUSTOM_SERVER_CONNECTIONS_ENABLED) {\',\'if (BuildConfig.FEATURE_CUSTOM_SERVER_CONNECTIONS_ENABLED && !viewModel.hasOmniaAccountPortal) {\')\n layout_replace(screen,\'                useEmailLogin = useEmailLogin\\n\',\'                useEmailLogin = useEmailLogin,\\n                isOmniaAccount = viewModel.hasOmniaAccountPortal\\n\')\n layout_replace(screen,\'    useEmailLogin: Boolean\\n) {\',\'    useEmailLogin: Boolean,\\n    isOmniaAccount: Boolean\\n) {\')\n layout_replace(screen,\'                    stringResource(R.string.auth_qr_connected)\\n                } else {\',\'                    stringResource(R.string.auth_qr_connected)\\n                } else if (isOmniaAccount) {\\n                    "Sign in to Omnia to bring your profiles, library and watch history together."\\n                } else {\')\n # This was infrastructure copy, not a consent or license notice. QR/custom flows retain their existing notice.\n layout_replace(screen,\'        AuthTermsAcknowledgement()\\n        uiState.error?\', \'        // Account actions follow the sign-in form.\\n        uiState.error?\')\n target=\'app/src/main/java/com/nuvio/tv/ui/screens/account/OmniaTvAccountPortalLink.kt\'\nelse:\n screen=\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/auth/AuthScreen.kt\'\n layout_replace(screen,\'if (AppFeaturePolicy.customServerConnectionsEnabled) {\\n            ServerConnectionMenu(\', \'if (AppFeaturePolicy.customServerConnectionsEnabled && !OmniaAccountPortal.availableFor(serverConnectionState.activeServer.backendUrl)) {\\n            ServerConnectionMenu(\')\n target=\'composeApp/src/commonMain/kotlin/com/nuvio/app/features/auth/OmniaAccountPortalLinks.kt\'\nPath(target).write_bytes(gzip.decompress(base64.b64decode(\'H4sIAAAAAAACCtVVTW/TQBC951csFQdbilYqcECIUlKrhUotqRJSxAlt7LGzynrHGu8mNVX+O2M7aZOSJs0FiT35483HvrfztlDxVGUgYsyl9TONUhWFTEE5T1BK5d2k09F5geSEsgmhTu4kgwssQabobaKcRiuNqtA72SNSNoMcrDsgKkLjc3tAwADnB6AnoLOJu3y+gNfSW+1kUuyCOLhzsnSVAfmdH3tGZ4f0nGpjrtXdD50wpc+F5coBaWXeNiVeCDvzzuHzrZC3TufALNfvamxgLzRGYyB2vXLouNJeeAbuVhm/H5h7V9dvsvbTvXDig5SPgfYCy30NsHzXmOhU70jGmMIolyLl8gpjZUakvzLKPMZsTkmMBNKCmyNN5RBoBhShTXXmqVF+AJxXO6Sq0/m8zr5l9awyIvVW9HOrVS+O+by4G66hzJW20zIAW2OTD+IM0YCyobjvCF4zjiubWmJciZ1VpYqdnj1VMwibPDoVwau/i0s1U9rUpS+QgraQHLNJgE1GZMJQELA12IdeJi1D4kQ84UzGnqj2gRZJIlXG1Jk4Td36SlxxLzaPxcehI22z00+B9caEYtFkaD0iyJcqcr2VoBuTFYQrourFPhFMkPRvtLy3NXPi8LU3WRYqhuSsCo7fsAmEXXFYmXo9DuLWHueNBwXHafhgR0GuLUPevW9LLgXnL8unrkAbGR1P+dP9BnsnjXp8+CPl4glzxf+XOkgswLIIwRZph5dfvo1ufo0GV0yq1OUFK80uH4qdWAGmBFFLIRa86WajwVFEfEWAUG3QUZdHw2C94x7fGDXkhnSuqHoJlV3hVn7KoAdvlRHUg7I6AP8R0YPzqH97Pvj5MqrX0dvJ5lHM0IlClSV7TXL6r+h+fKppWCfm1Yloh7NtsM9ciNfrAGZciTHhnC1Ebul3CDHyBUlV60aLzqLzB35bHmaLCAAA\')))\n',"omnia-login-layout","exec"))

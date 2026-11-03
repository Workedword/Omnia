package com.nuvio.app.core.sync

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlin.test.assertFailsWith
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive

class OmniaSharedPreferencesPolicyTest {
    @Test fun publicCatalogIdentifiersAreShareable() {
        assertTrue(isShareableCatalogIdentity("org.omnia.india", 512))
        assertTrue(isShareableCatalogIdentity("movie:popular/hi", 1024))
    }
    @Test fun configuredEndpointUrlsStayOutOfPreferences() {
        assertFalse(isShareableCatalogIdentity("https://synthetic.example/u/private/manifest.json", 1024))
        assertFalse(isShareableCatalogIdentity("addon?token=synthetic", 512))
        assertFalse(isShareableCatalogIdentity("addon#synthetic", 512))
    }
    @Test fun invalidOrOversizedIdentitiesAreNotShared() {
        assertFalse(isShareableCatalogIdentity(" ", 512))
        assertFalse(isShareableCatalogIdentity("ab", 1))
        assertFalse(isShareableCatalogIdentity("a\nb", 512))
        assertFalse(isShareableCatalogIdentity("a\\b", 512))
    }
    private fun row(id: String, enabled: Boolean = true, title: String = "", order: Int = 0) = JsonObject(mapOf(
        "addon_id" to JsonPrimitive("synthetic-addon"), "type" to JsonPrimitive("movie"), "catalog_id" to JsonPrimitive(id),
        "enabled" to JsonPrimitive(enabled), "custom_title" to JsonPrimitive(title), "order" to JsonPrimitive(order),
        "is_collection" to JsonPrimitive(false), "collection_id" to JsonPrimitive(""),
    ))
    private fun home(vararg rows: JsonObject) = JsonObject(mapOf("homeCatalogs" to JsonArray(rows.toList())))
    private fun mergeHome(base: JsonObject, local: JsonObject, remote: JsonObject) = mergeSharedPreferences(base, local, remote, setOf("homeCatalogs"))["homeCatalogs"] as JsonArray
    private val keys = setOf("heroEnabled", "continueWatchingVisible")
    private fun prefs(hero: Boolean, watching: Boolean) = JsonObject(mapOf("heroEnabled" to JsonPrimitive(hero), "continueWatchingVisible" to JsonPrimitive(watching)))
    private val scope = SharedPreferencesScope("isolated-synthetic-owner", 1)

    @Test fun disabledDeviceRejectsAnInflightResponse() {
        assertFalse(canApplySharedPreferences(SharedPreferencesRequest(scope, 2), scope, 2, false))
    }
    @Test fun disablingAndReenablingInvalidatesOlderRequests() {
        assertFalse(canApplySharedPreferences(SharedPreferencesRequest(scope, 2), scope, 4, true))
    }
    @Test fun accountSwitchRejectsPreviousAccountsResponse() {
        assertFalse(canApplySharedPreferences(SharedPreferencesRequest(scope, 2), SharedPreferencesScope("another-owner", 1), 2, true))
    }
    @Test fun profileSwitchRejectsPreviousProfilesResponse() {
        assertFalse(canApplySharedPreferences(SharedPreferencesRequest(scope, 2), scope.copy(profileId = 2), 2, true))
    }
    @Test fun signOutRejectsPendingResponse() {
        assertFalse(canApplySharedPreferences(SharedPreferencesRequest(scope, 2), null, 2, true))
    }
    @Test fun currentEnabledScopeAcceptsItsResponse() {
        assertTrue(canApplySharedPreferences(SharedPreferencesRequest(scope, 2), scope, 2, true))
    }
    @Test fun unrelatedConcurrentEditsSurvive() {
        assertEquals(prefs(false, false), mergeSharedPreferences(prefs(true, true), prefs(false, true), prefs(true, false), keys))
    }
    @Test fun untouchedLocalValuesDoNotRevertRemoteChanges() {
        assertEquals(prefs(false, false), mergeSharedPreferences(prefs(true, true), prefs(true, true), prefs(false, false), keys))
    }
    @Test fun deliberateLocalChangeWinsTheSameField() {
        assertEquals(prefs(false, false), mergeSharedPreferences(prefs(true, true), prefs(false, true), prefs(true, false), keys))
    }
    @Test fun unsupportedRemoteFieldsAreRetained() {
        val remote = JsonObject(prefs(true, true) + ("subtitleLanguage" to JsonPrimitive("hi")))
        assertEquals("hi", (mergeSharedPreferences(prefs(true, true), prefs(false, true), remote, keys)["subtitleLanguage"] as JsonPrimitive).content)
    }
    @Test fun missingBaselineNeverUploadsDefaultsAsChanges() {
        assertFailsWith<IllegalArgumentException> { mergeSharedPreferences(null, prefs(true, true), prefs(false, false), keys) }
    }
    @Test fun unsupportedLocalFieldsAreRejected() {
        val local = JsonObject(mapOf("decoder" to JsonPrimitive("hardware")))
        assertFailsWith<IllegalArgumentException> { mergeSharedPreferences(JsonObject(emptyMap()), local, JsonObject(emptyMap()), keys) }
    }
    @Test fun optingInCanExplicitlyChooseSavedSettings() {
        assertEquals(prefs(false, false), initialSharedPreferences(SharedPreferencesInitialChoice.UseSavedSettings, prefs(true, true), prefs(false, false), keys))
    }
    @Test fun choosingThisDevicePreservesFieldsItCannotRepresent() {
        val remote = JsonObject(prefs(false, false) + ("subtitleLanguage" to JsonPrimitive("hi")))
        val merged = initialSharedPreferences(SharedPreferencesInitialChoice.UseThisDevice, prefs(true, true), remote, keys)
        assertEquals(JsonPrimitive(true), merged["heroEnabled"])
        assertEquals(JsonPrimitive("hi"), merged["subtitleLanguage"])
    }
    @Test fun remoteOmissionsDoNotClearLocalDefaults() {
        assertEquals(emptyMap(), applicableSharedPreferences(JsonObject(emptyMap()), keys))
    }
    @Test fun hardwareAndOptInStateCannotBeSynced() {
        assertFalse("decoder" in sharedPreferenceKeys)
        assertFalse("bufferSize" in sharedPreferenceKeys)
        assertFalse("enabled" in sharedPreferenceKeys)
        assertFalse("realDebridApiKey" in sharedPreferenceKeys)
    }
    @Test fun blankOwnerAndInvalidProfilesAreRejected() {
        assertFailsWith<IllegalArgumentException> { SharedPreferencesScope("", 1) }
        assertFailsWith<IllegalArgumentException> { SharedPreferencesScope("owner", 0) }
        assertFailsWith<IllegalArgumentException> { SharedPreferencesScope("owner", 7) }
    }
    @Test fun negativeRevisionIsRejected() {
        assertFailsWith<IllegalArgumentException> { SharedPreferencesSnapshot(-1, JsonObject(emptyMap())) }
    }
    @Test fun concurrentChangesToDifferentCatalogsSurvive() {
        val result=mergeHome(home(row("a"),row("b",order=1)),home(row("a",enabled=false),row("b",order=1)),home(row("a"),row("b",title="Remote title",order=1)))
        assertEquals(JsonPrimitive(false),(result[0] as JsonObject)["enabled"])
        assertEquals(JsonPrimitive("Remote title"),(result[1] as JsonObject)["custom_title"])
    }
    @Test fun differentFieldsOnTheSameCatalogAreMerged() {
        val result=mergeHome(home(row("a")),home(row("a",enabled=false)),home(row("a",title="Remote title")))
        assertEquals(JsonPrimitive(false),(result[0] as JsonObject)["enabled"])
        assertEquals(JsonPrimitive("Remote title"),(result[0] as JsonObject)["custom_title"])
    }
    @Test fun absentLocalCatalogDoesNotDeleteARemoteRow() {
        assertEquals(JsonArray(listOf(row("a"))),mergeHome(home(row("a")),home(),home(row("a"))))
    }
    @Test fun newRemoteCatalogIsPreservedWhileEditingAnother() {
        val result=mergeHome(home(row("a")),home(row("a",enabled=false)),home(row("a"),row("new",order=1)))
        assertEquals(2,result.size)
        assertEquals(JsonPrimitive("new"),(result[1] as JsonObject)["catalog_id"])
    }
    @Test fun newConflictingCatalogDoesNotTreatDefaultsAsIntentionalEdits() {
        assertFailsWith<SharedPreferencesChoiceRequiredException> { mergeHome(home(),home(row("a")),home(row("a",enabled=false))) }
    }
    @Test fun duplicateCatalogIdentitiesAreRejected() {
        assertFailsWith<IllegalArgumentException> { mergeHome(home(),home(row("a"),row("a")),home()) }
    }
    @Test fun identityDoesNotConfuseColonsInsideIdentifierComponents() {
        val a=JsonObject(row("c") + ("addon_id" to JsonPrimitive("a:b")) + ("type" to JsonPrimitive("movie")))
        val b=JsonObject(row("movie:c") + ("addon_id" to JsonPrimitive("a")) + ("type" to JsonPrimitive("b")))
        assertEquals(2,mergeHome(home(),home(a,b),home()).size)
    }
    @Test fun partialExportsCannotErasePreferencesTheyFailedToRead() {
        assertFailsWith<IllegalArgumentException> { mergeSharedPreferences(prefs(true,true),JsonObject(mapOf("heroEnabled" to JsonPrimitive(false))),prefs(true,false),keys) }
    }
    @Test fun omittedCatalogDefaultsDoNotBecomeIntentionalLocalChanges() {
        val sparse=JsonObject(row("a").filterKeys { it !in setOf("enabled","custom_title","is_collection","collection_id") })
        val result=mergeHome(home(sparse),home(row("a")),home(row("a",enabled=false,title="Remote title")))
        assertEquals(JsonPrimitive(false),(result[0] as JsonObject)["enabled"])
        assertEquals(JsonPrimitive("Remote title"),(result[0] as JsonObject)["custom_title"])
    }
}

package com.nuvio.tv.core.sync

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

class OmniaPreferencesSyncRecordStoreTest {
    private val values = mutableMapOf<String, String>()
    private val store = OmniaPreferencesSyncRecordStore(values::get) { key, value -> values[key] = value }
    private val scope = SharedPreferencesScope("synthetic-owner", 1)
    @Test fun profileInstanceRoundTripsWithTheBaseline() {
        val record=SharedPreferencesLocalRecord(true,SharedPreferencesSnapshot(3,JsonObject(emptyMap()),"synthetic-profile-instance"))
        store.save(scope,record);assertEquals(record,store.load(scope))
    }
    @Test fun absentRecordDefaultsToOff() { assertEquals(SharedPreferencesLocalRecord(), store.load(scope)) }
    @Test fun malformedRecordDefaultsToOff() {
        values["omnia.settings.sync.v1.synthetic-owner.1"] = "{invalid"
        assertFalse(store.load(scope).enabled)
    }
    @Test fun unknownRecordVersionDefaultsToOff() {
        values["omnia.settings.sync.v1.synthetic-owner.1"] = "{\"version\":99,\"enabled\":true}"
        assertFalse(store.load(scope).enabled)
    }
    @Test fun optInAndBaselineRoundTripExactly() {
        val record = SharedPreferencesLocalRecord(true, SharedPreferencesSnapshot(7, JsonObject(mapOf("heroEnabled" to JsonPrimitive(false)))))
        store.save(scope, record);assertEquals(record, store.load(scope))
    }
    @Test fun otherAccountsAndProfilesDoNotShareOptIn() {
        store.save(scope, SharedPreferencesLocalRecord(true, SharedPreferencesSnapshot(0, JsonObject(emptyMap()))))
        assertFalse(store.load(scope.copy(owner = "other-owner")).enabled)
        assertFalse(store.load(scope.copy(profileId = 2)).enabled)
    }
    @Test fun disablingRetainsTheBaselineWithoutResettingPreferences() {
        val baseline = SharedPreferencesSnapshot(3, JsonObject(mapOf("heroEnabled" to JsonPrimitive(false))))
        store.save(scope, SharedPreferencesLocalRecord(false, baseline))
        assertEquals(SharedPreferencesLocalRecord(false, baseline), store.load(scope))
    }
}

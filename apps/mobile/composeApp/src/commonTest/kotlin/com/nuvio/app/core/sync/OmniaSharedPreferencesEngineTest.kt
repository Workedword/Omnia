package com.nuvio.app.core.sync

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

class OmniaSharedPreferencesEngineTest {
    private fun prefs(hero: Boolean, watching: Boolean) = JsonObject(mapOf("heroEnabled" to JsonPrimitive(hero), "continueWatchingVisible" to JsonPrimitive(watching)))
    private inner class Fixture {
        var active: SharedPreferencesScope? = SharedPreferencesScope("synthetic-owner", 1)
        var local = prefs(true, true)
        var remote = SharedPreferencesSnapshot(0, JsonObject(emptyMap()))
        var pulls = 0
        var pushes = 0
        var applies = 0
        var afterPull: suspend () -> Unit = {}
        var afterPush: suspend () -> Unit = {}
        var conflicts = 0
        val records = mutableMapOf<SharedPreferencesScope, SharedPreferencesLocalRecord>()
        val store = object : SharedPreferencesLocalStore {
            override fun load(scope: SharedPreferencesScope) = records[scope] ?: SharedPreferencesLocalRecord()
            override fun save(scope: SharedPreferencesScope, record: SharedPreferencesLocalRecord) { records[scope] = record }
        }
        val device = object : SharedPreferencesDevice {
            override val supportedKeys = setOf("heroEnabled", "continueWatchingVisible")
            override fun currentScope() = active
            override suspend fun export(scope: SharedPreferencesScope) = local
            override suspend fun apply(scope: SharedPreferencesScope, preferences: JsonObject, stillCurrent: () -> Boolean) {
                if (stillCurrent()) { local = JsonObject(local + preferences); applies++ }
            }
        }
        val transport = object : SharedPreferencesTransport {
            override suspend fun pull(scope: SharedPreferencesScope): SharedPreferencesSnapshot { pulls++;afterPull();return remote }
            override suspend fun push(scope: SharedPreferencesScope, expectedRevision: Long, preferences: JsonObject, expectedProfileInstance: String?): SharedPreferencesPushResult {
                pushes++;afterPush()
                if (conflicts > 0) { conflicts--;remote = remote.copy(revision = remote.revision + 1);return SharedPreferencesPushResult(true, remote) }
                assertEquals(remote.revision, expectedRevision)
                assertEquals(remote.profileInstance, expectedProfileInstance)
                remote = remote.copy(revision = remote.revision + 1, preferences = preferences)
                return SharedPreferencesPushResult(false, remote)
            }
        }
        val engine = OmniaSharedPreferencesEngine(device, store, transport)
    }

    @Test fun reusedProfileSlotDoesNotInheritAutomaticSync() = runTest {
        val f=Fixture();f.remote=f.remote.copy(profileInstance="original-profile");f.engine.enable()
        val before=f.applies;val pushes=f.pushes
        f.remote=SharedPreferencesSnapshot(0,JsonObject(emptyMap()),"replacement-profile")
        assertEquals(SharedPreferencesSyncStatus.ChooseInitialSettings,f.engine.synchronize())
        assertFalse(f.store.load(f.active!!).enabled);assertEquals(before,f.applies);assertEquals(pushes,f.pushes)
        assertEquals(prefs(true,true),f.local)
    }
    @Test fun profileReplacementDuringConflictRequiresNewConsent() = runTest {
        val f=Fixture();f.remote=f.remote.copy(profileInstance="original-profile");f.engine.enable();f.local=prefs(false,true)
        val before=f.applies;f.conflicts=1;f.afterPush={f.remote=f.remote.copy(profileInstance="replacement-profile")}
        assertEquals(SharedPreferencesSyncStatus.ChooseInitialSettings,f.engine.synchronize())
        assertFalse(f.store.load(f.active!!).enabled);assertEquals(before,f.applies)
    }
    @Test fun profileReplacementDuringFirstEnableNeverEnablesNewProfile() = runTest {
        val f=Fixture();f.remote=f.remote.copy(profileInstance="original-profile");f.conflicts=1
        f.afterPush={f.remote=f.remote.copy(profileInstance="replacement-profile")}
        assertEquals(SharedPreferencesSyncStatus.ChooseInitialSettings,f.engine.enable())
        assertFalse(f.store.load(f.active!!).enabled);assertEquals(0,f.applies)
    }
    @Test fun defaultOffPerformsNoNetworkCalls() = runTest {
        val f=Fixture();assertEquals(SharedPreferencesSyncStatus.Off,f.engine.synchronize())
        assertEquals(0,f.pulls);assertEquals(0,f.pushes);assertEquals(0,f.applies)
    }
    @Test fun savedSettingsRequireAnExplicitInitialChoice() = runTest {
        val f=Fixture();f.remote=SharedPreferencesSnapshot(1,prefs(false,false))
        assertEquals(SharedPreferencesSyncStatus.ChooseInitialSettings,f.engine.enable())
        assertFalse(f.store.load(f.active!!).enabled);assertEquals(prefs(true,true),f.local);assertEquals(0,f.pushes)
    }
    @Test fun firstEnableCanChooseSavedSettings() = runTest {
        val f=Fixture();f.remote=SharedPreferencesSnapshot(1,prefs(false,false))
        assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.enable(SharedPreferencesInitialChoice.UseSavedSettings))
        assertEquals(prefs(false,false),f.local);assertTrue(f.store.load(f.active!!).enabled);assertEquals(0,f.pushes)
    }
    @Test fun emptyAccountCanUseTheCurrentDevice() = runTest {
        val f=Fixture();assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.enable())
        assertEquals(prefs(true,true),f.remote.preferences);assertEquals(1,f.pushes)
    }
    @Test fun defaultsOmittedByAnotherPlatformDoNotBecomeLocalEdits() = runTest {
        val f=Fixture();f.remote=SharedPreferencesSnapshot(1,JsonObject(mapOf("heroEnabled" to JsonPrimitive(false))))
        assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.enable(SharedPreferencesInitialChoice.UseSavedSettings))
        assertEquals(prefs(false,true),f.local)
        f.remote=SharedPreferencesSnapshot(2,prefs(false,false))
        assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.synchronize())
        assertEquals(prefs(false,false),f.local);assertEquals(0,f.pushes)
    }
    @Test fun disablePreservesCurrentValuesAndStopsBothDirections() = runTest {
        val f=Fixture();f.engine.enable();f.engine.disable();f.local=prefs(false,true);f.remote=SharedPreferencesSnapshot(2,prefs(true,false))
        val before=listOf(f.pulls,f.pushes,f.applies)
        assertEquals(SharedPreferencesSyncStatus.Off,f.engine.synchronize());assertEquals(before,listOf(f.pulls,f.pushes,f.applies));assertEquals(prefs(false,true),f.local)
    }
    @Test fun disableDuringInitialPullCannotBeUndoneByItsResponse() = runTest {
        val f=Fixture();f.afterPull={f.engine.disable()}
        assertEquals(SharedPreferencesSyncStatus.Off,f.engine.enable())
        assertFalse(f.store.load(f.active!!).enabled);assertEquals(0,f.pushes);assertEquals(0,f.applies)
    }
    @Test fun disableDuringPushPreventsApplyingTheResponse() = runTest {
        val f=Fixture();f.engine.enable();f.local=prefs(false,true);val before=f.applies
        f.afterPush={f.engine.disable()}
        assertEquals(SharedPreferencesSyncStatus.Off,f.engine.synchronize())
        assertFalse(f.store.load(f.active!!).enabled);assertEquals(before,f.applies)
    }
    @Test fun accountSwitchDuringPullNeverAppliesToTheNewAccount() = runTest {
        val f=Fixture();val original=f.active!!;f.engine.enable();val before=f.applies
        f.afterPull={f.active=SharedPreferencesScope("other-owner",1);f.engine.refreshLocalState()}
        assertEquals(SharedPreferencesSyncStatus.Off,f.engine.synchronize());assertEquals(before,f.applies)
        assertFalse(f.store.load(f.active!!).enabled);assertTrue(f.store.load(original).enabled)
    }
    @Test fun returningToAnAccountStillInvalidatesItsOldRequest() = runTest {
        val f=Fixture();val original=f.active!!;f.engine.enable();val before=f.applies
        f.afterPull={f.active=SharedPreferencesScope("other-owner",1);f.engine.refreshLocalState();f.active=original;f.engine.refreshLocalState()}
        assertEquals(SharedPreferencesSyncStatus.Off,f.engine.synchronize());assertEquals(before,f.applies)
    }
    @Test fun concurrentUnrelatedSettingsAreMerged() = runTest {
        val f=Fixture();f.engine.enable();f.local=prefs(false,true);f.remote=SharedPreferencesSnapshot(2,prefs(true,false))
        assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.synchronize())
        assertEquals(prefs(false,false),f.remote.preferences);assertEquals(prefs(false,false),f.local)
    }
    @Test fun changesMadeDuringTheRequestRemainLocalForTheNextSync() = runTest {
        val f=Fixture();f.engine.enable();f.remote=SharedPreferencesSnapshot(2,prefs(true,false))
        f.afterPull={f.local=prefs(false,true)}
        assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.synchronize())
        assertEquals(prefs(false,false),f.local)
        assertEquals(prefs(true,false),f.store.load(f.active!!).baseline!!.preferences)
        f.afterPull={}
        assertEquals(SharedPreferencesSyncStatus.Synced,f.engine.synchronize())
        assertEquals(prefs(false,false),f.remote.preferences)
    }
    @Test fun networkFailureDoesNotEnableSyncOrReportSuccess() = runTest {
        val f=Fixture();f.afterPull={throw IllegalStateException("Synthetic offline")}
        assertEquals(SharedPreferencesSyncStatus.Error,f.engine.enable());assertFalse(f.store.load(f.active!!).enabled)
    }
    @Test fun retriesAreBoundedAndNeverClaimSuccessOnRepeatedConflict() = runTest {
        val f=Fixture();f.conflicts=8
        assertEquals(SharedPreferencesSyncStatus.Error,f.engine.enable());assertEquals(3,f.pushes);assertFalse(f.store.load(f.active!!).enabled)
    }
    @Test fun missingBaselineCannotUploadDeviceDefaults() = runTest {
        val f=Fixture();f.records[f.active!!]=SharedPreferencesLocalRecord(true,null)
        assertEquals(SharedPreferencesSyncStatus.ChooseInitialSettings,f.engine.synchronize());assertEquals(0,f.pulls);assertEquals(0,f.pushes)
    }
}

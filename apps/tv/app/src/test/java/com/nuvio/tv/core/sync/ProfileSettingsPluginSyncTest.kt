package com.nuvio.tv.core.sync

import io.github.jan.supabase.postgrest.Postgrest
import io.mockk.Called
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Public legacy entry points must respect optional sync rather than bypass its consent. */
class ProfileSettingsPluginSyncTest {
    private val preferences = mockk<OmniaPreferencesSyncService>(relaxed = true)
    private val postgrest = mockk<Postgrest>()
    private val credentials = mockk<ProviderCredentialSyncService>(relaxed = true)
    private val mediaServers = mockk<MediaServerSyncService>(relaxed = true)
    private fun service() = ProfileSettingsSyncService(
        authManager = mockk(relaxed = true),
        omniaPreferencesSyncService = preferences,
        postgrest = postgrest,
        profileManager = mockk(relaxed = true),
        profileDataStoreFactory = mockk(relaxed = true),
        syncClientIdentity = mockk(relaxed = true),
        providerCredentialSyncService = credentials,
        mediaServerSyncService = mediaServers,
        tmdbSettingsDataStore = mockk(relaxed = true),
        metaRepository = mockk(relaxed = true),
        cwEnrichmentCache = mockk(relaxed = true),
    )

    @Test fun startupRequestsConsentAwareSyncWithoutUsingLegacyTransport() {
        service()
        verify(exactly = 1) { preferences.requestSync() }
        verify { postgrest wasNot Called }
    }

    @Test fun offAndInitialChoiceDoNotClaimSettingsWerePulled() = runTest {
        val service = service()
        for (status in listOf(SharedPreferencesSyncStatus.Off, SharedPreferencesSyncStatus.ChooseInitialSettings, SharedPreferencesSyncStatus.SignInRequired)) {
            coEvery { preferences.synchronize() } returns status
            assertFalse(service.pullCurrentProfileFromRemote().getOrThrow())
            assertTrue(service.pushCurrentProfileToRemote().isSuccess)
        }
        coVerify(exactly = 6) { preferences.synchronize() }
        verify { postgrest wasNot Called }
    }

    @Test fun successfulPullReportsAppliedPreferences() = runTest {
        coEvery { preferences.synchronize() } returns SharedPreferencesSyncStatus.Synced
        assertTrue(service().pullCurrentProfileFromRemote().getOrThrow())
        verify { postgrest wasNot Called }
    }

    @Test fun errorsPropagateWithoutFallbackToLegacyTransport() = runTest {
        coEvery { preferences.synchronize() } returns SharedPreferencesSyncStatus.Error
        val service = service()
        assertTrue(service.pullCurrentProfileFromRemote().isFailure)
        assertTrue(service.pushCurrentProfileToRemote().isFailure)
        verify { postgrest wasNot Called }
    }

    @Test fun thrownTransportErrorIsReturnedAsFailure() = runTest {
        coEvery { preferences.synchronize() } throws IllegalStateException("Synthetic offline")
        val service = service()
        assertTrue(service.pullCurrentProfileFromRemote().isFailure)
        assertTrue(service.pushCurrentProfileToRemote().isFailure)
        verify { postgrest wasNot Called }
    }

    @Test fun foregroundRequestRetainsIndependentCredentialAndMediaServerSync() {
        val service = service()
        service.requestForegroundPull(force = true)
        verify(exactly = 2) { preferences.requestSync() }
        verify(exactly = 1) { credentials.requestForegroundPull(true) }
        verify(exactly = 1) { mediaServers.requestForegroundPull(true) }
        verify { postgrest wasNot Called }
    }
}

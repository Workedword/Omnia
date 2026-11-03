package com.nuvio.app.features.debrid

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class DebridProviderTest {
    @Test
    fun `torbox exposes local addon capabilities`() {
        assertTrue(DebridProviders.Torbox.authMethod == DebridProviderAuthMethod.DeviceCode)
        assertTrue(DebridProviders.Torbox.supports(DebridProviderCapability.ClientResolve))
        assertTrue(DebridProviders.Torbox.supports(DebridProviderCapability.LocalTorrentCacheCheck))
        assertTrue(DebridProviders.Torbox.supports(DebridProviderCapability.LocalTorrentResolve))
        assertFalse(DebridProviders.Torbox.supports(DebridProviderCapability.CloudLibrary))
    }

    @Test
    fun `premiumize exposes API key resolver capabilities without cloud library`() {
        assertTrue(DebridProviders.Premiumize.visibleInUi)
        assertTrue(DebridProviders.Premiumize.authMethod == DebridProviderAuthMethod.ApiKey)
        assertTrue(DebridProviders.Premiumize.supports(DebridProviderCapability.ClientResolve))
        assertTrue(DebridProviders.Premiumize.supports(DebridProviderCapability.LocalTorrentCacheCheck))
        assertTrue(DebridProviders.Premiumize.supports(DebridProviderCapability.LocalTorrentResolve))
        assertFalse(DebridProviders.Premiumize.supports(DebridProviderCapability.CloudLibrary))
    }

    @Test
    fun `real debrid is visible for client resolution without local torrent capabilities`() {
        assertTrue(DebridProviders.RealDebrid.authMethod == DebridProviderAuthMethod.ApiKey)
        assertTrue(DebridProviders.RealDebrid.visibleInUi)
        assertTrue(DebridProviders.RealDebrid.supports(DebridProviderCapability.ClientResolve))
        assertFalse(DebridProviders.RealDebrid.supports(DebridProviderCapability.LocalTorrentCacheCheck))
        assertFalse(DebridProviders.RealDebrid.supports(DebridProviderCapability.LocalTorrentResolve))
        assertFalse(DebridProviders.RealDebrid.supports(DebridProviderCapability.CloudLibrary))
    }
}

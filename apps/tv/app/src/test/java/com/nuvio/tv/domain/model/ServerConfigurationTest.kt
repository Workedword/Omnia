package com.nuvio.tv.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerConfigurationTest {
    private fun server(url: String, key: String) = ServerConfiguration(
        backendUrl = url,
        publishableKey = key,
        capabilities = ServerCapabilities(emailPasswordAuth = true, tvLogin = false),
        isCustom = true
    )

    @Test fun localOnlyBuildDoesNotOfferSignIn() {
        assertFalse(server("", "").isConfigured)
        assertFalse(server("https://example.com", "  ").isConfigured)
        assertFalse(server("not a URL", "public-key").isConfigured)
    }

    @Test fun discoveredServerCanOfferSignIn() {
        assertTrue(server("https://example.com", "public-key").isConfigured)
        assertTrue(server("http://192.168.1.10:8000", "public-key").isConfigured)
    }
}

package com.nuvio.tv.ui.screens.addon

import org.junit.Test
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Assert.assertEquals

class OmniaDirectoryPolicyTest {
    @Test fun configuredIdentityIsHiddenAndRemovalMakesItAvailableAgain() {
        val entry = DirectoryCandidate("https://example.com/manifest.json", null, setOf("demo.catalog"))
        val installed = listOf(DirectoryInstallIdentity("demo.catalog", "https://other.example/u/private-demo/manifest.json"))
        assertTrue(OmniaDirectoryPolicy.isInstalled(entry, installed))
        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, emptyList()))
    }
    @Test fun setupServicesMatchConfiguredPathsButNotLookalikeHosts() {
        val entry = DirectoryCandidate("", "https://example.com/provider/configure", setupOnly = true)
        assertTrue(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/provider/config-demo/manifest.json"))))
        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/provider-two/manifest.json"))))
        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com.evil.test/provider/manifest.json"))))
    }
    @Test fun distinctCatalogsOnTheSameServerRemainAvailable() {
        val entry = DirectoryCandidate("https://example.com/catalogs/india/manifest.json", "https://example.com/catalogs/india/configure", setOf("india"))
        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity("other", "https://example.com/catalogs/manifest.json"))))
    }
    @Test fun exactUrlsNormalizePortsAndSuffixesWithoutDiscardingQueryIdentity() {
        val entry = DirectoryCandidate("https://EXAMPLE.com:443/catalog/manifest.json?edition=one", null)
        assertTrue(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/catalog?edition=one#ignored"))))
        assertFalse(OmniaDirectoryPolicy.isInstalled(entry, listOf(DirectoryInstallIdentity(null, "https://example.com/catalog?edition=two"))))
    }
    @Test fun officialLabelRequiresFirstPartyPublicationAndHost() {
        assertEquals("Omnia Official", OmniaDirectoryPolicy.publisher("Omnia Official", "https://omnia.161.97.128.244.sslip.io/catalogs/configure"))
        assertEquals("Community", OmniaDirectoryPolicy.publisher("Omnia Official", "https://example.com/configure"))
        assertEquals("Community", OmniaDirectoryPolicy.publisher("Community", "https://omnia.161.97.128.244.sslip.io/catalogs/configure"))
    }
}

package com.nuvio.app.features.auth

import kotlin.test.Test
import kotlin.test.assertTrue
import kotlin.test.assertFalse

class OmniaAccountPortalTest {
    @Test fun acceptsOnlyTheExactOmniaBackend() {
        assertTrue(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN))
        assertTrue(OmniaAccountPortal.availableFor("  " + OmniaAccountPortal.ORIGIN + "/  "))
        assertFalse(OmniaAccountPortal.availableFor("http://omnia.161.97.128.244.sslip.io"))
        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + ".example.com"))
        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + "@example.com"))
        assertFalse(OmniaAccountPortal.availableFor(OmniaAccountPortal.ORIGIN + "?redirect=example.com"))
        assertFalse(OmniaAccountPortal.availableFor("https://custom.example.com"))
    }
    @Test fun accountLinksHaveNoCredentialsOrSessionParameters() {
        assertTrue(OmniaAccountPortal.ACCOUNT_URL == OmniaAccountPortal.ORIGIN + "/discord-account/")
        assertTrue(OmniaAccountPortal.SIGNUP_URL == OmniaAccountPortal.ORIGIN + "/account/signup")
        assertTrue(OmniaAccountPortal.RECOVERY_URL == OmniaAccountPortal.ORIGIN + "/account/recover")
        listOf(OmniaAccountPortal.ACCOUNT_URL, OmniaAccountPortal.SIGNUP_URL, OmniaAccountPortal.RECOVERY_URL).forEach {
            assertFalse('?' in it || '#' in it || '@' in it)
        }
    }
}

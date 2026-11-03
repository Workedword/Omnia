package com.nuvio.tv.ui.screens.account

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class OmniaDeviceLoginUrlTest {
    @Test fun browserReceivesOnlyTheShortCodeAndAllowlistedProvider() {
        assertEquals(OmniaDeviceLoginUrl.BASE + "?code=ABC234&provider=google", OmniaDeviceLoginUrl.create("abc-234", "google"))
        assertEquals(OmniaDeviceLoginUrl.BASE + "?code=ABC234&provider=discord", OmniaDeviceLoginUrl.create("ABC234", "discord"))
        assertEquals(OmniaDeviceLoginUrl.BASE + "?code=ABC234&provider=email", OmniaDeviceLoginUrl.create("ABC234", "email"))
        assertEquals(OmniaDeviceLoginUrl.BASE + "?code=ABC234", OmniaDeviceLoginUrl.create("ABC234", null))
        for (code in listOf("ABC234&nonce=secret", "https://evil.invalid", "", "ABC2345")) assertFailsWith<IllegalArgumentException> { OmniaDeviceLoginUrl.create(code, "google") }
        assertFailsWith<IllegalArgumentException> { OmniaDeviceLoginUrl.create("ABC234", "google&redirect=evil") }
    }
    @Test fun originCheckRejectsLookalikesPortsAndExtraPaths() {
        assertTrue(OmniaDeviceLoginUrl.isOmnia(OmniaDeviceLoginUrl.ORIGIN + "/"))
        for (suffix in listOf(".evil.invalid", ":444", "/extra")) assertFalse(OmniaDeviceLoginUrl.isOmnia(OmniaDeviceLoginUrl.ORIGIN + suffix))
        assertFalse(OmniaDeviceLoginUrl.isOmnia(OmniaDeviceLoginUrl.ORIGIN.replace("https:", "http:")))
    }
}

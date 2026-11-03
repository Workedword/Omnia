package com.nuvio.tv.mobile

import com.nuvio.tv.launcher.useTvInterface
import org.junit.Assert.*
import org.junit.Test

class MobileCompanionPolicyTest {
    @Test fun televisionsKeepRemoteInterfaceEvenWithoutLeanbackFlag() {
        assertTrue(useTvInterface(false, true))
        assertTrue(useTvInterface(true, false))
        assertFalse(useTvInterface(false, false))
    }
    @Test fun addonCredentialsRequireHttpsAndCannotUseUrlUserInfo() {
        assertNull(secureAddonUrl("http://example.com/manifest.json"))
        assertNull(secureAddonUrl("https://user:secret@example.com/manifest.json"))
        assertNull(secureAddonUrl("https://example.com/manifest.json#secret"))
        assertEquals("https://example.com/config/manifest.json?key=example", secureAddonUrl(" https://example.com/config/manifest.json?key=example "))
    }
}

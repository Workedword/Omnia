package com.nuvio.tv.core.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OmniaAuthLogPrivacyTest {
    @Test fun omniaDoesNotUploadAuthenticationPayloads() {
        assertFalse(authDiagnosticUploadsAllowed("https://omnia.161.97.128.244.sslip.io/", "https://reports.example.invalid"))
        assertFalse(authDiagnosticUploadsAllowed("https://custom.example.invalid", ""))
        assertTrue(authDiagnosticUploadsAllowed("https://custom.example.invalid", "https://reports.example.invalid"))
    }
    @Test fun authFailureSummaryExcludesMessagesAndCauses() {
        assertEquals("IllegalStateException", authFailureClass(IllegalStateException("access_token=private-value", RuntimeException("nonce=private-value"))))
        assertEquals("unspecified", authFailureClass(null))
    }
}

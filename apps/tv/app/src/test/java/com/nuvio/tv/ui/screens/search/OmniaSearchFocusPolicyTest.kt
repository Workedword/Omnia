package com.nuvio.tv.ui.screens.search

import android.view.KeyEvent
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OmniaSearchFocusPolicyTest {
    @Test fun emptyFieldReachesLeadingControlsInLtr() {
        assertTrue(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_LEFT, true))
        assertFalse(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_RIGHT, true))
    }
    @Test fun emptyFieldReachesLeadingControlsInRtl() {
        assertTrue(shouldFocusLeadingSearchControl("", true, KeyEvent.KEYCODE_DPAD_RIGHT, true))
        assertFalse(shouldFocusLeadingSearchControl("", true, KeyEvent.KEYCODE_DPAD_LEFT, true))
    }
    @Test fun typedQueriesKeepCaretNavigation() {
        for (query in listOf("Movie", " ", "Hindi series")) {
            assertFalse(shouldFocusLeadingSearchControl(query, false, KeyEvent.KEYCODE_DPAD_LEFT, true))
            assertFalse(shouldFocusLeadingSearchControl(query, true, KeyEvent.KEYCODE_DPAD_RIGHT, true))
        }
    }
    @Test fun hiddenDiscoverAndOtherDirectionsDoNotCaptureFocus() {
        assertFalse(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_LEFT, false))
        assertFalse(shouldFocusLeadingSearchControl("", true, KeyEvent.KEYCODE_DPAD_RIGHT, false))
        assertFalse(shouldFocusLeadingSearchControl("", false, KeyEvent.KEYCODE_DPAD_DOWN, true))
    }
}

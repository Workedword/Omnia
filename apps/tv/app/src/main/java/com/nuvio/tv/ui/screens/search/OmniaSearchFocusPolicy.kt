package com.nuvio.tv.ui.screens.search

import android.view.KeyEvent

/** Empty search must allow a remote to reach its leading controls. */
internal fun shouldFocusLeadingSearchControl(query: String, isRtl: Boolean, keyCode: Int, discoverVisible: Boolean): Boolean =
    discoverVisible && query.isEmpty() && keyCode == if (isRtl) KeyEvent.KEYCODE_DPAD_RIGHT else KeyEvent.KEYCODE_DPAD_LEFT

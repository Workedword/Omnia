package com.nuvio.tv.core.auth

import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive

/** Leaving or replacing device sign-in must prevent a late response signing in. */
internal suspend fun importActiveDeviceSession(importSession: suspend () -> Unit) {
    currentCoroutineContext().ensureActive()
    importSession()
}

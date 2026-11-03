package com.nuvio.tv.core.auth

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.cancel
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OmniaDeviceSessionImportTest {
    @Test fun activeDeviceFlowImportsExactlyOnce() = runBlocking {
        var imports = 0
        importActiveDeviceSession { imports++ }
        assertEquals(1, imports)
    }
    @Test fun cancelledDeviceFlowRejectsALateResponse() = runBlocking {
        var imports = 0
        var refused = false
        val job = launch(start = CoroutineStart.UNDISPATCHED) {
            currentCoroutineContext().cancel()
            try { importActiveDeviceSession { imports++ } }
            catch (_: CancellationException) { refused = true }
        }
        job.join()
        assertTrue(refused)
        assertEquals(0, imports)
    }
}

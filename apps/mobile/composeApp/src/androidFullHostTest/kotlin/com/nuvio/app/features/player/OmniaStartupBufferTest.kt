package com.nuvio.app.features.player

import android.app.Application
import androidx.media3.exoplayer.DefaultLoadControl
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], application = Application::class)
class OmniaStartupBufferTest {
    private fun threshold(control: DefaultLoadControl, name: String): Long =
        DefaultLoadControl::class.java.getDeclaredField(name).apply { isAccessible = true }.getLong(control)

    @Test fun initialBufferIsShorterWithoutReducingRecoveryProtection() {
        val field = NuvioExoPlayerPerformanceHelper::class.java.getDeclaredField("enabled").apply { isAccessible = true }
        val previous = field.getBoolean(NuvioExoPlayerPerformanceHelper)
        try {
            field.setBoolean(NuvioExoPlayerPerformanceHelper, true)
            val control = NuvioExoPlayerPerformanceHelper.buildLoadControl(RuntimeEnvironment.getApplication())
            assertEquals(1_500_000L, threshold(control, "bufferForPlaybackUs"))
            assertEquals(3_000_000L, threshold(control, "bufferForPlaybackAfterRebufferUs"))
            val custom = NuvioExoPlayerPerformanceHelper.buildLoadControl(RuntimeEnvironment.getApplication(),
                PlaybackBufferSettings(enabled = true, bufferForPlaybackMs = 7_000, bufferForPlaybackAfterRebufferMs = 9_000))
            assertEquals(7_000_000L, threshold(custom, "bufferForPlaybackUs"))
            assertEquals(9_000_000L, threshold(custom, "bufferForPlaybackAfterRebufferUs"))
        } finally { field.setBoolean(NuvioExoPlayerPerformanceHelper, previous) }
    }
}

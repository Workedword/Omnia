package com.nuvio.app.features.details.components

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.interop.UIKitViewController
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.nuvio.app.core.ui.LocalScreenActive
import com.nuvio.app.features.player.NuvioPlayerBridgeFactory
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.useContents
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive

@OptIn(ExperimentalForeignApi::class)
@Composable
actual fun HeroTrailerPlayerSurface(
    sourceUrl: String,
    sourceAudioUrl: String?,
    playWhenReady: Boolean,
    muted: Boolean,
    modifier: Modifier,
    onReady: () -> Unit,
    onEnded: () -> Unit,
    onError: () -> Unit,
) {
    val latestReady = rememberUpdatedState(onReady)
    val latestEnded = rememberUpdatedState(onEnded)
    val latestError = rememberUpdatedState(onError)
    val owner = LocalLifecycleOwner.current
    val screenActive = LocalScreenActive.current
    var foreground by remember(owner) {
        mutableStateOf(owner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED))
    }
    val bridge = remember(sourceUrl, sourceAudioUrl) {
        NuvioPlayerBridgeFactory.create()?.apply { configureHeroPreview(muted) }
    }
    if (bridge == null) {
        LaunchedEffect(sourceUrl, sourceAudioUrl) { latestError.value() }
        return
    }
    val controller = remember(bridge) { bridge.createPlayerViewController() }

    DisposableEffect(owner) {
        val observer = LifecycleEventObserver { _, _ ->
            foreground = owner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }
    DisposableEffect(bridge) {
        onDispose {
            bridge.pause()
            bridge.destroy()
        }
    }
    LaunchedEffect(bridge, muted) { bridge.setMuted(muted) }
    LaunchedEffect(bridge, playWhenReady, foreground, screenActive) {
        if (playWhenReady && foreground && screenActive) bridge.play() else bridge.pause()
    }
    LaunchedEffect(bridge) {
        bridge.loadFileWithAudio(sourceUrl, sourceAudioUrl, null, null)
        var ready = false
        var loadingTicks = 0
        while (isActive) {
            val loading = bridge.getIsLoading()
            if (bridge.getErrorMessage().isNotBlank()) {
                bridge.pause()
                latestError.value()
                break
            }
            if (bridge.getIsEnded()) {
                bridge.pause()
                latestEnded.value()
                break
            }
            if (!ready && !loading && (bridge.getIsPlaying() || bridge.getDurationMs() > 0L)) {
                ready = true
                latestReady.value()
            }
            if (!ready && ++loadingTicks >= 180) {
                bridge.pause()
                latestError.value()
                break
            }
            delay(250L)
        }
    }
    UIKitViewController(
        factory = { controller },
        modifier = modifier.clipToBounds(),
        interactive = false,
        onResize = { viewController, rect ->
            viewController.view.setFrame(rect)
            rect.useContents {
                bridge.syncVideoSurfaceLayout(width = size.width, height = size.height)
            }
        },
    )
}

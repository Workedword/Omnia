package com.nuvio.app.features.details

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object HeroTrailerAudioState {
    private val _muted = MutableStateFlow(false)
    val muted: StateFlow<Boolean> = _muted.asStateFlow()

    fun toggleMuted() {
        _muted.value = !_muted.value
    }
}

package com.nuvio.tv.ui.screens.detail

import com.nuvio.tv.domain.model.Meta

internal fun Meta.principalCastNames(): List<String> {
    val principal = castMembers
        .filter { it.character.orEmpty().trim().lowercase() !in listOf("director", "writer", "creator") }
        .map { it.name }
    return (principal.ifEmpty { cast }).asSequence()
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinctBy { it.lowercase() }
        .take(6)
        .toList()
}

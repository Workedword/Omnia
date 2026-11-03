package com.nuvio.app.features.details

internal fun MetaDetails.principalCastNames(): List<String> = cast.asSequence()
    .filter { it.role.orEmpty().trim().lowercase() !in listOf("director", "writer", "creator") }
    .map { it.name.trim() }
    .filter { it.isNotBlank() }
    .distinctBy { it.lowercase() }
    .take(6)
    .toList()

package com.nuvio.app.features.collection

/** Derived from the active profile; never mutates catalog preferences or sources. */
internal fun hiddenCollectionCatalogKeys(collections: List<Collection>, disabledCollectionIds: Set<String>): Set<String> =
    collections.asSequence()
        .filter { it.hideSourceRows && it.id !in disabledCollectionIds }
        .flatMap { it.folders.asSequence() }
        .flatMap { folder -> folder.resolvedCatalogSources.asSequence() }
        .map { source -> "${source.addonId}:${source.type}:${source.catalogId}" }
        .toSet()

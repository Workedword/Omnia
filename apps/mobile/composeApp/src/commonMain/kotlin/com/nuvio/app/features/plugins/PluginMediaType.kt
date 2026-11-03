package com.nuvio.app.features.plugins

/** Preserve the episodic type declared by a provider after normalizing catalog aliases. */
internal fun jsPluginMediaType(
    mediaType: String,
    supportedTypes: List<String>,
    season: Int?,
    episode: Int?,
): String {
    val normalizedType = normalizePluginType(mediaType)
    return if (
        normalizedType == "tv" && season != null && episode != null &&
        supportedTypes.any { it.equals("series", ignoreCase = true) }
    ) "series" else normalizedType
}

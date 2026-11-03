package com.nuvio.app.core.sync

import java.util.prefs.Preferences

internal actual object OmniaPreferencesSyncStorage {
    private val values = Preferences.userRoot().node("omnia/optional-preferences")
    actual fun load(key: String): String? {
        val parts = values.getInt(key + ".parts", 0)
        if (parts !in 1..64) return null
        return buildString {
            repeat(parts) { index -> append(values.get(key + "." + index, null) ?: return null) }
        }
    }
    actual fun save(key: String, value: String) {
        require(key.startsWith("omnia.settings.sync.v1."))
        val chunks = value.chunked(7500)
        require(chunks.size in 1..64)
        chunks.forEachIndexed { index, chunk -> values.put(key + "." + index, chunk) }
        values.putInt(key + ".parts", chunks.size)
        values.flush()
    }
    actual fun clear() { values.clear(); values.flush() }
}

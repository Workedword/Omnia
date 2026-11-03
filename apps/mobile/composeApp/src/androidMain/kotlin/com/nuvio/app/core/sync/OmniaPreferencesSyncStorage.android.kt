package com.nuvio.app.core.sync

import android.content.Context
import android.content.SharedPreferences

internal actual object OmniaPreferencesSyncStorage {
    private var preferences: SharedPreferences? = null
    fun initialize(context: Context) {
        preferences = context.applicationContext.getSharedPreferences("omnia_optional_preferences", Context.MODE_PRIVATE)
    }
    actual fun load(key: String): String? = preferences?.getString(key, null)
    actual fun save(key: String, value: String) {
        require(key.startsWith("omnia.settings.sync.v1."))
        val storage = requireNotNull(preferences) { "Device preference storage is not ready" }
        check(storage.edit().putString(key, value).commit()) { "Unable to save device sync preference" }
    }
    actual fun clear() {
        preferences?.let { check(it.edit().clear().commit()) { "Unable to clear device sync preferences" } }
    }
}

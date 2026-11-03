package com.nuvio.app.core.sync

/** Device-only storage. These records and the enabled flag are never synced. */
internal expect object OmniaPreferencesSyncStorage {
    fun load(key: String): String?
    fun save(key: String, value: String)
    fun clear()
}

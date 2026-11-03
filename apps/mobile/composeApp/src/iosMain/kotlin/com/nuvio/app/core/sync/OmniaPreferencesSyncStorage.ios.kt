package com.nuvio.app.core.sync

import platform.Foundation.NSUserDefaults

internal actual object OmniaPreferencesSyncStorage {
    actual fun load(key: String): String? = NSUserDefaults.standardUserDefaults.stringForKey(key)
    actual fun save(key: String, value: String) {
        require(key.startsWith("omnia.settings.sync.v1."))
        NSUserDefaults.standardUserDefaults.setObject(value, forKey = key)
    }
    actual fun clear() {
        val defaults = NSUserDefaults.standardUserDefaults
        defaults.dictionaryRepresentation().keys.filterIsInstance<String>()
            .filter { it.startsWith("omnia.settings.sync.v1.") }
            .forEach { defaults.removeObjectForKey(it) }
    }
}

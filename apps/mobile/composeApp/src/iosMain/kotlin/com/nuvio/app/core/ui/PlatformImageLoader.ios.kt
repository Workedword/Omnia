@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.nuvio.app.core.ui

import coil3.ImageLoader
import coil3.disk.DiskCache
import okio.Path.Companion.toPath
import platform.Foundation.NSCachesDirectory
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSUserDomainMask

internal actual fun ImageLoader.Builder.configurePlatformImageLoader(): ImageLoader.Builder = diskCache {
    val root = NSSearchPathForDirectoriesInDomains(NSCachesDirectory, NSUserDomainMask, true).first() as String
    DiskCache.Builder()
        .directory((root + "/image_cache").toPath())
        .maxSizeBytes(96L * 1024 * 1024)
        .build()
}

internal actual val platformProvidesImageLoader: Boolean = false

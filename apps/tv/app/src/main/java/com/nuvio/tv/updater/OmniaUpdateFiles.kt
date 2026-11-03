package com.nuvio.tv.updater

import java.io.File

/** Operates on direct installer files in the app-owned updates directory only. */
internal object OmniaUpdateFiles {
    private fun managed(directory: File): List<File> = directory.listFiles().orEmpty().filter {
        it.isFile && it.canonicalFile.parentFile == directory.canonicalFile &&
            (it.name.endsWith(".apk") || it.name.endsWith(".apk.part") || it.name == "update.dm")
    }

    fun prune(directory: File, keep: File? = null) {
        require(keep == null || keep.canonicalFile.parentFile == directory.canonicalFile)
        managed(directory).filter { it != keep }.forEach { it.delete() }
    }

    fun removeInstalled(directory: File, installedCode: Long, archiveCode: (File) -> Long?) {
        managed(directory).forEach { file ->
            val code = if (file.name.endsWith(".apk")) archiveCode(file) else null
            if (code == null || code <= installedCode) file.delete()
        }
    }
}

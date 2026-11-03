package com.nuvio.app.features.updater

import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class OmniaUpdateFilesTest {
    @Test fun upgradeRemovesInstalledAndCorruptFilesButKeepsPendingUpdateAndUserFiles() {
        val root = Files.createTempDirectory("omnia-update-cleanup").toFile()
        try {
            val names = listOf("old.apk", "current.apk", "future.apk", "corrupt.apk", "future.apk.part", "update.dm", "notes.txt")
            names.forEach { root.resolve(it).writeText(it) }
            val versions = mapOf("old.apk" to 1L, "current.apk" to 2L, "future.apk" to 3L)
            OmniaUpdateFiles.removeInstalled(root, 2) { versions[it.name] }
            assertEquals(setOf("future.apk", "notes.txt"), root.list()!!.toSet())
            OmniaUpdateFiles.removeInstalled(root, 3) { versions[it.name] }
            assertEquals(setOf("notes.txt"), root.list()!!.toSet())
        } finally { root.deleteRecursively() }
    }

    @Test fun nextDownloadReclaimsOldInstallersWithoutRecursingIntoOtherData() {
        val root = Files.createTempDirectory("omnia-update-prune").toFile()
        try {
            val pending = root.resolve("new.apk").apply { writeText("new") }
            root.resolve("old.apk").writeText("old")
            root.resolve("failed.apk.part").writeText("partial")
            val unrelated = root.resolve("nested").apply { mkdir() }.resolve("saved.apk").apply { writeText("saved") }
            OmniaUpdateFiles.prune(root, pending)
            assertTrue(pending.exists());assertTrue(unrelated.exists())
            assertFalse(root.resolve("old.apk").exists());assertFalse(root.resolve("failed.apk.part").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun anOutsideKeepPathIsRejected() {
        val root = Files.createTempDirectory("omnia-update-boundary").toFile()
        try {
            assertThrows(IllegalArgumentException::class.java) { OmniaUpdateFiles.prune(root, root.parentFile.resolve("outside.apk")) }
        } finally { root.deleteRecursively() }
    }

    @Test fun symlinksCannotDeleteOutsideTheInstallerDirectory() {
        val root = Files.createTempDirectory("omnia-update-symlink").toFile()
        val outside = Files.createTempFile("omnia-preserved", ".apk").toFile()
        try {
            outside.writeText("preserved")
            Files.createSymbolicLink(root.resolve("linked.apk").toPath(), outside.toPath())
            OmniaUpdateFiles.prune(root)
            assertEquals("preserved", outside.readText())
        } finally { root.deleteRecursively();outside.delete() }
    }
}

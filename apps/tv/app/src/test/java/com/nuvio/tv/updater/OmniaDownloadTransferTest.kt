package com.nuvio.tv.updater

import java.io.File
import java.nio.file.Files
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import okio.Buffer
import org.junit.Assert.*
import org.junit.Test


class OmniaDownloadTransferTest {
    private fun directory(): File { return Files.createTempDirectory("omnia-transfer").toFile() }
    private suspend fun download(server: MockWebServer, root: File, progress: (Long, Long?) -> Unit = { _, _ -> }): Result<File> {
        return ApkDownloader(OkHttpClient.Builder().readTimeout(2, TimeUnit.SECONDS).build()).download(server.url("/candidate.apk").toString(), root.resolve("candidate.apk"), progress)
    }

    @Test fun completeDownloadIsAtomicAndDoesNotEnterTheHttpCache() { runBlocking {
        val root = directory()
        try { MockWebServer().use { server ->
            val data = ByteArray(16384) { (it % 255).toByte() }
            server.enqueue(MockResponse().setBody(Buffer().write(data)))
            val file = download(server, root).getOrThrow()
            assertArrayEquals(data, file.readBytes())
            assertFalse(root.resolve("candidate.apk.part").exists())
            assertEquals("no-store", server.takeRequest().getHeader("Cache-Control"))
        } } finally { root.deleteRecursively() }
    } }

    @Test fun httpFailureLeavesNoInstallerOrPartialFile() { runBlocking {
        val root = directory()
        try { MockWebServer().use { server ->
            server.enqueue(MockResponse().setResponseCode(503).setBody("Unavailable"))
            assertTrue(download(server, root).isFailure)
            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())
        } } finally { root.deleteRecursively() }
    } }

    @Test fun truncatedDownloadCannotBecomeAnInstallableFile() { runBlocking {
        val root = directory()
        try { MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("short").setHeader("Content-Length", 4096).setSocketPolicy(SocketPolicy.DISCONNECT_AT_END))
            assertTrue(download(server, root).isFailure)
            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())
        } } finally { root.deleteRecursively() }
    } }

    @Test fun cancellationIsPropagatedAndReclaimsThePartialDownload() { runBlocking {
        val root = directory()
        try { MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("candidate bytes"))
            var cancelled = false
            try { download(server, root) { _, _ -> throw CancellationException("cancelled by test") } }
            catch (_: CancellationException) { cancelled = true }
            assertTrue(cancelled)
            assertFalse(root.resolve("candidate.apk").exists());assertFalse(root.resolve("candidate.apk.part").exists())
        } } finally { root.deleteRecursively() }
    } }
}

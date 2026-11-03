package com.nuvio.tv.updater

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ApkDownloader @Inject constructor(private val okHttpClient: OkHttpClient) {
    suspend fun download(
        url: String,
        destinationFile: File,
        onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit
    ): Result<File> = withContext(Dispatchers.IO) {
        val partial = File(destinationFile.parentFile, "${destinationFile.name}.part")
        try {
            destinationFile.parentFile?.mkdirs()
            if (destinationFile.exists()) check(destinationFile.delete()) { "Could not replace the saved update" }
            val request = Request.Builder().url(url).header("Cache-Control", "no-store").build()
            okHttpClient.newCall(request).execute().use { response ->
                check(response.isSuccessful) { "Download failed: HTTP ${response.code}" }
                val body = checkNotNull(response.body) { "Empty update download" }
                val total = body.contentLength().takeIf { it > 0 }
                var received = 0L
                body.byteStream().use { input ->
                    FileOutputStream(partial).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            currentCoroutineContext().ensureActive()
                            val read = input.read(buffer)
                            if (read < 0) break
                            if (read == 0) continue
                            output.write(buffer, 0, read);received += read
                            onProgress(received, total)
                        }
                        output.fd.sync()
                    }
                }
                check(received > 0L && (total == null || received == total)) { "Incomplete update download. Please retry." }
            }
            currentCoroutineContext().ensureActive()
            check(partial.renameTo(destinationFile)) { "Could not save update. Check free storage." }
            Result.success(destinationFile)
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (error: Exception) {
            Result.failure(error)
        } finally {
            partial.delete()
        }
    }
}

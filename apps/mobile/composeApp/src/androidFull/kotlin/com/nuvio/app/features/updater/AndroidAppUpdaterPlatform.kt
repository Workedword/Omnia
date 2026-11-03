package com.nuvio.app.features.updater

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.updates_download_failed_http
import nuvio.composeapp.generated.resources.updates_downloaded_file_missing
import nuvio.composeapp.generated.resources.updates_empty_download_body
import okhttp3.OkHttpClient
import okhttp3.Request
import org.jetbrains.compose.resources.getString
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit

object AndroidAppUpdaterPlatform {
    private const val preferencesName = "nuvio_updater"
    private const val ignoredTagKey = "ignored_release_tag"
    private const val updateChannelKey = "update_channel"

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .followRedirects(true)
        .followSslRedirects(true)
        .build()

    private var appContext: Context? = null
    private val downloadMutex = Mutex()
    private val maintenanceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var cleanupScheduled = false

    fun initialize(context: Context) {
        appContext = context.applicationContext
        val schedule = synchronized(this) {
            if (cleanupScheduled) false else { cleanupScheduled = true; true }
        }
        if (schedule) maintenanceScope.launch {
            downloadMutex.withLock {
                runCatching {
                    val current = context.packageManager.getPackageInfo(context.packageName, 0)
                    val code = if (Build.VERSION.SDK_INT >= 28) current.longVersionCode else current.versionCode.toLong()
                    listOf(File(context.cacheDir, "updates"), File(context.filesDir, "updates")).forEach { directory ->
                    OmniaUpdateFiles.removeInstalled(directory, code) { file ->
                        context.packageManager.getPackageArchiveInfo(file.path, 0)?.takeIf { it.packageName == context.packageName }?.let {
                            if (Build.VERSION.SDK_INT >= 28) it.longVersionCode else it.versionCode.toLong()
                        }
                    }
                    }
                }
            }
        }
    }

    fun getSupportedAbis(): List<String> = Build.SUPPORTED_ABIS?.toList().orEmpty()

    fun isDebugBuild(): Boolean {
        val context = appContext ?: return false
        return context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0
    }

    fun getIgnoredTag(): String? =
        preferences().getString(ignoredTagKey, null)

    fun setIgnoredTag(tag: String?) {
        preferences().edit().apply {
            if (tag == null) remove(ignoredTagKey) else putString(ignoredTagKey, tag)
        }.apply()
    }

    fun getUpdateChannel(): String? = preferences().getString(updateChannelKey, null)

    fun setUpdateChannel(channel: String) {
        preferences().edit().putString(updateChannelKey, channel).apply()
    }

    fun deleteDownloadedApk(path: String) {
        File(path).delete()
    }

    suspend fun downloadApk(
        assetUrl: String,
        assetName: String,
        onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,
    ): Result<String> = withContext(Dispatchers.IO) {
        downloadMutex.withLock {
            val context = requireContext()
            val safeName = assetName.replace(Regex("[^a-zA-Z0-9._-]"), "_")
            val directory = File(context.cacheDir, "updates").apply { mkdirs() }
            val destination = File(directory, safeName)
            val partial = File(directory, "$safeName.part")
            try {
                require(safeName.endsWith(".apk")) { "Invalid update filename" }
                OmniaUpdateFiles.prune(directory)
                val request = Request.Builder().url(assetUrl).header("Cache-Control", "no-store").build()
                httpClient.newCall(request).execute().use { response ->
                    check(response.isSuccessful) { "Download failed: HTTP ${response.code}" }
                    val body = checkNotNull(response.body) { "Empty update download" }
                    val totalBytes = body.contentLength().takeIf { it > 0L }
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
                                onProgress(received, totalBytes)
                            }
                            output.fd.sync()
                        }
                    }
                    check(received > 0L && (totalBytes == null || received == totalBytes)) { "Incomplete update download. Please retry." }
                }
                currentCoroutineContext().ensureActive()
                check(partial.renameTo(destination)) { "Could not save update. Check free storage." }
                Result.success(destination.absolutePath)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Exception) {
                Result.failure(error)
            } finally {
                partial.delete()
            }
        }
    }

    fun canRequestPackageInstalls(): Boolean {
        val context = appContext ?: return false
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                context.packageManager.canRequestPackageInstalls()
            } catch (_: SecurityException) {
            
                true
            }
        } else {
            true
        }
    }

    fun openUnknownSourcesSettings() {
        val context = appContext ?: return
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val intent = Intent(
            Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
            Uri.parse("package:${context.packageName}"),
        ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }

    fun installDownloadedApk(path: String): Result<Unit> = runCatching {
        val context = requireContext()
        val apkFile = File(path)
        check(apkFile.exists()) { runBlocking { getString(Res.string.updates_downloaded_file_missing) } }
        val archive = context.packageManager.getPackageArchiveInfo(apkFile.path, 0)
        check(archive?.packageName == context.packageName) { "This APK is not an update for this Omnia app." }

        val apkUri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            apkFile,
        )

        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(apkUri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        context.startActivity(intent)
    }

    private fun preferences() = requireContext().getSharedPreferences(preferencesName, Context.MODE_PRIVATE)

    private fun requireContext(): Context =
        requireNotNull(appContext) { "AndroidAppUpdaterPlatform.initialize must be called before use." }
}

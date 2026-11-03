package com.nuvio.tv.core.auth

/** Auth inputs, response bodies and exception messages must never reach logcat. */
@Suppress("UNUSED_PARAMETER")
internal object OmniaAuthLog {
    fun d(tag: String, message: String): Int = 0
    fun w(tag: String, message: String, error: Throwable? = null): Int =
        android.util.Log.w(tag, "Account operation warning: ${authFailureClass(error)}")
    fun e(tag: String, message: String, error: Throwable? = null): Int =
        android.util.Log.e(tag, "Account operation failed: ${authFailureClass(error)}")
}

internal fun authFailureClass(error: Throwable?): String = error?.javaClass?.simpleName ?: "unspecified"

internal fun authDiagnosticUploadsAllowed(backend: String, endpoint: String): Boolean =
    endpoint.isNotBlank() && !backend.trim().trimEnd('/').equals(
        "https://omnia.161.97.128.244.sslip.io", ignoreCase = true,
    )

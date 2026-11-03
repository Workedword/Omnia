package com.nuvio.tv.core.qr

import android.graphics.Bitmap
import android.graphics.Color
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.common.BitMatrix
import com.google.zxing.qrcode.QRCodeWriter

object QrCodeGenerator {

    fun generate(content: String, size: Int = 512, margin: Int = 4): Bitmap {
        val matrix = encodeMatrix(content, size, margin)
        // Preserve the complete square quiet zone. Rounded clipping and margins below
        // four modules make scanning from a distant TV unnecessarily fragile.
        val pixels = IntArray(matrix.width * matrix.height) { index ->
            if (matrix[index % matrix.width, index / matrix.width]) Color.BLACK else Color.WHITE
        }
        return Bitmap.createBitmap(pixels, matrix.width, matrix.height, Bitmap.Config.ARGB_8888)
    }

    internal fun encodeMatrix(content: String, size: Int, margin: Int = 4): BitMatrix =
        QRCodeWriter().encode(
            content, BarcodeFormat.QR_CODE, size, size,
            mapOf(EncodeHintType.MARGIN to margin.coerceAtLeast(4))
        )

    internal data class ModuleGrid(val left: Int, val top: Int, val moduleSize: Int, val modules: Int)

    /**
     * Locates the scaled module grid inside [matrix]. The top-left finder pattern starts the
     * symbol and is 7 modules wide, which gives the module size without assuming any padding.
     */
    internal fun moduleGrid(matrix: BitMatrix): ModuleGrid {
        // [left, top, width, height]; the finder patterns pin all four edges of the symbol
        val bounds = matrix.enclosingRectangle ?: return ModuleGrid(0, 0, 1, 0)
        val left = bounds[0]
        val top = bounds[1]
        var x = left
        while (x < matrix.width && matrix[x, top]) x++
        val moduleSize = ((x - left) / 7).coerceAtLeast(1)
        return ModuleGrid(left, top, moduleSize, bounds[2] / moduleSize)
    }
}

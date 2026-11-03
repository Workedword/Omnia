package com.nuvio.tv.launcher

import com.nuvio.tv.MainActivity
import android.app.UiModeManager
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.os.Bundle
import androidx.activity.ComponentActivity
import com.nuvio.tv.mobile.MobileCompanionActivity

internal fun useTvInterface(leanback: Boolean, television: Boolean): Boolean = leanback || television

open class OmniaLauncherActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val mode = (getSystemService(UI_MODE_SERVICE) as UiModeManager).currentModeType
        val isTv = useTvInterface(packageManager.hasSystemFeature(PackageManager.FEATURE_LEANBACK), mode == Configuration.UI_MODE_TYPE_TELEVISION)
        val destination = if (isTv) MainActivity::class.java else MobileCompanionActivity::class.java
        startActivity(Intent(intent).setClass(this, destination))
        finish()
    }
}

class AppIconDefault : OmniaLauncherActivity()

class AppIconArcticBlue : OmniaLauncherActivity()

class AppIconEmerald : OmniaLauncherActivity()

class AppIconRoseGold : OmniaLauncherActivity()

class AppIconCopper : OmniaLauncherActivity()

class AppIconGraphite : OmniaLauncherActivity()

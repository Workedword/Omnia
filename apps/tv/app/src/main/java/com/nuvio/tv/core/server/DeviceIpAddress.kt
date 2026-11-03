package com.nuvio.tv.core.server

import android.content.Context
import android.net.wifi.WifiManager
import java.net.Inet4Address
import java.net.NetworkInterface

object DeviceIpAddress {
    fun get(context: Context): String? {
        val addresses = runCatching {
            NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
                .filter { it.isUp && !it.isLoopback && !it.isPointToPoint }
                .flatMap { network -> network.inetAddresses.toList()
                    .filterIsInstance<Inet4Address>().map { network.name to it } }
        }.getOrDefault(emptyList())
        val wifiAddress = runCatching {
            val manager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            val ip = manager?.connectionInfo?.ipAddress ?: 0
            if (ip == 0) null else "${ip and 0xFF}.${ip shr 8 and 0xFF}.${ip shr 16 and 0xFF}.${ip shr 24 and 0xFF}"
        }.getOrNull()
        return selectLanAddress(wifiAddress, addresses)
    }

    internal fun selectLanAddress(wifiAddress: String?, addresses: List<Pair<String, Inet4Address>>): String? {
        val candidates = addresses.filter { (name, address) ->
            !address.isLoopbackAddress && !address.isLinkLocalAddress && !address.isAnyLocalAddress &&
                address.isSiteLocalAddress &&
                listOf("tun", "tap", "wg", "ppp", "docker", "veth").none { name.startsWith(it) }
        }
        // Only trust WifiManager when the address still belongs to a live interface.
        return candidates.firstOrNull { it.second.hostAddress == wifiAddress }?.second?.hostAddress
            ?: candidates.sortedBy { (name, _) ->
                if (name.startsWith("wlan") || name.startsWith("eth")) 0 else 1
            }.firstOrNull()?.second?.hostAddress
    }
}

package com.nuvio.tv.core.server
import java.net.InetAddress
import java.net.Inet4Address
import org.junit.Assert.*
import org.junit.Test
class DeviceIpAddressTest {
    private fun address(name: String, ip: String) = name to (InetAddress.getByName(ip) as Inet4Address)
    @Test fun staleWifiFallsBackToEthernetInsteadOfVpn() {
        assertEquals("192.168.1.40", DeviceIpAddress.selectLanAddress("192.168.2.8", listOf(address("tun0", "10.8.0.2"), address("eth0", "192.168.1.40"))))
    }
    @Test fun currentWifiWinsOverOtherInterfaces() {
        assertEquals("192.168.1.8", DeviceIpAddress.selectLanAddress("192.168.1.8", listOf(address("eth0", "10.0.0.3"), address("wlan0", "192.168.1.8"))))
    }
    @Test fun unreachableAndTunnelAddressesAreNotAdvertised() {
        assertNull(DeviceIpAddress.selectLanAddress(null, listOf(address("lo", "127.0.0.1"), address("eth0", "169.254.1.1"), address("wg0", "10.2.0.4"))))
    }
}

package com.nuvio.tv.updater

import com.nuvio.tv.data.remote.dto.GitHubReleaseDto
import org.junit.Assert.assertEquals
import org.junit.Test

class ReleaseSelectorTest {
    @Test
    fun `shared feed excludes phone APKs and source archives`() {
        fun asset(name: String) = com.nuvio.tv.data.remote.dto.GitHubAssetDto(name, "https://example.com/$name")
        val releases = listOf(
            release("v9.0.0+android").copy(assets = listOf(asset("Omnia-Mobile-9.0.0.apk"))),
            release("v0.3.9+tv").copy(assets = listOf(asset("Omnia-TV-0.3.9.apk"), asset("Omnia-TV-source.zip"))),
            release("v1.0.0-beta.1+tv", prerelease = true).copy(assets = listOf(asset("Omnia-TV-1.0.0.apk")))
        )
        val selected = ReleaseSelector.eligibleReleases(ReleaseSelector.forTv(releases), UpdateChannel.STABLE)
        assertEquals(listOf("v0.3.9+tv"), selected.map { it.tagName })
        assertEquals(listOf("Omnia-TV-0.3.9.apk"), selected.single().assets.map { it.name })
    }

    @Test
    fun `stable channel excludes GitHub and tag prereleases`() {
        val releases = listOf(
            release("1.1.0-beta.2", prerelease = true),
            release("1.1.0-beta.1"),
            release("1.0.1"),
            release("1.0.0")
        )

        val selected = ReleaseSelector.eligibleReleases(releases, UpdateChannel.STABLE)

        assertEquals(listOf("1.0.1", "1.0.0"), selected.map { it.tagName })
    }

    @Test
    fun `beta channel prefers final promotion over its betas`() {
        val releases = listOf(
            release("1.1.0-beta.10", prerelease = true),
            release("1.1.0"),
            release("1.1.0-beta.9", prerelease = true)
        )

        val selected = ReleaseSelector.eligibleReleases(releases, UpdateChannel.BETA)

        assertEquals(
            listOf("1.1.0", "1.1.0-beta.10", "1.1.0-beta.9"),
            selected.map { it.tagName }
        )
    }

    @Test
    fun `legacy release title marks beta without tag suffix`() {
        val releases = listOf(
            release(tag = "0.7.18", name = "Beta 0.7.18 Hotfix"),
            release(tag = "0.7.17")
        )

        val selected = ReleaseSelector.eligibleReleases(releases, UpdateChannel.STABLE)

        assertEquals(listOf("0.7.17"), selected.map { it.tagName })
    }

    @Test
    fun `drafts and invalid tags are excluded`() {
        val releases = listOf(
            release("1.2.0", draft = true),
            release("nightly"),
            release("1.1.0")
        )

        val selected = ReleaseSelector.eligibleReleases(releases, UpdateChannel.BETA)

        assertEquals(listOf("1.1.0"), selected.map { it.tagName })
    }

    private fun release(
        tag: String,
        name: String = tag,
        draft: Boolean = false,
        prerelease: Boolean = false
    ) = GitHubReleaseDto(
        tagName = tag,
        name = name,
        draft = draft,
        prerelease = prerelease
    )
}

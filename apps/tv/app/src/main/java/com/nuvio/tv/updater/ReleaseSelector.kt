package com.nuvio.tv.updater

import com.nuvio.tv.data.remote.dto.GitHubReleaseDto

internal object ReleaseSelector {
    fun forTv(releases: List<GitHubReleaseDto>): List<GitHubReleaseDto> = releases
        .map { release -> release.copy(assets = release.assets.filter {
            it.name.startsWith("Omnia-TV-") && it.name.endsWith(".apk", ignoreCase = true)
        }) }.filter { it.assets.isNotEmpty() }

    private val prereleaseNamePattern = Regex(
        "(?:^|[\\s._-])(alpha|beta|rc|preview)(?:[\\s._-]|$)",
        RegexOption.IGNORE_CASE
    )

    fun eligibleReleases(
        releases: List<GitHubReleaseDto>,
        channel: UpdateChannel
    ): List<GitHubReleaseDto> = releases
        .asSequence()
        .filterNot(GitHubReleaseDto::draft)
        .mapNotNull { release ->
            val version = releaseVersion(release) ?: return@mapNotNull null
            ReleaseCandidate(
                release = release,
                version = version,
                prerelease = isPrerelease(release, version)
            )
        }
        .filter { candidate -> channel == UpdateChannel.BETA || !candidate.prerelease }
        .sortedByDescending(ReleaseCandidate::version)
        .map(ReleaseCandidate::release)
        .toList()

    private fun releaseVersion(release: GitHubReleaseDto): SemanticVersion? =
        VersionUtils.parse(release.tagName) ?: VersionUtils.parse(release.name)

    private fun isPrerelease(
        release: GitHubReleaseDto,
        version: SemanticVersion
    ): Boolean = release.prerelease ||
        version.prerelease.isNotEmpty() ||
        prereleaseNamePattern.containsMatchIn(release.name.orEmpty())

    private data class ReleaseCandidate(
        val release: GitHubReleaseDto,
        val version: SemanticVersion,
        val prerelease: Boolean
    )
}

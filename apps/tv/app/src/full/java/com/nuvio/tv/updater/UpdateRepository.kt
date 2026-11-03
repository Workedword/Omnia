package com.nuvio.tv.updater

import com.nuvio.tv.BuildConfig
import com.nuvio.tv.data.remote.api.GitHubReleaseApi
import com.nuvio.tv.updater.model.AppUpdate
import javax.inject.Inject
import javax.inject.Singleton

internal class NoEligibleUpdateException(channel: UpdateChannel) :
    IllegalStateException("No compatible APK release found for ${channel.storedValue} channel")

@Singleton
class UpdateRepository @Inject constructor(
    private val gitHubReleaseApi: GitHubReleaseApi
) {

    suspend fun getLatestUpdate(channel: UpdateChannel): Result<AppUpdate> {
        return runCatching {
            val owner = BuildConfig.GITHUB_OWNER
            val repo = BuildConfig.GITHUB_REPO

            // Both platforms share the release repository; latest may belong to the other app.
            val response = gitHubReleaseApi.getReleases(owner = owner, repo = repo)
            if (!response.isSuccessful) error("Update service error: ${response.code()}")
            val releases = ReleaseSelector.forTv(response.body() ?: error("Empty update response"))
            val releaseWithAsset = ReleaseSelector
                .eligibleReleases(releases, channel)
                .firstNotNullOfOrNull { release ->
                    AbiSelector.chooseBestApkAsset(release.assets)?.let { asset ->
                        release to asset
                    }
                }
                ?: throw NoEligibleUpdateException(channel)
            val (dto, asset) = releaseWithAsset

            val tag = dto.tagName?.takeIf { it.isNotBlank() }
                ?: dto.name?.takeIf { it.isNotBlank() }
                ?: error("Release has no tag/name")

            AppUpdate(
                tag = tag,
                title = dto.name?.takeIf { it.isNotBlank() } ?: tag,
                notes = dto.body.orEmpty(),
                releaseUrl = dto.htmlUrl,
                assetName = asset.name,
                assetUrl = asset.browserDownloadUrl,
                assetSizeBytes = asset.size
            )
        }
    }
}

<div align="center">

<img src="../assets/omnia-logo.svg" alt="Omnia" width="360">

# Make Omnia yours

Catalogs, collections, subtitles, and community sources.

[Browse & configure](https://omnia.161.97.128.244.sslip.io/community) · [Get Omnia](https://github.com/Workedword/Omnia/releases) · [Submit your add-on](https://github.com/Workedword/Omnia/issues/new?template=addon-submission.yml)

</div>

## Default catalog

**Nuvio Catalog Addon** provides 27 discovery categories: trending, popular, airing today, critically acclaimed, new and upcoming, year and language browsing, Netflix, Disney+, Prime Video, international titles, independent films, limited series, documentaries, and family viewing.

[Catalog manifest](https://catalog.nuvio.tv/manifest.json) · [Configure](https://catalog.nuvio.tv/configure)

## Optional Omnia add-ons

| Add-on | Discover | Setup |
| --- | --- | --- |
| **Omnia Catalogs** | Choose and reorder movie, show, genre, and collection rows. | [Configure](https://omnia.161.97.128.244.sslip.io/catalogs/configure) |
| **Omnia India** | Hindi films, Indian cinema, TV shows, and web-series discovery. | [Configure](https://omnia.161.97.128.244.sslip.io/catalogs/india/configure) |
| **Omnia India Providers** | Curated setup for nine externally maintained Hindi movie and show providers. Separate provider-repository installation; playback unverified. | [Configure](https://omnia.161.97.128.244.sslip.io/catalogs/india/providers/configure) |

Catalogs organize titles and their metadata. Playback comes from the stream providers you choose.

## Community directory

Independent projects are optional. Their developers maintain availability, accounts, pricing, and content. Listing does not guarantee playback or compatibility on every device.

| Project | Category | How to use |
| --- | --- | --- |
| [Torrentio](https://torrentio.strem.fun/configure) | Playback providers | Configure filters and your optional debrid service, then add the generated manifest. Keep personalized links private. |
| [Comet](https://comet.elfhosted.com/configure) | Playback providers | Configure your selected instance and source service. Instance limits and requirements vary. |
| [MediaFusion](https://mediafusion.elfhosted.com/configure) | Playback providers | Configure sources, optional debrid services and discovery preferences, then add the generated manifest. |
| [PlavioHD](https://hd.plavio.site/configure) | Media add-on | Configure the provider and install its generated manifest. |
| [Sports Streams](https://sports.highfly.dev/configure) | Live sports | Configure your leagues; provider verification or paid features may apply. |
| [IPTV](https://ip-tv.hatip.dev/configure) | Channel catalogs | Choose countries and install the generated manifest. |
| [Nuvio Sports](https://nuviosports.xyz/configure) | Live sports | Use the developer’s configuration page. |
| [PenguPlay](https://pengu.uk/) | Provider service | Follow its developer’s account and setup requirements. |
| [Sports Replays](https://sports-replay.michaelrobgrove.workers.dev/configure) | Sports replays | Previously unreachable; availability and playback unverified. |
| [CNCVerse Bridge](https://cncverse.dpdns.org/) | Provider bridge | Configure your own movie, show, Indian-language, live TV and sports profile. Keep its generated manifest private. Playback unverified. |
| [StreamRadar India](https://streamradar.bricksgenius.com/configure) | Indian OTT catalogs | Choose services, their order, Trending, Just In, Coming Soon, and poster style. No account required. Public manifest checked; playback unverified. |

## Install on your device

- **Android / iPhone (0.4.9 or later):** open **Settings → Content & Discovery → Catalogs & add-ons → Community Add-ons**. Choose **Providers** for Torrentio, Comet, or MediaFusion, or **Live TV & Sports** for channel and sports entries.
- Select **Setup & details**, configure the service, then add its generated manifest URL in Omnia. Entries with a ready-to-install public manifest also show an Install button. Collection JSON and executable plugins use separate import paths.
- **Fire Stick / Android TV:** configure on your phone, then use your Omnia account’s add-on sync where supported, or enter the manifest URL on the TV.
- Keep access tokens and personalized manifest URLs private. Never include them in an issue or pull request.

## Build for the community

Developers can [submit an add-on](https://github.com/Workedword/Omnia/issues/new?template=addon-submission.yml) for review or propose a directory correction in a pull request. You do not need access to Omnia’s private source repository.

Provide a public setup URL, the integration format, supported resources and devices, account/cost requirements, a support contact, and any source/license information. Submissions are reviewed before listing; they are never automatically executed or installed.

Useful integration formats include HTTPS JSON manifests for catalogs, metadata, streams, and subtitles; collection-layout JSON; and supported provider repositories. Clearly distinguish these formats rather than presenting every URL as an installable manifest.

Only share content and services you are authorized to distribute. Required third-party notices remain with their respective projects.

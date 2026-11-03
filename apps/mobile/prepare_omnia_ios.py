"""Apply Omnia's iOS identity after prepare_omnia.py; no signing secrets required."""
from pathlib import Path
import json
import plistlib
import re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ios = ROOT / 'iosApp'

def replace(path, old, new):
    text = path.read_text(encoding='utf-8')
    if old not in text and new not in text:
        raise AssertionError(f'Unexpected upstream source: {path.name}: {old}')
    path.write_text(text.replace(old, new), encoding='utf-8')

config = ios / 'Configuration/Config.xcconfig'
replace(config, 'PRODUCT_NAME=Nuvio', 'PRODUCT_NAME=Omnia')
replace(config, 'PRODUCT_BUNDLE_IDENTIFIER=com.nuvio.app.Nuvio$(TEAM_ID)',
        'PRODUCT_BUNDLE_IDENTIFIER=io.github.workedword.omnia')
project = ios / 'iosApp.xcodeproj/project.pbxproj'
text = project.read_text(encoding='utf-8')
text = re.sub(r'DEVELOPMENT_TEAM = [^;]*;', 'DEVELOPMENT_TEAM = "";', text)
text = text.replace('com.nuvio.app.DownloadsWidgetExtension', 'io.github.workedword.omnia.DownloadsWidgetExtension')
text = text.replace('com.nuvio.media.DownloadsWidgetExtension', 'io.github.workedword.omnia.DownloadsWidgetExtension')
text = text.replace('PRODUCT_BUNDLE_IDENTIFIER = com.nuvio.app;', 'PRODUCT_BUNDLE_IDENTIFIER = io.github.workedword.omnia;')
text = text.replace('PRODUCT_BUNDLE_IDENTIFIER = com.nuvio.media;', 'PRODUCT_BUNDLE_IDENTIFIER = io.github.workedword.omnia;')
text = text.replace('com.nuvio.SubtitleTests', 'io.github.workedword.omnia.SubtitleTests')
text = text.replace('Nuvio.app', 'Omnia.app').replace('/Omnia.app/Nuvio', '/Omnia.app/Omnia')
project.write_text(text, encoding='utf-8')
for scheme in (ios / 'iosApp.xcodeproj/xcshareddata/xcschemes').glob('*.xcscheme'):
    scheme.write_text(scheme.read_text().replace('Nuvio.app', 'Omnia.app'), encoding='utf-8')

info_path = ios / 'iosApp/Info.plist'
info = plistlib.loads(info_path.read_bytes())
info['CFBundleDisplayName'] = 'Omnia'
info['NSLocalNetworkUsageDescription'] = 'Omnia connects to media servers on your local network.'
info['CFBundleURLTypes'][0]['CFBundleURLName'] = 'io.github.workedword.omnia.auth'
schemes = info['CFBundleURLTypes'][0]['CFBundleURLSchemes']
if 'omnia' not in schemes:
    schemes.insert(0, 'omnia')
info_path.write_bytes(plistlib.dumps(info, sort_keys=False))

# Use the same Compose navigation and screens as Android. Keep the native
# player/PiP host and scene lifecycle around it.
content_view = ios / 'iosApp/ContentView.swift'
replace(content_view, '''            if #available(iOS 16.0, *) {
                NativeNavContentView()
                    .accessibilityHidden(systemUI.pictureInPictureMessage != nil)
                    .allowsHitTesting(systemUI.pictureInPictureMessage == nil)
            } else {
                ComposeView()
                    .ignoresSafeArea(.all)
                    .accessibilityHidden(systemUI.pictureInPictureMessage != nil)
                    .allowsHitTesting(systemUI.pictureInPictureMessage == nil)
            }''', '''            ComposeView()
                .ignoresSafeArea(.all)
                .accessibilityHidden(systemUI.pictureInPictureMessage != nil)
                .allowsHitTesting(systemUI.pictureInPictureMessage == nil)''')

policy = ROOT / 'composeApp/src/iosFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.ios.kt'
replace(policy, 'supportersContributorsPageEnabled: Boolean = true', 'supportersContributorsPageEnabled: Boolean = false')
replace(policy, 'donationActionsEnabled: Boolean = true', 'donationActionsEnabled: Boolean = false')
bridge = ROOT / 'composeApp/src/commonMain/kotlin/com/nuvio/app/core/deeplink/AppUrlBridge.kt'
replace(bridge, 'if (scheme != "nuvio") return null', 'if (scheme != "nuvio" && scheme != "omnia") return null')

# Rasterize the existing Omnia vector mark into Apple's required opaque icons.
# Geometry matches omnia_mark.xml: radius 26, stroke 11, triangle (34,28)-(52,40)-(34,52).
colors = {'AppIcon':'#FF454F', 'AppIconArcticBlue':'#69C9FF', 'AppIconEmerald':'#43D9A3',
          'AppIconRoseGold':'#E6A6B5', 'AppIconCopper':'#CF8658', 'AppIconGraphite':'#AAB4C4'}
scale = 2048 / 80
for name, color in colors.items():
    image = Image.new('RGB', (2048, 2048), '#09090D')
    draw = ImageDraw.Draw(image)
    draw.ellipse(tuple(round(v*scale) for v in (8.5,8.5,71.5,71.5)), fill=color)
    draw.ellipse(tuple(round(v*scale) for v in (19.5,19.5,60.5,60.5)), fill='#09090D')
    draw.polygon([(round(x*scale),round(y*scale)) for x,y in [(34,28),(52,40),(34,52)]],fill=color)
    directory = ios / f'iosApp/Assets.xcassets/{name}.appiconset'
    image.resize((1024,1024), Image.Resampling.LANCZOS).save(directory/'app-icon-1024.png')
    (directory/'Contents.json').write_text(json.dumps({'images':[{'filename':'app-icon-1024.png','idiom':'universal','platform':'ios','size':'1024x1024'}],'info':{'author':'xcode','version':1}},indent=2))

script = ROOT / 'scripts/build-ios-ipa.sh'
text = script.read_text().replace('Nuvio.app', 'Omnia.app').replace('nuvio-${version}', 'Omnia-${version}')
script.write_text(text, encoding='utf-8')
assert '8QBDZ766S3' not in project.read_text()
assert 'PRODUCT_BUNDLE_IDENTIFIER = com.nuvio.' not in project.read_text()
assert plistlib.loads(info_path.read_bytes())['CFBundleDisplayName'] == 'Omnia'
print('Omnia iOS identity, six opaque icons, private account service, and IPA packaging prepared.')

"""Apply the Omnia browser/device sign-in overlay after the current native preparation.

Only account-flow files are touched. Use --check first. No signing, version,
network-security, player or settings source is replaced by this overlay.
"""
import argparse,json
from pathlib import Path

ASSETS=Path(__file__).resolve().parent/'native'

def prepare(root,platform):
    changes={}
    def text(name):return changes.get(name,(root/name).read_text(encoding='utf-8'))
    def replace(name,old,new):
        source=text(name)
        if new in source:return
        if source.count(old)!=1:raise ValueError('Unexpected source anchor: '+name)
        changes[name]=source.replace(old,new,1)
    if platform=='mobile':
        base='composeApp/src/commonMain/kotlin/com/nuvio/app/';tests='composeApp/src/commonTest/kotlin/com/nuvio/app/'
        for name,sub in [('OmniaBrowserSignIn.kt','features/auth/'),('OmniaAccountPortalLinks.kt','features/auth/'),('OmniaDeviceLoginUrl.kt','core/auth/')]:changes[base+sub+name]=(ASSETS/'mobile'/name).read_text(encoding='utf-8')
        changes[tests+'core/auth/OmniaDeviceLoginUrlTest.kt']=(ASSETS/'mobile/OmniaDeviceLoginUrlTest.kt').read_text(encoding='utf-8')
        name=base+'core/auth/DeviceLinkAuthRepository.kt'
        replace(name,'    fun start() {','    fun start(provider: String? = null) {')
        replace(name,'log.w(error) { "Device link sign-in stopped" }','log.w { "Device link sign-in stopped" }')
        replace(name,'log.w(error) { "Device link sign-in failed" }','log.w { "Device link sign-in failed" }')
        replace(name,'verificationUrl = session.verificationUriComplete,\n                )\n                pollAndComplete(session, nonce)', 'verificationUrl = if (OmniaDeviceLoginUrl.isOmnia(configuration.backendUrl)) OmniaDeviceLoginUrl.create(session.userCode, provider) else session.verificationUriComplete,\n                )\n                pollAndComplete(session, nonce)')
        # The completing state must preserve the already chosen URL; no provider is lost.
        source=text(name);needle='verificationUrl = session.verificationUriComplete,'
        if needle in source:changes[name]=source.replace(needle,'verificationUrl = (_state.value as? DeviceLinkAuthState.Waiting)?.verificationUrl ?: session.verificationUriComplete,')
        replace(name,'val user = result.user ?: SupabaseProvider.client.auth.retrieveUser(result.accessToken)','val user = SupabaseProvider.client.auth.retrieveUser(result.accessToken)')
        replace(name,'            SupabaseProvider.client.auth.importSession(','            AuthStorage.clearAnonymousUserId()\n            SupabaseProvider.client.auth.importSession(')
        replace(name,'if (isCustom) "${backendUrl.trimEnd(\'/\')}/link" else officialLinkUrl','if (OmniaDeviceLoginUrl.isOmnia(backendUrl)) OmniaDeviceLoginUrl.BASE else if (isCustom) "${backendUrl.trimEnd(\'/\')}/link" else officialLinkUrl')
        name='iosApp/iosApp/Info.plist'
        if '<string>omnia</string>' not in text(name):replace(name,'<string>nuvio</string>','<string>omnia</string>\n\t\t\t\t<string>nuvio</string>')
    else:
        base='app/src/main/java/com/nuvio/tv/ui/screens/account/';tests='app/src/test/java/com/nuvio/tv/ui/screens/account/'
        for name in ['OmniaTvBrowserSignIn.kt','OmniaTvAccountPortalLink.kt','OmniaDeviceLoginUrl.kt']:changes[base+name]=(ASSETS/'tv'/name).read_text(encoding='utf-8')
        changes[tests+'OmniaDeviceLoginUrlTest.kt']=(ASSETS/'tv/OmniaDeviceLoginUrlTest.kt').read_text(encoding='utf-8')
        changes['app/src/main/java/com/nuvio/tv/core/auth/OmniaAuthLogPrivacy.kt']=(ASSETS/'tv/OmniaAuthLogPrivacy.kt').read_text(encoding='utf-8')
        changes['app/src/test/java/com/nuvio/tv/core/auth/OmniaAuthLogPrivacyTest.kt']=(ASSETS/'tv/OmniaAuthLogPrivacyTest.kt').read_text(encoding='utf-8')
        changes['app/src/main/java/com/nuvio/tv/core/auth/OmniaDeviceSessionImport.kt']=(ASSETS/'tv/OmniaDeviceSessionImport.kt').read_text(encoding='utf-8')
        changes['app/src/test/java/com/nuvio/tv/core/auth/OmniaDeviceSessionImportTest.kt']=(ASSETS/'tv/OmniaDeviceSessionImportTest.kt').read_text(encoding='utf-8')
        for relative in ['app/src/main/java/com/nuvio/tv/core/auth/AuthManager.kt',base+'AccountViewModel.kt']:
            replace(relative,'import android.util.Log','import com.nuvio.tv.core.auth.OmniaAuthLog as Log')
        relative='app/src/main/java/com/nuvio/tv/core/auth/AuthManager.kt'
        replace(relative,'            auth.importTokenResponse(result)\n            Log.d(TAG, "$trace exchangeTvLoginSession imported', '            importActiveDeviceSession { auth.importTokenResponse(result) }\n            Log.d(TAG, "$trace exchangeTvLoginSession imported')
        replace(relative,'        } catch (e: Exception) {\n            Log.e(TAG, "$trace exchangeTvLoginSession failed', '        } catch (e: Exception) {\n            if (e is CancellationException) throw e\n            Log.e(TAG, "$trace exchangeTvLoginSession failed')
        relative='app/src/main/java/com/nuvio/tv/core/auth/diagnostics/AuthDiagnostics.kt'
        replace(relative,'        val payload = synchronized(lock) {','''        if (!com.nuvio.tv.core.auth.authDiagnosticUploadsAllowed(serverConfiguration.backendUrl, BuildConfig.PLAYBACK_REPORTS_BASE_URL)) {
            synchronized(lock) { finished = true; events.clear(); rawLogs.clear() }
            return Result.success("diagnostics-disabled")
        }
        val payload = synchronized(lock) {''')
        name=base+'AccountViewModel.kt'
        replace(name,'    private var qrLoginExchangeInFlight: Boolean = false','    private var qrLoginExchangeInFlight: Boolean = false\n    private var qrLoginExchangeJob: Job? = null')
        replace(name,'    fun exchangeQrLogin() {\n        viewModelScope.launch {','    fun exchangeQrLogin() {\n        if (qrLoginExchangeJob?.isActive == true) return\n        qrLoginExchangeJob = viewModelScope.launch {')
        for signature in ['fun signIn(email: String, password: String)', 'fun signUp(email: String, password: String)', 'fun signOut()']:
            replace(name,'    '+signature+' {\n        viewModelScope.launch {','    '+signature+' {\n        clearQrLoginSession()\n        viewModelScope.launch {')
        replace(name,'    fun startQrLogin() {','''    private var omniaBrowserProvider: String? = null
    internal fun startOmniaBrowserSignIn(provider: String) {
        if (!hasOmniaAccountPortal || provider !in setOf("google", "discord", "email")) return
        omniaBrowserProvider = provider
        startQrLogin()
    }

    fun startQrLogin() {''')
        replace(name,'if (requiresServerSetup || !serverConfiguration.capabilities.tvLogin) {','if (requiresServerSetup || (!serverConfiguration.capabilities.tvLogin && !hasOmniaAccountPortal)) {')
        replace(name,'redirectBaseUrl = serverConfiguration.deviceLoginWebBaseUrl.orEmpty(),','redirectBaseUrl = if (hasOmniaAccountPortal) OmniaDeviceLoginUrl.BASE else serverConfiguration.deviceLoginWebBaseUrl.orEmpty(),')
        replace(name,'val qrBitmap = withContext(Dispatchers.Default) {','val qrBitmap = if (hasOmniaAccountPortal) null else withContext(Dispatchers.Default) {')
        replace(name,'qrLoginUrl = result.verificationUriComplete,','qrLoginUrl = if (hasOmniaAccountPortal) OmniaDeviceLoginUrl.create(result.userCode, omniaBrowserProvider) else result.verificationUriComplete,')
        replace(name,'    fun clearQrLoginSession() {','    fun clearQrLoginSession() {\n        omniaBrowserProvider = null')
        replace(name,'    fun clearQrLoginSession() {\n        omniaBrowserProvider = null','    fun clearQrLoginSession() {\n        omniaBrowserProvider = null\n        qrLoginExchangeJob?.cancel()\n        qrLoginExchangeJob = null')
    return changes

if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('--root',required=True);args.add_argument('--platform',choices=['mobile','tv'],required=True);args.add_argument('--check',action='store_true');options=args.parse_args();root=Path(options.root).resolve();changes=prepare(root,options.platform)
    for name,source in changes.items():
        path=root/name
        if root not in path.resolve().parents:raise ValueError('Path outside native checkout')
        if not options.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source,encoding='utf-8',newline='\n')
    print(json.dumps({'platform':options.platform,'checkedOnly':options.check,'files':sorted(changes),'signingAndPackageIdentityChanged':False}))

"""Create an isolated XCUITest target. No credentials or production fixtures."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
tests = root / 'iosApp/OmniaUITests'
tests.mkdir(exist_ok=True)
(tests / 'OmniaUITests.swift').write_text(r'''
import XCTest

final class OmniaUITests: XCTestCase {
    let app = XCUIApplication(bundleIdentifier: "io.github.workedword.omnia")
    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
    }
    override func tearDownWithError() throws {
        if app.state == .runningForeground { capture("test-end-" + name) }
        app.terminate()
    }
    func capture(_ name: String) {
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = name
        shot.lifetime = .keepAlways
        add(shot)
        let tree = XCTAttachment(string: app.debugDescription)
        tree.name = name + "-accessibility"
        tree.lifetime = .keepAlways
        add(tree)
    }
    func item(_ title: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", title)).firstMatch
    }
    func tap(_ title: String, scroll: Bool = false) {
        var node = item(title)
        if scroll {
            for _ in 0..<7 {
                if node.exists && node.isHittable { break }
                app.swipeUp()
                node = item(title)
            }
        }
        XCTAssertTrue(node.waitForExistence(timeout: 20), "Missing control: \(title)")
        XCTAssertTrue(node.isHittable, "Unreachable control: \(title)")
        node.tap()
    }
    func enterGuest() {
        if item("Continue Without Account").waitForExistence(timeout: 15) {
            tap("Continue Without Account")
        }
        if item("Guest").waitForExistence(timeout: 8) { tap("Guest") }
        XCTAssertTrue(item("Home").waitForExistence(timeout: 30))
    }
    func openSettings() {
        // The shared mobile navigation opens settings through the profile
        // avatar. This isolated guest fixture is displayed as G.
        let profile = app.buttons["G"].firstMatch
        XCTAssertTrue(profile.waitForExistence(timeout: 15))
        profile.tap()
    }
    func testSharedNavigationAndSettings() {
        capture("startup")
        enterGuest()
        capture("home")
        tap("Discover")
        let discoverHeading = app.staticTexts.matching(NSPredicate(format: "label == %@", "Discover"))
        XCTAssertTrue(discoverHeading.firstMatch.waitForExistence(timeout: 10))
        let visibleHeadings = discoverHeading.allElementsBoundByIndex.filter { $0.frame.minY < app.frame.height * 0.7 && $0.frame.height > 0 }
        XCTAssertEqual(visibleHeadings.count, 1, "Discover heading must appear once above the filters")
        capture("search")
        tap("Library")
        capture("library")
        openSettings()
        capture("settings")
        tap("Account & Profiles", scroll: true)
        XCTAssertTrue(item("Switch Profile").waitForExistence(timeout: 10))
        capture("account-profiles")
        XCTAssertEqual(app.state, .runningForeground)
    }
    func testSettingsFooterBranding() {
        enterGuest()
        openSettings()
        let footer = item("Version 0.4.24 (30)")
        for _ in 0..<14 {
            if footer.exists && footer.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(footer.exists && footer.isHittable, "Settings footer was not reached")
        XCTAssertEqual(app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS[c] %@", "Tapframe")).count, 0)
        capture("omnia-settings-footer")
    }
    func testCatalogSettings() {
        enterGuest()
        openSettings()
        tap("Content", scroll: true)
        capture("content-discovery")
        tap("Choose catalogs", scroll: true)
        XCTAssertTrue(item("Search catalogs or providers").waitForExistence(timeout: 15))
        capture("catalog-filter")
        XCTAssertEqual(app.state, .runningForeground)
    }
    func testCommunityDirectoryIsVisible() {
        enterGuest()
        openSettings()
        tap("Add-ons", scroll: true)
        for _ in 0..<12 { app.swipeDown() }
        tap("Discover add-ons", scroll: true)
        XCTAssertTrue(item("DISCOVER ADD-ONS").waitForExistence(timeout: 20))
        XCTAssertTrue(item("Hide directory").exists)
        XCTAssertFalse(item("Check catalog endpoints").exists)
        tap("Omnia Official", scroll: true)
        let availableCard = item("Available add-on: Omnia Catalogs")
        XCTAssertTrue(availableCard.waitForExistence(timeout: 15))
        tap("Add Omnia Catalogs to Omnia, Add to Omnia", scroll: true)
        for _ in 0..<15 {
            if !availableCard.exists { break }
            Thread.sleep(forTimeInterval: 1)
        }
        XCTAssertFalse(availableCard.exists, "Installed add-on must leave the available directory")
        capture("installed-addon-hidden-from-directory")
        for _ in 0..<8 { app.swipeDown() }
        tap("Community", scroll: true)
        tap("Catalogs", scroll: true)
        tap("Collections", scroll: true)
        tap("Providers", scroll: true)
        tap("Live TV & Sports", scroll: true)
        XCTAssertTrue(item("IPTV").waitForExistence(timeout: 20))
        XCTAssertTrue(item("Sports Streams").exists)
        capture("community-live-tv-and-sports")
    }
    @available(iOS 16.4, *)
    func testAddonDeepLinksAndPlayback() {
        enterGuest()
        for number in 1...8 {
            app.open(URL(string: "omnia://omnia.161.97.128.244.sslip.io/downloads/qa-regression/\(number)/manifest.json")!)
            if item("Current Add-ons").exists && item("Current Add-ons").isHittable { tap("Current Add-ons") }
            // Manifest deep links install directly; there is no confirmation
            // dialog in the shared Android/iOS handler.
            let installed = item(String(format: "Omnia QA %02d", number))
            if !installed.waitForExistence(timeout: 5) {
                for _ in 0..<12 {
                    if installed.exists { break }
                    app.swipeUp()
                }
            }
            XCTAssertTrue(installed.waitForExistence(timeout: 15))
        }
        capture("eight-installed-addons")
        app.swipeUp()
        app.swipeUp()
        capture("addons-scrolled")
        XCTAssertTrue(item("Omnia QA 08").exists)
        app.open(URL(string: "omnia://detail/movie/omniaqa%3Atest")!)
        capture("playback-details")
        let castCredit = item("Omnia QA Actor One, Omnia QA Actor Two")
        for _ in 0..<8 {
            if castCredit.exists && castCredit.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(castCredit.waitForExistence(timeout: 15), "Inline actor names are missing")
        let directorCredit = item("Omnia QA Director")
        XCTAssertTrue(directorCredit.exists, "Director credit is missing")
        XCTAssertGreaterThan(castCredit.frame.minY, directorCredit.frame.minY, "Actor names must appear below the director")
        capture("inline-cast-credits")
        for _ in 0..<6 { app.swipeDown() }
        tap("Play")
        let source = app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Local test clip")).firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 20))
        source.tap()
        // Playback controls auto-hide. Reveal them in the blank upper-middle
        // player area; do not confuse hidden controls with a stalled stream.
        if !item("Pause").exists {
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.25)).tap()
        }
        XCTAssertTrue(item("Pause").waitForExistence(timeout: 20), "Player did not enter playing state")
        capture("playing-legal-test-clip")
        tap("Pause")
        XCTAssertTrue(item("Play").waitForExistence(timeout: 5))
        capture("paused-test-clip")
        tap("Play")
        XCTAssertTrue(item("Pause").waitForExistence(timeout: 5))
        XCTAssertEqual(app.state, .runningForeground)
    }
}
''', encoding='utf-8')
ruby = r'''
require 'xcodeproj'
project = Xcodeproj::Project.open('iosApp/iosApp.xcodeproj')
app = project.targets.find { |t| t.name == 'iosApp' }
raise 'Missing application target' unless app
target = project.targets.find { |t| t.name == 'OmniaUITests' }
unless target
  target = project.new_target(:ui_test_bundle, 'OmniaUITests', :ios, '16.1')
  target.add_dependency(app)
  group = project.main_group.new_group('OmniaUITests', 'OmniaUITests')
  target.source_build_phase.add_file_reference(group.new_file('OmniaUITests.swift'))
end
target.build_configurations.each do |config|
  config.build_settings.merge!({
    'PRODUCT_BUNDLE_IDENTIFIER' => 'io.github.workedword.omnia.uitests',
    'PRODUCT_NAME' => 'OmniaUITests',
    'PRODUCT_MODULE_NAME' => 'OmniaUITests',
    'GENERATE_INFOPLIST_FILE' => 'YES',
    'SWIFT_VERSION' => '5.0',
    'TEST_TARGET_NAME' => 'iosApp',
    'CODE_SIGNING_ALLOWED' => 'NO',
    'TARGETED_DEVICE_FAMILY' => '1,2'
  })
end
project.save
scheme = Xcodeproj::XCScheme.new
scheme.add_build_target(app)
scheme.add_test_target(target)
scheme.set_launch_target(app)
scheme.save_as('iosApp/iosApp.xcodeproj', 'OmniaUITests', true)
'''
subprocess.run(['ruby', '-e', ruby], cwd=root, check=True)
print('Prepared credential-free iPhone UI tests.')

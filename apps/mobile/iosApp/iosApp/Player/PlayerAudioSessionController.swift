import AVFoundation
import CallKit

/// Call observation/UI callbacks stay on main. Potentially blocking audio-session IPC
/// runs in order on its own serial queue, including deactivation after a player closes.
final class PlayerAudioSessionController: NSObject, CXCallObserverDelegate {
    private let callObserver = CXCallObserver()
    private static let audioQueue = DispatchQueue(label: "io.omnia.audio-session", qos: .userInitiated)
    // Only audioQueue reads/writes this set. Closing a preview must not deactivate
    // the shared audio session underneath a newly opened full-screen player.
    private static var activeOwners = Set<UUID>()
    private let audioOwner = UUID()
    private var isActive = false
    private var generation: UInt64 = 0
    private var interruptionObserver: NSObjectProtocol?
    var onConfigurationChanged: (() -> Void)?

    func activate() {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.activate() }
            return
        }
        if !isActive {
            isActive = true
            callObserver.setDelegate(self, queue: .main)
            interruptionObserver = NotificationCenter.default.addObserver(
                forName: AVAudioSession.interruptionNotification,
                object: AVAudioSession.sharedInstance(), queue: .main
            ) { [weak self] notification in
                guard let self, self.isActive,
                      let value = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                      AVAudioSession.InterruptionType(rawValue: value) == .ended else { return }
                self.configure()
            }
        }
        configure()
    }

    func deactivate() {
        guard Thread.isMainThread else {
            DispatchQueue.main.async { [weak self] in self?.deactivate() }
            return
        }
        guard isActive else { return }
        isActive = false
        generation &+= 1
        callObserver.setDelegate(nil, queue: nil)
        if let interruptionObserver {
            NotificationCenter.default.removeObserver(interruptionObserver)
            self.interruptionObserver = nil
        }
        let owner = audioOwner
        Self.audioQueue.async {
            Self.activeOwners.remove(owner)
            guard Self.activeOwners.isEmpty else { return }
            do {
                try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            } catch {
                print("[NowPlaying] Could not deactivate audio session")
            }
        }
    }

    func callObserver(_ callObserver: CXCallObserver, callChanged call: CXCall) {
        guard isActive else { return }
        let hasCall = !call.hasEnded || callObserver.calls.contains {
            $0.uuid != call.uuid && !$0.hasEnded
        }
        configure(hasCall: hasCall)
    }

    private func configure(hasCall: Bool? = nil) {
        guard isActive else { return }
        generation &+= 1
        let requestGeneration = generation
        let mixing = hasCall ?? callObserver.calls.contains { !$0.hasEnded }
        let options: AVAudioSession.CategoryOptions = mixing ? [.mixWithOthers] : []
        let owner = audioOwner
        Self.audioQueue.async { [weak self] in
            Self.activeOwners.insert(owner)
            let session = AVAudioSession.sharedInstance()
            do {
                if session.category != .playback || session.mode != .moviePlayback || session.categoryOptions != options {
                    try session.setCategory(.playback, mode: .moviePlayback, options: options)
                }
                try session.setActive(true)
                DispatchQueue.main.async { [weak self] in
                    guard let self, self.isActive, self.generation == requestGeneration else { return }
                    self.onConfigurationChanged?()
                }
            } catch {
                print("[NowPlaying] Could not activate audio session")
            }
        }
    }

    deinit {
        if let interruptionObserver { NotificationCenter.default.removeObserver(interruptionObserver) }
    }
}

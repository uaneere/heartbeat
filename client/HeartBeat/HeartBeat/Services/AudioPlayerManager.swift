import AVFoundation
import Foundation

enum PlaybackSegmentKind: Equatable {
    case fragment(index: Int)
    case transition
    case loopBridge
}

@Observable
@MainActor
final class AudioPlayerManager: NSObject {
    private var queuePlayer: AVQueuePlayer?
    private var timeObserver: Any?
    private var currentItemObservation: NSKeyValueObservation?
    private var itemKinds: [ObjectIdentifier: PlaybackSegmentKind] = [:]
    private var statusObservations: [ObjectIdentifier: NSKeyValueObservation] = [:]

    private var onNearEnd: (() -> Void)?
    private var onFragmentStarted: ((Int) -> Void)?
    private var didTriggerNearEnd = false
    private var currentFragmentIndex: Int?
    private var prefetchedFragmentIndex: Int?
    private var loopBridgeQueuedForIndex: Int?

    var isPlaying = false
    var playbackError: String?

    var hasNextFragmentQueued: Bool {
        prefetchedFragmentIndex != nil
    }

    func configure(
        onNearEnd: @escaping () -> Void,
        onFragmentStarted: @escaping (Int) -> Void
    ) {
        self.onNearEnd = onNearEnd
        self.onFragmentStarted = onFragmentStarted
    }

    func play(fragment: MusicFragment, onBuffered: (() -> Void)? = nil) {
        stopInternal()
        activateSession()

        let player = AVQueuePlayer()
        player.actionAtItemEnd = .advance
        queuePlayer = player

        currentItemObservation = player.observe(\.currentItem, options: [.new]) { [weak self] player, _ in
            Task { @MainActor in
                self?.handleCurrentItemChanged(player.currentItem)
            }
        }

        currentFragmentIndex = fragment.fragmentIndex
        prefetchedFragmentIndex = nil
        loopBridgeQueuedForIndex = nil
        didTriggerNearEnd = false

        appendItem(
            url: fragment.fragmentURL,
            kind: .fragment(index: fragment.fragmentIndex),
            onReady: onBuffered
        )
        scheduleNearEndObserver(duration: TimeInterval(fragment.fragmentDuration))

        player.play()
        isPlaying = true
        onFragmentStarted?(fragment.fragmentIndex)
    }

    /// Следующий отрывок готов — transition + fragment в конец очереди.
    func prefetchNext(_ fragment: MusicFragment) {
        guard prefetchedFragmentIndex != fragment.fragmentIndex else { return }

        prefetchedFragmentIndex = fragment.fragmentIndex
        loopBridgeQueuedForIndex = nil

        if let transition = fragment.transitionURL {
            appendItem(url: transition, kind: .transition)
        }
        appendItem(url: fragment.fragmentURL, kind: .fragment(index: fragment.fragmentIndex))
    }

    /// Следующий ещё генерируется — loop-bridge + повтор текущего.
    func enqueueLoopBridge(for fragment: MusicFragment) {
        guard prefetchedFragmentIndex == nil else { return }
        guard loopBridgeQueuedForIndex != fragment.fragmentIndex else { return }
        guard let bridge = fragment.loopBridgeURL else { return }

        loopBridgeQueuedForIndex = fragment.fragmentIndex
        appendItem(url: bridge, kind: .loopBridge)
        appendItem(url: fragment.fragmentURL, kind: .fragment(index: fragment.fragmentIndex))
    }

    func togglePlayback() {
        guard let queuePlayer else { return }
        if isPlaying {
            queuePlayer.pause()
            isPlaying = false
        } else {
            queuePlayer.play()
            isPlaying = true
        }
    }

    func stop() {
        stopInternal()
        try? AVAudioSession.sharedInstance().setActive(false)
    }

    // MARK: - Private

    private func activateSession() {
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
        try? AVAudioSession.sharedInstance().setActive(true)
    }

    private func appendItem(url: URL, kind: PlaybackSegmentKind, onReady: (() -> Void)? = nil) {
        guard let queuePlayer else { return }

        let item = makePlayerItem(url: url, kind: kind, onReady: onReady)
        if let last = queuePlayer.items().last {
            queuePlayer.insert(item, after: last)
        } else {
            queuePlayer.insert(item, after: nil)
        }
    }

    private func makePlayerItem(url: URL, kind: PlaybackSegmentKind, onReady: (() -> Void)? = nil) -> AVPlayerItem {
        let item = AVPlayerItem(url: url)
        item.canUseNetworkResourcesForLiveStreamingWhilePaused = true
        item.preferredForwardBufferDuration = 8

        let id = ObjectIdentifier(item)
        itemKinds[id] = kind

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(itemDidFinish(_:)),
            name: .AVPlayerItemDidPlayToEndTime,
            object: item
        )

        var didCallReady = false
        statusObservations[id] = item.observe(\.status, options: [.new]) { [weak self] item, _ in
            Task { @MainActor in
                if item.status == .readyToPlay, !didCallReady {
                    didCallReady = true
                    onReady?()
                }
                if item.status == .failed {
                    let message = item.error?.localizedDescription ?? "Не удалось загрузить аудио"
                    self?.playbackError = "\(message)\n\(url.absoluteString)"
                }
            }
        }

        return item
    }

    private func handleCurrentItemChanged(_ item: AVPlayerItem?) {
        guard let item else { return }
        guard let kind = itemKinds[ObjectIdentifier(item)] else { return }

        if case .fragment(let index) = kind {
            currentFragmentIndex = index
            if prefetchedFragmentIndex == index {
                prefetchedFragmentIndex = nil
            }
            loopBridgeQueuedForIndex = nil
            didTriggerNearEnd = false
            onFragmentStarted?(index)

            let duration = item.duration.seconds
            if duration.isFinite, duration > 0 {
                scheduleNearEndObserver(duration: duration)
            }
        }
    }

    private func scheduleNearEndObserver(duration: TimeInterval) {
        removeTimeObserver()
        guard let queuePlayer, duration > 0 else { return }

        let leadTime = min(AppConfig.prefetchBeforeEnd, max(duration * 0.3, 3))
        let triggerAt = max(duration - leadTime, 0)

        timeObserver = queuePlayer.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.5, preferredTimescale: 600),
            queue: .main
        ) { [weak self] time in
            Task { @MainActor in
                guard let self, self.isPlaying, !self.didTriggerNearEnd else { return }
                if time.seconds >= triggerAt {
                    self.didTriggerNearEnd = true
                    self.onNearEnd?()
                }
            }
        }
    }

    @objc private func itemDidFinish(_ notification: Notification) {
        guard let item = notification.object as? AVPlayerItem else { return }
        let id = ObjectIdentifier(item)
        itemKinds.removeValue(forKey: id)
        statusObservations.removeValue(forKey: id)
        NotificationCenter.default.removeObserver(self, name: .AVPlayerItemDidPlayToEndTime, object: item)

        if queuePlayer?.items().isEmpty == true {
            isPlaying = false
        }
    }

    private func removeTimeObserver() {
        if let timeObserver, let queuePlayer {
            queuePlayer.removeTimeObserver(timeObserver)
        }
        timeObserver = nil
    }

    private func stopInternal() {
        removeTimeObserver()
        currentItemObservation?.invalidate()
        currentItemObservation = nil
        queuePlayer?.pause()
        queuePlayer?.removeAllItems()
        queuePlayer = nil
        itemKinds.removeAll()
        statusObservations.removeAll()
        currentFragmentIndex = nil
        prefetchedFragmentIndex = nil
        loopBridgeQueuedForIndex = nil
        didTriggerNearEnd = false
        isPlaying = false
        playbackError = nil
        NotificationCenter.default.removeObserver(self)
    }
}

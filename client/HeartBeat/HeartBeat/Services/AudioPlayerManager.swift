import AVFoundation
import Foundation

@Observable
@MainActor
final class AudioPlayerManager: NSObject {
    private var player: AVPlayer?
    private var timeObserver: Any?
    private var onNearEnd: (() -> Void)?
    private var didTriggerPrefetch = false

    var isPlaying = false

    func play(track: CurrentTrack, onNearEnd: @escaping () -> Void) {
        stop()
        self.onNearEnd = onNearEnd
        didTriggerPrefetch = false

        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
        try? AVAudioSession.sharedInstance().setActive(true)

        let item = AVPlayerItem(url: track.audioURL)
        player = AVPlayer(playerItem: item)
        player?.play()
        isPlaying = true

        let interval = CMTime(seconds: 1, preferredTimescale: 1)
        timeObserver = player?.addPeriodicTimeObserver(forInterval: interval, queue: .main) { [weak self] time in
            guard let self else { return }
            Task { @MainActor in
                self.checkPrefetch(currentTime: time.seconds, duration: Double(track.durationSeconds))
            }
        }

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(playerDidFinish),
            name: .AVPlayerItemDidPlayToEndTime,
            object: item
        )
    }

    func togglePlayback() {
        guard let player else { return }
        if isPlaying {
            player.pause()
            isPlaying = false
        } else {
            player.play()
            isPlaying = true
        }
    }

    func stop() {
        if let timeObserver, let player {
            player.removeTimeObserver(timeObserver)
        }
        timeObserver = nil
        player?.pause()
        player = nil
        isPlaying = false
        didTriggerPrefetch = false
        NotificationCenter.default.removeObserver(self)
    }

    @objc private func playerDidFinish() {
        isPlaying = false
        onNearEnd?()
    }

    private func checkPrefetch(currentTime: Double, duration: Double) {
        guard !didTriggerPrefetch else { return }
        let remaining = duration - currentTime
        if remaining <= AppConfig.prefetchBeforeEnd && remaining > 0 {
            didTriggerPrefetch = true
            onNearEnd?()
        }
    }
}

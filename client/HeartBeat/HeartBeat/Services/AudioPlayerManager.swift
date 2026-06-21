import AVFoundation
import Foundation

@Observable
@MainActor
final class AudioPlayerManager: NSObject {
    private var player: AVPlayer?
    private var endContinuation: CheckedContinuation<Void, Never>?
    private var timeObserver: Any?

    var isPlaying = false

    /// Воспроизвести URL и дождаться окончания
    func playAndWait(url: URL) async {
        stopInternal(keepSession: false)

        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
        try? AVAudioSession.sharedInstance().setActive(true)

        let item = AVPlayerItem(url: url)
        player = AVPlayer(playerItem: item)

        await withCheckedContinuation { continuation in
            endContinuation = continuation

            NotificationCenter.default.addObserver(
                self,
                selector: #selector(itemDidFinish),
                name: .AVPlayerItemDidPlayToEndTime,
                object: item
            )

            player?.play()
            isPlaying = true
        }
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
        stopInternal(keepSession: false)
    }

    private func stopInternal(keepSession: Bool) {
        if let timeObserver, let player {
            player.removeTimeObserver(timeObserver)
        }
        timeObserver = nil
        player?.pause()
        player = nil
        isPlaying = false
        NotificationCenter.default.removeObserver(self)

        if let endContinuation {
            self.endContinuation = nil
            endContinuation.resume()
        }

        if !keepSession {
            try? AVAudioSession.sharedInstance().setActive(false)
        }
    }

    @objc private func itemDidFinish() {
        isPlaying = false
        NotificationCenter.default.removeObserver(self)
        endContinuation?.resume()
        endContinuation = nil
    }
}

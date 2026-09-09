import collections
import numpy as np


class VoiceActivityDetector:
    """
    Intelligent Human Voice Activity Detector (HVAD).
    Differentiates human speech from non-living background noise (fans, AC, hum, mic static)
    using adaptive noise tracking, spectral variance, and zero-crossing rate analysis.
    """

    def __init__(
        self,
        min_energy_threshold: float = 550.0,
        silence_duration_ms: int = 260,
        max_speech_duration_ms: int = 30000,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20
    ):
        self.min_energy_threshold = min_energy_threshold
        self.silence_duration_ms = silence_duration_ms
        self.max_speech_duration_ms = max_speech_duration_ms
        self.sample_rate = sample_rate

        self.consecutive_speech_ms = 0.0
        self.consecutive_silence_ms = 0.0
        self.is_speaking = False

        # Adaptive noise floor baseline (16-bit PCM scale)
        self.noise_floor = 300.0
        self.energy_history = collections.deque(maxlen=15)

    def process_frame(self, frame_bytes: bytes) -> bool:
        """
        Process a PCM chunk (16-bit mono 16kHz).
        Returns True if the frame contains active human speech.
        Automatically rejects vehicle horns, roadside traffic drone, and steady appliance hum.
        """
        if len(frame_bytes) < 2:
            return False

        samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            return False

        chunk_duration_ms = (len(samples) / float(self.sample_rate)) * 1000.0

        # 1. Root Mean Square (RMS) energy
        rms_energy = float(np.sqrt(np.mean(samples**2)))
        self.energy_history.append(rms_energy)

        # 2. Zero Crossing Rate (ZCR)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(samples)))) / (2.0 * len(samples))

        # 3. Ambient Noise Floor Adaptation (during silence or when AI is idle)
        if not self.is_speaking:
            # Slowly adapt to steady background sound
            self.noise_floor = (self.noise_floor * 0.94) + (rms_energy * 0.06)

        # 4. Dynamic Speech Threshold (adapted above room noise floor)
        dynamic_threshold = max(self.min_energy_threshold, self.noise_floor * 2.3)

        # 5. Stationarity Check (Differentiate human speech from steady non-living road traffic/fan noise)
        # Constant road noise has near-zero variance in energy (< 0.15 coefficient of variation)
        # Human speech exhibits high dynamic syllabic variance (> 0.22)
        is_stationary_noise = False
        if len(self.energy_history) >= 8:
            arr = np.array(self.energy_history)
            mean_e = np.mean(arr)
            std_e = np.std(arr)
            if mean_e > 0:
                cv = std_e / mean_e
                # If energy is steady and variation is very low, it's non-living appliance or road drone
                if cv < 0.14 and rms_energy < dynamic_threshold * 1.6:
                    is_stationary_noise = True

        # 6. Spectral Peakiness / Tonality (Vehicle Horn & Siren Rejection)
        # Vehicle horns, sirens, and whistles concentrate energy into 1 to 4 narrow frequency bins.
        # Human speech distributes energy across multiple vowel formant peaks and consonant bands.
        is_horn_or_siren = False
        if len(samples) >= 128:
            # Apply Hanning window to prevent rectangular window spectral leakage
            window = np.hanning(len(samples))
            fft_mags = np.abs(np.fft.rfft(samples * window))
            max_idx = int(np.argmax(fft_mags))
            max_mag = float(fft_mags[max_idx])
            sum_mag = float(np.sum(fft_mags)) + 1e-6
            mean_mag = float(np.mean(fft_mags)) + 1e-6
            peakiness = max_mag / mean_mag
            prominent_bins = int(np.sum(fft_mags >= max_mag * 0.5))

            # Frequencies of FFT bins
            fft_freqs = np.fft.rfftfreq(len(samples), d=1.0 / 16000.0)
            peak_freq = float(fft_freqs[max_idx])

            # Top 2 and Top 4 bins concentration
            top2_mag = float(np.sum(np.partition(fft_mags, -2)[-2:]))
            top2_ratio = top2_mag / sum_mag
            top4_mag = float(np.sum(np.partition(fft_mags, -4)[-4:]))
            top4_ratio = top4_mag / sum_mag

            # Vehicle horns and sirens are extreme tonal resonances concentrated between 280Hz and 4500Hz
            # with high spectral concentration in 2-4 bins (unlike human speech formants).
            if 280.0 <= peak_freq <= 4500.0 and (
                top4_ratio > 0.65 and top2_ratio > 0.36 and (top2_ratio + top4_ratio) > 1.05
            ) and max_mag > 150.0:
                is_horn_or_siren = True

        # 7. Speech Decision Logic
        # Must exceed dynamic threshold, not be stationary road noise, not be a vehicle horn, and have speech ZCR
        is_frame_speech = (
            rms_energy > dynamic_threshold
            and not is_stationary_noise
            and not is_horn_or_siren
            and (0.015 < zero_crossings < 0.55)
        )

        if is_frame_speech:
            self.consecutive_speech_ms += chunk_duration_ms
            self.consecutive_silence_ms = 0.0
            # Require at least 60ms of continuous human speech before flipping to True
            if self.consecutive_speech_ms >= 60.0:
                self.is_speaking = True
        else:
            self.consecutive_speech_ms = 0.0
            if self.is_speaking:
                self.consecutive_silence_ms += chunk_duration_ms
                if self.consecutive_silence_ms >= self.silence_duration_ms:
                    self.is_speaking = False

        return self.is_speaking

    def is_barge_in(self, speech_duration_ms: int, min_trigger_ms: int = 500) -> bool:
        """Verify if continuous caller speech is long enough to warrant stopping AI playback."""
        return speech_duration_ms >= min_trigger_ms

    def reset(self):
        """Reset internal speech state for a new utterance."""
        self.consecutive_speech_ms = 0.0
        self.consecutive_silence_ms = 0.0
        self.is_speaking = False
        self.energy_history.clear()


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
        min_energy_threshold: float = 240.0,
        silence_duration_ms: int = 650,  # 650ms natural pause release
        max_speech_duration_ms: int = 30000,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
        outdoor_mode: bool = False  # Balanced indoor/outdoor sensitivity
    ):
        self.min_energy_threshold = min_energy_threshold
        self.silence_duration_ms = silence_duration_ms
        self.max_speech_duration_ms = max_speech_duration_ms
        self.sample_rate = sample_rate
        self.outdoor_mode = outdoor_mode

        self.consecutive_speech_ms = 0.0
        self.consecutive_silence_ms = 0.0
        self.is_speaking = False

        # Adaptive noise floor baseline (16-bit PCM scale)
        # Higher baseline for outdoor to ignore wind/traffic rumble
        self.noise_floor = 280.0 if outdoor_mode else 200.0
        self.noise_floor_steady_count = 0
        self.max_noise_floor = 1500.0  # Cap to prevent threshold from rising too high in traffic
        self.energy_history = collections.deque(maxlen=20)  # Longer history for stable outdoor detection
        self.stable_energy_frames = 0  # Track steady-state noise
        self.last_debug = {
            "rms": 0.0,
            "threshold": self.min_energy_threshold,
            "reason": "idle",
            "is_speaking": False,
            "zcr": 0.0,
        }
        self._last_debug_reason = None

    def process_frame(self, frame_bytes: bytes) -> bool:
        """
        Process a PCM chunk (16-bit mono 16kHz).
        Returns True if the frame contains active human speech.
        Automatically rejects vehicle horns, roadside traffic drone, and steady appliance hum.
        """
        if len(frame_bytes) < 2:
            self.last_debug = {
                "rms": 0.0,
                "threshold": self.min_energy_threshold,
                "reason": "short_frame",
                "is_speaking": self.is_speaking,
                "zcr": 0.0,
            }
            return False

        samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            self.last_debug = {
                "rms": 0.0,
                "threshold": self.min_energy_threshold,
                "reason": "empty_frame",
                "is_speaking": self.is_speaking,
                "zcr": 0.0,
            }
            return False

        chunk_duration_ms = (len(samples) / float(self.sample_rate)) * 1000.0

        # 1. Root Mean Square (RMS) energy
        rms_energy = float(np.sqrt(np.mean(samples**2)))
        self.energy_history.append(rms_energy)

        # 2. Zero Crossing Rate (ZCR)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(samples)))) / (2.0 * len(samples))

        # 3. Ambient Noise Floor Adaptation (during silence or when AI is idle)
        # OUTDOOR OPTIMIZED: Careful adaptation with hard caps to prevent outdoor noise from inflating threshold
        if not self.is_speaking:
            if len(self.energy_history) >= 6:
                arr = np.array(list(self.energy_history))
                mean_e = np.mean(arr)
                cv = np.std(arr) / (mean_e + 1e-6)
                # Only adapt noise floor if this is clearly stationary background noise
                # Outdoor mode: higher cv threshold (0.22) to ignore wind gusts & traffic variation
                cv_threshold = 0.22 if self.outdoor_mode else 0.15
                energy_cap = 2500.0 if self.outdoor_mode else 2000.0
                
                if cv < cv_threshold and rms_energy < energy_cap:
                    # Very slow adaptation in outdoor mode (98% old, 2% new)
                    adapt_factor = 0.02 if self.outdoor_mode else 0.04
                    self.noise_floor = min(self.max_noise_floor, 
                                          (self.noise_floor * (1 - adapt_factor)) + (rms_energy * adapt_factor))
                    self.stable_energy_frames += 1
                    self.noise_floor_steady_count = min(self.noise_floor_steady_count + 1, 20)
                else:
                    self.stable_energy_frames = 0
                    self.noise_floor_steady_count = max(0, self.noise_floor_steady_count - 1)
            else:
                self.stable_energy_frames = 0
                self.noise_floor_steady_count = max(0, self.noise_floor_steady_count - 1)

        # 4. Dynamic Speech Threshold (adapted above room noise floor)
        multiplier = 1.4 if self.outdoor_mode else 1.5
        dynamic_threshold = max(self.min_energy_threshold, self.noise_floor * multiplier)

        # 5. Stationarity Check (Differentiate human speech from steady non-living fan noise/appliance drone)
        is_stationary_noise = False
        rejection_reason = "valid_human_speech"
        if len(self.energy_history) >= 4:
            arr = np.array(list(self.energy_history))
            mean_e = np.mean(arr)
            std_e = np.std(arr)
            if mean_e > 0:
                cv = std_e / mean_e
                if cv < 0.14 and rms_energy < 3200.0:
                    is_stationary_noise = True
                    rejection_reason = "stationary_noise"

        # 6. Spectral Peakiness / Tonality (Vehicle Horn & Siren Rejection)
        # Vehicle horns, sirens, and whistles concentrate energy into 1 to 4 narrow frequency bins.
        is_horn_or_siren = False
        if len(samples) >= 128 and not is_stationary_noise:
            window = np.hanning(len(samples))
            fft_mags = np.abs(np.fft.rfft(samples * window))
            max_idx = int(np.argmax(fft_mags))
            max_mag = float(fft_mags[max_idx])
            sum_mag = float(np.sum(fft_mags)) + 1e-6
            fft_freqs = np.fft.rfftfreq(len(samples), d=1.0 / 16000.0)
            peak_freq = float(fft_freqs[max_idx])
            top2_mag = float(np.sum(np.partition(fft_mags, -2)[-2:]))
            top2_ratio = top2_mag / sum_mag
            top4_mag = float(np.sum(np.partition(fft_mags, -4)[-4:]))
            top4_ratio = top4_mag / sum_mag

            if 280.0 <= peak_freq <= 4500.0 and (
                top4_ratio > 0.65 and top2_ratio > 0.36 and (top2_ratio + top4_ratio) > 1.05
            ) and max_mag > 150.0:
                is_horn_or_siren = True
                rejection_reason = "horn_like_tone"

        # 7. Speech Decision Logic
        zcr_ok = 0.012 < zero_crossings < 0.65
        if rms_energy <= dynamic_threshold:
            rejection_reason = "low_energy"
        elif is_stationary_noise:
            rejection_reason = "stationary_noise"
        elif is_horn_or_siren:
            rejection_reason = "horn_like_tone"
        elif not zcr_ok:
            rejection_reason = "zcr_out_of_range"

        is_frame_speech = (
            rms_energy > dynamic_threshold
            and not is_stationary_noise
            and not is_horn_or_siren
            and zcr_ok
        )

        if is_frame_speech:
            self.consecutive_speech_ms += chunk_duration_ms
            self.consecutive_silence_ms = 0.0
            speech_attack_threshold = 80.0
            if self.consecutive_speech_ms >= speech_attack_threshold:
                self.is_speaking = True
                rejection_reason = "valid_human_speech"
        else:
            self.consecutive_speech_ms = 0.0
            if self.is_speaking:
                self.consecutive_silence_ms += chunk_duration_ms
                if self.consecutive_silence_ms >= self.silence_duration_ms:
                    self.is_speaking = False
                    rejection_reason = "silence_release"
            else:
                self.consecutive_silence_ms = 0.0

        self.last_debug = {
            "rms": round(float(rms_energy), 2),
            "threshold": round(float(dynamic_threshold), 2),
            "reason": rejection_reason,
            "is_speaking": bool(self.is_speaking),
            "zcr": round(float(zero_crossings), 4),
        }
        self._last_debug_reason = rejection_reason

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
        self.last_debug.update({
            "rms": 0.0,
            "threshold": self.min_energy_threshold,
            "reason": "reset",
            "is_speaking": False,
            "zcr": 0.0,
        })

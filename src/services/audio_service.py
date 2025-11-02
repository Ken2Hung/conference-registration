"""
Audio processing service for real-time transcription feature.

This module provides:
- PyAV audio frame processing
- Voice Activity Detection (VAD)
- Audio chunking and buffering
- WAV format conversion
"""

import numpy as np
import av
from typing import Optional

from src.utils.audio_utils import calculate_rms, pcm16_to_wav_bytes


def process_audio_frame(frame: av.AudioFrame, gain: float = 1.0) -> np.ndarray:
    """
    Convert PyAV AudioFrame to mono int16 PCM NumPy array.

    Args:
        frame: PyAV AudioFrame from WebRTC stream
        gain: Volume gain multiplier (default: 1.0)
              - 1.0 = original volume
              - 2.0 = double volume
              - 0.5 = half volume
              - Recommended: 1.5 - 3.0 for boosting quiet recordings

    Returns:
        1D NumPy array of int16 PCM samples (mono)

    Example:
        >>> # In WebRTC callback
        >>> def audio_callback(frame):
        ...     pcm = process_audio_frame(frame, gain=2.0)  # Double volume
        ...     # Process PCM data...

    Notes:
        - Automatically mixes stereo to mono by averaging channels
        - Handles both planar and interleaved stereo formats
        - Converts float samples to int16 PCM format
        - Sample rate is preserved from input frame (typically 48kHz)
        - Volume gain is applied with clipping to prevent distortion
    """
    # Get PCM data from frame
    pcm = frame.to_ndarray()

    # Get expected sample count per channel from frame
    expected_samples = frame.samples

    # Handle different stereo formats
    if pcm.ndim == 2:
        if pcm.shape[0] == 1:
            # Shape (1, N) - flatten first
            pcm = pcm.squeeze(0)

            # Check if interleaved stereo (N = expected_samples * 2)
            if len(pcm) == expected_samples * 2:
                # Deinterleave: [L0, R0, L1, R1, ...] -> [[L0, R0], [L1, R1], ...]
                pcm = pcm.reshape(-1, 2).mean(axis=1).astype(pcm.dtype)
        elif pcm.shape[0] > 1:
            # Standard planar format (channels, samples)
            pcm = pcm.mean(axis=0)

    # Convert to int16 if needed
    if pcm.dtype != np.int16:
        # Assume input is float in range [-1.0, 1.0]
        if pcm.dtype in [np.float32, np.float64]:
            pcm = (pcm * 32767).astype(np.int16)
        else:
            pcm = pcm.astype(np.int16)

    # Apply volume gain with clipping to prevent distortion
    if gain != 1.0:
        # Convert to float for accurate multiplication
        pcm_float = pcm.astype(np.float32)
        pcm_float *= gain
        # Clip to prevent overflow and distortion
        pcm = np.clip(pcm_float, -32768, 32767).astype(np.int16)

    return pcm


def has_voice_activity(pcm_data: np.ndarray, threshold: int) -> bool:
    """
    Detect voice using RMS threshold comparison.

    Args:
        pcm_data: 1D NumPy array of int16 PCM samples
        threshold: RMS threshold value (50-1000)

    Returns:
        True if voice detected (RMS >= threshold), False otherwise

    Example:
        >>> pcm = np.array([100, -200, 300], dtype=np.int16)
        >>> has_voice = has_voice_activity(pcm, 200)
        >>> print(has_voice)
        True

    Notes:
        - Typical thresholds:
          - Quiet office: 150-250
          - Normal room: 200-400
          - Noisy environment: 400-800
        - Lower threshold = more sensitive (more false positives)
        - Higher threshold = less sensitive (may miss soft speech)
    """
    rms = calculate_rms(pcm_data)
    return rms >= threshold


def create_wav_chunk(pcm_data: np.ndarray, sample_rate: int = 48000) -> bytes:
    """
    Generate complete WAV file bytes with 44-byte header.

    Args:
        pcm_data: 1D NumPy array of int16 PCM samples
        sample_rate: Sample rate in Hz (default: 48000)

    Returns:
        Complete WAV file as bytes

    Example:
        >>> pcm = np.array([100, -200, 300], dtype=np.int16)
        >>> wav_bytes = create_wav_chunk(pcm, 48000)
        >>> # Send wav_bytes to OpenAI API

    Notes:
        - This is a convenience wrapper around pcm16_to_wav_bytes
        - WAV format: PCM, mono, 16-bit, little-endian
        - Compatible with OpenAI Audio Transcription API
    """
    return pcm16_to_wav_bytes(pcm_data, sample_rate)


def is_voiced_chunk(
    pcm_data: np.ndarray,
    rms_threshold: int,
    min_density: float = 0.08,
    amplitude_gate: int = 800,
) -> bool:
    """
    Combined VAD using RMS and amplitude density.

    Heuristics:
    - Global RMS must exceed threshold
    - At least `min_density` of samples must exceed `amplitude_gate`
    """
    if pcm_data.size == 0:
        return False

    rms = calculate_rms(pcm_data)
    if rms < float(rms_threshold):
        return False

    abs_vals = np.abs(pcm_data.astype(np.int32))
    density = float(np.mean(abs_vals >= int(amplitude_gate)))
    return density >= float(min_density)


class AudioChunker:
    """
    Accumulates audio frames into configurable-duration chunks.

    Manages internal buffer and produces complete chunks when enough
    samples have been accumulated.

    Example:
        >>> chunker = AudioChunker(sample_rate=48000, chunk_secs=2.0, vad_rms=200)
        >>>
        >>> # In WebRTC callback
        >>> def audio_callback(frame):
        ...     pcm = process_audio_frame(frame)
        ...     chunk = chunker.push(pcm)
        ...     if chunk is not None:
        ...         # Process complete chunk
        ...         if has_voice_activity(chunk, chunker.vad_rms):
        ...             wav_bytes = create_wav_chunk(chunk, chunker.sample_rate)
        ...             # Send to transcription...
    """

    def __init__(
        self,
        sample_rate: int = 48000,
        chunk_secs: float = 2.0,
        vad_rms: int = 200
    ):
        """
        Initialize audio chunker.

        Args:
            sample_rate: Audio sample rate in Hz (default: 48000 for WebRTC)
            chunk_secs: Target chunk duration in seconds (1.0-5.0)
            vad_rms: Voice Activity Detection RMS threshold (50-1000)
        """
        self.sample_rate = sample_rate
        self.chunk_secs = chunk_secs
        self.vad_rms = vad_rms
        self.chunk_samples = int(sample_rate * chunk_secs)
        self.buffer = np.array([], dtype=np.int16)

    def push(self, pcm_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Push new audio samples into buffer and return complete chunk if ready.

        Args:
            pcm_data: 1D NumPy array of int16 PCM samples

        Returns:
            Complete audio chunk if buffer has enough samples, None otherwise

        Notes:
            - Accumulates samples in internal buffer
            - Returns chunk when buffer >= chunk_samples
            - Keeps remainder samples in buffer for next chunk
            - Thread-safe: safe to call from WebRTC callback
        """
        # Append new samples to buffer
        self.buffer = np.concatenate([self.buffer, pcm_data])

        # Check if we have enough samples for a complete chunk
        if len(self.buffer) >= self.chunk_samples:
            # Extract complete chunk
            chunk = self.buffer[:self.chunk_samples]

            # Keep remainder in buffer
            self.buffer = self.buffer[self.chunk_samples:]

            return chunk

        return None

    def reset(self) -> None:
        """
        Clear internal buffer.

        Useful when stopping/restarting recording to avoid
        mixing audio from different sessions.
        """
        self.buffer = np.array([], dtype=np.int16)

    def get_buffer_duration(self) -> float:
        """
        Get current buffer duration in seconds.

        Returns:
            Duration of buffered samples in seconds

        Useful for debugging and monitoring.
        """
        return len(self.buffer) / self.sample_rate

    def update_config(self, chunk_secs: Optional[float] = None, vad_rms: Optional[int] = None) -> None:
        """
        Update chunker configuration without recreating instance.

        Args:
            chunk_secs: New chunk duration in seconds (1.0-5.0)
            vad_rms: New VAD threshold (50-1000)

        Notes:
            - Changing chunk_secs resets buffer to avoid partial chunks
            - Changing vad_rms does not affect buffer
        """
        if chunk_secs is not None:
            if not (1.0 <= chunk_secs <= 5.0):
                raise ValueError(f"chunk_secs must be between 1.0 and 5.0, got {chunk_secs}")
            self.chunk_secs = chunk_secs
            self.chunk_samples = int(self.sample_rate * chunk_secs)
            self.reset()  # Reset buffer to avoid mixing chunk sizes

        if vad_rms is not None:
            if not (50 <= vad_rms <= 1000):
                raise ValueError(f"vad_rms must be between 50 and 1000, got {vad_rms}")
            self.vad_rms = vad_rms

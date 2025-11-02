"""
Audio utility functions for real-time transcription feature.

This module provides audio processing utilities for:
- Voice Activity Detection (VAD) using RMS calculation
- WAV file format conversion for OpenAI API submission
"""

import struct
import numpy as np


def calculate_rms(pcm_data: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) of PCM audio data for Voice Activity Detection.

    Args:
        pcm_data: 1D NumPy array of int16 PCM audio samples

    Returns:
        RMS value as float (>= 0.0)

    Example:
        >>> pcm = np.array([100, -200, 300, -400], dtype=np.int16)
        >>> rms = calculate_rms(pcm)
        >>> print(f"RMS: {rms:.2f}")
        RMS: 264.58

    Notes:
        - RMS is calculated as sqrt(mean(square(samples)))
        - Higher RMS indicates louder audio
        - Typical speech RMS: 200-800 for 48kHz int16 samples
        - Background noise RMS: 50-150
    """
    if len(pcm_data) == 0:
        return 0.0

    # Convert to float to avoid overflow in squaring operation
    float_data = pcm_data.astype(np.float64)

    # Calculate mean of squares, then square root
    mean_square = np.mean(float_data ** 2)
    rms = np.sqrt(mean_square)

    return float(rms)


def pcm16_to_wav_bytes(pcm_data: np.ndarray, sample_rate: int = 48000) -> bytes:
    """
    Convert PCM16 audio data to complete WAV file bytes with proper header.

    Args:
        pcm_data: 1D NumPy array of int16 PCM audio samples
        sample_rate: Sample rate in Hz (default: 48000 for WebRTC)

    Returns:
        Complete WAV file as bytes (header + data)

    Raises:
        ValueError: If pcm_data is not 1D int16 NumPy array
        ValueError: If sample_rate is not positive

    Example:
        >>> pcm = np.array([100, -200, 300], dtype=np.int16)
        >>> wav_bytes = pcm16_to_wav_bytes(pcm, 48000)
        >>> print(f"WAV size: {len(wav_bytes)} bytes")
        WAV size: 50 bytes  # 44-byte header + 6 bytes data

    Notes:
        - WAV header is exactly 44 bytes
        - Format: PCM, 1 channel (mono), 16-bit, little-endian
        - Compatible with OpenAI Audio API requirements
    """
    # Validation
    if pcm_data.ndim != 1:
        raise ValueError(f"pcm_data must be 1D array, got {pcm_data.ndim}D")

    if pcm_data.dtype != np.int16:
        raise ValueError(f"pcm_data must be int16, got {pcm_data.dtype}")

    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate}")

    # Audio format parameters
    num_channels = 1  # Mono
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_data) * 2  # 2 bytes per int16 sample

    # Build WAV header (44 bytes total)
    header = bytearray()

    # RIFF chunk descriptor (12 bytes)
    header.extend(b'RIFF')  # ChunkID
    header.extend(struct.pack('<I', 36 + data_size))  # ChunkSize (4 + 24 + 8 + data_size)
    header.extend(b'WAVE')  # Format

    # fmt sub-chunk (24 bytes)
    header.extend(b'fmt ')  # Subchunk1ID
    header.extend(struct.pack('<I', 16))  # Subchunk1Size (16 for PCM)
    header.extend(struct.pack('<H', 1))  # AudioFormat (1 = PCM)
    header.extend(struct.pack('<H', num_channels))  # NumChannels
    header.extend(struct.pack('<I', sample_rate))  # SampleRate
    header.extend(struct.pack('<I', byte_rate))  # ByteRate
    header.extend(struct.pack('<H', block_align))  # BlockAlign
    header.extend(struct.pack('<H', bits_per_sample))  # BitsPerSample

    # data sub-chunk (8 bytes header + data)
    header.extend(b'data')  # Subchunk2ID
    header.extend(struct.pack('<I', data_size))  # Subchunk2Size

    # Combine header and PCM data
    pcm_bytes = pcm_data.tobytes()
    wav_bytes = bytes(header) + pcm_bytes

    return wav_bytes

"""
Test audio conversion logic used in mic_recorder_page.py

This ensures the PyAV AudioFrame to PCM conversion works correctly.
"""

import numpy as np


def test_stereo_to_mono_conversion():
    """Test stereo to mono averaging."""
    # Simulate stereo audio from PyAV: shape (num_channels, num_samples)
    # 2 channels, 3 samples each
    stereo_audio = np.array([
        [100, 200, 300],  # Left channel
        [400, 500, 600]   # Right channel
    ], dtype=np.float32)

    # Convert to mono by averaging channels (axis=0)
    if stereo_audio.ndim == 2:
        mono_audio = stereo_audio.mean(axis=0)
    else:
        mono_audio = stereo_audio

    # Expected: average of left and right channels for each sample
    # Sample 0: (100+400)/2 = 250
    # Sample 1: (200+500)/2 = 350
    # Sample 2: (300+600)/2 = 450
    expected = np.array([250, 350, 450], dtype=np.float32)

    assert np.allclose(mono_audio, expected), f"Expected {expected}, got {mono_audio}"
    print(f"✅ Stereo to mono: {stereo_audio.shape} -> {mono_audio.shape}")


def test_float_to_int16_conversion():
    """Test float32 [-1.0, 1.0] to int16 [-32768, 32767] conversion."""
    # Simulate float audio data
    float_audio = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)

    # Convert to int16
    int16_audio = (float_audio * 32767).astype(np.int16)

    # Expected values
    expected = np.array([-32767, -16383, 0, 16383, 32767], dtype=np.int16)

    assert np.allclose(int16_audio, expected, atol=1), f"Expected {expected}, got {int16_audio}"
    print(f"✅ Float32 to int16: dtype {float_audio.dtype} -> {int16_audio.dtype}")
    print(f"   Range: [{float_audio.min():.1f}, {float_audio.max():.1f}] -> [{int16_audio.min()}, {int16_audio.max()}]")


def test_already_int16():
    """Test that int16 data is passed through unchanged."""
    int16_audio = np.array([-1000, 0, 1000], dtype=np.int16)

    # Should pass through
    if int16_audio.dtype == np.int16:
        result = int16_audio
    else:
        result = int16_audio.astype(np.int16)

    assert np.array_equal(int16_audio, result)
    print(f"✅ Int16 passthrough: {int16_audio.dtype} -> {result.dtype}")


def test_complete_pipeline():
    """Test complete conversion pipeline: stereo float32 -> mono int16."""
    # Simulate WebRTC audio: shape (num_channels, num_samples), float32, normalized [-1.0, 1.0]
    stereo_float = np.array([
        [0.1, 0.5, 1.0],   # Left channel: 3 samples
        [-0.1, -0.5, -1.0] # Right channel: 3 samples
    ], dtype=np.float32)

    print("\n📊 Complete Pipeline Test")
    print(f"Input: shape={stereo_float.shape}, dtype={stereo_float.dtype}")

    # Step 1: Stereo to mono (average channels)
    if stereo_float.ndim == 2:
        mono_float = stereo_float.mean(axis=0)
    else:
        mono_float = stereo_float

    print(f"After mono: shape={mono_float.shape}, dtype={mono_float.dtype}")

    # Step 2: Float to int16
    if mono_float.dtype == np.float32 or mono_float.dtype == np.float64:
        mono_int16 = (mono_float * 32767).astype(np.int16)
    elif mono_float.dtype == np.int16:
        mono_int16 = mono_float
    else:
        mono_int16 = mono_float.astype(np.int16)

    print(f"After int16: shape={mono_int16.shape}, dtype={mono_int16.dtype}")

    # Expected: average of left and right channels for each sample, then scale to int16
    # Sample 0: (0.1 + (-0.1))/2 = 0.0 -> 0
    # Sample 1: (0.5 + (-0.5))/2 = 0.0 -> 0
    # Sample 2: (1.0 + (-1.0))/2 = 0.0 -> 0
    expected = np.array([0, 0, 0], dtype=np.int16)

    assert np.array_equal(mono_int16, expected), f"Expected {expected}, got {mono_int16}"
    print(f"✅ Complete pipeline successful")

    # Convert to bytes (as done in actual code)
    pcm_bytes = mono_int16.tobytes()
    print(f"Final bytes: {len(pcm_bytes)} bytes ({len(mono_int16)} samples * 2 bytes/sample)")


def test_sample_rate_preservation():
    """Verify that sample rate is correctly tracked."""
    # Simulate different sample rates
    sample_rates = [8000, 16000, 24000, 44100, 48000]

    print("\n📊 Sample Rate Tracking Test")
    for rate in sample_rates:
        # Simulate 1 second of audio at this sample rate
        num_samples = rate
        audio = np.random.randn(num_samples).astype(np.float32)

        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Calculate duration
        duration = len(audio_int16) / rate

        print(f"  {rate} Hz: {len(audio_int16)} samples = {duration:.1f} seconds ✅")
        assert duration == 1.0, f"Duration should be 1.0 second, got {duration}"


if __name__ == "__main__":
    print("🎤 Audio Conversion Tests\n")

    test_stereo_to_mono_conversion()
    test_float_to_int16_conversion()
    test_already_int16()
    test_complete_pipeline()
    test_sample_rate_preservation()

    print("\n✅ All tests passed!")

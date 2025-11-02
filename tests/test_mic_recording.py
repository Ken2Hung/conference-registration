"""
Test script for microphone recording functionality.

This script verifies:
1. WAV file format correctness
2. Sample rate consistency
3. Audio playback speed validation
"""

import wave
import os
from pathlib import Path
import numpy as np


def analyze_wav_file(filepath: str) -> dict:
    """Analyze WAV file properties and detect potential issues."""
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        with wave.open(filepath, 'rb') as f:
            info = {
                "path": filepath,
                "size_bytes": os.path.getsize(filepath),
                "channels": f.getnchannels(),
                "sample_width": f.getsampwidth(),
                "sample_rate": f.getframerate(),
                "num_frames": f.getnframes(),
                "duration_seconds": f.getnframes() / f.getframerate() if f.getframerate() > 0 else 0,
            }

            # Read first 1 second of audio for analysis
            frames_to_read = min(f.getnframes(), f.getframerate())
            if frames_to_read > 0:
                audio_bytes = f.readframes(frames_to_read)
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

                # Calculate RMS
                rms = np.sqrt(np.mean(audio_data.astype(np.float64) ** 2))
                info["rms_first_sec"] = float(rms)

                # Detect silence
                info["is_silent"] = rms < 100

            return info
    except Exception as e:
        return {"error": str(e), "path": filepath}


def detect_sample_rate_mismatch(filepath: str) -> dict:
    """
    Detect if WAV file has sample rate mismatch issues.

    Common issue: Audio recorded at 16kHz but WAV header says 48kHz,
    causing 3x slower playback.
    """
    result = analyze_wav_file(filepath)

    if "error" in result:
        return result

    header_rate = result["sample_rate"]
    duration = result["duration_seconds"]
    size_bytes = result["size_bytes"]

    # Calculate expected size based on header
    expected_size = 44 + (header_rate * 2 * duration)  # 44-byte header + samples

    # Check if actual size matches expected
    size_ratio = size_bytes / expected_size if expected_size > 0 else 0

    result["expected_size"] = int(expected_size)
    result["size_ratio"] = size_ratio

    # Detect common mismatches
    if 0.3 < size_ratio < 0.4:
        result["likely_issue"] = "Recorded at ~16kHz but header says 48kHz (3x slower playback)"
        result["suggested_sample_rate"] = 16000
    elif 0.45 < size_ratio < 0.55:
        result["likely_issue"] = "Recorded at ~24kHz but header says 48kHz (2x slower playback)"
        result["suggested_sample_rate"] = 24000
    elif 0.9 < size_ratio < 1.1:
        result["likely_issue"] = None
        result["suggested_sample_rate"] = header_rate
    else:
        result["likely_issue"] = f"Unknown mismatch (ratio: {size_ratio:.2f})"
        result["suggested_sample_rate"] = None

    return result


def test_all_recordings():
    """Test all recordings in resource directory."""
    resource_dir = Path("resource")

    if not resource_dir.exists():
        print("❌ Resource directory not found")
        return

    wav_files = sorted(resource_dir.glob("mic-record-*.wav"))

    if not wav_files:
        print("❌ No WAV files found in resource/")
        return

    print(f"🔍 Found {len(wav_files)} WAV files\n")

    for wav_file in wav_files:
        print(f"{'='*60}")
        print(f"📁 File: {wav_file.name}")

        result = detect_sample_rate_mismatch(str(wav_file))

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            continue

        print(f"📊 Size: {result['size_bytes']:,} bytes")
        print(f"🎚️  Sample rate: {result['sample_rate']} Hz")
        print(f"⏱️  Duration: {result['duration_seconds']:.2f} seconds")
        print(f"🔊 RMS (1st sec): {result.get('rms_first_sec', 0):.1f}")

        if result.get("is_silent"):
            print("⚠️  WARNING: Audio appears to be silent")

        if result.get("likely_issue"):
            print(f"⚠️  ISSUE: {result['likely_issue']}")
            print(f"💡 Suggested fix: Re-record or convert to {result['suggested_sample_rate']} Hz")
        else:
            print("✅ No obvious issues detected")

        print()


if __name__ == "__main__":
    print("🎤 Microphone Recording Test\n")
    test_all_recordings()

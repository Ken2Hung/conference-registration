# 音訊播放速度問題診斷指南

## 問題：錄 5 秒播放 10 秒（慢一倍）

這是典型的**採樣率或樣本數錯誤**。

## 🔍 可能原因

### 1. Stereo 轉 Mono 的 Axis 錯誤
如果用錯 axis 平均立體聲：
- **錯誤**：把兩個聲道的樣本串接，導致樣本數加倍
- **結果**：5 秒音訊變成 10 秒播放（慢一倍）

### 2. 採樣率標記錯誤
- WebRTC 實際輸出 24kHz
- WAV header 寫入 48kHz
- 播放器用 48kHz 速率播放 24kHz 的數據 → 慢一倍

## 🧪 診斷步驟

### 1. 重新錄音並查看詳細日誌

```bash
# 啟動應用程式
./start.sh

# 在瀏覽器中：
# 1. 開啟麥克風錄音頁面
# 2. 點擊「開始錄音」
# 3. 說話 5 秒（可以數 1, 2, 3, 4, 5）
# 4. 點擊「停止錄音」
# 5. 查看 terminal 的 Console 輸出
```

### 2. 分析 Console 輸出

#### ✅ 正常情況（樣本數正確）：

```
[MicRecorder] === RAW FRAME DEBUG ===
  Frame: sample_rate=48000, samples=960, layout=stereo, format=fltp
  to_ndarray() shape: (2, 960), dtype: float32
  Detected PLANAR stereo: averaged axis=0
  After mono: shape=(960,)
  Expected samples: 960
  Actual samples after conversion: 960
  Final chunk: 1920 bytes = 960 samples
  Expected duration: 0.020s
  Actual duration: 0.020s
  ✅ Using sample rate: 48000 Hz
```

**解讀**：
- Shape `(2, 960)` = 2 聲道，每聲道 960 個樣本
- 使用 `axis=0` 平均 → 結果 `(960,)` - **正確！**
- 樣本數：960 = 960 - **匹配！**

#### ❌ 問題情況 1：樣本數加倍（Axis 錯誤）

```
[MicRecorder] === RAW FRAME DEBUG ===
  Frame: sample_rate=48000, samples=960, layout=stereo, format=fltp
  to_ndarray() shape: (960, 2), dtype: float32
  Detected INTERLEAVED stereo: averaged axis=1
  After mono: shape=(960,)
  Expected samples: 960
  Actual samples after conversion: 960
  ✅ Using sample rate: 48000 Hz
```

或者：

```
[MicRecorder] === RAW FRAME DEBUG ===
  Frame: sample_rate=48000, samples=960, layout=stereo, format=fltp
  to_ndarray() shape: (2, 960), dtype: float32
  Detected PLANAR stereo: averaged axis=0
  After mono: shape=(960,)
  Expected samples: 960
  Actual samples after conversion: 1920
  ⚠️  SAMPLE COUNT MISMATCH! Ratio: 2.00x
```

**問題**：樣本數變 2 倍 → 播放慢一倍

#### ❌ 問題情況 2：採樣率錯誤

```
[MicRecorder] === RAW FRAME DEBUG ===
  Frame: sample_rate=24000, samples=480, layout=stereo, format=fltp
  ...
  ✅ Using sample rate: 24000 Hz
```

但 WAV 檔案分析顯示：

```bash
$ python3 tests/test_mic_recording.py
📊 Size: 480000 bytes
🎚️  Sample rate: 48000 Hz  # ← 錯誤！實際應該是 24000
⏱️  Duration: 5.0 seconds   # ← 錯誤！實際應該是 2.5 秒
```

### 3. 檢查實際檔案

```bash
# 查看最新錄音
ls -lh resource/mic-record-*.wav | tail -1

# 分析檔案
python3 -c "
import wave
wav_file = 'resource/mic-record-20251102-XXXXXX.wav'  # 替換為實際檔名
with wave.open(wav_file, 'rb') as f:
    rate = f.getframerate()
    frames = f.getnframes()
    duration = frames / rate
    print(f'採樣率: {rate} Hz')
    print(f'Frame 數: {frames}')
    print(f'計算時長: {duration:.1f} 秒')
"
```

**預期結果**（錄 5 秒）：
- 48000 Hz: 240000 frames, 5.0 秒 ✅
- 24000 Hz: 120000 frames, 5.0 秒 ✅

**錯誤結果**（錄 5 秒但播 10 秒）：
- 48000 Hz: 480000 frames, 10.0 秒 ❌ ← 樣本數加倍！
- 48000 Hz: 240000 frames, 5.0 秒但播放 10 秒 ❌ ← 實際應該是 24kHz！

## 🔧 解決方案

### 修復已實施

我已經在程式中添加：

1. **自動偵測 Stereo 格式**
   - Planar `(channels, samples)` → 用 `axis=0`
   - Interleaved `(samples, channels)` → 用 `axis=1`

2. **樣本數驗證**
   - 比較轉換前後的樣本數
   - 如果不匹配會顯示警告

3. **詳細診斷日誌**
   - 顯示原始 frame 資訊
   - 顯示轉換過程
   - 顯示最終樣本數和時長

### 如果問題仍然存在

根據 Console 輸出判斷：

#### 情況 A：樣本數加倍 (Ratio: 2.00x)

**原因**：Stereo 轉換錯誤

**臨時解決**：檢查 Console 顯示的 shape，手動調整 axis

**請提供**：完整的 `RAW FRAME DEBUG` 輸出

#### 情況 B：樣本數正確但播放慢一倍

**原因**：採樣率報告錯誤

**檢查**：
```bash
# 在 Console 看到的採樣率
Frame: sample_rate=XXXXX

# 與實際 WAV 檔案的採樣率對比
python3 tests/test_mic_recording.py
```

如果不一致，需要進一步調查 WebRTC 設定。

## 📊 測試計算

### 正確的計算公式

```
樣本數 = 採樣率 × 時長（秒）
Bytes = 樣本數 × 2 (int16)

錄音 5 秒 @ 48kHz:
- 樣本數 = 48000 × 5 = 240000
- Bytes = 240000 × 2 = 480000 + 44 (header) = 480044 bytes

錄音 5 秒 @ 24kHz:
- 樣本數 = 24000 × 5 = 120000
- Bytes = 120000 × 2 = 240000 + 44 = 240044 bytes
```

### 如果檔案大小是 480044 bytes

**Case 1: Header 寫 48kHz**
- 樣本數 = 240000
- 時長 = 240000 / 48000 = 5.0 秒 ✅

**Case 2: Header 寫 24kHz**
- 樣本數 = 240000
- 時長 = 240000 / 24000 = 10.0 秒 ❌（慢一倍）

### 如果檔案大小是 960044 bytes（樣本數加倍）

**原因**：Stereo 轉換錯誤，樣本數變 2 倍
- 應該是 240000 samples
- 實際寫入 480000 samples
- 播放時間 = 480000 / 48000 = 10.0 秒（慢一倍）

## 🎯 請提供這些資訊

1. **Console 的完整 `RAW FRAME DEBUG` 輸出**
2. **實際錄音時長**（用碼表計時）
3. **播放時長**（播放器顯示）
4. **WAV 檔案大小**（bytes）
5. **執行測試腳本的輸出**：
   ```bash
   python3 tests/test_mic_recording.py
   ```

有了這些資訊，我可以精確定位問題並修復！

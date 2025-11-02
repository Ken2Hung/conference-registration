# 麥克風錄音問題診斷指南

## 問題：錄音已停止（未檢測到音訊數據）

這個問題表示雖然你按下了錄音和停止，但系統沒有接收到任何音訊數據。

## 🔍 診斷步驟

### 1. 查看 Console 日誌

修復後的程式會輸出詳細的診斷資訊。請執行以下步驟：

```bash
# 啟動應用程式（查看 terminal console）
./start.sh
```

### 2. 進行測試錄音

1. 開啟瀏覽器到麥克風錄音頁面
2. **打開瀏覽器的開發者工具** (F12 或右鍵 → 檢查)
3. 切換到 **Console** 標籤
4. 點擊「開始錄音」
5. 允許麥克風權限
6. 說話 5-10 秒
7. 點擊「停止錄音」

### 3. 分析 Console 輸出

#### ✅ 正常情況（應該看到）：

```
[MicRecorder] === Starting new recording ===
[MicRecorder] Token: 12345678...
[MicRecorder] File: resource/mic-record-20251102-120000.wav
[MicRecorder] Worker thread started: Thread-5
[MicRecorder] Current token set to: 12345678...
[MicRecorder] Recording state initialized, waiting for WebRTC stream...

[MicRecorder] Worker thread started for token 12345678...

[MicRecorder] === First Audio Callback ===
  Callback count: 1
  Token: 12345678...
  Original: 48000Hz, stereo, fltp
  Converted: 48000Hz, mono, s16
  Chunk size: 1920 bytes (960 samples)
  Duration: 0.020 seconds

[MicRecorder] First chunk queued successfully, RMS=1234.5

[MicRecorder] Opening WAV file: resource/mic-record-20251102-120000.wav
[MicRecorder] Sample rate: 48000 Hz
[MicRecorder] First chunk written: 1920 bytes, RMS=1234.5

[MicRecorder] Audio callback progress: 100 frames processed
[MicRecorder] Progress: 50 chunks, 1.0s

[MicRecorder] Stop signal received, processed 250 chunks, 480000 bytes
[MicRecorder] Closing WAV file, total: 480000 bytes
[MicRecorder] Worker thread finished

[MicRecorder] === Recording Summary ===
  Total callbacks: 250
  Bytes written: 480000
  Sample rate: 48000 Hz
[MicRecorder] ✅ Recording successful: 5.0 seconds
```

#### ❌ 問題情況 1：Audio callback 從未被調用

```
[MicRecorder] === Starting new recording ===
...
[MicRecorder] Worker thread started for token 12345678...

[停止錄音後]
[MicRecorder] === Recording Summary ===
  Total callbacks: 0
  Bytes written: 0
  Sample rate: 48000 Hz
[MicRecorder] ⚠️  WARNING: No audio data written
[MicRecorder] ⚠️  Audio callback was NEVER called - WebRTC stream may not have started
```

**可能原因**：
- WebRTC 串流未啟動
- 麥克風權限未授予
- 瀏覽器不支援 WebRTC

**解決方法**：
1. 確認瀏覽器已授權麥克風（檢查網址列的麥克風圖示）
2. 使用 Chrome 或 Edge 瀏覽器（不要用 Safari）
3. 確認 WebRTC 狀態顯示「已取得麥克風串流，正在錄音中」（綠色訊息）
4. 重新整理頁面並再試一次

#### ❌ 問題情況 2：Audio callback 被調用但沒有寫入數據

```
[MicRecorder] === Starting new recording ===
...
[MicRecorder] === First Audio Callback ===
  Callback count: 1
  ...
[MicRecorder] First chunk queued successfully, RMS=1234.5

[MicRecorder] Audio callback progress: 100 frames processed

[停止錄音後]
[MicRecorder] === Recording Summary ===
  Total callbacks: 250
  Bytes written: 0
  Sample rate: 48000 Hz
[MicRecorder] ⚠️  WARNING: No audio data written
[MicRecorder] ⚠️  Audio callback was called 250 times but no data was written
[MicRecorder] ⚠️  This suggests queue/worker issue - check logs above
```

**可能原因**：
- Worker thread 沒有從 queue 讀取數據
- Worker thread 啟動失敗
- Queue 傳遞問題

**解決方法**：
1. 檢查是否有 `[MicRecorder] Worker thread started` 訊息
2. 檢查是否有任何 Python 例外錯誤
3. 嘗試重新啟動應用程式

#### ❌ 問題情況 3：Queue 找不到

```
[MicRecorder] Warning: No queue found for token 12345678 at callback #1
[MicRecorder] Warning: No queue found for token 12345678 at callback #2
```

**可能原因**：
- Token 不匹配
- 初始化順序問題

**解決方法**：
1. 重新啟動應用程式
2. 清除瀏覽器快取

### 4. 檢查檔案系統

```bash
# 查看最新的錄音檔案
ls -lh resource/mic-record-*.wav | tail -3

# 檢查檔案大小
python3 tests/test_mic_recording.py
```

## 🛠️ 常見解決方案

### 方案 1：重新授權麥克風
1. 在瀏覽器網址列點擊鎖頭圖示
2. 找到麥克風權限
3. 設為「允許」
4. 重新整理頁面

### 方案 2：使用正確的瀏覽器
- ✅ 推薦：Chrome、Microsoft Edge
- ⚠️ 可能有問題：Firefox
- ❌ 不推薦：Safari（WebRTC 支援較差）

### 方案 3：檢查 WebRTC 狀態
錄音時應該看到：
- ✅ 綠色訊息：「已取得麥克風串流，正在錄音中」
- ⚠️ 黃色訊息：「正在嘗試建立 WebRTC 連線」→ 等待幾秒
- ❌ 紅色訊息：「無法取得麥克風串流」→ 檢查權限

### 方案 4：完全重啟
```bash
# 停止應用程式 (Ctrl+C)
# 清除舊音檔
rm resource/mic-record-*.wav

# 重新啟動
./start.sh
```

## 📊 預期的正常流程

1. **點擊開始錄音**
   - Console: `[MicRecorder] === Starting new recording ===`
   - Console: `[MicRecorder] Worker thread started`

2. **瀏覽器請求麥克風權限**
   - 點擊「允許」

3. **WebRTC 開始串流**
   - UI 顯示綠色訊息
   - Console: `[MicRecorder] === First Audio Callback ===`
   - Console: `[MicRecorder] First chunk queued successfully`
   - Console: `[MicRecorder] First chunk written`

4. **錄音進行中**
   - Console 每 100 frames 顯示進度
   - Console 每 50 chunks 顯示時長

5. **點擊停止錄音**
   - Console: `[MicRecorder] Stop signal received`
   - Console: `[MicRecorder] Closing WAV file`
   - Console: `[MicRecorder] ✅ Recording successful`
   - UI 顯示錄音時長

6. **檢查檔案**
   ```bash
   ls -lh resource/mic-record-*.wav
   # 應該看到新檔案，大小 > 44 bytes
   ```

## 🆘 如果問題仍然存在

請提供以下資訊：

1. **完整的 Console 輸出**（從開始錄音到停止）
2. **瀏覽器版本**（Chrome/Edge/Firefox/Safari）
3. **作業系統**（macOS/Windows/Linux）
4. **WebRTC 狀態訊息**（綠色/黃色/紅色）
5. **是否有任何錯誤訊息**

將這些資訊提供給開發者以進一步診斷。

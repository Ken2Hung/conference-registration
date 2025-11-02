# Microphone Recording Test Guide

## 修復內容總結

### 問題 1：短錄音（<5秒）不產生音檔
**原因**：Race condition - worker thread 還沒來得及寫入數據，檔案就被刪除

**修復**：
- 增加 worker 完成時間（timeout 從 1秒 → 3秒）
- 移除自動刪除空檔案的邏輯
- 優化停止流程：先發送停止信號 → 等待 worker 完成 → 再清理資源

### 問題 2：音訊播放速度異常
**原因**：強制 reformat 到 48000 Hz 可能導致採樣率轉換錯誤

**修復**：
- 自動偵測 WebRTC frame 的實際採樣率
- reformat 時保持原始採樣率，只轉換格式（s16）和聲道（mono）
- WAV 檔案使用偵測到的實際採樣率
- 添加詳細的診斷日誌

## 測試步驟

### 1. 啟動應用程式
```bash
./start.sh
```

### 2. 開啟麥克風錄音頁面
在瀏覽器中導航到錄音測試頁面（「麥克風錄音測試」）

**建議瀏覽器**：Chrome 或 Microsoft Edge（Safari 的 WebRTC 支援較不穩定）

### 3. 測試短錄音（3-5秒）
1. 點擊「▶️ 開始錄音」
2. 授權麥克風
3. 說話 3-5 秒
4. 點擊「⏹️ 停止錄音」
5. **檢查**：
   - Console 應顯示詳細的錄音資訊
   - `resource/` 目錄下應有新的 WAV 檔案
   - 檔案大小 > 44 bytes（不是空檔案）

### 4. 測試長錄音（30秒以上）
1. 點擊「▶️ 開始錄音」
2. 授權麥克風
3. 說話 30-60 秒
4. 點擊「⏹️ 停止錄音」
5. **檢查**：
   - 播放音檔，確認語速正常
   - 時長與實際錄音時間一致

### 5. 檢查 Console 輸出
應該看到類似的日誌：

```
[MicRecorder] Worker thread started for token 12345678...
[MicRecorder] Frame info:
  Original: 48000Hz, stereo, fltp
  Converted: 48000Hz, mono, s16
  Chunk size: 1920 bytes (960 samples)
  Duration: 0.020 seconds
[MicRecorder] Opening WAV file: resource/mic-record-20251102-120000.wav
[MicRecorder] Sample rate: 48000 Hz
[MicRecorder] First chunk written: 1920 bytes, RMS=1234.5
[MicRecorder] Progress: 50 chunks, 1.0s
[MicRecorder] Progress: 100 chunks, 2.0s
...
[MicRecorder] Stop signal received, processed 150 chunks, 288000 bytes
[MicRecorder] Closing WAV file, total: 288000 bytes
[MicRecorder] Worker thread finished
```

**重要資訊**：
- `Original`: WebRTC 提供的原始格式和採樣率
- `Converted`: 轉換後的格式（應保持相同採樣率）
- `Sample rate`: 寫入 WAV 的採樣率（應與 Original 一致）

### 6. 執行自動化測試
```bash
python3 tests/test_mic_recording.py
```

這會分析所有錄音檔案，檢測：
- 檔案大小和時長
- 採樣率一致性
- 是否為靜音
- 是否有採樣率 mismatch 問題

## 預期結果

### ✅ 成功指標
- 短錄音（3-5秒）正確產生音檔
- 長錄音（30秒+）語速正常
- Console 顯示正確的採樣率資訊
- 音檔可以正常播放，無速度異常

### ⚠️ 已知限制
- Safari 的 WebRTC 支援較不穩定，建議使用 Chrome
- 極短錄音（<1秒）可能因 queue 延遲而數據不完整
- 首次錄音可能需要等待瀏覽器授權麥克風

## 常見問題排查

### Q: 顯示「已錄製：0.0 秒」但有產生檔案
**可能原因**：
- UI 刷新延遲，重新載入頁面後應正常
- 檢查 Console 確認實際寫入的 bytes

### Q: 音訊播放速度還是很慢
**診斷步驟**：
1. 檢查 Console 的 "Original" 和 "Converted" 採樣率是否一致
2. 執行 `python3 tests/test_mic_recording.py` 檢查檔案
3. 如果 Original 是 16000Hz 但 WAV 是 48000Hz，表示還有問題

**可能解決方案**：
- 清除瀏覽器快取並重新載入
- 使用不同瀏覽器測試
- 檢查是否有舊版本的程式碼在執行

### Q: 無法取得麥克風權限
**解決方法**：
- 確認使用 HTTPS 或 localhost
- 檢查瀏覽器設定中的麥克風權限
- 嘗試使用隱私模式重新測試

## 測試後清理
```bash
# 刪除測試音檔
rm resource/mic-record-*.wav

# 或保留最新的幾個
ls -t resource/mic-record-*.wav | tail -n +6 | xargs rm
```

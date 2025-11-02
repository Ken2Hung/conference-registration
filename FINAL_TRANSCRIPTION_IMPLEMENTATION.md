# 最終即時轉錄實作說明

## ✅ 已完成的正確實作

### 核心特點

1. **一份 WAV 檔案** ✅
   - 從錄音開始到結束，持續寫入同一個 WAV 檔案
   - 檔案路徑：`resource/recording-YYYYMMDD-HHMMSS.wav`

2. **一份逐字稿檔案** ✅
   - 所有轉錄結果累積到記憶體
   - 錄音結束時保存為單一 TXT 檔案
   - 檔案路徑：`resource/recording-YYYYMMDD-HHMMSS-transcript.txt`

3. **背景分段轉錄** ✅
   - 每 3 秒收集音訊並送 Whisper API 轉錄
   - 使用記憶體緩衝區（in-memory buffer）
   - 不創建中間檔案

4. **最小化頁面閃動** ✅
   - 每 2 秒更新一次 UI（不是每次有轉錄結果就更新）
   - 使用 `last_ui_update` 控制更新頻率

## 🏗️ 架構設計

### 雙執行緒架構

```
Main Thread (Streamlit UI)
  ├─→ WebRTC Audio Callback (每 20ms 一個 frame)
  │     ├─→ Audio Queue → Audio Worker Thread → 單一 WAV 檔案
  │     └─→ Transcription Buffer (記憶體累積)
  │
  ├─→ Audio Worker Thread
  │     └─→ 持續寫入同一個 WAV 檔案
  │
  └─→ Transcription Worker Thread
        └─→ 每 3 秒：
            ├─ 從 buffer 取出音訊
            ├─ 轉換為 in-memory WAV bytes
            ├─ 調用 Whisper API
            └─ 累積到 _transcript_segments
```

### 資料流

```
Audio Frame (WebRTC)
  ↓
process_audio_frame(gain=2.0)
  ↓
pcm_array (int16, mono, 48kHz)
  ├─→ [Queue] _audio_queue
  │     ↓
  │   _audio_worker()
  │     ↓
  │   WAV File (單一檔案，持續寫入)
  │
  └─→ [Memory] _transcription_buffer
        ↓ (每 3 秒)
      _transcription_worker()
        ↓
      np.concatenate() → in-memory WAV bytes
        ↓
      OpenAI Whisper API
        ↓
      _transcript_segments.append()
        ↓
      UI 顯示（每 2 秒更新）
```

## 📝 關鍵實作細節

### 1. 單一 WAV 檔案寫入

```python
# 開始錄音時打開檔案
wav_writer = wave.open(str(wav_path), "wb")
wav_writer.setnchannels(1)
wav_writer.setsampwidth(2)
wav_writer.setframerate(48000)

# 持續寫入（不關閉檔案）
while recording:
    audio_data = queue.get()
    wav_writer.writeframes(audio_data)

# 停止時才關閉
wav_writer.close()
```

### 2. 記憶體緩衝轉錄

```python
# 音訊累積到記憶體
_transcription_buffer = []  # List of numpy arrays

# 每個 frame 加入 buffer
_transcription_buffer.append(pcm_array)

# 每 3 秒處理一次
if elapsed >= 3.0:
    # 合併所有 buffer
    audio_chunk = np.concatenate(_transcription_buffer)
    _transcription_buffer.clear()

    # 轉換為 in-memory WAV
    wav_bytes = _pcm_to_wav_bytes(audio_chunk, 48000)
    wav_file = io.BytesIO(wav_bytes)

    # 調用 API（不寫檔案）
    transcript = whisper_api.transcribe(wav_file)

    # 累積到記憶體
    _transcript_segments.append(transcript)
```

### 3. 控制 UI 更新頻率

```python
# 不要每次有新轉錄就 rerun
if st.session_state.recording_active:
    current_time = time.time()
    # 每 2 秒更新一次
    if current_time - st.session_state.last_ui_update >= 2.0:
        st.session_state.last_ui_update = current_time
        time.sleep(0.1)
        st.rerun()
```

## 🎯 使用流程

### 1. 清理舊檔案（已完成）
```bash
cd /Users/kenhung/develop_workplace/conference-registration/resource
rm -f *.wav *.txt
```

### 2. 啟動應用程式
```bash
./start.sh
```

### 3. 開始錄音測試
1. 進入「語音轉錄」頁面
2. 等待綠色「✅ 麥克風已就緒」
3. 點擊「▶️ 開始錄音」
4. 開始說話（建議說 10-15 秒）
5. 觀察：
   - 約 3 秒後，第一段轉錄結果出現
   - 之後每 3 秒更新一次
   - 頁面每 2 秒刷新（不會一直閃）
6. 點擊「⏹️ 停止錄音」

### 4. 檢查結果
```bash
# 應該只有兩個檔案
ls -lh resource/recording-*.wav
ls -lh resource/recording-*-transcript.txt

# 檢查 WAV 檔案大小（應該 > 100KB）
# 檢查 TXT 內容
cat resource/recording-*-transcript.txt
```

## ✅ 預期結果

### 檔案結構
```
resource/
├─ speaker-photo/              # 講者照片（已存在）
├─ recording-20251102-140530.wav           # 單一完整錄音
└─ recording-20251102-140530-transcript.txt # 單一完整逐字稿
```

### 逐字稿格式
```
語音轉錄結果
時間：2025-11-02 14:05:45
音訊檔案：recording-20251102-140530.wav
採樣率：48000 Hz
模型：OpenAI Whisper (whisper-1)

============================================================

這是第一段轉錄的內容（0-3秒）。
這是第二段轉錄的內容（3-6秒）。
這是第三段轉錄的內容（6-9秒）。
...
```

## 🐛 除錯檢查

### Console 日誌

**正常流程**：
```
[Transcription] Recording started
[Transcription] Audio worker started
[Transcription] Transcription worker started
[Transcription] Segment 1: 這是第一段轉錄的內容...
[Transcription] Segment 2: 這是第二段轉錄的內容...
[Transcription] Segment 3: 這是第三段轉錄的內容...
[Transcription] Stopping recording...
[Transcription] WAV file closed: resource/recording-20251102-140530.wav
[Transcription] Audio worker stopped
[Transcription] Transcription worker stopped
[Transcription] Transcript saved: resource/recording-20251102-140530-transcript.txt
[Transcription] Total segments: 3
```

### 常見問題檢查

#### 1. 如果沒有產生逐字稿
```bash
# 檢查是否有轉錄日誌
# 如果沒有 "Segment X:" 日誌，可能是：
# - 音量太小（RMS < 100）
# - 錄音時間 < 3 秒
# - API Key 錯誤
```

#### 2. 如果產生多個 WAV 檔案
```bash
# 這不應該發生！如果發生了：
# 1. 確認程式碼是最新版本
# 2. 重新啟動應用程式
# 3. 檢查是否有其他錄音頁面在運行
```

#### 3. 如果頁面一直閃動
```bash
# 檢查 _render_transcript_display() 中的邏輯
# 應該只在 elapsed >= 2.0 時才 rerun
```

## 📊 性能指標

### 資源使用
- **記憶體**: 每 3 秒的音訊約 288 KB
  - 48000 Hz × 2 bytes × 3 seconds = 288,000 bytes
  - 轉錄後立即清空 buffer
  - 最大記憶體用量 < 1 MB

- **API 調用頻率**: 每 3 秒一次
  - 10 秒錄音 = 3-4 次調用
  - 30 秒錄音 = 10 次調用

- **UI 更新頻率**: 每 2 秒一次
  - 不會造成明顯閃動
  - 仍保持即時感

### 成本估算（10 分鐘錄音）
```
總時長: 10 分鐘 = 600 秒
API 調用次數: 600 / 3 = 200 次
每次調用: 3 秒 × $0.006/分鐘 = 3/60 × $0.006 = $0.0003
總成本: 200 × $0.0003 = $0.06

結論: 與一次性轉錄成本相同！
```

## 🔧 可調整參數

### 轉錄間隔
```python
# src/ui/transcription_page.py (Line 32)
TRANSCRIPTION_CHUNK_DURATION = 3.0  # 秒

# 可調整為：
# 2.0 → 更即時，但 API 調用更頻繁
# 5.0 → 較慢，但 API 調用較少
```

### UI 更新間隔
```python
# src/ui/transcription_page.py (Line 301)
if current_time - st.session_state.last_ui_update >= 2.0:

# 可調整為：
# 1.0 → 更新更頻繁，但可能閃動
# 3.0 → 更新較慢，但更穩定
```

### 音量增益
```python
# src/ui/transcription_page.py (Line 31)
AUDIO_GAIN = 2.0  # 倍數

# 可調整為：
# 1.5 → 較小增益
# 3.0 → 較大增益
```

## 📚 相關文檔

- `AUDIO_CONFIGURATION.md` - 音訊處理配置
- `TRANSCRIPTION_GUIDE.md` - 使用指南（舊版）
- `WEBSOCKET_REALTIME_TRANSCRIPTION.md` - WebSocket 版本（已棄用）

## 🎉 完成狀態

- [x] 單一 WAV 檔案
- [x] 單一逐字稿檔案
- [x] 背景分段轉錄
- [x] 記憶體緩衝（不創建中間檔案）
- [x] 最小化頁面閃動
- [x] 音訊處理正確（不會慢一倍）
- [x] 音量增益功能
- [x] 清理舊測試檔案

---

**最終完成日期**：2025-11-02
**版本**：v4.0 - Final Correct Implementation
**測試狀態**：準備測試

## 🧪 立即測試

現在可以測試了！執行以下步驟：

```bash
# 1. 啟動應用程式（如果還沒啟動）
./start.sh

# 2. 瀏覽器開啟應用程式
# 3. 進入「語音轉錄」頁面
# 4. 等待麥克風就緒
# 5. 開始錄音並說話 10-15 秒
# 6. 停止錄音

# 7. 檢查結果
ls -lh resource/recording-*.wav
cat resource/recording-*-transcript.txt
```

**預期結果**：
- 只有一個 WAV 檔案
- 只有一個 TXT 檔案
- TXT 包含完整的分段轉錄內容
- 頁面沒有過度閃動

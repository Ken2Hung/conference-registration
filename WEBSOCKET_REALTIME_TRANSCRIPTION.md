# WebSocket 即時轉錄架構說明

## ✅ 已重構為正確的 Realtime API 架構

### 問題分析

**舊版本的問題**：
- ❌ 每 3 秒創建一個獨立的 WAV chunk 檔案
- ❌ 每個 chunk 單獨調用 Whisper API
- ❌ 產生大量小檔案（很多空的轉錄結果）
- ❌ 不是真正的即時轉錄

**新版本的改進**：
- ✅ 使用 WebSocket 持續串流音訊
- ✅ 透過事件驅動接收轉錄結果
- ✅ 只產生一份完整的 WAV 和一份完整的逐字稿
- ✅ 真正的即時轉錄效果

## 🏗️ 新架構設計

### 整體流程

```
User
  ↓ Start Recording
AudioRecorder Component (transcription_page.py)
  ↓ startRecording()
audioStore (Global State)
  ├─→ Audio Processor Worker (_audio_worker)
  │     ↓ Process Audio Data
  │     ↓ WAV Data
  │     └─→ WAV File (resource/recording-*.wav)
  │
  └─→ Realtime Transcription Service
        ↓ sendAudioChunk() → WebSocket
        ↓ OpenAI Realtime API (WebSocket)
        ↓ Event: conversation.item.input_audio_transcription.completed
        ↓ Transcribed Text
        └─→ Callback: _on_transcript_done()
              ↓ Update transcriptStore (_realtime_transcript)
              ↓ MESSAGE
              └─→ Update Transcription (UI)
```

### 核心組件

#### 1. RealtimeTranscriptionService
**位置**: `src/services/realtime_transcription_service.py`

**功能**：
- WebSocket 連線管理
- 音訊串流發送
- 事件監聽與回調
- 自動重連處理

**主要方法**：
```python
# 啟動 WebSocket 連線
service.start()

# 發送音訊片段
service.send_audio_chunk(pcm_array)

# 停止連線
service.stop()

# 獲取完整逐字稿
transcript = service.get_full_transcript()
```

#### 2. Audio Callback (WebRTC)
**位置**: `src/ui/transcription_page.py:audio_callback()`

**流程**：
```python
def audio_callback(frame: av.AudioFrame):
    # 1. 處理音訊（stereo → mono, 音量增益）
    pcm_array = process_audio_frame(frame, gain=2.0)

    # 2. 計算 RMS（音量監控）
    rms = calculate_rms(pcm_array)

    # 3. 同時進行兩個操作：
    if recording_active:
        # A. 寫入 WAV 檔案（完整錄音）
        _audio_queue.put(pcm_array.tobytes())

        # B. 發送到 Realtime API（即時轉錄）
        _transcription_service.send_audio_chunk(pcm_array)
```

#### 3. 事件回調機制

**轉錄完成回調**：
```python
def _on_transcript_done(transcript: str):
    # 收到完整的轉錄段落
    _realtime_transcript.append(transcript)
    st.session_state.segment_count += 1
```

**部分更新回調**（可選）：
```python
def _on_transcript_delta(delta: str):
    # 收到部分轉錄文字（漸進式顯示）
    print(f"Delta: {delta}")
```

**錯誤處理回調**：
```python
def _on_transcription_error(error: str):
    st.session_state.transcription_status = f"❌ {error}"
```

## 📊 WebSocket 訊息格式

### 1. Session Configuration
```json
{
  "type": "session.update",
  "session": {
    "modalities": ["text", "audio"],
    "input_audio_format": "pcm16",
    "input_audio_transcription": {
      "model": "whisper-1"
    },
    "turn_detection": {
      "type": "server_vad",
      "threshold": 0.5,
      "prefix_padding_ms": 300,
      "silence_duration_ms": 500
    }
  }
}
```

### 2. 發送音訊
```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64_encoded_pcm_data..."
}
```

### 3. 接收轉錄結果
```json
{
  "type": "conversation.item.input_audio_transcription.completed",
  "transcript": "這是轉錄的文字內容..."
}
```

## 🔧 技術細節

### 音訊處理

**格式**：
- 採樣率：48000 Hz
- 格式：PCM16 (int16)
- 聲道：Mono（單聲道）
- 音量增益：2.0x

**處理流程**：
```
WebRTC Frame (stereo, 48kHz)
  ↓
process_audio_frame(frame, gain=2.0)
  ↓ deinterleave stereo → mono
  ↓ apply volume gain
  ↓
NumPy array (int16, mono)
  ↓
├─→ WAV Writer Queue → WAV File
└─→ Realtime API → base64 encode → WebSocket
```

### 執行緒模型

```
主執行緒 (Streamlit UI)
  ├─→ WebRTC Audio Callback (streamlit-webrtc)
  ├─→ _audio_worker (WAV 寫入執行緒)
  └─→ RealtimeTranscriptionService
        └─→ WebSocket Event Loop (asyncio, 獨立執行緒)
```

### 狀態同步

使用 `threading.Lock` 確保執行緒安全：

```python
_recording_lock = threading.Lock()  # 錄音狀態
_wav_lock = threading.Lock()        # WAV 寫入
_rms_lock = threading.Lock()        # RMS 值
_transcript_lock = threading.Lock() # 逐字稿累積
```

## 🚀 使用方法

### 1. 安裝依賴
```bash
pip install websockets>=12.0
```

### 2. 設定 API Key
```bash
# 方法 A：環境變數
export OPENAI_API_KEY=sk-...

# 方法 B：.env 檔案
echo "OPENAI_API_KEY=sk-..." > .env

# 方法 C：頁面輸入（首次啟動時）
```

### 3. 啟動應用程式
```bash
./start.sh
```

### 4. 使用流程
1. **等待麥克風就緒**：綠色「✅ 麥克風已就緒」
2. **開始錄音**：點擊「▶️ 開始錄音」
3. **說話**：開始說話，逐字稿會即時出現
4. **停止錄音**：點擊「⏹️ 停止錄音」
5. **查看結果**：
   - 完整逐字稿顯示在頁面
   - 可下載 TXT 檔案
   - WAV 錄音保存在 `resource/` 目錄

## 📁 檔案結構

### 每次錄音只產生兩個檔案

```
resource/
├─ recording-20251102-123456.wav           # 完整錄音
└─ recording-20251102-123456-transcript.txt # 完整逐字稿
```

**不再產生**：
- ❌ 多個 chunk WAV 檔案
- ❌ 空的轉錄檔案
- ❌ 臨時檔案

## ⚙️ 配置參數

### 音訊配置
```python
# src/ui/transcription_page.py
SAMPLE_RATE = 48000      # 採樣率（不可更改，WebRTC 固定）
SAMPLE_WIDTH = 2         # 位元深度（不可更改，PCM16）
AUDIO_GAIN = 2.0         # 音量增益（可調整：1.0 - 3.0）
```

### WebSocket 配置
```python
# src/services/realtime_transcription_service.py
url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

# VAD（語音活動偵測）設定
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,           # 靈敏度（0.0 - 1.0）
    "prefix_padding_ms": 300,   # 前置緩衝（毫秒）
    "silence_duration_ms": 500  # 靜音判定時間（毫秒）
}
```

## 🐛 除錯與監控

### Console 日誌

```bash
# WebSocket 連線
[RealtimeTranscription] Service started
[RealtimeTranscription] WebSocket connected
[RealtimeTranscription] Session configured

# 轉錄結果
[Transcription] Segment done: 這是第一段轉錄的內容...
[Transcription] Segment done: 這是第二段轉錄的內容...

# 停止
[RealtimeTranscription] Service stopped
[RealtimeTranscription] WebSocket closed
```

### 常見錯誤

#### 1. WebSocket 連線失敗
```
[RealtimeTranscription] Connection error: ...
```
**解決方法**：
- 檢查 API Key 是否正確
- 檢查網路連線
- 確認 API 配額未用盡

#### 2. 沒有轉錄結果
**可能原因**：
- 音量太小（檢查 RMS 值）
- 背景噪音太大
- VAD 閾值太高

**解決方法**：
```python
# 提高音量增益
AUDIO_GAIN = 3.0

# 降低 VAD 閾值
"threshold": 0.3
```

## 💰 成本分析

### OpenAI Realtime API 定價
- **音訊輸入**：$0.06 / 分鐘
- **音訊輸出**：$0.24 / 分鐘（本應用不使用）
- **文字輸入/輸出**：標準 GPT-4 價格

### 成本估算
```
錄音 10 分鐘：
- 音訊輸入：10 * $0.06 = $0.60
- 文字轉錄：包含在音訊輸入中
總成本：$0.60
```

**注意**：
- 比 Whisper API ($0.006/分鐘) 貴 10 倍
- 但提供即時轉錄體驗
- 適合需要即時反饋的場景

## 🆚 與舊版本比較

| 特性 | 舊版（Whisper API 分段） | 新版（Realtime API WebSocket） |
|------|------------------------|------------------------------|
| **轉錄方式** | 每 3 秒調用一次 Whisper API | WebSocket 持續串流 |
| **檔案產生** | 多個 chunk 檔案 | 單一完整檔案 |
| **即時性** | 每 3 秒更新一次 | 真正即時（VAD 觸發） |
| **API 成本** | $0.006/分鐘 | $0.06/分鐘 |
| **準確度** | 高 | 高 |
| **實現複雜度** | 中等 | 較高 |
| **適用場景** | 批次轉錄 | 即時轉錄 |

## ✅ 檢查清單

- [x] 使用 OpenAI Realtime API (gpt-4o-realtime-preview)
- [x] WebSocket 串流音訊
- [x] 事件驅動轉錄更新
- [x] 只產生一份 WAV 和一份 TXT
- [x] 真正的即時顯示效果
- [x] 音訊處理正確（不會慢一倍）
- [x] 音量增益功能
- [x] 執行緒安全
- [x] 錯誤處理與重連

---

**重構完成日期**：2025-11-02
**版本**：v3.0 - WebSocket Realtime Transcription
**測試狀態**：待測試

## 🧪 測試步驟

1. 安裝依賴：`pip install websockets`
2. 啟動應用：`./start.sh`
3. 進入語音轉錄頁面
4. 等待麥克風就緒
5. 開始錄音並說話
6. 觀察即時轉錄結果
7. 停止錄音
8. 檢查 `resource/` 目錄：
   - 應該只有一個 WAV 檔案
   - 應該只有一個 TXT 檔案
   - TXT 應該包含完整轉錄內容

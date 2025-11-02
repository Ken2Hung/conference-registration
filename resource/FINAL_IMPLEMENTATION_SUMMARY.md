# 語音轉錄功能最終實作總結

## 📅 完成日期
**2025-11-02**

## ✅ 完成的所有功能

### 核心功能
1. **即時語音轉錄** - 使用 OpenAI Whisper API 進行即時轉錄
2. **單一檔案輸出** - 每次錄音只產生一個 WAV 和一個 TXT
3. **背景分段轉錄** - 每 3 秒在背景進行轉錄，不創建中間檔案
4. **記憶體緩衝** - 使用 in-memory buffer 處理音訊，減少磁碟 I/O

### 最新改進（2025-11-02）
1. **麥克風權限自動請求** ✅
   - 進入頁面時自動請求麥克風權限
   - 用戶不需要點擊按鈕即可授權

2. **語音活動檢測（VAD）** ✅
   - 使用 RMS 閾值過濾靜音片段
   - 防止 Whisper 在靜音時產生奇怪字幕
   - 閾值: RMS < 300.0 的片段會被跳過

3. **繁體中文 Prompt** ✅
   - 添加繁體中文提示給 Whisper API
   - 明確要求不在靜音時產生文字
   - 提高轉錄準確度

## 🏗️ 技術架構

### Token-Based 狀態管理
使用唯一 token 管理每次錄音的狀態：
```python
_active_token: Optional[str] = None
_audio_queues: dict[str, "queue.Queue"] = {}
_transcription_buffers: dict[str, list] = {}
_transcript_segments: dict[str, list] = {}
_wav_writers: dict[str, wave.Wave_write] = {}
```

### 雙執行緒架構
```
Main Thread (Streamlit UI)
  ├─→ WebRTC Audio Callback (每 20ms)
  │     ├─→ Audio Queue → Audio Worker Thread
  │     └─→ Transcription Buffer (記憶體累積)
  │
  ├─→ Audio Worker Thread
  │     └─→ 持續寫入單一 WAV 檔案
  │
  └─→ Transcription Worker Thread
        └─→ 每 3 秒：
            ├─ VAD 檢查 (RMS >= 300.0)
            ├─ 轉換為 in-memory WAV bytes
            ├─ 調用 Whisper API (繁體中文 prompt)
            └─→ 累積到記憶體

Stop Event
  └─→ 優雅停止所有執行緒
        └─→ 保存完整逐字稿 TXT
```

### 音訊處理流程
```
WebRTC Frame (stereo, 48kHz)
  ↓
process_audio_frame(frame, gain=2.0)
  ↓ deinterleave stereo → mono
  ↓ apply volume gain (2.0x)
  ↓
NumPy array (int16, mono, 48000 Hz)
  ├─→ [Queue] → Audio Worker → Single WAV File
  └─→ [Memory Buffer] → Transcription Worker
                        ↓
                     VAD Check (RMS >= 300.0)
                        ↓ (Pass)
                     Whisper API (繁體中文 prompt)
                        ↓
                     Transcript Segments (記憶體)
                        ↓
                     UI Display (每 2 秒更新)
```

## 📝 關鍵實作細節

### 1. 麥克風權限自動請求
**檔案**: `src/ui/transcription_page.py:210`
```python
webrtc_ctx = webrtc_streamer(
    key="transcription-mic",
    mode=WebRtcMode.SENDONLY,
    audio_frame_callback=audio_callback,
    media_stream_constraints={"audio": True, "video": False},
    rtc_configuration=rtc_configuration,
    async_processing=True,
    desired_playing_state=True,  # ← 自動請求麥克風權限
)
```

**原理**: `desired_playing_state=True` 會在頁面載入時立即啟動 WebRTC，觸發瀏覽器的麥克風權限請求。

### 2. VAD 語音活動檢測
**檔案**: `src/ui/transcription_page.py:34, 564-569`
```python
# 閾值常數
VAD_RMS_THRESHOLD = 300.0  # Minimum RMS to consider as speech

# 在 transcription worker 中檢查
chunk_rms = float(calculate_rms(audio_chunk))

if chunk_rms < VAD_RMS_THRESHOLD:
    print(f"[Transcription] Skipping silent chunk (RMS={chunk_rms:.1f} < {VAD_RMS_THRESHOLD})")
    continue
```

**原理**:
- 計算音訊片段的 RMS（Root Mean Square）值
- RMS 值代表音量強度
- 低於閾值的片段被視為靜音，不送 API 轉錄
- 防止 Whisper 在靜音時產生幻覺字幕

### 3. 繁體中文 Prompt
**檔案**: `src/ui/transcription_page.py:577-584`
```python
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=wav_file,
    language="zh",  # 指定中文
    response_format="text",
    prompt="以下是繁體中文的語音內容。請準確轉錄，不要在靜音或背景噪音時產生文字。"
)
```

**原理**:
- `language="zh"` 提示模型使用中文
- Prompt 明確要求繁體中文
- 指示不在靜音時產生文字，減少幻覺

### 4. 單一 WAV 檔案寫入
**檔案**: `src/ui/transcription_page.py:421-479`
```python
# 開始錄音時打開 WAV 檔案
wav_writer = wave.open(str(wav_path), "wb")
wav_writer.setnchannels(1)
wav_writer.setsampwidth(2)
wav_writer.setframerate(48000)

# 持續寫入（不關閉檔案）
while not stop_event.is_set():
    try:
        audio_data, rms = audio_queue.get(timeout=0.1)
        wav_writer.writeframes(audio_data)
        bytes_written += len(audio_data)
    except queue.Empty:
        continue

# 停止時才關閉
wav_writer.close()
```

### 5. 記憶體緩衝轉錄
**檔案**: `src/ui/transcription_page.py:521-595`
```python
# 累積到記憶體
transcription_buffer.append(pcm_array)

# 每 3 秒處理一次
if elapsed >= TRANSCRIPTION_CHUNK_DURATION:
    audio_chunk = np.concatenate(buffer)
    buffer.clear()

    # VAD 檢查
    if chunk_rms < VAD_RMS_THRESHOLD:
        continue

    # 轉換為 in-memory WAV bytes
    wav_bytes = _pcm_to_wav_bytes(audio_chunk, SAMPLE_RATE)
    wav_file = io.BytesIO(wav_bytes)  # ← 不寫檔案

    # 調用 API
    transcript = client.audio.transcriptions.create(...)

    # 累積到記憶體
    segments.append(transcript)
```

## 🔧 配置參數

### 可調整參數
```python
# 音訊處理
SAMPLE_RATE = 48000        # 採樣率（固定，WebRTC 標準）
AUDIO_GAIN = 2.0           # 音量增益 (1.0 - 3.0)

# 轉錄設定
TRANSCRIPTION_CHUNK_DURATION = 3.0  # 轉錄間隔（秒）
VAD_RMS_THRESHOLD = 300.0           # VAD 閾值（調整靈敏度）

# UI 更新
UI_UPDATE_INTERVAL = 2.0   # UI 更新頻率（秒）
```

### 調整建議

**如果背景噪音大**:
```python
VAD_RMS_THRESHOLD = 500.0  # 提高閾值
```

**如果想更即時**:
```python
TRANSCRIPTION_CHUNK_DURATION = 2.0  # 縮短間隔
UI_UPDATE_INTERVAL = 1.0            # 更頻繁更新
```

**如果聲音太小**:
```python
AUDIO_GAIN = 3.0  # 提高增益
```

## 📊 測試準備

### 環境檢查
- ✅ Streamlit 應用程式正在運行
- ✅ 舊測試檔案已清理
- ✅ Python 語法檢查通過
- ✅ 瀏覽器可訪問 http://localhost:8501

### 測試文檔
已創建完整測試指南: `resource/TESTING_GUIDE.md`

包含:
- 詳細測試步驟
- 預期結果說明
- 檢查清單
- 問題排查指引

## 📁 檔案結構

### 每次錄音產生的檔案
```
resource/
├─ recording-YYYYMMDD-HHMMSS.wav           # 完整錄音（單一檔案）
└─ recording-YYYYMMDD-HHMMSS-transcript.txt # 完整逐字稿（單一檔案）
```

### 逐字稿格式範例
```
語音轉錄結果
時間：2025-11-02 17:30:45
音訊檔案：recording-20251102-173045.wav
採樣率：48000 Hz
模型：OpenAI Whisper (whisper-1)

============================================================

這是第一段轉錄的內容。
這是第二段轉錄的內容。
這是第三段轉錄的內容。
```

## 🐛 已修復的所有問題

### 問題 1: RecursionError
- **原因**: `load_dotenv()` 每次渲染都被調用
- **修復**: 使用全局變數快取檢查結果

### 問題 2: 多個檔案生成
- **原因**: 每 3 秒創建一個 chunk WAV 檔案
- **修復**: 改為單一 WAV + in-memory 處理

### 問題 3: 無法收到音訊
- **原因**: WebRTC 狀態未正確綁定
- **修復**: 使用 token-based 系統

### 問題 4: 頁面閃爍
- **原因**: 每次轉錄都 rerun
- **修復**: 控制 UI 更新頻率（每 2 秒）

### 問題 5: 按鈕重複觸發
- **原因**: 停止按鈕未 disable
- **修復**: 添加 `disabled` 屬性

### 問題 6: 靜音時產生奇怪字幕
- **原因**: Whisper 會在靜音時幻覺
- **修復**: 添加 VAD 過濾 + 繁體中文 prompt

### 問題 7: 麥克風權限流程
- **原因**: 需要手動點擊才請求權限
- **修復**: 頁面載入時自動請求

## 📚 相關文檔

- `TESTING_GUIDE.md` - 測試指南（本次創建）
- `FINAL_FIX_SUMMARY.md` - 問題修復總結
- `FINAL_TRANSCRIPTION_IMPLEMENTATION.md` - 實作細節
- `AUDIO_CONFIGURATION.md` - 音訊配置說明
- `WEBSOCKET_REALTIME_TRANSCRIPTION.md` - WebSocket 版本（已棄用）

## 💰 成本分析

### OpenAI Whisper API 定價
- **每分鐘**: $0.006
- **10 分鐘錄音**: $0.06
- **完全免費額度**: 無（需付費）

### 實際成本估算
```
錄音時長: 15 秒
轉錄次數: 15s / 3s = 5 次
每次時長: 3 秒
每次成本: 3/60 × $0.006 = $0.0003
總成本: 5 × $0.0003 = $0.0015 ≈ $0.002

結論: 15 秒錄音約 $0.002，與一次性轉錄成本相同
```

## ✅ 完成清單

- [x] 單一 WAV 檔案輸出
- [x] 單一逐字稿檔案輸出
- [x] 背景分段轉錄
- [x] 記憶體緩衝處理（不創建中間檔案）
- [x] 最小化頁面閃動
- [x] 音訊處理正確（stereo → mono）
- [x] 音量增益功能
- [x] Token-based 狀態管理
- [x] 執行緒安全
- [x] 麥克風權限自動請求
- [x] VAD 語音活動檢測
- [x] 繁體中文 prompt
- [x] 清理舊測試檔案
- [x] 創建測試指南

## 🚀 下一步

### 立即可進行的測試
1. 瀏覽器開啟 http://localhost:8501
2. 點擊「語音轉錄」頁面
3. 允許麥克風權限
4. 按照 `TESTING_GUIDE.md` 進行測試

### 建議的改進（未來）
1. **可調整 VAD 閾值 UI** - 讓用戶在頁面上調整閾值
2. **音訊視覺化** - 顯示波形或頻譜
3. **導出格式選項** - 支援 SRT, VTT 等字幕格式
4. **多語言支援** - 支援英文、日文等其他語言

---

**最終版本**: v5.1 - Complete with VAD and Auto Mic Request
**測試狀態**: 準備就緒，可立即測試
**文檔狀態**: 完整
**建議瀏覽器**: Chrome / Edge（WebRTC 支援最佳）

# 時間軸格式更新說明

## 📅 更新日期
**2025-11-02**

## ✨ 新功能

### 時間軸顯示格式
現在轉錄結果會顯示**時間軸**，方便對照音訊時間點！

**格式**: `HH:MM  逐字稿內容`

其中：
- `HH` = 小時（從錄音開始計算）
- `MM` = 分鐘（從錄音開始計算）
- 雙空格分隔時間和內容

## 📝 顯示範例

### UI 即時顯示
```
00:00  歡迎大家來到今天的會議。
00:03  今天我們要討論的主題是語音轉錄技術。
00:06  首先讓我介紹一下 Whisper API 的功能。
00:09  Whisper 是 OpenAI 開發的語音識別模型。
00:12  它支援多種語言，包括繁體中文。
```

### 保存的 TXT 文檔格式
```
語音轉錄結果
時間：2025-11-02 17:45:30
音訊檔案：recording-20251102-174530.wav
採樣率：48000 Hz
模型：OpenAI Whisper (whisper-1)
格式：時間軸（HH:MM）+ 逐字稿內容

============================================================

00:00  歡迎大家來到今天的會議。
00:03  今天我們要討論的主題是語音轉錄技術。
00:06  首先讓我介紹一下 Whisper API 的功能。
00:09  Whisper 是 OpenAI 開發的語音識別模型。
00:12  它支援多種語言，包括繁體中文。
```

## 🔧 技術實作

### 資料結構變更

**舊格式**（純文字）:
```python
_transcript_segments[token] = [
    "歡迎大家來到今天的會議。",
    "今天我們要討論的主題是語音轉錄技術。",
    ...
]
```

**新格式**（包含時間戳）:
```python
_transcript_segments[token] = [
    {"time": "00:00", "text": "歡迎大家來到今天的會議。"},
    {"time": "00:03", "text": "今天我們要討論的主題是語音轉錄技術。"},
    ...
]
```

### 時間計算邏輯

**相對時間計算**:
```python
# 錄音開始時記錄時間戳
_recording_start_time[token] = time.time()

# 轉錄時計算相對時間
elapsed_seconds = int(current_time - start_time)
hours = elapsed_seconds // 3600
minutes = (elapsed_seconds % 3600) // 60
time_str = f"{hours:02d}:{minutes:02d}"
```

**範例**:
- 錄音開始: 17:45:00
- 第一段轉錄: 17:45:03 → 相對時間 00:00 (因為是前 3 秒的累積)
- 第二段轉錄: 17:45:06 → 相對時間 00:03
- 第三段轉錄: 17:45:09 → 相對時間 00:06

### 顯示邏輯

**即時顯示**（`src/ui/transcription_page.py:274-281`）:
```python
formatted_lines = []
for seg in segments:
    if isinstance(seg, dict):
        formatted_lines.append(f"{seg['time']}  {seg['text']}")
    else:
        # Fallback for old format (backward compatibility)
        formatted_lines.append(str(seg))

current_transcript = "\n".join(formatted_lines)
```

**檔案保存**（使用相同邏輯）:
- 使用相同的格式化邏輯
- 保存到 TXT 時包含時間軸
- 檔案頭部說明格式

## 📊 使用案例

### 案例 1: 短時間錄音（< 1 小時）
```
00:00  開始錄音。
00:03  這是第一段內容。
00:06  這是第二段內容。
00:15  經過 15 秒了。
00:30  經過 30 秒了。
00:45  經過 45 秒了。
```

### 案例 2: 長時間錄音（> 1 小時）
```
00:00  會議開始。
00:03  介紹與會人員。
00:15  第一個議題討論。
00:30  中場休息前的總結。
01:00  經過一小時，繼續下一個議題。
01:15  第二個議題討論。
02:30  會議結束。
```

### 案例 3: 包含靜音過濾
```
00:00  開始說話。
00:03  繼續說話。
（靜音 5 秒，VAD 過濾掉）
00:12  重新開始說話。
00:15  結束。
```

注意：靜音期間不會產生轉錄結果，所以時間軸可能會跳躍。

## ✅ 優點

1. **時間定位** - 快速找到特定時間點的內容
2. **對照音訊** - 可以對照 WAV 檔案的時間點
3. **會議記錄** - 方便記錄會議時間軸
4. **字幕製作** - 可以作為字幕檔的基礎

## 🔄 向後兼容

代碼包含向後兼容邏輯：
```python
if isinstance(seg, dict):
    # 新格式：使用時間軸
    formatted_lines.append(f"{seg['time']}  {seg['text']}")
else:
    # 舊格式：直接輸出文字
    formatted_lines.append(str(seg))
```

如果系統中有舊的 session，仍然可以正常顯示。

## 📁 修改的檔案

### src/ui/transcription_page.py
**修改位置**:
1. Line 51: 添加 `_recording_start_time` 字典
2. Line 359: 記錄錄音開始時間
3. Line 596-616: 轉錄時計算相對時間並儲存 dict
4. Line 274-281: UI 顯示使用時間軸格式
5. Line 445-454: 停止時格式化時間軸
6. Line 668: 檔案頭部說明格式

## 🧪 測試步驟

### 1. 基本測試
1. 開始錄音
2. 說話 3 秒 → 預期看到 `00:00 [你的內容]`
3. 再說話 3 秒 → 預期看到 `00:03 [你的內容]`
4. 停止錄音
5. 檢查 TXT 檔案格式

### 2. 長時間測試
1. 錄音 5 分鐘
2. 檢查時間軸是否正確
3. 預期看到 `00:00`, `00:03`, ..., `04:57` 等

### 3. 靜音測試
1. 說話 3 秒
2. 靜音 10 秒
3. 再說話 3 秒
4. 檢查時間軸是否跳躍（例如 `00:00` → `00:13`）

## 📝 預期輸出範例

### Console 日誌
```
[Transcription] Starting recording with token 9c79a7a3
[Transcription] WAV path: resource/recording-20251102-174530.wav
[Transcription] Audio worker started for token 9c79a7a3
[Transcription] Transcription worker started for token 9c79a7a3
[Transcription] Segment 1 [00:00] (RMS=2463.3): 歡迎大家來到今天的會議。
[Transcription] Segment 2 [00:03] (RMS=6497.8): 今天我們要討論的主題是語音轉錄技術。
[Transcription] Skipping silent chunk (RMS=89.3 < 300.0)
[Transcription] Segment 3 [00:09] (RMS=3214.5): 首先讓我介紹一下 Whisper API 的功能。
[Transcription] Stopping recording for token 9c79a7a3
[Transcription] Saved transcript: resource/recording-20251102-174530-transcript.txt
```

### UI 顯示
即時轉錄結果文字區塊：
```
00:00  歡迎大家來到今天的會議。
00:03  今天我們要討論的主題是語音轉錄技術。
00:09  首先讓我介紹一下 Whisper API 的功能。
```

### TXT 文檔內容
```
語音轉錄結果
時間：2025-11-02 17:45:45
音訊檔案：recording-20251102-174530.wav
採樣率：48000 Hz
模型：OpenAI Whisper (whisper-1)
格式：時間軸（HH:MM）+ 逐字稿內容

============================================================

00:00  歡迎大家來到今天的會議。
00:03  今天我們要討論的主題是語音轉錄技術。
00:09  首先讓我介紹一下 Whisper API 的功能。
```

## 💡 未來可能的改進

1. **秒級精度**: 改為 `HH:MM:SS` 格式
2. **SRT 字幕格式**: 導出標準字幕檔
3. **時間戳可點擊**: UI 上點擊時間可跳轉到音訊位置
4. **時間區間**: 顯示每段的起始和結束時間

---

**更新版本**: v5.3 - Timeline Format Support
**狀態**: 已完成
**測試**: 準備測試

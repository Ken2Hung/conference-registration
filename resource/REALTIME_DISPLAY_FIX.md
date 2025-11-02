# 即時顯示修復與時間格式更新

## 📅 更新日期
**2025-11-02**

## 🐛 問題描述

### 問題 1: 即時顯示不工作
**症狀**: 按下「開始錄音」後，下方一直顯示「🎤 錄音中，等待第一段轉錄結果（約 3 秒後）...」，但沒有呈現逐字稿內容。

**可能原因**:
1. 轉錄結果沒有正確保存到 `_transcript_segments[token]`
2. UI 讀取 segments 時出錯
3. 格式化邏輯有問題
4. UI 更新頻率不夠

### 問題 2: 時間格式需求變更
**需求**: 時間軸格式從 `HH:MM` 改為 `yyyy-mm-dd hh:mi:ss`

## ✅ 修復方案

### 修復 1: 時間格式更新

**修改位置**: `src/ui/transcription_page.py:618`

**修改前**:
```python
# Use actual clock time (HH:MM)
time_str = datetime.now().strftime("%H:%M")
```

**修改後**:
```python
# Use actual clock time (yyyy-mm-dd hh:mi:ss)
time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

**新格式範例**:
```
2025-11-02 17:45:23  歡迎大家來到今天的會議。
2025-11-02 17:45:26  今天我們要討論的主題是語音轉錄技術。
2025-11-02 17:45:29  首先讓我介紹一下 Whisper API 的功能。
```

### 修復 2: 添加詳細除錯訊息

**目的**: 追蹤轉錄結果是否正確保存和讀取

**修改位置**:
1. `src/ui/transcription_page.py:269-276` - UI 讀取時的除錯
2. `src/ui/transcription_page.py:627-633` - 轉錄 worker 保存時的除錯

**添加的除錯訊息**:

**UI 端**:
```python
print(f"[Transcription UI] Active: {st.session_state.transcription_active}, Token: {token[:8] if token else 'None'}")
print(f"[Transcription UI] Retrieved {len(segments)} segments from token {token[:8]}")
if segments:
    print(f"[Transcription UI] Displaying {len(segments)} segments")
```

**Worker 端**:
```python
if segments is not None:
    segments.append(segment_data)
    segment_count = len(segments)
    print(f"[Transcription] Segment {segment_count} [{time_str}] (RMS={chunk_rms:.1f}): {transcript[:50]}...")
    print(f"[Transcription] Total segments in buffer: {segment_count}")
else:
    print(f"[Transcription] ERROR: segments list is None for token {token[:8]}")
```

### 修復 3: UI 即時更新確認

**檢查項目**:
1. ✅ UI 更新頻率：每 1 秒
2. ✅ Segments 讀取邏輯正確
3. ✅ 格式化邏輯支援 dict 格式
4. ✅ 顯示 token 資訊以便除錯

**UI 顯示邏輯** (`src/ui/transcription_page.py:272-304`):
```python
if st.session_state.transcription_active and token:
    with _recorder_lock:
        segments = _transcript_segments.get(token, [])

    # 格式化 segments
    formatted_lines = []
    for seg in segments:
        if isinstance(seg, dict):
            formatted_lines.append(f"{seg['time']}  {seg['text']}")
        else:
            formatted_lines.append(str(seg))

    current_transcript = "\n".join(formatted_lines)

    if current_transcript:
        # 顯示即時轉錄結果
        st.text_area(...)
    else:
        # 顯示等待訊息（包含 token 以便除錯）
        st.info(f"🎤 錄音中，等待第一段轉錄結果（約 3 秒後）... [Token: {token[:8]}]")

    # 每 1 秒自動刷新
    if current_time - st.session_state.last_ui_update >= 1.0:
        st.session_state.last_ui_update = current_time
        time.sleep(0.1)
        st.rerun()
```

### 修復 4: 更新所有時間格式說明

**修改位置**:
1. `src/ui/transcription_page.py:299` - UI 幫助文字
2. `src/ui/transcription_page.py:319` - 完整逐字稿幫助文字
3. `src/ui/transcription_page.py:671` - 文檔格式說明

**統一格式**: `yyyy-mm-dd hh:mi:ss + 逐字稿內容`

## 🧪 測試與驗證

### 測試步驟 1: 基本即時顯示測試

1. **開始錄音**
   - 點擊「開始錄音」按鈕
   - 觀察 console 輸出：
     ```
     [Transcription] Starting recording with token abc12345
     [Transcription] Audio worker started for token abc12345
     [Transcription] Transcription worker started for token abc12345
     ```

2. **說話並觀察**
   - 清晰說話 3 秒（例如：「這是第一句測試語音」）
   - 觀察 console 應該出現：
     ```
     [Transcription] Segment 1 [2025-11-02 17:45:23] (RMS=2463.3): 這是第一句測試語音
     [Transcription] Total segments in buffer: 1
     ```

3. **檢查 UI 顯示**
   - 約 3 秒後，UI 應該從「等待第一段轉錄結果」變為顯示轉錄內容
   - 文字區塊應該顯示：
     ```
     2025-11-02 17:45:23  這是第一句測試語音
     ```

4. **繼續測試**
   - 再說話 3 秒（例如：「這是第二句測試語音」）
   - 觀察 console：
     ```
     [Transcription UI] Retrieved 1 segments from token abc12345
     [Transcription UI] Displaying 1 segments
     [Transcription] Segment 2 [2025-11-02 17:45:26] (RMS=3214.5): 這是第二句測試語音
     [Transcription] Total segments in buffer: 2
     [Transcription UI] Retrieved 2 segments from token abc12345
     [Transcription UI] Displaying 2 segments
     ```
   - UI 應該立即更新顯示兩段內容

### 測試步驟 2: 時間格式驗證

1. 記下當前時間（例如 2025-11-02 17:45:20）
2. 開始錄音並說話
3. **驗證時間格式**：
   - ✅ 格式為 `YYYY-MM-DD HH:MM:SS`
   - ✅ 日期正確（2025-11-02）
   - ✅ 時間正確（17:45:23）
   - ✅ 精確到秒

### 測試步驟 3: Console 除錯訊息檢查

**正常流程的 Console 輸出**:
```
[Transcription] Starting recording with token abc12345
[Transcription] WAV path: resource/recording-20251102-174520.wav
[Transcription] Audio worker started for token abc12345
[Transcription] Transcription worker started for token abc12345
[Transcription UI] Active: True, Token: abc12345
[Transcription UI] Retrieved 0 segments from token abc12345
[Transcription] Opening WAV file: resource/recording-20251102-174520.wav
[Transcription] First chunk written, RMS=1234.5
[Transcription] Segment 1 [2025-11-02 17:45:23] (RMS=2463.3): 這是第一句測試語音
[Transcription] Total segments in buffer: 1
[Transcription UI] Active: True, Token: abc12345
[Transcription UI] Retrieved 1 segments from token abc12345
[Transcription UI] Displaying 1 segments
[Transcription] Segment 2 [2025-11-02 17:45:26] (RMS=3214.5): 這是第二句測試語音
[Transcription] Total segments in buffer: 2
[Transcription UI] Retrieved 2 segments from token abc12345
[Transcription UI] Displaying 2 segments
```

**異常情況檢查**:

❌ **如果看到**:
```
[Transcription] ERROR: segments list is None for token abc12345
```
→ 表示 `_transcript_segments` 初始化有問題

❌ **如果看到**:
```
[Transcription UI] Retrieved 0 segments from token abc12345
（一直是 0）
```
→ 表示轉錄結果沒有正確保存

### 測試步驟 4: 完整流程測試

1. **清理舊檔案**
   ```bash
   cd /Users/kenhung/develop_workplace/conference-registration/resource
   rm -f recording-*.wav recording-*.txt
   ```

2. **開始測試**
   - 開始錄音
   - 說話 15 秒（包含 2-3 次停頓）
   - 停止錄音

3. **檢查結果**
   ```bash
   # 檢查檔案
   ls -lh recording-*.wav recording-*.txt

   # 檢查逐字稿格式
   cat recording-*-transcript.txt
   ```

4. **預期 TXT 內容**:
   ```
   語音轉錄結果
   時間：2025-11-02 17:45:45
   音訊檔案：recording-20251102-174520.wav
   採樣率：48000 Hz
   模型：OpenAI Whisper (whisper-1)
   格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容

   ============================================================

   2025-11-02 17:45:23  這是第一句測試語音。
   2025-11-02 17:45:26  這是第二句測試語音。
   2025-11-02 17:45:29  這是第三句測試語音。
   ```

## 📊 顯示效果對比

### 舊版本（HH:MM）
```
17:45  歡迎大家來到今天的會議。
17:45  今天我們要討論的主題是語音轉錄技術。
17:48  首先讓我介紹一下 Whisper API 的功能。
```

### 新版本（yyyy-mm-dd hh:mi:ss）
```
2025-11-02 17:45:23  歡迎大家來到今天的會議。
2025-11-02 17:45:26  今天我們要討論的主題是語音轉錄技術。
2025-11-02 17:48:12  首先讓我介紹一下 Whisper API 的功能。
```

**優點**:
- ✅ 包含完整日期
- ✅ 精確到秒（不只是分鐘）
- ✅ 易於排序和搜尋
- ✅ 符合標準日期時間格式

## 🔍 問題排查指南

### 問題：一直顯示「等待第一段轉錄結果」

**檢查清單**:
1. ☑️ Console 是否顯示 `[Transcription] Segment 1 ...`？
   - **是** → 轉錄正常，UI 讀取有問題
   - **否** → 轉錄本身有問題

2. ☑️ Console 是否顯示 `[Transcription UI] Retrieved X segments`？
   - **X > 0** → Segments 已讀取，格式化有問題
   - **X = 0** → Segments 沒有被讀取到

3. ☑️ Console 是否顯示 `ERROR: segments list is None`？
   - **是** → 初始化問題，檢查 `_start_recording()`

4. ☑️ RMS 值是否足夠大（> 300）？
   - **否** → 被 VAD 過濾掉了，提高音量或降低閾值

### 問題：時間格式不正確

**檢查**:
- 查看 console 的 `[Transcription] Segment X [時間]` 訊息
- 確認格式為 `YYYY-MM-DD HH:MM:SS`
- 檢查系統時間是否正確

### 問題：頁面不更新

**檢查**:
- Console 是否每秒顯示 `[Transcription UI] Active: True`？
- 確認 `st.session_state.last_ui_update` 正常運作
- 檢查瀏覽器 console 是否有錯誤

## 📝 修改的檔案

### src/ui/transcription_page.py
**修改位置**:
1. **Line 269-276**: UI 端除錯訊息
2. **Line 299**: UI 幫助文字更新
3. **Line 304**: 顯示 token 資訊
4. **Line 319**: 完整逐字稿幫助文字更新
5. **Line 618**: 時間格式改為 `%Y-%m-%d %H:%M:%S`
6. **Line 627-633**: Worker 端除錯訊息
7. **Line 671**: 文檔格式說明更新

## ✅ 完成清單

- [x] 時間格式改為 `yyyy-mm-dd hh:mi:ss`
- [x] 添加 UI 端除錯訊息
- [x] 添加 Worker 端除錯訊息
- [x] 顯示 token 資訊以便追蹤
- [x] 更新所有幫助文字
- [x] 更新文檔格式說明
- [x] Python 語法檢查通過

---

**更新版本**: v5.5 - Real-time Display Fix with Full DateTime
**狀態**: 已完成，待測試
**建議**: 執行完整測試流程，觀察 console 輸出以驗證即時顯示功能

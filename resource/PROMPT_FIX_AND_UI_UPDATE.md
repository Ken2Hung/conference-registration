# Prompt 移除與 UI 更新修復

## 📅 更新日期
**2025-11-02**

## 🐛 問題報告

### 問題 1: Prompt 內容被轉錄出來
**症狀**:
```
[Transcription] Segment 3 [2025-11-02 18:10:04] (RMS=2810.1): 請使用繁體中文輸出，嚴格禁止簡體中文。
```

**原因**:
- 之前為了限制繁體中文，添加了 `prompt="請使用繁體中文輸出，嚴格禁止簡體中文。"`
- Whisper API 的 `prompt` 參數會被當作「上下文範例」
- 當音訊內容與 prompt 相似時，Whisper 會直接輸出 prompt 的內容

**Whisper API prompt 參數的問題**:
- ❌ 指令性文字（如「請使用...」）會被轉錄出來
- ❌ 重複的提示詞會被輸出
- ✅ 只適合提供專有名詞、前文上下文

### 問題 2: UI 不會即時更新轉錄內容
**症狀**:
- 開始錄音後，UI 顯示「等待轉錄結果...」
- 即使 console 顯示已經有轉錄結果，UI 也不更新
- 需要等到錄音結束才看到逐字稿

**可能原因**:
1. 使用固定 key 的 text_area 導致 Streamlit 不更新
2. 使用條件式 text_area（有內容時一個，沒內容時另一個）導致組件切換
3. Streamlit 無法正確識別內容變化

## ✅ 修復方案

### 修復 1: 移除 Prompt 參數

**修改位置**: `src/ui/transcription_page.py:624-632`

**修改前**（會被轉錄）:
```python
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=wav_file,
    language="zh",
    response_format="text",
    prompt="請使用繁體中文輸出，嚴格禁止簡體中文。"  # ❌ 會被轉錄出來
)
```

**修改後**（正確）:
```python
# Transcribe with Traditional Chinese language setting
# Note: DO NOT use prompt parameter - Whisper will transcribe it as content
# language="zh" defaults to Traditional Chinese for most cases
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=wav_file,
    language="zh",
    response_format="text"
)
```

**說明**:
- ✅ 只使用 `language="zh"` 參數
- ✅ Whisper 預設會輸出繁體中文（在台灣、香港等地區）
- ✅ 不使用 prompt 避免被轉錄
- ✅ 如果需要簡繁轉換，可以在後處理階段進行

### 修復 2: 單一 Text Area 結構

**修改位置**: `src/ui/transcription_page.py:304-319`

**修改前**（條件式組件，有問題）:
```python
if current_transcript:
    st.text_area(
        f"即時逐字稿（錄音中... 最後更新：{last_update_time}）",
        value=current_transcript,
        key="realtime_transcript_display"  # 固定 key
    )
else:
    st.text_area(
        f"即時逐字稿（等待中... {last_update_time}）",
        value="等待轉錄結果...",
        key="realtime_transcript_display"  # 固定 key
    )
```

**問題**:
- 使用條件判斷創建兩個不同的 text_area
- 固定 key 可能導致 Streamlit 緩存舊值
- Streamlit 可能無法正確識別組件已更改

**修改後**（單一組件，正確）:
```python
# Prepare display content
if current_transcript:
    display_value = current_transcript
    caption_text = f"📊 已轉錄：{len(current_transcript)} 字元 | 分段數：{segment_count} | 更新時間：{last_update_time}"
else:
    display_value = f"🎤 等待轉錄結果...\n\n開始時間：{last_update_time}\nToken：{token[:8]}\n\n約 3 秒後會出現第一段轉錄結果"
    caption_text = f"⏳ 等待中... | 已檢查次數：{st.session_state.segment_count} | 更新時間：{last_update_time}"

# Single text area - always displayed with same structure
st.text_area(
    f"即時逐字稿 (最後更新：{last_update_time})",
    value=display_value,
    height=300,
    help="格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容 | 每 0.5 秒自動更新"
)
st.caption(caption_text)
```

**優點**:
- ✅ 始終是同一個 text_area 組件
- ✅ 只改變 value 和 label
- ✅ 不使用固定 key，讓 Streamlit 自動管理
- ✅ Streamlit 能正確識別內容變化並更新

### 修復 3: 添加詳細除錯訊息

**修改位置**: `src/ui/transcription_page.py:299-302`

```python
# Debug: Print what we're about to display
print(f"[Transcription UI] Current transcript length: {len(current_transcript)}")
if segments:
    print(f"[Transcription UI] Latest segment: {segments[-1] if segments else 'None'}")
```

**作用**:
- 每次 UI 更新時打印當前狀態
- 顯示最新的 segment 內容
- 幫助追蹤 UI 更新過程

## 🧪 測試驗證

### 測試 1: Prompt 不被轉錄

1. **開始錄音並說話**
   - 清晰說話 15 秒

2. **檢查 Console 輸出**
   ```
   [Transcription] Segment 1 [2025-11-02 18:15:23] (RMS=2463.3): 這是測試語音內容。
   ```
   - ✅ 不應該出現「請使用繁體中文輸出，嚴格禁止簡體中文。」
   - ✅ 只包含實際說話的內容

3. **檢查逐字稿文檔**
   ```bash
   cat resource/recording-*-transcript.txt
   ```
   - ✅ 不包含 prompt 內容

### 測試 2: UI 即時更新

1. **開始錄音**
   - 點擊「開始錄音」
   - 觀察 text_area 顯示「等待轉錄結果...」
   - 觀察更新時間每 0.5 秒變化

2. **說話測試**
   - 清晰說話 3 秒（例如：「這是第一句測試語音」）

3. **觀察 Console**（約 3 秒後）:
   ```
   [Transcription] Segment 1 [2025-11-02 18:15:23] (RMS=2463.3): 這是第一句...
   [Transcription] Total segments in buffer: 1
   ```

4. **觀察 UI**（約 0.5 秒後）:
   - text_area 內容應該從「等待轉錄結果...」變為：
   ```
   2025-11-02 18:15:23  這是第一句測試語音
   ```
   - Caption 顯示：`📊 已轉錄：12 字元 | 分段數：1 | 更新時間：18:15:23`

5. **繼續說話**
   - 再說話 3 秒（例如：「這是第二句測試語音」）
   - 約 0.5 秒後，text_area 應該顯示：
   ```
   2025-11-02 18:15:23  這是第一句測試語音
   2025-11-02 18:15:26  這是第二句測試語音
   ```
   - Caption 更新為：`📊 已轉錄：24 字元 | 分段數：2 | 更新時間：18:15:26`

### 測試 3: 完整流程測試

1. **清理舊檔案**
   ```bash
   cd /Users/kenhung/develop_workplace/conference-registration/resource
   rm -f recording-*.wav recording-*.txt
   ```

2. **錄音 15 秒**
   - 說話內容：清晰的繁體中文句子
   - 包含 2-3 次停頓（測試 VAD）

3. **觀察 Console 輸出**
   ```
   [Transcription] Starting recording with token abc12345
   [Transcription UI] Active: True, Token: abc12345
   [Transcription UI] Retrieved 0 segments from token abc12345
   [Transcription UI] Current transcript length: 0

   （約 3 秒後）
   [Transcription] Segment 1 [2025-11-02 18:15:23] (RMS=2463.3): 這是第一句...
   [Transcription] Total segments in buffer: 1
   [Transcription UI] Retrieved 1 segments from token abc12345
   [Transcription UI] Current transcript length: 45
   [Transcription UI] Latest segment: {'time': '2025-11-02 18:15:23', 'text': '這是第一句...'}
   ```

4. **檢查結果**
   ```bash
   ls -lh recording-*.wav recording-*.txt
   cat recording-*-transcript.txt
   ```

5. **驗證**:
   - ✅ 只有一個 WAV 和一個 TXT
   - ✅ TXT 不包含 prompt 內容
   - ✅ TXT 包含所有轉錄段落
   - ✅ 使用繁體中文（如果需要）

## 📊 預期 Console 輸出

### 正常流程

```
[Transcription] Starting recording with token abc12345
[Transcription] Audio worker started for token abc12345
[Transcription] Transcription worker started for token abc12345

[Transcription UI] Active: True, Token: abc12345
[Transcription UI] Retrieved 0 segments from token abc12345
[Transcription UI] Current transcript length: 0

（每 0.5 秒重複）
[Transcription UI] Active: True, Token: abc12345
[Transcription UI] Retrieved 0 segments from token abc12345
[Transcription UI] Current transcript length: 0

（約 3 秒後）
[Transcription] Segment 1 [2025-11-02 18:15:23] (RMS=2463.3): 這是第一句測試語音
[Transcription] Total segments in buffer: 1

（0.5 秒後）
[Transcription UI] Active: True, Token: abc12345
[Transcription UI] Retrieved 1 segments from token abc12345
[Transcription UI] Current transcript length: 45
[Transcription UI] Latest segment: {'time': '2025-11-02 18:15:23', 'text': '這是第一句測試語音'}
[Transcription UI] Displaying 1 segments

（繼續說話，再過 3 秒）
[Transcription] Segment 2 [2025-11-02 18:15:26] (RMS=3214.5): 這是第二句測試語音
[Transcription] Total segments in buffer: 2

（0.5 秒後）
[Transcription UI] Retrieved 2 segments from token abc12345
[Transcription UI] Current transcript length: 90
[Transcription UI] Latest segment: {'time': '2025-11-02 18:15:26', 'text': '這是第二句測試語音'}
[Transcription UI] Displaying 2 segments
```

## 🔍 關鍵觀察點

### 1. Prompt 不被轉錄
**檢查**: Console 輸出的 `Segment X` 訊息
- ✅ 只包含實際說話的內容
- ❌ 不應該出現「請使用繁體中文輸出...」

### 2. UI 即時更新
**檢查**: text_area 內容
- ✅ 約 3 秒後出現第一段轉錄
- ✅ 約 0.5 秒後顯示新的轉錄
- ✅ 更新時間每 0.5 秒變化

### 3. Console 除錯訊息
**檢查**: Console 輸出
- ✅ 每 0.5 秒顯示 `[Transcription UI] Current transcript length: X`
- ✅ 顯示 `Latest segment: {'time': ..., 'text': ...}`
- ✅ 長度應該隨著新 segment 增加

## 📝 修改的檔案

### src/ui/transcription_page.py
**修改位置**:
1. **Line 624-632**: 移除 prompt 參數
2. **Line 299-302**: 添加詳細除錯訊息
3. **Line 304-319**: 改用單一 text_area 結構

## ✅ 完成清單

- [x] 移除 prompt 參數
- [x] 改用單一 text_area 結構
- [x] 移除固定 key
- [x] 添加詳細除錯訊息
- [x] Python 語法檢查通過
- [x] 創建測試指南

---

**更新版本**: v5.7 - Prompt Removal and UI Update Fix
**狀態**: 已完成
**測試**: 準備測試

## 🚀 立即測試

重點觀察：
1. ✅ Console 不出現 prompt 內容
2. ✅ UI 約 3 秒後顯示第一段轉錄
3. ✅ 新轉錄約 0.5 秒後在 UI 顯示
4. ✅ Console 顯示 `Current transcript length` 逐漸增加

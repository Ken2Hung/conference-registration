# 語音轉錄功能測試指南

## ✅ 已完成的改進

### 1. 麥克風權限自動請求
- **改進前**: 需要點擊「開始錄音」才請求麥克風權限
- **改進後**: 進入「語音轉錄」頁面時自動請求麥克風權限
- **實作位置**: `src/ui/transcription_page.py:210`
  ```python
  desired_playing_state=True  # Always request mic permission on page load
  ```

### 2. 語音活動檢測（VAD）過濾靜音
- **問題**: Whisper 在靜音或背景噪音時會產生奇怪的字幕
- **解決方案**: 添加 RMS 閾值過濾，只轉錄有語音的片段
- **實作位置**: `src/ui/transcription_page.py:34, 564-569`
  ```python
  VAD_RMS_THRESHOLD = 300.0  # Minimum RMS to consider as speech

  # In transcription worker:
  chunk_rms = float(calculate_rms(audio_chunk))
  if chunk_rms < VAD_RMS_THRESHOLD:
      print(f"[Transcription] Skipping silent chunk (RMS={chunk_rms:.1f})")
      continue
  ```

### 3. 繁體中文 Prompt
- **問題**: Whisper 轉錄時可能產生簡體中文或不準確的內容
- **解決方案**: 添加繁體中文 prompt 提示，明確要求不在靜音時產生文字
- **實作位置**: `src/ui/transcription_page.py:577-584`
  ```python
  transcript = client.audio.transcriptions.create(
      model="whisper-1",
      file=wav_file,
      language="zh",
      response_format="text",
      prompt="以下是繁體中文的語音內容。請準確轉錄，不要在靜音或背景噪音時產生文字。"
  )
  ```

## 🧪 測試步驟

### 準備工作
1. 確認應用程式正在運行（已啟動在 http://localhost:8501）
2. 確認 `resource/` 目錄已清理（舊測試檔案已刪除）
3. 準備測試用語音內容（建議 15-20 秒，包含說話和停頓）

### 測試流程

#### 1. 麥克風權限測試
1. 瀏覽器開啟 http://localhost:8501
2. 點擊側邊欄的「語音轉錄」
3. **預期結果**:
   - 瀏覽器立即彈出麥克風權限請求
   - 允許後顯示「✅ 麥克風已就緒，點擊「開始錄音」開始錄音」
   - 不需要點擊任何按鈕就能看到權限請求

#### 2. 錄音功能測試
1. 點擊「▶️ 開始錄音」按鈕
2. 開始說話（建議內容：清晰的繁體中文句子）
3. 觀察頁面狀態：
   - 狀態變更為「🎧 麥克風已連線，正在錄音並即時轉錄...」
   - 音量條應該隨聲音變化
   - Console 應該顯示 RMS 值
4. 說話約 5 秒後**停頓 3-5 秒**（測試 VAD）
5. 再說話 5 秒
6. 點擊「⏹️ 停止錄音」

#### 3. VAD 過濾測試
觀察 console 日誌，應該看到類似：

```
[Transcription] Starting recording with token abc123...
[Transcription] Audio worker started
[Transcription] Transcription worker started
[Transcription] First chunk written, RMS=1234.5
[Transcription] Segment 1: 這是第一段測試語音內容...
[Transcription] Skipping silent chunk (RMS=89.3 < 300.0)  # ← 靜音被過濾
[Transcription] Segment 2: 這是第二段測試語音內容...
[Transcription] Stopping recording...
```

**關鍵驗證點**:
- ✅ 靜音片段顯示 "Skipping silent chunk"
- ✅ 沒有出現奇怪的字幕（如「謝謝觀看」、「字幕製作」等）

#### 4. 檔案生成測試
停止錄音後，檢查 `resource/` 目錄：

```bash
cd /Users/kenhung/develop_workplace/conference-registration/resource
ls -lh recording-*.wav recording-*.txt
```

**預期結果**:
```
-rw-r--r-- 1 user staff 480K Nov 2 17:30 recording-20251102-173045.wav
-rw-r--r-- 1 user staff  1.2K Nov 2 17:30 recording-20251102-173045-transcript.txt
```

**關鍵驗證點**:
- ✅ **只有一個** WAV 檔案
- ✅ **只有一個** TXT 檔案
- ✅ WAV 檔案大小合理（約 15 秒 = ~480 KB）

#### 5. 逐字稿內容測試
查看逐字稿內容：

```bash
cat resource/recording-*-transcript.txt
```

**預期內容格式**:
```
語音轉錄結果
時間：2025-11-02 17:30:45
音訊檔案：recording-20251102-173045.wav
採樣率：48000 Hz
模型：OpenAI Whisper (whisper-1)

============================================================

這是第一段測試語音內容。
這是第二段測試語音內容。
```

**關鍵驗證點**:
- ✅ 只包含有語音的片段
- ✅ 使用繁體中文
- ✅ 沒有靜音時產生的奇怪內容
- ✅ 轉錄準確度高

## 📊 測試檢查清單

### 功能測試
- [ ] 進入頁面時自動請求麥克風權限
- [ ] 允許權限後顯示「麥克風已就緒」
- [ ] 點擊「開始錄音」成功開始錄音
- [ ] 音量條正常顯示（隨聲音變化）
- [ ] 約 3 秒後開始顯示第一段轉錄
- [ ] 靜音片段被正確過濾（console 顯示 "Skipping silent chunk"）
- [ ] 點擊「停止錄音」成功停止
- [ ] 停止後可以下載逐字稿

### 檔案測試
- [ ] 只產生一個 WAV 檔案
- [ ] 只產生一個 TXT 檔案
- [ ] WAV 檔案大小合理
- [ ] TXT 檔案包含完整轉錄內容

### 內容品質測試
- [ ] 轉錄內容為繁體中文
- [ ] 沒有靜音時的奇怪字幕
- [ ] 轉錄準確度高
- [ ] 只包含實際說話的內容

### 效能測試
- [ ] 頁面沒有過度閃爍
- [ ] UI 更新流暢（約每 2 秒）
- [ ] 沒有 console 錯誤

## 🐛 常見問題排查

### 問題 1: 麥克風權限沒有自動請求
**可能原因**:
- 瀏覽器之前拒絕過權限
- 使用不支援 WebRTC 的瀏覽器

**解決方法**:
1. 清除瀏覽器網站設定中的麥克風權限
2. 使用 Chrome 或 Edge 瀏覽器
3. 確保使用 HTTPS 或 localhost

### 問題 2: 靜音時還是產生字幕
**可能原因**:
- VAD 閾值太低
- 背景噪音太大

**解決方法**:
1. 檢查 console 中的 RMS 值
2. 如果背景噪音 RMS > 300，調高閾值：
   ```python
   VAD_RMS_THRESHOLD = 500.0  # 提高閾值
   ```
3. 在安靜環境中測試

### 問題 3: 轉錄內容不是繁體中文
**檢查**:
- 確認 prompt 參數正確傳遞
- 檢查 console 是否有 API 錯誤

### 問題 4: 產生多個檔案
**這不應該發生！** 如果發生：
1. 重新啟動應用程式
2. 清理 `resource/` 目錄
3. 確認使用最新版本的 `transcription_page.py`

## 📝 測試報告範本

測試完成後，請記錄結果：

```
測試日期: 2025-11-02
測試時間: 17:30
錄音時長: 15 秒
測試環境: macOS + Chrome

1. 麥克風權限: ✅ 自動請求成功
2. VAD 過濾: ✅ 靜音片段被正確過濾
3. 檔案生成: ✅ 只有一個 WAV 和一個 TXT
4. 繁體中文: ✅ 轉錄結果為繁體中文
5. 轉錄品質: ✅ 準確度高，無奇怪字幕

問題: 無

建議: 無
```

---

**準備測試**: 應用程式已運行，舊檔案已清理，可以開始測試！

**瀏覽器**: http://localhost:8501 → 語音轉錄頁面

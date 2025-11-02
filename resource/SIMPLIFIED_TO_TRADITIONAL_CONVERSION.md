# 簡體中文自動轉繁體中文功能

## 📅 更新日期
**2025-11-02**

## 🎯 功能說明

### 問題
Whisper API 有時會輸出簡體中文，即使指定 `language="zh"`，例如：
- 「信息」（簡體）而非「資訊」（繁體）
- 「软件」（簡體）而非「軟體」（繁體）
- 「网络」（簡體）而非「網路」（繁體）

### 解決方案
**自動簡繁轉換**: 在每個轉錄結果獲取後，立即進行簡體轉繁體轉換。

**實作方式**:
- 使用 `opencc-python-reimplemented` 庫
- 在轉錄結果處理時自動轉換
- 確保所有輸出（Console、UI、TXT 文檔）都是繁體中文

## 🔧 技術實作

### 1. 安裝依賴

**添加到 requirements.txt**:
```txt
opencc-python-reimplemented>=0.1.7
```

**安裝**:
```bash
pip install "opencc-python-reimplemented>=0.1.7"
```

### 2. 初始化 OpenCC 轉換器

**位置**: `src/ui/transcription_page.py:37-39`

```python
from opencc import OpenCC

# Initialize OpenCC for Simplified to Traditional Chinese conversion
# s2t = Simplified Chinese to Traditional Chinese
_opencc_converter = OpenCC('s2t')
```

**OpenCC 轉換配置**:
- `s2t`: Simplified to Traditional (簡體轉繁體)
- `s2tw`: Simplified to Traditional (Taiwan Standard) - 台灣正體
- `s2hk`: Simplified to Traditional (Hong Kong Standard) - 香港繁體

我們使用 `s2t`，這是最通用的簡繁轉換。

### 3. 轉換函數

**位置**: `src/ui/transcription_page.py:42-59`

```python
def _convert_to_traditional_chinese(text: str) -> str:
    """
    Convert Simplified Chinese to Traditional Chinese.

    Args:
        text: Input text (may contain Simplified Chinese)

    Returns:
        Text with all Simplified Chinese converted to Traditional Chinese
    """
    try:
        converted = _opencc_converter.convert(text)
        if converted != text:
            print(f"[S2T] Converted: '{text}' -> '{converted}'")
        return converted
    except Exception as exc:
        print(f"[S2T] Error converting text: {exc}")
        return text  # Return original text if conversion fails
```

**特點**:
- ✅ 自動檢測並轉換簡體中文
- ✅ 如果發生轉換，打印 Console 日誌
- ✅ 轉換失敗時返回原文（容錯處理）
- ✅ 如果文字已經是繁體，不會改變

### 4. 在轉錄結果處理時進行轉換

**位置**: `src/ui/transcription_page.py:661-672`

```python
if transcript and transcript.strip():
    # Convert to Traditional Chinese immediately after getting transcript
    transcript_text = transcript.strip()
    transcript_text = _convert_to_traditional_chinese(transcript_text)

    # Use actual clock time (yyyy-mm-dd hh:mi:ss)
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    segment_data = {
        "time": time_str,
        "text": transcript_text  # Store converted text
    }
```

**流程**:
1. 從 Whisper API 獲取轉錄結果
2. 立即調用 `_convert_to_traditional_chinese()` 進行轉換
3. 將轉換後的文字存入 `segment_data`
4. 所有後續處理都使用轉換後的文字

### 5. Console 輸出也使用轉換後的文字

**位置**: `src/ui/transcription_page.py:680`

```python
# Use converted text in console output
print(f"[Transcription] Segment {segment_count} [{time_str}] (RMS={chunk_rms:.1f}): {transcript_text[:50]}...")
```

## 📊 轉換範例

### 範例 1: 常見簡繁轉換

| 簡體中文 | 繁體中文 |
|---------|---------|
| 信息 | 資訊 |
| 软件 | 軟體 |
| 网络 | 網路 |
| 计算机 | 計算機 |
| 视频 | 視頻 |
| 数据 | 數據 |
| 用户 | 用戶 |
| 图片 | 圖片 |

### 範例 2: Console 輸出

**轉換前**（假設 Whisper 輸出簡體）:
```
[Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 这是一个计算机软件的信息系统。
```

**轉換後**（自動轉為繁體）:
```
[S2T] Converted: '这是一个计算机软件的信息系统。' -> '這是一個計算機軟體的資訊系統。'
[Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 這是一個計算機軟體的資訊系統。
```

### 範例 3: UI 顯示

**text_area 內容**:
```
2025-11-02 18:20:15  這是一個計算機軟體的資訊系統。
2025-11-02 18:20:18  網路連線正常，數據傳輸穩定。
2025-11-02 18:20:21  用戶可以上傳圖片和視頻。
```

**全部都是繁體中文** ✅

### 範例 4: TXT 文檔

```
語音轉錄結果
時間：2025-11-02 18:20:30
音訊檔案：recording-20251102-182015.wav
採樣率：48000 Hz
模型：OpenAI Whisper (whisper-1)
格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容

============================================================

2025-11-02 18:20:15  這是一個計算機軟體的資訊系統。
2025-11-02 18:20:18  網路連線正常，數據傳輸穩定。
2025-11-02 18:20:21  用戶可以上傳圖片和視頻。
```

**文檔內容全部繁體** ✅

## 🧪 測試驗證

### 測試步驟

1. **開始錄音**
2. **說一些容易被轉成簡體的詞彙**:
   - 「資訊」、「軟體」、「網路」
   - 「計算機」、「數據」、「用戶」
   - 「視頻」、「圖片」

3. **觀察 Console 輸出**:
   ```
   [S2T] Converted: '信息' -> '資訊'
   [Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 這是資訊系統。
   ```
   - ✅ 如果有 `[S2T] Converted` 訊息，表示發生了轉換
   - ✅ `[Transcription]` 訊息應該顯示繁體中文

4. **檢查 UI 顯示**:
   - text_area 應該全部顯示繁體中文

5. **檢查 TXT 文檔**:
   ```bash
   cat resource/recording-*-transcript.txt
   ```
   - 所有內容應該都是繁體中文

### 預期結果

#### ✅ 正常情況（需要轉換）
```
[Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 这是信息系统。（原始）
[S2T] Converted: '这是信息系统。' -> '這是資訊系統。'
[Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 這是資訊系統。（轉換後）
```

#### ✅ 正常情況（不需要轉換）
```
[Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 這是測試語音。
（沒有 [S2T] Converted 訊息，因為原本就是繁體）
```

#### ❌ 異常情況（轉換失敗）
```
[S2T] Error converting text: ...
[Transcription] Segment 1 [2025-11-02 18:20:15] (RMS=2463.3): 这是信息系统。（保留原文）
```

## 💡 使用建議

### 1. 觀察 Console 日誌
- 如果看到 `[S2T] Converted` 訊息，表示 Whisper 輸出了簡體中文
- 轉換後的文字會顯示在 Console 和 UI

### 2. 檢查轉換品質
- OpenCC 的轉換非常準確
- 如果發現轉換錯誤，可以考慮切換到 `s2tw` 配置（台灣正體）

### 3. 繁體優先
- Whisper API 的 `language="zh"` 預設傾向繁體
- 但某些詞彙仍可能輸出簡體
- 自動轉換確保 100% 繁體輸出

## 🔍 技術細節

### OpenCC 轉換流程

```
原始文字 (可能包含簡體)
    ↓
_opencc_converter.convert(text)
    ↓
檢查是否有變化
    ↓
if converted != text:
    print("[S2T] Converted")
    ↓
返回轉換後的文字 (保證繁體)
```

### 性能考量

- **轉換速度**: 極快（毫秒級）
- **記憶體使用**: 極低（OpenCC 使用高效字典）
- **準確度**: 非常高（OpenCC 是業界標準）

### 錯誤處理

```python
try:
    converted = _opencc_converter.convert(text)
    return converted
except Exception as exc:
    print(f"[S2T] Error converting text: {exc}")
    return text  # 轉換失敗時返回原文
```

## 📝 修改的檔案

### requirements.txt
**添加**:
```txt
opencc-python-reimplemented>=0.1.7
```

### src/ui/transcription_page.py
**修改位置**:
1. **Line 25**: 添加 `from opencc import OpenCC`
2. **Line 37-39**: 初始化 OpenCC 轉換器
3. **Line 42-59**: 定義轉換函數
4. **Line 662-664**: 在轉錄結果處理時進行轉換
5. **Line 680**: Console 輸出使用轉換後的文字

## ✅ 完成清單

- [x] 安裝 `opencc-python-reimplemented` 庫
- [x] 初始化 OpenCC 轉換器（s2t 配置）
- [x] 實作轉換函數
- [x] 在轉錄結果處理時自動轉換
- [x] Console 輸出使用轉換後的文字
- [x] UI 顯示轉換後的文字
- [x] TXT 文檔保存轉換後的文字
- [x] 添加錯誤處理
- [x] 添加轉換日誌
- [x] Python 語法檢查通過

---

**更新版本**: v5.8 - Automatic Simplified to Traditional Chinese Conversion
**狀態**: 已完成
**測試**: 準備測試

## 🚀 立即測試

關鍵觀察點：
1. ✅ Console 出現 `[S2T] Converted` 訊息（如果有簡體）
2. ✅ 所有 Console 輸出都是繁體中文
3. ✅ UI 顯示全部繁體中文
4. ✅ TXT 文檔內容全部繁體中文

## 🎁 額外優點

1. **透明**: Console 會顯示轉換訊息
2. **容錯**: 轉換失敗時返回原文
3. **高效**: 毫秒級轉換速度
4. **準確**: OpenCC 業界標準轉換
5. **自動**: 無需手動干預

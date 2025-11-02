# 快速入門指南：即時麥克風語音轉錄功能

**功能分支**: `003-realtime-mic-transcription`
**建立日期**: 2025-10-29
**相關文件**: [spec.md](spec.md) | [data-model.md](data-model.md) | [contracts/](contracts/)

---

## 概述

本指南幫助開發者快速設定和測試即時麥克風語音轉錄功能。這個功能允許使用者透過瀏覽器麥克風錄音，並透過 OpenAI gpt-4o-mini-transcribe 模型進行即時逐字稿轉錄，支援實體檔案持久化。

---

## 環境需求

### 系統需求

- **作業系統**: macOS, Linux, Windows
- **Python**: 3.9.6 (專案標準版本)
- **瀏覽器**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ (支援 WebRTC)
- **麥克風**: 任何可用的音訊輸入裝置
- **網路**: 穩定的網際網路連線 (用於 OpenAI API 請求)

### 必要軟體

- **Python 虛擬環境**: `venv` 或 `virtualenv`
- **Git**: 用於版本控制
- **文字編輯器**: VS Code, PyCharm, 或其他 Python IDE

---

## 安裝步驟

### 1. 取得程式碼

```bash
# 如果尚未 clone 專案
git clone <repository-url>
cd conference-registration

# 切換到功能分支
git checkout 003-realtime-mic-transcription

# 確認分支
git branch --show-current
# 應顯示: 003-realtime-mic-transcription
```

### 2. 建立並啟動虛擬環境

```bash
# 建立虛擬環境 (如果尚未建立)
python3 -m venv venv

# 啟動虛擬環境
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate

# 確認 Python 版本
python --version
# 應顯示: Python 3.9.6 或相容版本
```

### 3. 安裝相依套件

這個功能需要安裝新的相依套件：

```bash
# 安裝所有相依套件 (包含新增的套件)
pip install -r requirements.txt

# 新增的套件包括:
# - streamlit-webrtc==0.47.1  (瀏覽器麥克風存取)
# - av==11.0.0                (音訊處理)
# - numpy==1.24.3             (音訊陣列操作)
# - openai==1.12.0            (OpenAI API 客戶端)
# - python-dotenv==1.0.0      (環境變數管理)

# 驗證安裝
pip list | grep -E "streamlit-webrtc|av|openai"
# 應看到這些套件的版本資訊
```

### 4. 設定 OpenAI API 金鑰

這是**最重要**的步驟！沒有 API 金鑰將無法使用轉錄功能。

#### 4.1 取得 API 金鑰

1. 前往 [OpenAI Platform](https://platform.openai.com/)
2. 登入或註冊帳號
3. 導航到 API Keys 頁面: https://platform.openai.com/api-keys
4. 點擊 "Create new secret key"
5. 複製產生的金鑰 (格式: `sk-proj-...` 或 `sk-...`)

#### 4.2 設定環境變數

**方法 A: 使用 .env 檔案 (推薦)**

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env 檔案
nano .env  # 或使用你偏好的編輯器

# 新增以下內容:
OPENAI_API_KEY=sk-proj-your-actual-api-key-here

# 儲存並關閉
```

**方法 B: 設定系統環境變數**

```bash
# macOS/Linux (臨時設定，終端機關閉後失效)
export OPENAI_API_KEY="sk-proj-your-actual-api-key-here"

# macOS/Linux (永久設定)
echo 'export OPENAI_API_KEY="sk-proj-your-actual-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Windows (命令提示字元)
set OPENAI_API_KEY=sk-proj-your-actual-api-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-proj-your-actual-api-key-here"
```

#### 4.3 驗證 API 金鑰

```bash
# 使用 Python 驗證
python -c "import os; print('API Key set:', 'OPENAI_API_KEY' in os.environ)"
# 應顯示: API Key set: True

# 測試 API 連線 (選用)
python -c "
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('API key valid!')
"
# 如果金鑰有效，應該不會報錯
```

### 5. 確保 resource/ 目錄存在

逐字稿檔案會儲存在專案根目錄的 `resource/` 資料夾：

```bash
# 建立目錄 (如果不存在)
mkdir -p resource

# 驗證目錄存在且可寫入
touch resource/.test && rm resource/.test
echo "resource/ directory is ready"
```

---

## 啟動應用程式

### 使用啟動腳本 (推薦)

```bash
# 執行啟動腳本
./start.sh

# 這個腳本會:
# 1. 啟動虛擬環境
# 2. 執行 streamlit run app.py
# 3. 自動在瀏覽器開啟應用程式

# 如果需要手動指定連接埠:
streamlit run app.py --server.port 8502
```

### 手動啟動

```bash
# 確保虛擬環境已啟動
source venv/bin/activate

# 啟動 Streamlit 應用程式
streamlit run app.py

# 應該會看到類似以下輸出:
#   You can now view your Streamlit app in your browser.
#   Local URL: http://localhost:8501
#   Network URL: http://192.168.x.x:8501
```

### 存取應用程式

1. 開啟瀏覽器 (Chrome, Firefox, Safari, Edge)
2. 前往 `http://localhost:8501`
3. 應該會看到會議註冊系統的主畫面
4. 點擊導航列的「即時轉錄」按鈕進入轉錄頁面

---

## 使用轉錄功能

### 第一次使用流程

#### 1. 開啟轉錄頁面

- 在應用程式主畫面找到「即時轉錄」或「Real-time Transcription」按鈕
- 點擊進入轉錄介面

#### 2. 設定參數 (選用)

**檔案名稱設定**:
- 留空: 系統自動產生檔名 (格式: `transcript-20251029-143022.txt`)
- 輸入自訂名稱: 例如 "會議記錄" (自動加上 `.txt` 副檔名)

**音訊參數調整**:
- **片段秒數 (Chunk Duration)**: 1.0-5.0 秒，預設 2.0 秒
  - 較短: 更即時的轉錄，但 API 成本較高
  - 較長: 降低 API 成本，但更新間隔較長

- **VAD 音量門檻 (Voice Activity Detection)**: 50-1000，預設 200
  - 較低 (50-150): 更敏感，捕捉輕聲說話
  - 較高 (300-1000): 較不敏感，過濾更多靜音和背景噪音

#### 3. 開始錄音

1. 點擊「開始轉錄」按鈕
2. 瀏覽器會請求麥克風權限
3. **重要**: 必須允許麥克風存取，否則功能無法運作
4. 看到「✅ 麥克風已連線」訊息表示成功

#### 4. 開始說話

- 對著麥克風清楚地說話 (中文或英文皆可)
- 每 2 秒 (或你設定的片段長度) 會自動送出一個音訊片段
- 轉錄文字會在 3-5 秒內出現在畫面上
- 文字會即時顯示並自動捲動到最新內容

#### 5. 停止錄音

- 點擊「停止」按鈕結束轉錄
- 系統會自動寫入結束時間戳記到檔案
- 可以在 `resource/` 目錄找到完整的逐字稿檔案

#### 6. 下載逐字稿 (選用)

- 點擊「下載目前逐字稿 (.txt)」按鈕
- 瀏覽器會下載名為 `transcript-live.txt` 的檔案
- 內容與畫面上顯示的相同

---

## 測試功能

### 基本功能測試

#### 測試 1: 麥克風權限

```
步驟:
1. 點擊「開始轉錄」
2. 瀏覽器顯示權限請求提示

預期結果:
✅ 允許權限: 顯示「麥克風已連線」
❌ 拒絕權限: 顯示「請允許瀏覽器存取麥克風以開始轉錄」
```

#### 測試 2: 中文語音轉錄

```
步驟:
1. 開始轉錄
2. 對麥克風說: "這是一段測試語音，用來驗證中文轉錄功能是否正常運作"
3. 等待 5 秒

預期結果:
✅ 畫面顯示轉錄的中文文字
✅ 準確度應該 > 80%
✅ 繁體中文正確顯示
```

#### 測試 3: 英文語音轉錄

```
步驟:
1. 開始轉錄
2. 對麥克風說: "This is a test of the real-time transcription feature"
3. 等待 5 秒

預期結果:
✅ 畫面顯示轉錄的英文文字
✅ 大小寫和標點符號正確
```

#### 測試 4: 檔案持久化

```
步驟:
1. 開始轉錄 (不輸入自訂檔名)
2. 說話 10 秒
3. 點擊「停止」
4. 開啟終端機執行: ls -la resource/

預期結果:
✅ 看到新建立的檔案 transcript-YYYYMMDD-HHMMSS.txt
✅ 檔案大小 > 0 bytes
✅ 使用 cat resource/transcript-*.txt 查看內容，應包含:
   - 開始時間標記
   - 轉錄的文字
   - 結束時間標記
```

#### 測試 5: VAD 靜音過濾

```
步驟:
1. 設定 VAD 門檻為 200
2. 開始轉錄
3. 保持靜默 10 秒 (不說話)
4. 觀察畫面

預期結果:
✅ 不應該出現任何文字 (或只有少量 [ERROR] 訊息)
✅ 沒有消耗過多 API 請求
```

#### 測試 6: 錯誤處理

```
步驟:
1. 暫時停用網路連線 (關閉 WiFi)
2. 開始轉錄並說話
3. 觀察畫面

預期結果:
✅ 顯示 [ERROR] 訊息，例如: "[ERROR] 網路連線失敗"
✅ 應用程式不會當機
✅ 重新連線後繼續運作
```

---

## 常見問題排解

### 問題 1: 無法啟動應用程式

**症狀**: 執行 `streamlit run app.py` 時出現錯誤

**可能原因與解決方法**:

```bash
# 錯誤: ModuleNotFoundError: No module named 'streamlit_webrtc'
# 解決: 重新安裝相依套件
pip install -r requirements.txt

# 錯誤: ImportError: cannot import name 'OpenAI' from 'openai'
# 解決: 更新 openai 套件到正確版本
pip install --upgrade openai==1.12.0

# 錯誤: FileNotFoundError: [Errno 2] No such file or directory: 'app.py'
# 解決: 確認目前在專案根目錄
pwd  # 應該顯示 .../conference-registration
ls app.py  # 應該找到檔案
```

### 問題 2: 麥克風權限被拒絕

**症狀**: 點擊「開始轉錄」後顯示「請允許瀏覽器存取麥克風」

**解決方法 (Chrome)**:

1. 點擊網址列左側的鎖頭圖示
2. 找到「麥克風」權限設定
3. 選擇「允許」
4. 重新整理頁面 (F5)
5. 再次點擊「開始轉錄」

**解決方法 (Firefox)**:

1. 點擊網址列左側的資訊圖示
2. 找到「權限」→「使用麥克風」
3. 選擇「允許」
4. 重新整理頁面

**解決方法 (Safari)**:

1. 打開「偏好設定」→「網站」→「麥克風」
2. 找到 `localhost` 或應用程式網址
3. 選擇「允許」
4. 重新整理頁面

### 問題 3: API 金鑰錯誤

**症狀**: 轉錄時顯示 `[ERROR] 無效的 API 金鑰`

**解決方法**:

```bash
# 1. 確認環境變數已設定
echo $OPENAI_API_KEY  # macOS/Linux
echo %OPENAI_API_KEY%  # Windows

# 2. 驗證金鑰格式
# 正確格式: sk-proj-... 或 sk-...
# 長度: 約 50-60 個字元

# 3. 檢查 .env 檔案
cat .env | grep OPENAI_API_KEY
# 應該看到: OPENAI_API_KEY=sk-proj-...

# 4. 確認沒有多餘的空格或引號
# 錯誤: OPENAI_API_KEY=" sk-proj-... "
# 正確: OPENAI_API_KEY=sk-proj-...

# 5. 重新啟動應用程式
streamlit run app.py
```

### 問題 4: 沒有文字出現

**症狀**: 開始轉錄後，說話但畫面沒有顯示任何文字

**排查步驟**:

```bash
# 1. 檢查麥克風是否正常運作
# macOS: 系統偏好設定 → 聲音 → 輸入
# Windows: 設定 → 系統 → 聲音 → 輸入裝置
# 對麥克風說話，觀察音量指示器是否有反應

# 2. 調整 VAD 門檻
# 在轉錄頁面將 VAD 門檻調低到 50
# 重新開始轉錄並說話

# 3. 查看終端機輸出
# 觀察是否有錯誤訊息或例外

# 4. 檢查網路連線
ping google.com  # 確認網路正常

# 5. 驗證 API 配額
# 前往 https://platform.openai.com/usage
# 確認還有可用的 API 配額
```

### 問題 5: 轉錄結果不準確

**症狀**: 轉錄文字與實際說話內容差異很大

**改善方法**:

1. **改善音訊品質**:
   - 靠近麥克風說話 (距離 15-30 公分)
   - 減少背景噪音 (關閉風扇、音樂等)
   - 使用外接麥克風代替筆電內建麥克風

2. **調整參數**:
   - 增加片段秒數到 3-5 秒 (提供更多上下文)
   - 降低 VAD 門檻以捕捉更多音訊

3. **改善說話方式**:
   - 清楚地發音，不要太快
   - 避免口齒不清或吃字
   - 在句子之間稍作停頓

### 問題 6: 檔案無法儲存

**症狀**: 轉錄完成但 `resource/` 目錄中沒有檔案

**解決方法**:

```bash
# 1. 確認目錄存在
ls -la resource/
# 如果不存在:
mkdir -p resource

# 2. 檢查寫入權限
touch resource/.test && echo "Permission OK" && rm resource/.test

# 3. 確認檔案路徑
# 檔案應該在專案根目錄的 resource/ 下
# 絕對路徑: /Users/<username>/develop_workplace/conference-registration/resource/

# 4. 查看終端機錯誤訊息
# 如果有 PermissionError 或 OSError，檢查目錄權限:
chmod 755 resource/

# 5. 手動測試檔案寫入
python -c "
with open('resource/test.txt', 'w', encoding='utf-8') as f:
    f.write('測試')
print('File written successfully')
"
```

### 問題 7: 效能問題 (延遲或卡頓)

**症狀**: 轉錄延遲超過 10 秒，或介面卡頓

**原因與解決方法**:

1. **API 延遲**:
   - 正常 API 回應時間: 1-3 秒
   - 如果超過 5 秒，可能是網路或 API 伺服器問題
   - 解決: 稍後再試，或檢查 OpenAI 服務狀態

2. **瀏覽器效能**:
   - 關閉其他分頁以釋放記憶體
   - 使用 Chrome 或 Firefox (效能較好)
   - 重新啟動瀏覽器

3. **片段設定**:
   - 縮短片段秒數到 1.5-2.0 秒
   - 提高 VAD 門檻減少 API 呼叫

---

## 進階設定

### 自訂輸出目錄

預設情況下，逐字稿檔案儲存在 `resource/` 目錄。如果需要更改:

```python
# 在 src/ui/transcription_page.py 中修改
from src.models.transcription import FileOutputConfig

config = FileOutputConfig(
    output_directory="/path/to/custom/directory",
    filename="custom-transcript"
)
```

### 調整 API 參數

```python
# 在 src/services/transcription_service.py 中
# 可以修改 transcribe_audio_chunk 函數的參數

# 指定語言 (提高準確度)
text = transcribe_audio_chunk(
    wav_bytes,
    language="zh"  # 強制使用中文
)

# 提供上下文提示詞 (改善專有名詞識別)
text = transcribe_audio_chunk(
    wav_bytes,
    prompt="會議中提到的專有名詞: Streamlit, WebRTC, PyAV"
)
```

### 啟用除錯模式

```bash
# 設定環境變數啟用詳細日誌
export STREAMLIT_LOGGER_LEVEL=debug

# 啟動應用程式
streamlit run app.py

# 終端機會顯示更多除錯資訊
```

---

## 測試資源

### 測試音訊建議

**中文測試語句**:
- "這是一段測試語音，用來驗證即時轉錄功能是否正常運作"
- "今天天氣很好，我們要測試麥克風的語音轉錄品質"
- "Streamlit 是一個很棒的 Python 網頁框架"

**英文測試語句**:
- "This is a test of the real-time transcription feature using OpenAI's API"
- "The quick brown fox jumps over the lazy dog"
- "Python, JavaScript, and TypeScript are popular programming languages"

**混合語言測試**:
- "我今天要使用 OpenAI 的 API 來進行 speech-to-text"
- "This feature uses WebRTC 來存取瀏覽器的 microphone"

### 效能測試指令碼

建立檔案 `test_transcription.py` 用於自動化測試:

```python
"""Test script for transcription performance."""
import time
import numpy as np
from src.services.audio_service import create_wav_chunk
from src.services.transcription_service import transcribe_audio_chunk

def test_latency():
    """Measure transcription latency."""
    # Generate 2 seconds of silent audio
    pcm = np.zeros(96000, dtype=np.int16)
    wav_bytes = create_wav_chunk(pcm, 48000)

    # Measure API call time
    start = time.time()
    result = transcribe_audio_chunk(wav_bytes)
    elapsed = time.time() - start

    print(f"Transcription completed in {elapsed:.2f} seconds")
    print(f"Result: {result}")

    # Check success criteria (SC-002)
    assert elapsed < 3.0, "Transcription took too long"

if __name__ == "__main__":
    test_latency()
```

執行測試:

```bash
python test_transcription.py
```

---

## 相關文件

### 功能規格與設計

- **功能規格**: [spec.md](spec.md) - 完整的需求定義和使用者情境
- **資料模型**: [data-model.md](data-model.md) - 實體定義和驗證規則
- **服務合約**: [contracts/transcription-service.md](contracts/transcription-service.md) - API 介面規格

### 技術研究

- **研究文件**: [research.md](research.md) - 技術決策和實作模式
- **實作計畫**: [plan.md](plan.md) - 開發階段和架構

### 專案文件

- **專案說明**: `/CLAUDE.md` - 專案概述和開發規範
- **需求文件**: `/requirements/PR-gpt4o-transcripbe.md` - 原始需求

---

## 取得協助

### 開發問題

如果遇到無法解決的問題:

1. **查看日誌**: 終端機中的 Streamlit 輸出通常包含有用的錯誤訊息
2. **檢查文件**: 確認已按照本指南的所有步驟操作
3. **驗證環境**: 確認 Python 版本、套件版本和 API 金鑰設定正確

### API 相關問題

- **OpenAI 平台狀態**: https://status.openai.com/
- **OpenAI API 文件**: https://platform.openai.com/docs/guides/speech-to-text
- **OpenAI 社群論壇**: https://community.openai.com/

### 套件問題

- **streamlit-webrtc**: https://github.com/whitphx/streamlit-webrtc
- **PyAV**: https://pyav.org/docs/stable/
- **Streamlit**: https://docs.streamlit.io/

---

## 下一步

完成快速入門後，你可以:

1. **閱讀資料模型文件** ([data-model.md](data-model.md)) 了解內部結構
2. **查看服務合約** ([contracts/transcription-service.md](contracts/transcription-service.md)) 理解 API 介面
3. **開始實作功能** 根據 [plan.md](plan.md) 的階段進行開發
4. **執行測試套件** 確保所有功能正常運作

祝開發順利！ 🎉

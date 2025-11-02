# PR：Streamlit（麥克風即時）＋ OpenAI **gpt-4o-mini-transcribe** 逐字稿
**不需上傳檔案**；按下「開始轉錄」後，瀏覽器即授權麥克風，將語音以**小片段（預設 2 秒）**串流回 Python，後端把片段送到 **`audio.transcriptions`**（模型：`gpt-4o-mini-transcribe`）並即時把文字顯示在前端。

> 為了維持你指定的 **`gpt-4o-mini-transcribe`**（非 Realtime 模型），本實作採用「**瀏覽器錄音 → 小片段上傳 → 持續轉錄**」的方式達到準即時。官方 Audio API 明確支援 `gpt-4o(-mini)-transcribe` 在 **/audio/transcriptions** 端點使用。citeturn0search7  
> 若你未來想做到更低延遲或雙向語音，則可改用 **Realtime API（WebRTC/WebSocket）** 與 `gpt-realtime(-mini)`。本文在最後附上替代方案與成本比較。citeturn0search6turn0search11

---

## 摘要 (Summary)
- ✅ **按鈕一鍵啟動**：按下「開始轉錄」即啟用麥克風、開始分段轉錄。
- ✅ **即時顯示**：每段完成後就追加到畫面文字區，提供 **.txt** 下載。
- ✅ **低耦合**：轉錄邏輯封裝於 `transcriber.py`，UI 在 `app.py`。  
- ✅ **不需上傳整檔**：使用者無須先準備媒體檔。  
- 🔧 **可調參數**：片段長度（預設 2 秒）、簡易 VAD 門檻（節省費用）。
- 🧩 **技術要點**：用 `streamlit-webrtc` 取得瀏覽器麥克風並於 Python 即時處理音訊片段。citeturn6view0

---

## 架構 (Architecture)

```
Browser (getUserMedia via streamlit-webrtc)
   └─ 音訊幀 (48000Hz) → Python 音訊 callback
        └─ 累積至 2s PCM16 → 轉 .wav bytes
             └─ OpenAI audio.transcriptions.create(model="gpt-4o-mini-transcribe")
                  └─ 累積結果至 session_state → UI 實時追加呈現 → 可下載 .txt
```

---

## 新增/變更檔案 (Files Changed)

```
.
├─ app.py                 # Streamlit 主程式（UI＋webrtc＋狀態顯示/下載）
├─ transcriber.py         # OpenAI 轉錄封裝（呼叫 audio.transcriptions）
├─ audio_chunker.py       # 音訊片段化與簡易 VAD
├─ requirements.txt       # 依賴套件
├─ .env.example           # OPENAI_API_KEY / OPENAI_BASE_URL
└─ PR-Streamlit-RT-Mic-gpt4o-mini-transcribe.md  # 本文件
```
---
# PR 更新：即時麥克風轉錄之**持久化改為寫入 `./resource/*.txt` 實體檔**

本更新在前一版「Streamlit + gpt-4o-mini-transcribe（麥克風即時）」基礎上，將**持久化策略**由僅存在記憶體改為：
- 轉錄過程會**即時 append** 到專案根目錄下的 **`resource/`** 目錄內的 **`.txt`** 檔案。
- 檔名可由使用者輸入；若留空則自動以 `transcript-YYYYMMDD-HHMMSS.txt` 產生。
- `resource/` 目錄若不存在會自動建立。
- 「停止」按鈕會在檔尾寫入簡單結束標記（時間）。

> 仍維持：不需上傳整檔、按下開始即時轉錄、頁面同步顯示、同時可下載目前內容為 .txt。

---

## 變更摘要

- ✨ 新增檔名輸入框：`輸出檔名（.txt，自動生成可留空）`  
- ✨ 新增 `resource/` 目錄自動建立與檔案路徑管理 `st.session_state.file_path`  
- ✨ 背景轉錄執行緒每產生一段文字便**立即寫入**目標檔案（UTF-8）  
- ✨ 「開始轉錄」在檔頭寫入起始時間、「停止」在檔尾寫入結束時間  
- 🧵 以 `threading.Lock` 確保多執行緒寫檔安全

---

## 檔案差異（重點節錄）

### `app.py`（完整更新版）
```python
import os, datetime, threading, queue, time, numpy as np, av, streamlit as st
from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from audio_chunker import Chunker, pcm16_to_wav_bytes
from transcriber import transcribe_wav_bytes

load_dotenv()
st.set_page_config(page_title="即時逐字稿 (gpt-4o-mini-transcribe)", layout="centered")
st.title("🎤 即時逐字稿 – gpt-4o-mini-transcribe")
st.caption("按「開始轉錄」後使用瀏覽器麥克風，持續以 2 秒小段上傳到 OpenAI 轉錄並即時顯示；同時寫入 ./resource/*.txt")

# --- 狀態初始化 ----
if "transcript" not in st.session_state:
    st.session_state.transcript = []
if "running" not in st.session_state:
    st.session_state.running = False
if "audio_q" not in st.session_state:
    st.session_state.audio_q = queue.Queue(maxsize=32)  # 音訊 chunk 佇列
if "worker_started" not in st.session_state:
    st.session_state.worker_started = False
if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "file_lock" not in st.session_state:
    st.session_state.file_lock = threading.Lock()

# --- UI 控制 ----
basename = st.text_input("輸出檔名（.txt，自動生成可留空）", value="")

col1, col2, col3 = st.columns([1,1,2])
with col1:
    if st.button("▶️ 開始轉錄", type="primary"):
        # 設定輸出檔路徑
        os.makedirs("resource", exist_ok=True)
        if basename.strip():
            filename = basename.strip()
            if not filename.endswith(".txt"):
                filename += ".txt"
        else:
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"transcript-{ts}.txt"
        st.session_state.file_path = os.path.join("resource", filename)

        # 檔頭標記
        with st.session_state.file_lock, open(st.session_state.file_path, "a", encoding="utf-8") as f:
            f.write(f"# START {datetime.datetime.now().isoformat()}\n")

        st.session_state.running = True

with col2:
    if st.button("⏹️ 停止"):
        # 檔尾標記
        if st.session_state.file_path:
            with st.session_state.file_lock, open(st.session_state.file_path, "a", encoding="utf-8") as f:
                f.write(f"# END   {datetime.datetime.now().isoformat()}\n")
        st.session_state.running = False

chunk_secs = st.slider("片段秒數", 1.0, 5.0, 2.0, 0.5)
vad_rms    = st.slider("VAD 音量門檻 (RMS)", 50, 1000, 200, 10)

if st.session_state.file_path:
    st.info(f"寫入中：`{st.session_state.file_path}`")

placeholder = st.empty()
download_btn = st.empty()

# --- 音訊處理 callback ----
chunker = Chunker(sample_rate=48000, chunk_secs=float(chunk_secs), vad_rms=int(vad_rms))

def audio_frame_callback(frame: av.AudioFrame) -> av.AudioFrame:
    # 取得 PCM，混成單聲道 int16
    pcm = frame.to_ndarray()
    if pcm.ndim == 2:
        pcm = pcm.mean(axis=0)
    pcm = pcm.astype(np.int16, copy=False)

    # 僅在 running 時收集
    if st.session_state.running:
        chunk = chunker.push(pcm)
        if chunk is not None:
            wav_bytes = pcm16_to_wav_bytes(chunk, sample_rate=48000)
            try:
                st.session_state.audio_q.put_nowait(wav_bytes)
            except queue.Full:
                pass  # 忽略擁塞，避免阻塞音訊回調
    return frame

# --- 啟動 WebRTC 麥克風 ----
rtc_configuration = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
webrtc_streamer(
    key="mic",
    mode=WebRtcMode.SENDONLY,
    audio_frame_callback=audio_frame_callback,
    media_stream_constraints={"video": False, "audio": True},
    rtc_configuration=rtc_configuration,
)

# --- 轉錄背景執行緒 ----
def worker():
    while True:
        wav_bytes = st.session_state.audio_q.get()
        try:
            text = transcribe_wav_bytes(wav_bytes)
            text = text.strip()
            if text:
                st.session_state.transcript.append(text)
                # 立刻寫檔
                if st.session_state.file_path:
                    with st.session_state.file_lock, open(st.session_state.file_path, "a", encoding="utf-8") as f:
                        f.write(text + "\n")
        except Exception as e:
            st.session_state.transcript.append(f"[ERROR] {e}")
        finally:
            time.sleep(0.01)

if not st.session_state.worker_started:
    threading.Thread(target=worker, daemon=True).start()
    st.session_state.worker_started = True

# --- UI 呈現與下載 ---
joined = "\n".join(st.session_state.transcript[-400:])  # 避免過長
placeholder.text_area("逐字稿（即時追加）", joined, height=320)
if joined:
    download_btn.download_button(
        "下載目前逐字稿 (.txt)",
        data=joined.encode("utf-8"),
        file_name="transcript-live.txt",
        mime="text/plain",
        use_container_width=True,
    )
```

---

## 注意事項

- 目錄 `resource/` 需有寫入權限（Docker 或雲端主機請掛載對應 Volume/磁碟）。
- 若希望每次「開始轉錄」覆蓋舊檔，可將 `"a"` 改為 `"w"`（需自行評估多執行緒）。
- 可在 `worker()` 裡加入簡單的段落時間戳（例如每段前加 `datetime`）。
- 若要避免檔名中出現非法字元，請在組檔名時做清理。

---

## 版本控制與部署

- 建議將 `resource/` 列入 `.gitignore`（避免將逐字稿進版）。
- 部署到雲端（如 Streamlit Community / EC2 / Azure App Service）時，請確認容器或主機的持久化策略（Volume）。

---

## 參考
- **Audio API（Speech-to-Text Quickstart）**：支援 `gpt-4o(-mini)-transcribe` 於 `/audio/transcriptions`。citeturn0search7  
- **streamlit-webrtc 官方文件**：瀏覽器麥克風串流到 Python、音訊回調示例。citeturn6view0  
- **Realtime API**（若要更低延遲）：官方指南。citeturn0search6turn0search11

---

## Commit 範例
- `feat(rt-transcribe): mic streaming + chunked transcription via gpt-4o-mini-transcribe`
- `chore: add VAD & rtc config, .env.example, requirements`
- `docs: add PR for real-time mic transcription`

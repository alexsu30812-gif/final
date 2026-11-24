# DeepMIR Final Project：四週團隊計畫

2026年11月24日 · @Someone

## 計畫摘要

我們只有 28 天，所以要做出一條可靠的 pipeline，並回答一個問題：**自動 structure planning 是否比固定結構更能讓 B 的 chorus 融入新歌？** 目前還沒有跑過任何東西，因此第一個目標是在 Dec 6 前做出一首能跑通的歌。

| 項目 | Dec 22 前要完成 | 進度超前才做 | 暫時不做 |
|---|---|---|---|
| Song B | 人工挑選 pairs，再做簡單的 retrieval demo | 以人工挑選的 B 評估 retrieval | Cross-lingual B |
| Genres | 3 種 genre，只做英文歌 | 第四種 genre | Cross-genre pairs |
| Chorus | 保留 B 的 chorus 音訊，只做有限的 pitch 與 tempo 調整 | 用 SoulX-Singer 重新演唱 chorus | Interplay transfer |
| Generation | ACE-Step 1.5 在 chorus 前後做 repaint | Seam LoRA | Score-to-audio control |
| Lyrics | LLM 在生成前依 syllable 限制寫 lyrics | Audio-first lyric fitting | Cantonese tone constraints |
| Evaluation | Chorus retention、seam metrics、blind listening test | Era-mismatch ablation | 大規模 user study |

與 pitch 相比，有一項改動需要全隊同意：core version 在生成音訊之前先寫 lyrics，因為 audio-first lyrics 需要多一個重新演唱的步驟，可能卡住其他所有工作。我們仍可把 audio-first lyrics 當作 stretch result 或 future work 呈現。

**本週**：開一場 60 分鐘的 kickoff、確認分工，並在 Nov 29（日）前證明 ACE-Step 能在我們的 GPU 上圍繞固定的 chorus 生成。

## 現在要討論的事

今天先定前 5 項，它們會卡住本週每個人的第一個小目標；其餘 5 項在 Gate 1（Nov 29）前決定即可。每項都有建議選項，沒有異議就直接採用，把結果填在最後一欄。

### 今天決定（Nov 25 前）

| 議題 | 選項 | 建議 | 結果 |
|---|---|---|---|
| 1. 誰當 Member A / B / C / D | (a) 依「如何選擇角色」表各自認領　(b) 先把 C 給有最強 GPU 的人，其餘三人再認領 | (b)：C 的工作完全卡在 GPU 上 | |
| 2. 用哪張 GPU | (a) 成員自己的 GPU　(b) 學校或實驗室 server　(c) 雲端租用 | 先用手邊最強的那張跑 Gate 1，另一個選項當備案；至少 12 GB | |
| 3. Lyrics 與音訊的順序 | (a) 先寫 lyrics 再生成音訊　(b) 先生成音訊再填 lyrics（pitch 原案） | (a)：(b) 多一個重新演唱的步驟，可能卡住全部；(b) 留到 future work | |
| 4. 共用工具 | (a) GitHub + 共用雲端硬碟　(b) 全部放在一台 server 上 | (a)：程式碼進 git，音檔放雲端硬碟，不進 git | |
| 5. 會議節奏 | (a) 週日晚上 30 分鐘　(b) 週日 30 分鐘 + 週三群組文字回報 | (b)：週三一句話回報「做完哪個小目標、卡在哪裡」 | |

### Gate 1 前決定（Nov 29 前）

| 議題 | 選項 | 建議 | 結果 |
|---|---|---|---|
| 6. 哪 3 種 genre、年代差距多少 | (a) R&B、pop、disco，差 20 年　(b) 換掉其中一種　(c) 差距降為 15 年 | (a)；若 Member A 找不到足夠的 pairs 再改 (c) | |
| 7. 目標歌曲長度 | (a) 約 2 分鐘　(b) 約 90 秒　(c) 3 分鐘以上 | (a)；若 Gate 1 量出來太慢，降到 (b) | |
| 8. Chorus 允許的改動 | (a) 最多 2 個半音、tempo 變動 8%　(b) 完全不改，只挑 key 與 tempo 接近的 pairs | (a)：(b) 會讓可用的 pairs 太少 | |
| 9. Retrieval demo 的資料 | (a) Music4All　(b) FMA　(c) 只用人工挑選的 pairs | 先申請 (a)，Dec 1 前沒拿到就改 (b) | |
| 10. Lyrics LLM | (a) 有額度的 LLM API　(b) 本地開源模型 | (a)：Member B 就不需要 GPU | |

### 向 TAs 或課程網頁確認

- [ ] Dec 22 報告的長度與形式
- [ ] Slides 是否同樣需要提前一天繳交（本計畫依 pitch 規則假設是）
- [ ] 是否還需繳交書面報告或程式碼，以及期限

## System architecture

整體 pipeline 分三段：先檢索並分析 song B，再擷取其內容並規劃結構，最後用 ACE-Step 生成；只有 structure planner 是我們新做的部分。

Core version 不訓練任何模型，Seam LoRA 只在進度超前時才做。Cross-lingual retrieval 與 Cantonese lyrics 目前不在範圍內，所以沒有畫進來。

## System flowchart

工作分成四個階段，每個階段由一位成員負責，彼此以固定的 handoff 檔案銅接，所以沒有人需要等別人把程式寫完。

步驟 4 與 5 是我們要測試的貢獻。對照方法把這兩步換成直接生成或固定結構，其他步驟完全相同。本週先講定三種 handoff 格式，在真正的階段完成前先用手做的範例檔案。

## 分工

每人負責一個 pipeline 階段和一項共同職責，四人從第一天起就能平行作業。成員在 kickoff 時依下方的需求選擇角色。Member C 需要最強的 GPU。

| Member | 負責 | 主要工具 | 產出 | 共同職責 |
|---|---|---|---|---|
| Member A | 資料與分析 | MERT、All-In-One、Demucs、CREPE、SheetSage、Whisper | Song pairs、A profiles、B chorus packages、retrieval demo | 期末簡報與 demo 音訊 |
| Member B | 規劃與 lyrics | LLM、rule-based constraints、CMUdict | Structure planner、lyrics、三種實驗條件 | Pipeline 整合與共用 repo |
| Member C | 音訊生成 | ACE-Step 1.5、repaint、音訊處理 | 生成的歌曲、seam 處理、batch runs | GPU 排程與 run logs |
| Member D | 評估 | Whisper、DTW、SongEval、CoverHunter、統計 | Metrics、sanity tests、listening test、結果圖表 | 每週 gate 檢查與時程 |

每個人都要報告自己做的部分，也要依 flowchart 的箭頭審查相鄰一位成員的 handoff。

### 如何選擇角色

GPU 數字在本週實測 ACE-Step 之前都只是規劃用的估計值。

| 角色 | GPU 需求 | 適合人選 | 所需資源 |
|---|---|---|---|
| Member A：資料與分析 | 中等，間歇使用（約 8 GB） | 對歌曲結構敏銳，耐得住資料清理與人工檢查 | 最多的儲存空間、dataset 存取權、跑 Demucs 與 MERT 的 GPU 時間 |
| Member B：規劃與 lyrics | 低（若用 LLM API 則不需要） | Python 與系統整合最強，懂一些樂理，熟悉 LLM prompting | LLM API 或額度、GitHub、一般筆電 |
| Member C：音訊生成 | 最高（至少 12 GB，最好 16 到 24 GB） | PyTorch 與模型除錯經驗最豐富，能判斷音質 | 可長時間使用的專用 GPU（特別是 Dec 14 到 16），以及存放生成音訊的空間 |
| Member D：評估 | 低到中等，短時間任務（約 8 GB 或共用） | 擅長統計與實驗設計、有條理、能找到受試者 | 跑 Whisper 與 CREPE 的共用 GPU、問卷工具、至少 12 位評分者 |

## 時程

時程中有三個週日 gate，Dec 13 code freeze，最後 9 天用於整理結果與準備報告。

| Gate | 通過條件 | 若未通過 |
|---|---|---|
| Gate 1，Nov 29 | ACE-Step 在我們的 GPU 上圍繞固定 chorus 生成，並量測 VRAM 與時間 | 把原始 chorus 貼回，只重新生成 seams |
| Gate 2，Dec 6 | 一個指令產出一首含 B chorus 的完整歌曲，且 metrics 能在其上執行 | 停止新增功能，四人一起 debug pipeline 直到能跑 |
| Gate 3，Dec 13 | 3 種方法都能在 3 組 development pairs 上執行，且 metrics 能抓出已知的壞音訊 | 縮減為 6 組 test pairs 與 2 個 seeds，然後照樣 freeze |

## 每位成員的小目標

每個人一次只看自己清單上「下一個」小目標就好：每個目標約 1 到 3 天，箭頭後面是「做到什麼程度算完成」，做完就打勾。日期是最晚期限，標 Gate 的那一項沒做完時，當週週日改用風險表裡的 fallback。

### Member A：資料與分析

- [ ] Nov 25 選好 1 組 R&B development pair → A 與 B 的音檔放進共用資料夾
- [ ] Nov 27 跑通 Demucs 與 All-In-One → 產出 B 的 vocals / 伴奏分離檔與段落標記
- [ ] Nov 29 人工修正 chorus 邊界 → chorus 起訖時間寫進 chorus package v0
- [ ] Dec 1 Music4All 存取權有結果 → 拿到權限，或決定改用 FMA
- [ ] Dec 3 A profile script → 一個指令輸出 tempo、key、音域、genre、結構
- [ ] Dec 5 B chorus package script → 一個指令輸出音訊、lyrics、melody、tempo、key、樂句長度
- [ ] Dec 6 挑好 12 組 pairs → pair 清單（3 組 development + 9 組 test）
- [ ] Dec 10 12 個 chorus packages 都人工檢查過 lyrics 與邊界
- [ ] Dec 13 Retrieval demo → 輸入 artist A，輸出排序後的候選 B
- [ ] Dec 16 Listening 片段剪好，系統介紹 slides 草稿完成
- [ ] Dec 19 簡報定稿，demo 片段選好

### Member B：規劃與 lyrics

- [ ] Nov 25 開好 repo 與資料夾結構 → 四個人都能 push
- [ ] Nov 26 定義 plan.json 與 chorus package 格式 → 各有一個手寫範例檔，Member A 與 C 都同意
- [ ] Nov 28 3 個固定歌曲模板 → 3 個 plan.json（Method 2 要用）
- [ ] Nov 29 LLM lyric prompt v0 → 對範例 plan 寫出符合 syllable 數的 lyrics
- [ ] Dec 3 Planner v1 → 對 development pair 輸出候選結構並選出一個
- [ ] Dec 6 一個指令跑完 pipeline → 輸入一組 pair，輸出一首歌（Gate 2）
- [ ] Dec 10 三種條件都能跑 → 同一組 pair 輸出 3 個版本，長度與輸入一致
- [ ] Dec 13 Freeze 程式碼 → 在 repo 打上 tag（Gate 3）
- [ ] Dec 16 Final runs 期間只修會讓 pipeline 壞掉的 bug，每個改動都記錄

### Member C：音訊生成

- [ ] Nov 26 裝好 ACE-Step 1.5 → 生成一首完整歌曲
- [ ] Nov 28 圍繞固定 chorus 做 repaint → 一個輸出檔，加上 VRAM 與每首耗時紀錄
- [ ] Nov 29 檢查 chorus 有沒有被改動（Gate 1）→ 給出是/否；若有改動，改用「貼回原 chorus」
- [ ] Dec 2 Key 與 tempo 對齊 → chorus 在允許範圍內移調、變速
- [ ] Dec 4 依 plan.json 生成新段落 → 用 Member B 的範例檔跑出一首
- [ ] Dec 6 一種 seam 方法 → chorus 兩側各 repaint 幾拍的版本
- [ ] Dec 10 只在 3 組 development pairs 上調好 seam 設定
- [ ] Dec 13 Batch runner → 固定 seeds、有 log、中斷可續跑，並量過一整個 batch 的時間
- [ ] Dec 16 81 首 test 歌曲全部生成，每次失敗都有回報

### Member D：評估

- [ ] Nov 27 寫下 chorus retention 與音域的數值定義 → 一頁說明，全隊同意
- [ ] Nov 29 Lyric metric → 對任一首歌輸出 chorus 的 Whisper WER
- [ ] Nov 29 Melody metric → 輸出 pitch intervals 加 DTW 的分數
- [ ] Dec 2 Listening test 題目草稿
- [ ] Dec 4 Seam metric 與音域檢查
- [ ] Dec 6 所有 metrics 跑在第一首 end-to-end 歌曲上（Gate 2）
- [ ] Dec 9 Sanity test → 已知的壞音訊會被 metrics 抓出來
- [ ] Dec 12 盲測表單完成、順序隨機，並找 2 人試填修正
- [ ] Dec 18 表單 Dec 16 開放、Dec 18 23:59 關閉 → 至少 12 份回覆
- [ ] Dec 19 結果圖表與失敗分析完成

### 全員

- [ ] Nov 25 Kickoff：定完「現在要討論的事」的前 5 項
- [ ] Dec 18 每人至少找 3 位未參與本專案的評分者
- [ ] Dec 20 完整計時彩排，之後把 slides 寄給 TAs
- [ ] Dec 21 最終彩排，測試 demo 音訊
- [ ] Dec 22 上台報告

## 實驗與評估

最終實驗共生成 81 首歌：9 組 test pairs × 3 種方法 × 每種方法 3 個固定 seeds。每組 pair 另做一個 plain splice，共 9 個非生成的 baseline 片段。

| 設計項目 | 選擇 |
|---|---|
| Development set | 3 組 pairs，用於所有調整，絕不當作 test 結果報告 |
| Test set | 9 組 pairs：3 種 genre 各 3 組有年代差距的 pairs，例如 R&B、pop、disco |
| Baseline | Plain splice，不做生成 |
| Method 1 | Direct conditional generation |
| Method 2 | Fixed song structure |
| Method 3（ours） | Automatic chorus-conditioned structure planning |
| 保持相同 | Backbone model、輸入、歌曲長度、seeds 與 retry budget |

Constraints 與品質分開報告，避免一首好聽的歌掩蓋掉 chorus 已經遺失的事實。

| 問題 | Metric | 類型 |
|---|---|---|
| Chorus 有保留下來嗎？ | Lyric WER、melody interval DTW、version-identification match | Constraint |
| 符合 artist A 嗎？ | 有聲時間落在 A 音域外的比例、tempo 與 key 吻合度 | Constraint |
| 接縫聽起來自然嗎？ | 20 秒 seam 片段的盲評、seam 處的 feature jump | Quality |
| 整首歌成立嗎？ | 整首歌盲評、SongEval | Quality |
| 方法可靠嗎？ | 失敗率、retry 次數、每首歌的 GPU 時間 | Cost |

**Listening test**：目標至少 12 位評分者。每位評分者聽隨機 3 組 pairs 在全部 4 種條件下的 seam 片段，再加上同一組 pair 的 3 首完整歌曲，總共約 15 分鐘。

為避免 cherry-picking，所有 listening 片段都用 seed 1，自動 metrics 則報告全部 3 個 seeds。只有 9 組 pairs，因此結果應呈現為初步證據，並附上含不確定性的 paired differences，而不是宣稱已經普遍證明。

## 風險與 fallback

最大的風險是 ACE-Step 改動了 chorus 或接得不好，所以我們最先測這件事，並預備一條較簡單的路線。

| 風險 | 早期徵兆 | Fallback | 負責人 |
|---|---|---|---|
| Repaint 改動了保留的 chorus | 生成後 chorus 區段有差異（Nov 29） | 把原始 chorus 貼回，只重新生成 seams | Member C |
| GPU 太慢或記憶體太小 | 單首歌耗時太久，跑不完 81 次 | 縮短歌曲、減為 2 個 seeds，或只用 6 組 test pairs | Member C |
| Music4All 無法及時使用 | Dec 1 前仍無存取權 | Retrieval demo 改用 FMA，pairs 維持人工挑選 | Member A |
| Music4All 的 30 秒片段沒有涵蓋 chorus | 檢索到的片段沒有可用的 chorus | 片段只用於排序，選定的 pairs 另找完整歌曲 | Member A |
| Transcription 錯誤 | Lyrics 或 melody 未通過人工檢查 | 限定 12 組 pairs 並人工修正 | Member A |
| Planner 沒有改善 | Dec 13 前 development pairs 看不到提升 | 報告 negative result，並聚焦於哪些 constraints 真正重要 | Member B |
| 生成的 vocals 不清楚 | 新段落 WER 偏高 | 在 retry budget 內生成，並報告失敗率 | Member B |
| 評分者太少 | Dec 17 前回覆少於 8 份 | 每位成員多找人，並縮短表單 | Member D |
| Demo 的版權問題 | 公開資料中使用商業歌曲 | 只在課堂上播放、標註每首 B 的出處，公開內容一律用 FMA | Member A |

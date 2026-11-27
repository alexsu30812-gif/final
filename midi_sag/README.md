# MIDI-SAG：可用在 baseline 的地方與試跑步驟

2026-11-27 整理。**尚未實際執行**，內容來自閱讀 [MIDI-SAG](https://github.com/fundwotsai2001/MIDI-SAG) 的 README、三個 `inference_*.sh`、`install.sh`、`MuseControlLite_inference_continuation.py`（大部分）、`MuseControlLite_inference_47s_scale_up.py`、`config_inference_full_song.py`、`utils/extract_conditions.py`，以及 [MuseControlLite](https://github.com/fundwotsai2001/MuseControlLite) README。論文：[arXiv 2602.22029](https://arxiv.org/abs/2602.22029)。

## 它做什麼

輸入人聲音訊與人聲 MIDI，輸出伴奏 WAV，並與人聲混音。底層是 Stable Audio Open 1.0 加 MuseControlLite adapter。條件有四種：

| 條件 | 來源 |
| --- | --- |
| 和弦 | 和弦檔（`start end chord`，秒），預設由 AccoMontage2 依 `CHORD_STYLE` 產生 |
| 旋律 | **人聲音訊**經 RMVPE 抽 F0，不是讀 MIDI |
| 節奏 | ground-truth 模式從 MIDI 的第一個 tempo 由 t = 0 起排拍點（假設 4/4、固定速度） |
| 段落 | `STRUCTURE_STARTS`／`STRUCTURE_TAGS`，每段可有不同文字提示 |

每段生成約 47.55 秒；`full_song` 模式把各段接起來，下一段以前一段生成的伴奏作為音訊參考。

## 對照 baseline 投影片（`baseline_tryout_report_fixed.pptx`）

1. **第 9 頁選項 C 需要修正。** 投影片寫 MuseControlLite 支援 melody + in/outpainting。MuseControlLite README 雖然列出 audio inpainting／outpainting，但同時寫明 audio condition 的 adapter **尚未釋出**。MIDI-SAG 的遮罩設定預設關閉，也沒有開放給使用者。所以目前**不能用它鎖住 B 副歌的原音訊再補前後段**。
2. **MIDI-SAG 幾乎就是第 9 頁選項 A 的現成版本。** 選項 A 是 SoulX-Singer 人聲 + MuseControlLite 伴奏再混音，MIDI-SAG 的 ComposeFlow 模式正是這條鏈。選項 A 投影片列的缺點是「3 個模型 + 混音，工作量最大」，MIDI-SAG 已經把串接做好了。
3. **可以給選項 B 當 guide。** 選項 B 是把規劃好的 MIDI 合成粗略 guide，再交給 ACE-Step 重生。MIDI-SAG 的伴奏比純合成器 guide 更接近真實編曲，可以比較兩種 guide 的效果。
4. **第 8 頁 Route 2 的「A chords」可以直接餵進去。** 把我們的和弦規劃（含和弦選位的零格／一格修改）寫成和弦檔，放在 `CHORD_PATH`，略過 AccoMontage2 那一步。腳本沒有內建這個開關，要自己改，見下方步驟 3。AccoMontage2 的 `RANDB` 風格可以當「不看 A 草稿」的對照組。
5. **副歌人聲可沿用 baseline 的 Demucs `vocals.wav`。** 旋律條件讀人聲音訊，所以伴奏會跟著 B 的真實唱法走。新段落也需要人聲音訊，要先用 SoulX-Singer 或導唱產生。
6. **第 4 頁的兩個問題，可以試 MIDI-SAG 附帶的工具。**
   - pYIN 還有一個八度錯誤：可改試 GAME 做人聲轉 MIDI。
   - allin1 把速度判成兩倍（158 vs 80）：可改試 Singing-Vocal-Beat-Tracking，它能設定 `MIN_BPM`／`MAX_BPM`。

   這兩個工具都還沒有驗證過。
7. **`STRUCTURE_STARTS`／`STRUCTURE_TAGS` 和 `plan.json` 的段落表是同一件事。** 段落從小節換算成秒就能直接用，固定曲式和自動規劃兩組都能用它渲染。

## 已知風險

- 腳本裡寫死了作者機器上的路徑（`/data/home/fundwotsai/...`），出現在 `MuseControlLite_inference_continuation.py` 和 `inference_ComposeFlow.sh`，需要手動改。
- 只能在 CUDA 上跑（程式到處呼叫 `.cuda()`），repo 沒寫 VRAM 需求。
- Stable Audio Open 是 gated 模型：需要 Hugging Face 帳號，在模型頁同意條款，再 `huggingface-cli login`。
- ground-truth 模式的拍點從 t = 0 開始。人聲 MIDI 與音訊**要從第一個重拍開始裁切**，MIDI 要寫入正確的 tempo，否則預設 120 BPM。
- 在讀過的程式裡，段與段之間只看到直接串接（`torch.cat`），沒看到 crossfade，接縫要實測。
- MuseControlLite 公開的權重以 MTG-Jamendo 器樂為主；MIDI-SAG 自己的訓練資料沒有讀到。R&B 風格好不好要實測。
- `install.sh` 用 Python 3.9、torch 2.5.1，而且沒有指定 CUDA 版本的 index URL。如果 GPU 是 RTX 50 系列，torch 2.5.1 很可能不支援，需要換成新版 torch，再確認其他套件相容。

## 在 GPU 電腦上試跑

```bash
# 0. 放在本 repo 之外，或放在已被 .gitignore 排除的 third_party/
git clone https://github.com/fundwotsai2001/MIDI-SAG.git third_party/MIDI-SAG
cd third_party/MIDI-SAG
conda create -n midi-sag python=3.9 -y && conda activate midi-sag
./install.sh                      # 會下載 RMVPE、GAME、MuseControlLite、SoulX-Singer 權重
huggingface-cli login             # 先在 stabilityai/stable-audio-open-1.0 頁面同意條款

# 1. 找出並改掉寫死的路徑
grep -rn "/data/home/fundwotsai" --include=*.py --include=*.sh .
ls MIDI-SAG_checkpoints           # 確認 rmvpe_model.pt 的實際位置，與腳本一致
```

1. **先跑原作者範例**（`inference_gt_MIDI-SAG.sh`，`MODE="47s"`）。記錄耗時與 VRAM 峰值（另開視窗跑 `nvidia-smi --query-gpu=memory.used --format=csv -l 1`），並試聽。
2. **換成我們的 B 副歌。** `VOCAL_AUDIO_PATH` 用 Demucs 的 `vocals.wav`，`VOCAL_MIDI_PATH` 用 pYIN 或 GAME 轉出的 MIDI，tempo 設成 80。兩者都從副歌第一個重拍開始裁切。先跑 `MODE="47s"`。
3. **換成我們自己的和弦。** 用本資料夾的 `chords_to_lab.py` 產生和弦檔，覆蓋到腳本的 `CHORD_PATH`（`$OUTPUT_DIR/Harmonization_results/btc_txt/${SONG_NAME}_chord_gen.txt`）。再把腳本中呼叫 `AccoMontage2/demo_SOME.py` 的步驟註解掉，避免檔案被覆寫。
   ```bash
   python chords_to_lab.py --bpm 80 C:maj A:min F:maj G:maj C:maj D:min7 F:maj G:maj -o chord_gen.txt
   ```
4. **每次記錄：**
   - 伴奏有沒有照和弦走：用和弦辨識對照和弦檔。
   - 拍點有沒有對齊。
   - 人聲和伴奏融不融合。
   - 耗時。
   - 失敗原因。

   填進 `run_manifest.json`，格式見主 README。

如果步驟 3 可行，Route 2 的和弦規劃就能直接產生可聽的音訊，也可以和 ACE-Step repaint（Route 1）用同一組 B 比較。

# 11/27 會議：和弦選位與副歌入口的示範程式

音檔不進 Git，用下列腳本在本機重新產生。所有音檔都是原創合成的示意樂句。

| 資料夾 | 內容 | 執行（在 `meeting_1127/` 底下） |
| --- | --- | --- |
| `reharmonization/` | 八小節只改一格和弦：產生 `baseline`、`targeted`、`position_control` 三個 WAV | `python3 reharmonization/reproduce.py`（只用標準函式庫） |
| `crossed/` | 兩個主歌結尾 × 兩個副歌的交叉試聽，給 `index.html` 使用 | `python3 crossed/make_examples.py` |
| `harmony_validation/` | 在 POP909 上做的代理測試：人工改壞一格，看各方法能否找回；另有跨歌配對的敏感度測試。CSV／JSON 是已跑好的結果 | 見下方 |

## harmony_validation

需要 POP909（每首歌一個資料夾，內含 `NNN.mid` 與 `chord_midi.txt`），資料集不放在本 repo。

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python harmony_validation/diagnostic.py /path/to/POP909/training     # 寫出 per_song.csv、summary.json
python harmony_validation/cross_song.py /path/to/POP909/training     # 寫出 cross_pairs.csv、cross_summary.json
python harmony_validation/conservative_edits.py                       # 寫出 conservative_summary.json
```

原本的結果用 numpy 2.2.6、pretty_midi 0.2.11 算出，種子 11272026。輸入資料的指紋記錄在 `summary.json`。

這些數字是代理指標，**不是聽感結果**：它只衡量方法能不能找回被改掉的標註和弦。

## 相關文件

`../docs/` 收有會議提案與文獻核查 PDF。

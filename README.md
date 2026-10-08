# Kurage 論点AIマップ（kronten）

すでにある声（国会の発言・X の投稿・ニュースのコメント・任意の CSV）から、**話題の地図**と、話題ごとの**論点（賛成か反対かを問える1文）**を作る。誰がどこで言った声か（国会の質疑・政府の答弁・会派・年・ネット）を分けて見られる。

広聴AI（DD2030）がやっている「文章の山から話題の地図を作る」部分に、論点と出典・会派・時期の内訳を足したもの。論点の賛否と合意点は [Kurage 合意点マップ（kconsensus）](../kconsensus) に渡す。

## 作り方（1本）

```bash
.venv/bin/python scripts/build_map.py --slug kodomo-sns --tracker kodomo-sns --reactions kodomo-sns
.venv/bin/python scripts/build_map.py --slug mydata --theme "テーマ名" --csv data/opinions.csv   # text 列・attribute_* 列
/usr/bin/python3 scripts/shot.py outputs/<slug>/map.html   # 360/390/1280px のはみ出し確認
```

→ `outputs/<slug>/map.json` と `map.html`

## 中身

| 段 | 使うもの | 理由 |
|---|---|---|
| 材料 | 国会トラッカー（xb4g/giin の tracker_speech）・合意点マップの reaction・CSV | 「書いてもらう」入口ではなく、すでにある声を拾う |
| 区切り | 発言を200字前後に区切り、トラッカーの語の**組**を全部含む部分だけ | 1語だけで拾うと施政方針演説の別の話題まで混ざった |
| 埋め込み | intfloat/multilingual-e5-large（fastembed・手元の CPU） | 日本語に強い・外部に送らない |
| まとめ | KMeans（random_state 固定） | 同じ材料なら毎回同じ結果（広聴AIは同じ入力2回で208件中24件ぶれた） |
| 名前・要約・論点 | gemma4:12b-it-qat（0.3 の Ollama・think:false・JSON スキーマで型を縛る） | まとまり1つに1回だけ。`format:"json"` だけだと name に true が入った |

- 埋め込みは `outputs/<slug>/embeddings.npy` に保存し、件数が同じなら読み直す。
- 0.3 の Ollama は kojima で動いているがモデル置き場が ollama ユーザーの持ち物で、新しいモデル（bge-m3 等）を pull できない（2026-10-08）。埋め込みを CPU にしたのはそのため。

## 試作の公開

`https://proto.exbridge.jp/kronten/`（noindex）。FTP `/web/proto_exbridge_jp/kronten/`。

## 参考にした OSS

- Jigsaw sensemaking-tools（Apache-2.0）：論点（proposition）の生成。Gemini 前提なので考え方だけ使い、gemma4 で作り直した。
- 広聴AI（AGPL-3.0）・Talk to the City：話題の地図。コードは使っていない（AGPL を持ち込まない）。

ライセンス: MIT

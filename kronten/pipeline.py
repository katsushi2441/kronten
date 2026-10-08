"""話題の地図と論点を作る。

1. 埋め込み（multilingual-e5-large・手元の CPU。外部に送らない）
2. まとめる（KMeans・乱数の種を固定。同じ入力なら毎回同じまとまりになる）
3. 名前・要約・論点（gemma4:12b・手元の Ollama。まとまり1つにつき1回だけ呼ぶ）
4. 出典・会派・年ごとの内訳と、代表的な声（元の発言へのリンクつき）

広聴AI（話題の地図まで）に対して、論点（賛否を問える1文）と、誰がいつ言ったかの内訳まで出す。
"""
import collections
import json
import math
import os
import re
import urllib.request

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

OLLAMA = os.environ.get("KRONTEN_OLLAMA", "http://192.168.0.3:11434")
LLM = os.environ.get("KRONTEN_LLM", "gemma4:12b-it-qat")
EMBED = "intfloat/multilingual-e5-large"
CACHE = os.environ.get("FASTEMBED_CACHE_PATH", "/mnt/data/cache/fastembed")


def embed(texts, cache=None):
    """埋め込み。cache（.npy）があり件数が合えば読み直す（作り直しのたびに CPU で数分かけない）。"""
    if cache and os.path.exists(cache):
        e = np.load(cache)
        if len(e) == len(texts):
            return e
    from fastembed import TextEmbedding
    m = TextEmbedding(EMBED, cache_dir=CACHE)
    e = np.array(list(m.embed(["passage: " + t for t in texts], batch_size=16)))
    e = e / np.linalg.norm(e, axis=1, keepdims=True)
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        np.save(cache, e)
    return e


def choose_k(n):
    return max(5, min(14, round(math.sqrt(n / 3))))


# 返す形を型で縛る。"format": "json" だけだと name に true、summary に数字が入ることがあった（2026-10-08）
SCHEMA = {"type": "object", "properties": {
    "name": {"type": "string"}, "summary": {"type": "string"},
    "propositions": {"type": "array", "items": {"type": "string"}}},
    "required": ["name", "summary", "propositions"]}


def llm_json(prompt):
    body = json.dumps({"model": LLM, "prompt": prompt, "stream": False, "format": SCHEMA,
                       "think": False, "options": {"temperature": 0, "num_predict": 900}}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"}), timeout=600))
    try:
        return json.loads(r.get("response") or "{}")
    except json.JSONDecodeError:
        return {}


PROMPT = """あなたは、国会の発言とネットの声を整理する担当者です。
次の発言は、テーマ「{theme}」について、意味が近いものを集めた1つのまとまりです。

{samples}

このまとまりについて、JSON で返してください。
name には、何についての話題かを表す日本語の見出しを入れます。20字以内の体言止めにし、「〜について」は付けません。
summary には、このまとまりで言われていることの日本語の要約を入れます。80字以内で、発言に書かれていないことは足しません。
propositions には、賛成か反対かを問える論点の日本語の文を1〜2個入れます。各40字以内で「〜すべきだ」「〜である」の形にし、発言の中に根拠があるものだけにします。どちらかの立場に誘導する言葉は使いません。

例: {{"name": "年齢による利用制限", "summary": "16歳未満の利用を法律で制限する海外の動きと、その実効性をめぐる意見。", "propositions": ["16歳未満のSNS利用を法律で禁止すべきだ"]}}
"""


def _text(x):
    """LLM が {"name": {"text": ...}} のように入れ子で返しても、文字列を取り出す。"""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        return next((_text(v) for v in x.values() if _text(v)), "")
    if isinstance(x, list):
        return " ".join(_text(v) for v in x).strip()
    return ""


def label(theme, members):
    samples = "\n".join(f"- [{m['source']}] {m['text'][:200]}" for m in members)
    d = llm_json(PROMPT.format(theme=theme, samples=samples))
    raw = d.get("propositions") or []
    raw = raw if isinstance(raw, list) else [raw]
    props = [t for t in (_text(p) for p in raw) if t][:2]
    return {"name": _text(d.get("name"))[:30], "summary": _text(d.get("summary")), "propositions": props}


def build(theme, items, k=None, seed=0, cache=None):
    texts = [it["text"] for it in items]
    E = embed(texts, cache)
    k = k or choose_k(len(items))
    km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(E)
    xy = PCA(n_components=2, random_state=seed).fit_transform(E)
    clusters = []
    for c in range(k):
        idx = np.where(km.labels_ == c)[0]
        d = E[idx] @ km.cluster_centers_[c]
        order = idx[np.argsort(-d)]
        # 代表は中心に近い順。ただし出典が偏らないよう、出典ごとに最大4件まで
        reps, per = [], collections.Counter()
        for i in order:
            s = items[i]["source"]
            if per[s] < 4:
                reps.append(int(i))
                per[s] += 1
            if len(reps) >= 8:
                break
        lab = label(theme, [items[i] for i in reps])
        mem = [items[i] for i in idx]
        years = collections.Counter(m["date"][:4] for m in mem if m["date"])
        clusters.append({
            "id": c, **lab, "size": int(len(idx)),
            "by_source": dict(collections.Counter(m["source"] for m in mem).most_common()),
            "by_group": dict(collections.Counter(m["group"] for m in mem if m["role"] == "q").most_common(8)),
            "by_year": dict(sorted(years.items())),
            "quotes": [{k2: items[i][k2] for k2 in ("text", "source", "who", "group", "date", "url")} for i in reps[:6]],
            "center": [float(xy[idx, 0].mean()), float(xy[idx, 1].mean())],
        })
        print(f"  まとまり {c + 1}/{k}: {lab['name']}（{len(idx)}件）", flush=True)
    clusters.sort(key=lambda x: -x["size"])
    points = [{"x": round(float(xy[i, 0]), 4), "y": round(float(xy[i, 1]), 4),
               "c": int(km.labels_[i]), "s": items[i]["source"]} for i in range(len(items))]
    return {"theme": theme, "n": len(items), "k": k, "embed_model": EMBED, "llm": LLM,
            "sources": dict(collections.Counter(it["source"] for it in items).most_common()),
            "clusters": clusters, "points": points}

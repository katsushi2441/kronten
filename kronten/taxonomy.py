"""網目状の論点（1つの声が複数の論点に当てはまってよい）。2026-10-08、Xで「MECEではなく網目状のtaxonomyが欲しい」と指摘を受けて作った。

地図（KMeans）は1つの声を1つの話題にしか入れないので、同じ観点が出どころの文体の違いで別の話題に分かれると、
重なりが見えなくなる。ここでは論点の一覧（outputs/<slug>/taxonomy.json）を決め、声ごとに当てはまる論点を全部付けて、
論点ごとに「出どころ別に何%が触れているか」を数える。判定は gemma4（10件ずつまとめて1回）。
"""
import json
import urllib.request

from . import pipeline

SCHEMA = {"type": "object", "properties": {"tags": {"type": "array", "items": {
    "type": "object", "properties": {"n": {"type": "integer"}, "labels": {"type": "array", "items": {"type": "integer"}}},
    "required": ["n", "labels"]}}}, "required": ["tags"]}


def tag_batch(labels, texts):
    lab = "\n".join(f"{i}. {x['name']}：{x['desc']}" for i, x in enumerate(labels, 1))
    body = "\n".join(f"[{i}] {t[:220]}" for i, t in enumerate(texts, 1))
    prompt = (f"論点の分類:\n{lab}\n\n次の声それぞれについて、当てはまる論点の番号をすべて選んでください。"
              "複数でもよく、当てはまるものが無ければ空にします。賛成でも反対でも、その論点に触れていれば付けます（例: 「年齢制限は効果がない」も年齢制限の論点）。声の中にはっきり書かれていることだけで判断します。\n\n"
              f"{body}\n\ntags に、声の番号 n と、当てはまる論点の番号の配列 labels を入れてください。")
    b = json.dumps({"model": pipeline.LLM, "prompt": prompt, "stream": False, "format": SCHEMA, "think": False,
                    "options": {"temperature": 0, "num_predict": 800}}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(pipeline.OLLAMA + "/api/generate", data=b,
                                                                headers={"Content-Type": "application/json"}), timeout=600))
    try:
        out = {t["n"]: [l for l in t.get("labels") or [] if 1 <= l <= len(labels)] for t in json.loads(r["response"])["tags"]}
    except Exception:
        out = {}
    return [sorted(set(out.get(i, []))) for i in range(1, len(texts) + 1)]


def stats(labels, items, tags, group_of):
    groups = sorted({group_of(it["source"]) for it in items}, key=lambda g: ["国会", "ネット", "インタビュー"].index(g) if g in ("国会", "ネット", "インタビュー") else 9)
    tot = {g: sum(1 for it in items if group_of(it["source"]) == g) for g in groups}
    rows = []
    for li, lab in enumerate(labels, 1):
        cnt = {g: 0 for g in groups}
        for it, tg in zip(items, tags):
            if li in tg:
                cnt[group_of(it["source"])] += 1
        rows.append({"name": lab["name"], "desc": lab["desc"],
                     "by_group": {g: {"n": cnt[g], "pct": round(cnt[g] / tot[g] * 100, 1) if tot[g] else 0} for g in groups}})
    return {"groups": groups, "totals": tot, "rows": rows,
            "multi": round(sum(1 for t in tags if len(t) >= 2) / max(1, len(tags)) * 100, 1),
            "none": round(sum(1 for t in tags if not t) / max(1, len(tags)) * 100, 1)}

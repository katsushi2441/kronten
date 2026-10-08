"""材料の読み込み。「すでにある声」を、同じ形の行（Item）にそろえる。

Item = {id, text, source, who, group, role, date, url}
  source : 国会（質疑）/ 国会（政府答弁）/ X / Yahooコメント / CSV など、どこから拾った声か
  group  : 会派・投稿先など、絞り込みに使う属性
  role   : q（議員の質疑）/ gov（政府の答弁）/ net（ネットの声）/ csv
"""
import csv
import re
import sqlite3

GIIN_DB = "/home/kojima/work/xb4g/giin/data/giin.sqlite"
TRACKERS = "/home/kojima/work/xb4g/giin/data/trackers.json"
KCONSENSUS_DB = "/home/kojima/work/kconsensus/data/kconsensus.sqlite"

# 議事の進行や挨拶だけの文。論点の材料にならないので落とす
PROCEDURAL = re.compile(r"^(ありがとうございま|以上で|お答えいたします|お答え申し上げます|おはようございます|時間が(参り|来)|質問を終わ|よろしくお願い)")


def _sentences(body):
    body = re.sub(r"^○\S+?(君|大臣|委員|参考人|長)\s*", "", body.strip())
    body = body.replace("\r", "").replace("\n", "").replace("　", " ")
    return [s.strip() + "。" for s in body.split("。") if s.strip()]


def _chunks(body, max_len=220):
    """発言を、200字前後のかたまりに区切る（1文が長ければそのまま1かたまり）。"""
    out, cur = [], ""
    for s in _sentences(body):
        if PROCEDURAL.match(s):
            continue
        if cur and len(cur) + len(s) > max_len:
            out.append(cur)
            cur = ""
        cur += s
    if cur:
        out.append(cur)
    return [c for c in out if len(c) >= 30]


def tracker_words(key):
    import json
    t = json.load(open(TRACKERS, encoding="utf-8"))
    rows = t if isinstance(t, list) else t["trackers"]
    tr = next(a for a in rows if a["key"] == key)
    # 「子ども SNS」のような組は、組の語を全部含むときだけ当てる（「子ども」「環境」1語だけだと
    # 施政方針演説の子育て支援や国土強靱化まで拾ってしまった。2026-10-08）
    return tr["name"], [ws.split() for ws in tr["words"]]


def load_tracker(key):
    """国会トラッカーの発言。テーマの語を含むかたまりだけ使う（同じ発言の別の話題を混ぜない）。"""
    name, words = tracker_words(key)   # words = [["子ども","SNS"], ["SNS","年齢制限"], ...]
    con = sqlite3.connect(GIIN_DB)
    items = []
    for sid, date, speaker, kaiha, kind, body, url in con.execute(
            "SELECT speech_id,date,speaker,kaiha_at,kind,body,speech_url FROM tracker_speech "
            "WHERE tracker=? AND kind IN ('q','gov') ORDER BY date", (key,)):
        for i, ch in enumerate(_chunks(body or "")):
            if not any(all(w in ch for w in grp) for grp in words):
                continue
            items.append({
                "id": f"{sid}:{i}", "text": ch,
                "source": "国会（質疑）" if kind == "q" else "国会（政府答弁）",
                "who": speaker or "", "group": (kaiha or "政府") if kind == "q" else "政府",
                "role": kind, "date": date or "", "url": url or "",
            })
    return name, items


def load_reactions(slug):
    """合意点マップに取り込んだネットの声（X・ニュースのコメント）。"""
    con = sqlite3.connect(KCONSENSUS_DB)
    tid = con.execute("SELECT id FROM topic WHERE slug=?", (slug,)).fetchone()[0]
    items = []
    for rid, platform, text, url in con.execute(
            "SELECT id,platform,text,url FROM reaction WHERE topic_id=?", (tid,)):
        t = re.sub(r"https?://\S+", "", text or "").strip()
        if len(t) < 15:
            continue
        items.append({"id": f"r{rid}", "text": t, "source": platform, "who": "",
                      "group": platform, "role": "net", "date": "", "url": url or ""})
    return items


def load_csv(path, text_col="text"):
    """任意の CSV。attribute_ で始まる列は絞り込みの属性として group に入れる（最初の1列）。"""
    items = []
    with open(path, encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f)):
            t = (r.get(text_col) or "").strip()
            if len(t) < 10:
                continue
            attrs = [v for k, v in r.items() if k.startswith("attribute_") and v]
            items.append({"id": f"c{i}", "text": t, "source": r.get("source") or "CSV",
                          "who": "", "group": attrs[0] if attrs else "CSV", "role": "csv",
                          "date": r.get("date", ""), "url": r.get("url", "")})
    return items

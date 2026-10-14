"""Xの反応マップ：1つの投稿への返信を集め、立場の割合と話題に分けて、1枚のカードとページにする。

**なぜ作ったか。** 議員の投稿に、国会の質疑や地元の数字のカードを貼って返信すると、画像が見られて評価された
（2026-10-14）。話題の投稿ほど「反応の全体がどうなっているか」を知りたい人が多く、投稿した本人も引用しやすい。

**集め方の限界（2026-10-14 実測）。** fxtwitter の返信は「いいね順16件」と「新しい順16件」まで（続きの cursor は 404）。
fxtwitter の検索は止まっている。Yahoo リアルタイム検索の「@アカウント」で約40件、そのうち返信先がこの投稿のものだけを足す。
合わせて1投稿30〜60件ほど。**全部の返信ではない**ので、カードとページに必ずそう書く。割合は返信の数で、人の数ではない。

**載せないもの。** 返信した人のアカウント名と、返信の原文。出すのは立場ごとの割合と、AIがまとめた話題の要約だけ
（だれかの返信を晒さない・きつい言葉を広めない）。
"""
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request

from kronten.pipeline import LLM, OLLAMA

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
STANCES = ["賛同", "条件つき・別の提案", "反対・批判", "質問", "その他"]


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (kronten xmap)"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def post_id(url):
    m = re.search(r"/status(?:es)?/(\d+)", url) or re.match(r"^(\d{6,})$", url.strip())
    if not m:
        raise ValueError("投稿のURL（https://x.com/<アカウント>/status/<番号>）を渡してください")
    return m.group(1)


def _clean(text):
    t = re.sub(r"(^|\s)@\w+", " ", text or "")
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def collect(pid):
    """投稿と返信を集める。返信は [{id, text, likes, src}]（アカウント名は持たない）"""
    d = _get(f"https://api.fxtwitter.com/2/conversation/{pid}")
    st = d.get("status") or {}
    if not st:
        raise ValueError("投稿を読めませんでした（削除・非公開・鍵つきの可能性）")
    author = (st.get("author") or {}).get("screen_name", "")
    post = dict(id=pid, url=f"https://x.com/{author}/status/{pid}", author=(st.get("author") or {}).get("name", ""),
                screen_name=author, text=st.get("text") or "", created=st.get("created_timestamp") or 0,
                likes=st.get("likes") or 0, replies=st.get("replies") or 0, reposts=st.get("reposts") or 0)
    got = {}

    def add(rid, text, likes, src, by):
        if by and by.lower() == author.lower():   # 本人の続きの投稿は反応に数えない
            return
        t = _clean(text)
        if len(t) < 4 or rid in got:
            return
        got[rid] = dict(id=rid, text=t[:400], likes=int(likes or 0), src=src)
    for mode, src in (("likes", "いいね上位"), ("recency", "新しい順")):
        try:
            r = _get(f"https://api.fxtwitter.com/2/conversation/{pid}?ranking_mode={mode}")
        except Exception:  # noqa: BLE001
            continue
        for x in r.get("replies") or []:
            add(x["id"], x.get("text"), x.get("likes"), src, (x.get("author") or {}).get("screen_name"))
        time.sleep(1)
    # Yahoo リアルタイム検索（返信先がこの投稿のものだけ）
    acc = []

    def walk(o):
        if isinstance(o, dict):
            if "screenName" in o and ("text" in o or "displayText" in o):
                acc.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for prm in ({"b": 1}, {"md": "h"}):
        u = "https://search.yahoo.co.jp/realtime/search?" + urllib.parse.urlencode({"p": "@" + author, "ei": "UTF-8", **prm})
        h = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, u], capture_output=True, text=True).stdout
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
        if m:
            try:
                walk(json.loads(m.group(1)))
            except ValueError:
                pass
        time.sleep(1)
    for t in acc:
        if str(t.get("inReplyTo") or "") == pid:
            add(str(t.get("id")), re.sub(r"\tSTART\t|\tEND\t", "", t.get("displayTextBody") or t.get("displayText") or ""),
                t.get("likesCount"), "Yahoo", t.get("screenName"))
    return post, list(got.values())


def _llm(prompt, schema, num_predict=1500):
    body = json.dumps({"model": LLM, "prompt": prompt, "stream": False, "format": schema, "think": False,
                       "options": {"temperature": 0, "num_predict": num_predict}}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"}), timeout=900))
    return json.loads(r.get("response") or "{}")


def classify(post, replies, batch=25):
    """返信ごとの立場（元の投稿に対して）。返信1件ずつに番号を振り、番号と立場の組で返させる"""
    schema = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
        "n": {"type": "integer"}, "stance": {"type": "string", "enum": STANCES}}, "required": ["n", "stance"]}}},
        "required": ["items"]}
    for i in range(0, len(replies), batch):
        part = replies[i:i + batch]
        lines = "\n".join(f"{j}: {r['text'][:200]}" for j, r in enumerate(part))
        prompt = (f"次の「元の投稿」への返信を、元の投稿の主張に対する立場で分けてください。\n"
                  f"立場は {'・'.join(STANCES)} のどれか1つ。\n"
                  "- 賛同：主張に同意・応援・感謝\n- 条件つき・別の提案：一部は同意だが条件や別の案を出す\n"
                  "- 反対・批判：主張や投稿者・政党への反対、批判、皮肉\n- 質問：たずねている\n- その他：関係のない話・宣伝・判断できない\n"
                  "皮肉や反語は、言葉の表面ではなく言いたいことで判断してください。\n\n"
                  f"# 元の投稿\n{_clean(post['text'])[:600]}\n\n# 返信（番号: 本文）\n{lines}\n")
        got = {x["n"]: x["stance"] for x in (_llm(prompt, schema).get("items") or []) if isinstance(x, dict)}
        for j, r in enumerate(part):
            r["stance"] = got.get(j, "その他") if got.get(j) in STANCES else "その他"
    return replies


def topics(post, replies, k=3):
    """話題（2〜4個）。名前・1文の要約・どの返信が入るか。要約は返信の言葉を言い換え、原文や人の名前は書かない"""
    schema = {"type": "object", "properties": {"topics": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "summary": {"type": "string"}, "members": {"type": "array", "items": {"type": "integer"}}},
        "required": ["name", "summary", "members"]}}}, "required": ["topics"]}
    lines = "\n".join(f"{j}: {r['text'][:160]}" for j, r in enumerate(replies))
    prompt = (f"次の「元の投稿」への返信を、話題で{k}つ前後（2〜4つ）にまとめてください。\n"
              "- name：話題の短い名前（15字以内）。「政策への評価」「様々な意見」のようなぼんやりした名前にせず、"
              "返信が具体的に言っている中身（例：「実現したのは政権の手柄」「扶養150万円の壁が残る」）にする\n"
              "- summary：その話題で返信が言っていることを1文（50字以内）。"
              "返信の原文をそのまま引用しない。人の名前・アカウント名・悪口の言葉は書かない\n"
              "- members：その話題に入る返信の番号（1つの返信は1つの話題だけ）\n"
              "どの話題にも入らない返信は入れなくてよい。\n\n"
              f"# 元の投稿\n{_clean(post['text'])[:600]}\n\n# 返信（番号: 本文）\n{lines}\n")
    out = []
    seen = set()
    for t in (_llm(prompt, schema, 1200).get("topics") or [])[:4]:
        mem = [m for m in t.get("members") or [] if isinstance(m, int) and 0 <= m < len(replies) and m not in seen]
        seen.update(mem)
        if not mem or not t.get("name"):
            continue
        out.append(dict(name=str(t["name"])[:20], summary=str(t.get("summary") or "")[:70], n=len(mem)))
    out.sort(key=lambda x: -x["n"])
    return out


def build(url):
    pid = post_id(url)
    post, reps = collect(pid)
    if len(reps) < 8:
        raise ValueError(f"返信が {len(reps)} 件しか集まらなかったので、地図にしません（8件以上）")
    classify(post, reps)
    tops = topics(post, reps)
    cnt = {s: 0 for s in STANCES}
    for r in reps:
        cnt[r["stance"]] += 1
    src = {}
    for r in reps:
        src[r["src"]] = src.get(r["src"], 0) + 1
    return dict(id=pid, post=post, n=len(reps), stance=cnt, topics=tops, sources=src,
                built_at=time.strftime("%Y-%m-%d %H:%M"), model=LLM)

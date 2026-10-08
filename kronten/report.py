"""map.json → 1枚の HTML（ライトテーマ・スマホ対応・外部の JS を使わない）。

上から: 見出し → 材料の内訳 → 話題の地図（散布図）→ 話題ごとのカード（論点・出典の内訳・代表的な声）→ 作り方。
"""
import html

LOGO = "https://exbridge.jp/images/logo-mark-128.png"
MASCOT = "https://kurage.exbridge.jp/images/kurage_mascot_simple_v2.png"
COLORS = ["#0a9a8f", "#e07a2e", "#4a6fd1", "#c2417a", "#6a9a1f", "#8a55c7", "#d4a017",
          "#2a8bb5", "#b5482a", "#3f7f5f", "#7a6a55", "#5a5ad1", "#a0336a", "#2f9e7e"]
SRC_COLOR = {"国会（質疑）": "#4a6fd1", "国会（政府答弁）": "#7a8fb8", "X": "#12202f", "Yahooコメント": "#e07a2e"}


def h(s):
    return html.escape(str(s), quote=True)


def bar(d, total, colors=None):
    segs = "".join(
        f'<span style="width:{v / total * 100:.1f}%;background:{(colors or {}).get(k, "#9fb3c0")}" title="{h(k)} {v}"></span>'
        for k, v in d.items())
    legend = "".join(
        f'<li><i style="background:{(colors or {}).get(k, "#9fb3c0")}"></i>{h(k)} {v}</li>' for k, v in d.items())
    return f'<div class="bar">{segs}</div><ul class="lg">{legend}</ul>'


def scatter(m):
    """点の色は出典（国会・X・ニュース）。話題は番号で示し、一覧の番号と対応させる（名前を書くと重なって読めなかった）。"""
    pts = m["points"]
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H, P = 640, 380, 22
    sx = lambda x: P + (x - x0) / ((x1 - x0) or 1) * (W - 2 * P)
    sy = lambda y: H - P - (y - y0) / ((y1 - y0) or 1) * (H - 2 * P)
    dots = "".join(f'<circle cx="{sx(p["x"]):.1f}" cy="{sy(p["y"]):.1f}" r="3.2" fill="{SRC_COLOR.get(p["s"], "#9fb3c0")}" fill-opacity=".5"/>' for p in pts)
    marks = "".join(
        f'<g><circle cx="{sx(c["center"][0]):.1f}" cy="{sy(c["center"][1]):.1f}" r="10" fill="#fff" stroke="#12202f" stroke-width="1.5"/>'
        f'<text x="{sx(c["center"][0]):.1f}" y="{sy(c["center"][1]) + 4:.1f}" text-anchor="middle" class="cl">{n}</text></g>'
        for n, c in enumerate(m["clusters"], 1))
    legend = "".join(f'<li><i style="background:{v}"></i>{h(k)}</li>' for k, v in SRC_COLOR.items() if k in m["sources"])
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="話題の地図">{dots}{marks}</svg><ul class="lg">{legend}<li>丸の番号＝話題の一覧の番号</li></ul>'


def gap(m):
    """話題を「国会が中心」「ネットが中心」「両方」に分ける（国会＝質疑＋政府答弁の割合）。"""
    kokkai, net, both = [], [], []
    for c in m["clusters"]:
        k = sum(v for s, v in c["by_source"].items() if s.startswith("国会"))
        r = k / c["size"]
        (kokkai if r >= 0.6 else net if r <= 0.1 else both).append(c)
    if not kokkai or not net:
        return ""
    li = lambda cs: "".join(f'<li><a href="#t{c["id"]}">{h(c["name"])}</a> <small>{c["size"]}件</small></li>' for c in cs)
    return f"""<section class="card gap"><p class="sub" style="margin-top:0">国会とネットのずれ</p>
<div class="g2"><div><b>国会で話されている話題</b><ul>{li(kokkai)}</ul></div>
<div><b>ネットで話されている話題</b><ul>{li(net)}</ul></div></div>
{('<p class="note">両方で話されている話題: ' + '、'.join(h(c['name']) for c in both) + '</p>') if both else ''}
<p class="note">国会の声（質疑・政府答弁）が6割以上のまとまりを「国会」、1割以下を「ネット」に分けています。</p></section>"""


def render(m):
    total = m["n"]
    cards = []
    for n, c in enumerate(m["clusters"], 1):
        col = COLORS[c["id"] % len(COLORS)]
        props = "".join(f"<li>{h(p)}</li>" for p in c["propositions"]) or "<li class='mut'>（論点の文を作れませんでした）</li>"
        groups = ""
        if c["by_group"]:
            groups = "<p class='sub'>質疑した議員の会派</p><p class='tags'>" + "".join(
                f"<span>{h(k)} {v}</span>" for k, v in c["by_group"].items()) + "</p>"
        years = ""
        if c["by_year"]:
            years = "<p class='sub'>国会での年ごとの件数</p><p class='tags'>" + "".join(
                f"<span>{h(k)}年 {v}</span>" for k, v in c["by_year"].items()) + "</p>"
        quotes = "".join(
            f"<li><span class='src'>{h(q['source'])}{('・' + h(q['who'])) if q['who'] else ''}{('・' + h(q['date'])) if q['date'] else ''}</span>"
            f"{h(q['text'][:160])}{'…' if len(q['text']) > 160 else ''}"
            f"{(' <a href=' + chr(34) + h(q['url']) + chr(34) + ' rel=nofollow target=_blank>元の発言</a>') if q['url'] else ''}</li>"
            for q in c["quotes"])
        cards.append(f"""<section class="card" id="t{c['id']}">
<h2><em class="no">{n}</em>{h(c['name'])} <small>{c['size']}件</small></h2>
<p>{h(c['summary'])}</p>
<p class="sub">この話題から立てた論点（賛否を問える文）</p><ul class="props">{props}</ul>
<p class="sub">どこから拾った声か</p>{bar(c['by_source'], c['size'], SRC_COLOR)}
{groups}{years}
<details><summary>代表的な声を読む</summary><ul class="qs">{quotes}</ul></details>
</section>""")
    toc = "".join(f'<a href="#t{c["id"]}"><em>{n}</em>{h(c["name"])}<b>{c["size"]}</b></a>' for n, c in enumerate(m["clusters"], 1))
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{h(m['theme'])}の論点AIマップ｜Kurage 論点AIマップ</title>
<meta name="description" content="{h(m['theme'])}について、国会の発言とネットの声{total:,}件から、話題の地図と賛否を問える論点を作りました。">
<style>
:root{{--ink:#12202f;--teal:#0a9a8f;--line:#dfe7ec;--mut:#5d6b7a;--bg:#f5f8fa}}
*{{box-sizing:border-box;min-width:0}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.75}}
header{{background:#fff;border-bottom:1px solid var(--line)}}
.hd{{max-width:860px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:10px}}
.hd a{{display:flex;align-items:center;gap:10px;color:var(--ink);text-decoration:none;font-weight:900}}
.hd img{{width:34px;height:34px;object-fit:contain}}
.wrap{{max-width:860px;margin:0 auto;padding:22px 16px 70px;overflow-wrap:anywhere}}
.kick{{color:var(--teal);font-weight:700;letter-spacing:.09em;font-size:12px;margin:0}}
h1{{font-size:clamp(21px,4.6vw,30px);margin:.2em 0 .2em;font-weight:900;line-height:1.4}}
.lead{{color:var(--mut);margin:.4em 0 1.2em}}
.hero{{display:flex;gap:14px;align-items:flex-start}}
.hero img{{width:84px;height:auto;object-fit:contain;flex:none}}
.card{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 2px 10px rgba(18,32,47,.05);margin:0 0 16px}}
h2{{font-size:19px;margin:0 0 .3em;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
h2 i,.toc i,.lg i{{display:inline-block;width:12px;height:12px;border-radius:3px;flex:none}}
h2 .no{{font-style:normal;font-weight:900;width:26px;height:26px;border:1.5px solid #12202f;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:13px;flex:none}}
h2 small{{color:var(--mut);font-weight:400;font-size:13px}}
.sub{{font-size:12.5px;color:var(--mut);font-weight:700;margin:.9em 0 .3em;letter-spacing:.04em}}
.props{{margin:0;padding-left:1.2em}} .props li{{font-weight:700;margin:.2em 0}}
.bar{{display:flex;height:10px;border-radius:6px;overflow:hidden;background:#eef2f5}}
.lg{{list-style:none;margin:.4em 0 0;padding:0;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--mut)}}
.lg li{{display:flex;align-items:center;gap:5px}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin:0}} .tags span{{background:#eef6f5;border-radius:99px;padding:1px 10px;font-size:12.5px}}
details{{margin-top:.8em}} summary{{cursor:pointer;color:var(--teal);font-weight:700;font-size:14px}}
.qs{{margin:.5em 0 0;padding-left:1.1em;font-size:14px}} .qs li{{margin:.5em 0}}
.src{{display:block;font-size:12px;color:var(--mut)}}
.toc{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px}}
.toc a{{display:flex;align-items:center;gap:8px;color:var(--ink);text-decoration:none;font-size:14px;padding:6px 8px;border-radius:8px;background:#f7fafb}}
.toc em{{font-style:normal;font-weight:900;width:22px;height:22px;border:1.5px solid #12202f;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex:none;background:#fff}}
.toc b{{white-space:nowrap;margin-left:auto;color:var(--mut);font-weight:400;font-size:12px}}
svg{{width:100%;height:auto;background:#fbfdfd;border:1px solid var(--line);border-radius:12px}}
svg .cl{{font-size:11px;font-weight:900;fill:#12202f}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .g2 ul{{margin:.3em 0 0;padding-left:1.1em}} .g2 a{{color:var(--ink)}}
@media(max-width:560px){{.g2{{grid-template-columns:1fr}} .hero img{{width:60px}}}}
.mut,.note{{color:var(--mut);font-size:13px}}
</style></head><body>
<header><div class="hd"><a href="https://proto.exbridge.jp/kronten/"><img src="{LOGO}" width="34" height="34" alt="株式会社エクスブリッジ">Kurage 論点AIマップ</a></div></header>
<main class="wrap">
<div class="hero"><div>
<p class="kick">RONTEN AI MAP（試作）</p>
<h1>{h(m['theme'])}の論点AIマップ</h1>
<p class="lead">国会の発言とネットの声 {total:,}件を、意味の近さで{m['k']}つの話題にまとめ、話題ごとに「賛成か反対かを問える論点」を立てました。誰がどこで言った声か（国会の質疑・政府の答弁・X・ニュースのコメント）を分けて見られます。</p>
</div><img src="{MASCOT}" width="84" height="84" alt="Kurage"></div>
<section class="card"><p class="sub" style="margin-top:0">材料（どこから拾った声か）</p>{bar(m['sources'], total, SRC_COLOR)}</section>
{gap(m)}
<section class="card"><p class="sub" style="margin-top:0">話題の一覧</p><div class="toc">{toc}</div></section>
<section class="card"><p class="sub" style="margin-top:0">話題の地図（1点が1つの声。近いほど意味が近い）</p>{scatter(m)}</section>
{''.join(cards)}
<section class="card note"><p class="sub" style="margin-top:0">作り方</p>
<p>国会の発言は、国会会議録検索システムから当社の国会トラッカーが集めたもの（発言を200字前後に区切り、テーマの語を含む部分だけ）。ネットの声は、当社の合意点マップに取り込んだ X の投稿と Yahoo!ニュースのコメントです。</p>
<p>意味の近さは {h(m['embed_model'])}（手元のCPUで計算）、まとめ方は KMeans（同じ材料なら毎回同じ結果）、話題の名前・要約・論点は {h(m['llm'])}（手元のGPU）で作りました。外部のAIには送っていません。名前と論点はAIの要約なので、必ず代表的な声と元の発言で確かめてください。件数は「声のかたまりの数」で、人数ではありません。</p>
<p>作成 {h(m.get('built_at', ''))}　株式会社エクスブリッジ（名古屋）</p></section>
</main></body></html>"""

"""map.json → 1枚の HTML（ライトテーマ・スマホ対応・外部の JS を使わない）。

上から: 見出し → 材料の内訳 → 話題の地図（散布図）→ 話題ごとのカード（論点・出典の内訳・代表的な声）→ 作り方。
"""
import html

BASE = "https://kurage.exbridge.jp/kronten.php"
LOGO = "https://exbridge.jp/images/logo-mark-128.png"
TRACK = ('<script>(function(){var s=document.createElement("script");s.src="https://kurage.exbridge.jp/simpletrack.php?url="'
         '+encodeURIComponent(location.href)+"&ref="+encodeURIComponent(document.referrer);document.head.appendChild(s)})();</script>')
STORE = "https://kappstore.exbridge.jp/app.php?id=10cb19eab638123f&"
GITHUB = "https://github.com/katsushi2441/kronten"
MASCOT = "https://kurage.exbridge.jp/images/kurage_mascot_simple_v2.png"
COLORS = ["#0a9a8f", "#e07a2e", "#4a6fd1", "#c2417a", "#6a9a1f", "#8a55c7", "#d4a017",
          "#2a8bb5", "#b5482a", "#3f7f5f", "#7a6a55", "#5a5ad1", "#a0336a", "#2f9e7e"]
SRC_COLOR = {"国会（質疑）": "#4a6fd1", "国会（政府答弁）": "#7a8fb8", "X": "#12202f", "Yahooコメント": "#e07a2e",
             "チームみらいAIインタビュー": "#c2417a"}
MIRAI_CREDIT = ("データ出典：「みらい議会AIインタビュー（チームみらい）」 https://gikai.team-mir.ai/ ／ "
                "利用規約 https://gikai.team-mir.ai/developers/interview-data-terms ／ ライセンス CC BY 4.0（回答者ごとの論点別の意見を1件として、話題にまとめて利用）")


def group_of(src):
    if src.startswith("国会"):
        return "国会"
    if src == "チームみらいAIインタビュー":
        return "インタビュー"
    return "ネット"


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
    """話題を、どこで話されているかで分ける（国会＝質疑＋政府答弁／ネット＝X・ニュースのコメント／インタビュー＝チームみらい）。
    1つの出どころが6割以上ならその列、そうでなければ「いくつかで」"""
    cols = {"国会": [], "ネット": [], "インタビュー": [], "いくつかで": []}
    for c in m["clusters"]:
        g = {}
        for s_, v in c["by_source"].items():
            g[group_of(s_)] = g.get(group_of(s_), 0) + v
        top = max(g, key=g.get)
        cols[top if g[top] / c["size"] >= 0.6 else "いくつかで"].append(c)
    used = [k for k in ("国会", "ネット", "インタビュー") if any(group_of(s_) == k for s_ in m["sources"])]
    if len(used) < 2:
        return ""
    li = lambda cs: "".join(f'<li><a href="#t{c["id"]}">{h(c["name"])}</a> <small>{c["size"]}件</small></li>' for c in cs) or "<li class='mut'>なし</li>"
    label = {"国会": "国会で話されている話題", "ネット": "ネットで話されている話題", "インタビュー": "チームみらいのAIインタビューで話されている話題"}
    boxes = "".join(f"<div><b>{label[k]}</b><ul>{li(cols[k])}</ul></div>" for k in used)
    both = cols["いくつかで"]
    return f"""<section class="card gap"><p class="sub" style="margin-top:0">{'・'.join(used)}のずれ</p>
<div class="g2">{boxes}</div>
{('<p class="note">いくつかの出どころにまたがる話題: ' + '、'.join(h(c['name']) for c in both) + '</p>') if both else ''}
<p class="note">1つの出どころの声が6割以上のまとまりを、その出どころの話題としています。同じ論点が複数の出どころで話されていることもあるので、下の「論点の網目」とあわせて読んでください。{'チームみらいのAIインタビューの意見は、AIが回答を要約した文で書きぶりがそろっているため、話題の違いだけでなく文体の違いでも分かれている可能性があります。インタビューの話題は、AIが尋ねた質問に沿って並びます。' if 'インタビュー' in used else ''}</p></section>"""


GROUP_COLOR = {"国会": "#4a6fd1", "ネット": "#12202f", "インタビュー": "#c2417a"}


def mesh(m):
    """網目状の論点の表（1つの声が複数の論点に当てはまってよい）。論点ごとに、出どころ別に何%の声が触れているか"""
    me = m.get("mesh")
    if not me:
        return ""
    gs = me["groups"]
    head = "".join(f'<th>{h(g)}<small>{me["totals"][g]:,}件</small></th>' for g in gs)
    body = ""
    for r in sorted(me["rows"], key=lambda r: -max(v["pct"] for v in r["by_group"].values())):
        cells = "".join(
            f'<td><div class="mb"><span style="width:{min(100, r["by_group"][g]["pct"] * 2):.0f}%;background:{GROUP_COLOR.get(g, "#9fb3c0")}"></span></div>'
            f'<b>{r["by_group"][g]["pct"]:.0f}%</b><small>{r["by_group"][g]["n"]}件</small></td>' for g in gs)
        body += f'<tr><th class="ln">{h(r["name"])}<small>{h(r["desc"])}</small></th>{cells}</tr>'
    return f"""<section class="card"><p class="sub" style="margin-top:0">論点の網目（1つの声が複数の論点に当てはまる）</p>
<p class="note">上の地図は1つの声を1つの話題にしか入れないため、同じ観点でも出どころの書きぶりが違うと別の話題に分かれ、重なりが見えにくくなります。ここでは論点の一覧を決め、声ごとに当てはまる論点を全部付けて、出どころごとに何%の声がその論点に触れているかを並べました（棒は50%で端まで）。2つ以上の論点に当たる声は{me['multi']:.0f}%、どれにも当たらない声は{me['none']:.0f}%です。</p>
<div class="scroll"><table class="mesh"><tr><th></th>{head}</tr>{body}</table></div></section>"""


def render(m, slug="", links=None):
    """links: 関連ページ [(見出し, URL)]。slug があれば kurage の公開ページとして（検索に出す）作る"""
    total = m["n"]
    links = links or []
    url = f"{BASE}/t/{slug}/" if slug else ""
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
{'' if slug else '<meta name="robots" content="noindex">'}
<title>{h(m['theme'])}の論点｜国会とネットの声{total:,}件の論点AIマップ</title>
<meta name="description" content="{h(m['theme'])}について、国会の発言とネットの声{total:,}件を{m['k']}つの話題にまとめ、賛否を問える論点を立てました。国会とネットで話題がどうずれているかも分かります。">
{f'<link rel="canonical" href="{url}"><meta property="og:url" content="{url}">' if url else ''}
<meta property="og:type" content="article"><meta property="og:site_name" content="Kurage 論点AIマップ">
<meta property="og:title" content="{h(m['theme'])}の論点AIマップ"><meta property="og:image" content="{MASCOT}">
<meta name="twitter:card" content="summary">
{TRACK if slug else ''}
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
.g2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}} .g2 ul{{margin:.3em 0 0;padding-left:1.1em}} .g2 a{{color:var(--ink)}}
@media(max-width:560px){{.g2{{grid-template-columns:1fr}} .hero img{{width:60px}}}}
.rel{{margin:0;padding-left:1.1em}} .rel a{{color:var(--teal)}}
.scroll{{overflow-x:auto}} table.mesh{{border-collapse:collapse;width:100%;min-width:520px;font-size:13px}}
.mesh th,.mesh td{{border-bottom:1px solid var(--line);padding:6px 6px;text-align:left;vertical-align:top}}
.mesh th small,.mesh td small{{display:block;font-weight:400;color:var(--mut);font-size:11px}} .mesh th.ln{{width:38%}}
.mb{{height:8px;background:#eef2f5;border-radius:4px;overflow:hidden;margin:3px 0}} .mb span{{display:block;height:100%}}
.mut,.note{{color:var(--mut);font-size:13px}}
</style></head><body>
<header><div class="hd"><a href="{BASE}/"><img src="{LOGO}" width="34" height="34" alt="株式会社エクスブリッジ">Kurage 論点AIマップ</a></div></header>
<main class="wrap">
<div class="hero"><div>
<p class="kick">RONTEN AI MAP</p>
<h1>{h(m['theme'])}の論点AIマップ</h1>
<p class="lead">国会の発言とネットの声 {total:,}件を、意味の近さで{m['k']}つの話題にまとめ、話題ごとに「賛成か反対かを問える論点」を立てました。誰がどこで言った声か（国会の質疑・政府の答弁・X・ニュースのコメント）を分けて見られます。</p>
</div><img src="{MASCOT}" width="84" height="84" alt="Kurage"></div>
<section class="card"><p class="sub" style="margin-top:0">材料（どこから拾った声か）</p>{bar(m['sources'], total, SRC_COLOR)}</section>
{gap(m)}
{mesh(m)}
<section class="card"><p class="sub" style="margin-top:0">話題の一覧</p><div class="toc">{toc}</div></section>
<section class="card"><p class="sub" style="margin-top:0">話題の地図（1点が1つの声。近いほど意味が近い）</p>{scatter(m)}</section>
{''.join(cards)}
<section class="card note"><p class="sub" style="margin-top:0">作り方</p>
<p>国会の発言は、国会会議録検索システムから当社の国会トラッカーが集めたもの（発言を200字前後に区切り、テーマの語を含む部分だけ）。ネットの声は、当社の合意点マップに取り込んだ X の投稿と Yahoo!ニュースのコメントです。</p>
<p>意味の近さは {h(m['embed_model'])}（手元のCPUで計算）、まとめ方は KMeans（同じ材料なら毎回同じ結果）、話題の名前・要約・論点は {h(m['llm'])}（手元のGPU）で作りました。外部のAIには送っていません。名前と論点はAIの要約なので、必ず代表的な声と元の発言で確かめてください。件数は「声のかたまりの数」で、人数ではありません。</p>
{('<p>' + h(MIRAI_CREDIT) + '</p>') if 'チームみらいAIインタビュー' in m['sources'] else ''}
<p>作成 {h(m.get('built_at', ''))}　株式会社エクスブリッジ（名古屋）</p></section>
{('<section class="card"><p class="sub" style="margin-top:0">関連するページ</p><ul class="rel">' + ''.join(f'<li><a href="{h(u)}">{h(t)}</a></li>' for t, u in links) + '</ul></section>') if links else ''}
<section class="card"><p class="sub" style="margin-top:0">このシステムについて</p>
<p>Kurage 論点AIマップは、国会の発言・SNS・ニュースのコメント・アンケートの自由記述など「すでにある声」から、話題の地図と論点を作るシステムです。AI エージェントからは MCP で引けます（<a href="{BASE}/about#mcp">使い方</a>）。ソースコードは <a href="{GITHUB}">GitHub</a>（MIT）、自社のサーバーに置く版は <a href="{STORE}ref=kronten-map">Kurage App Store</a> にあります。</p></section>
</main></body></html>"""


def _page(title, desc, url, body):
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{h(title)}</title><meta name="description" content="{h(desc)}">
<link rel="canonical" href="{url}"><meta property="og:url" content="{url}"><meta property="og:type" content="website">
<meta property="og:site_name" content="Kurage 論点AIマップ"><meta property="og:title" content="{h(title)}"><meta property="og:image" content="{MASCOT}">
<meta name="twitter:card" content="summary">{TRACK}
<style>
:root{{--ink:#12202f;--teal:#0a9a8f;--line:#dfe7ec;--mut:#5d6b7a;--bg:#f5f8fa}}
*{{box-sizing:border-box;min-width:0}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.8}}
header{{background:#fff;border-bottom:1px solid var(--line)}}
.hd{{max-width:860px;margin:0 auto;padding:10px 16px}} .hd a{{display:flex;align-items:center;gap:10px;color:var(--ink);text-decoration:none;font-weight:900}}
.hd img{{width:34px;height:34px;object-fit:contain}}
.wrap{{max-width:860px;margin:0 auto;padding:22px 16px 70px;overflow-wrap:anywhere}}
.kick{{color:var(--teal);font-weight:700;letter-spacing:.09em;font-size:12px;margin:0}}
h1{{font-size:clamp(22px,4.8vw,32px);margin:.2em 0 .3em;font-weight:900;line-height:1.4}}
h2{{font-size:19px;margin:0 0 .4em}}
.lead{{color:var(--mut)}}
.hero{{display:flex;gap:16px;align-items:flex-start}} .hero img{{width:96px;height:auto;object-fit:contain;flex:none}}
.card{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 2px 10px rgba(18,32,47,.05);margin:0 0 16px}}
.maps a{{display:block;padding:12px 14px;border:1px solid var(--line);border-radius:12px;color:var(--ink);text-decoration:none;margin:0 0 8px}}
.maps b{{display:block;font-size:17px}} .maps small{{color:var(--mut)}}
.steps{{padding-left:1.3em}} code,pre{{background:#eef3f6;border-radius:6px;padding:1px 6px;font-size:13px}}
pre{{padding:10px;overflow-x:auto}} a{{color:var(--teal)}}
.btn{{display:inline-block;background:var(--teal);color:#fff;font-weight:800;padding:10px 18px;border-radius:99px;text-decoration:none;margin:4px 6px 0 0}}
.btn.o{{background:#fff;color:var(--teal);border:1px solid var(--teal)}}
@media(max-width:560px){{.hero img{{width:64px}}}}
</style></head><body>
<header><div class="hd"><a href="{BASE}/"><img src="{LOGO}" width="34" height="34" alt="株式会社エクスブリッジ">Kurage 論点AIマップ</a></div></header>
<main class="wrap">{body}
<p class="lead" style="font-size:13px">株式会社エクスブリッジ（名古屋）　<a href="{BASE}/about">このシステムについて・MCP</a>　<a href="{GITHUB}">GitHub</a>　<a href="{STORE}ref=kronten-foot">Kurage App Store</a></p>
</main></body></html>"""


def render_index(maps):
    """maps: [(slug, map.json の中身)]"""
    items = "".join(
        f'<a href="{BASE}/t/{h(s)}/"><b>{h(m["theme"])}</b><small>国会とネットの声 {m["n"]:,}件・{m["k"]}の話題・'
        f'論点 {sum(len(c["propositions"]) for c in m["clusters"])}本（{h(m.get("built_at", "")[:10])}）</small></a>'
        for s, m in maps)
    body = f"""<div class="hero"><div><p class="kick">RONTEN AI MAP</p>
<h1>論点AIマップ｜国会とネットの声から、話題と論点を地図にする</h1>
<p class="lead">国会の発言、Xの投稿、ニュースのコメント、アンケートの自由記述。<b>すでに書かれている声</b>を集めて、意味の近さで話題にまとめ、話題ごとに「賛成か反対かを問える論点」を立てます。国会で話されていることと、ネットで話されていることのずれも、地図で見えます。</p></div>
<img src="{MASCOT}" width="96" height="96" alt="Kurage"></div>
<section class="card"><h2>論点AIマップ</h2><div class="maps">{items}</div></section>
<section class="card"><h2>何が違うのか</h2>
<p>意見を集める道具（AIインタビュー、Pol.is、広聴AIなど）は、たいてい「意見を書いてもらう」ところから始まります。答えに来る人が集まらないと、地図が作れません。論点AIマップは、すでに書かれている声から始めるので、人を待たずに地図ができます。</p>
<p>声には「どこで・誰が・いつ」が付いたまま残るので、国会の質疑と政府の答弁、会派、年、ネットの投稿を分けて見られます。まとめ方は毎回同じ結果になる方法で、話題の名前と論点だけを手元のAIで作ります。外部のAIには送りません。</p>
<p>立てた論点は、<a href="https://kurage.exbridge.jp/kconsensus.php/?ref=kronten">Kurage 合意点マップ</a>に渡して、賛否と合意点を集めます。</p></section>
<section class="card"><h2>自社・自治体・議員事務所で使う</h2>
<p>パブリックコメント、住民アンケート、議員事務所に届いた声、社内アンケートの自由記述などを CSV で入れれば、同じ地図と論点が作れます。自社のサーバーで動くので、声を外に出しません。</p>
<a class="btn" href="{STORE}ref=kronten-top">Kurage App Store で見る</a><a class="btn o" href="{GITHUB}">GitHub（MIT）</a></section>"""
    return _page("論点AIマップ｜国会とネットの声から話題と論点を地図にする（Kurage）",
                 "国会の発言・SNS・ニュースのコメントなど、すでにある声から話題の地図と賛否を問える論点を作ります。国会とネットのずれも見えます。MCP対応。",
                 f"{BASE}/", body)


def render_about():
    body = f"""<p class="kick">ABOUT</p><h1>このシステムについて・MCP</h1>
<section class="card"><h2>作り方</h2><ol class="steps">
<li>声を集める。国会の発言は国会会議録検索システムから（当社の国会トラッカー）、ネットの声は X の投稿とニュースのコメント（当社の合意点マップ）。CSV も入れられます。</li>
<li>国会の発言は200字前後に区切り、テーマの語の組を含む部分だけを使います。</li>
<li>意味の近さを multilingual-e5-large で計算し、KMeans でまとめます（同じ材料なら毎回同じ結果）。</li>
<li>まとまりごとに、話題の名前・要約・論点を gemma4（手元のGPU）で作ります。</li>
</ol>
<p>話題の名前と論点はAIの要約です。必ず代表的な声と元の発言で確かめてください。件数は声のかたまりの数で、人数ではありません。</p></section>
<section class="card" id="mcp"><h2>MCP（AI エージェント向け）</h2>
<p><code>{BASE}/mcp</code>（Streamable HTTP・読み取り専用・登録不要）</p>
<pre>claude mcp add --transport http kronten {BASE}/mcp</pre>
<p>道具: <code>list_maps</code>（地図の一覧）、<code>get_map</code>（話題・論点・出典の内訳）、<code>get_topic</code>（1つの話題の代表的な声と元の発言のURL）、<code>search_propositions</code>（論点を語で探す）。</p></section>"""
    return _page("このシステムについて・MCP｜Kurage 論点AIマップ",
                 "論点AIマップの作り方と、AI エージェントから使う MCP の案内。",
                 f"{BASE}/about", body)

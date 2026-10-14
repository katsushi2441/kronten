"""Xの反応マップのカード画像（1200×630）とページ（HTML）。xmap.build() の結果から作る。"""
import datetime
import html
import os
import urllib.parse

from PIL import Image, ImageDraw, ImageFont

BASE = "https://kurage.exbridge.jp/kronten.php"
W, H = 1200, 630
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FM = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
COLORS = {"賛同": "#0a9a8f", "条件つき・別の提案": "#7cc9bd", "反対・批判": "#d9534f", "質問": "#1f3a5f", "その他": "#c9d3dc"}


def _fit(dr, text, path, size, maxw, minimum=12):
    while size > minimum:
        f = ImageFont.truetype(path, size)
        if dr.textlength(text, font=f) <= maxw:
            return f
        size -= 1
    return ImageFont.truetype(path, size)


def _wrap(dr, text, font, maxw, lines):
    out, cur = [], ""
    for ch in text:
        if dr.textlength(cur + ch, font=font) > maxw and cur:
            out.append(cur)
            cur = ""
            if len(out) == lines:
                out[-1] = out[-1][:-1] + "…"
                return out
        cur += ch
    if cur:
        out.append(cur)
    return out


def pct(n, total):
    return round(n * 100 / total) if total else 0


def draw(m, path):
    img = Image.new("RGB", (W, H), "#ffffff")
    dr = ImageDraw.Draw(img, "RGBA")
    dr.ellipse([-180, -240, 480, 380], fill=(230, 244, 242, 255))
    dr.ellipse([W - 460, H - 330, W + 220, H + 240], fill=(240, 246, 246, 255))
    X, IW = 56, W - 112
    p = m["post"]
    tag = f"Xの反応マップ｜{p['author']}さんの投稿"
    ft = _fit(dr, tag, FM, 22, 760)
    tw = dr.textlength(tag, font=ft)
    dr.rounded_rectangle([X, 30, X + tw + 36, 74], radius=22, fill="#e6f4f2", outline="#bfe3de")
    dr.text((X + 18, 52), tag, font=ft, fill="#0a726b", anchor="lm")
    d = datetime.datetime.strptime(m["built_at"], "%Y-%m-%d %H:%M")
    dr.text((W - X, 52), f"返信{m['n']}件を分類（{d.month}/{d.day} {d:%H:%M}時点）", font=ImageFont.truetype(FR, 18), fill="#5d6b7a", anchor="rm")
    # 元の投稿（2行）
    fq = ImageFont.truetype(FR, 22)
    y = 100
    for ln in _wrap(dr, "「" + " ".join(p["text"].split()) + "」", fq, IW, 2):
        dr.text((X, y), ln, font=fq, fill="#2f3b4d", anchor="lm")
        y += 32
    # 立場の帯
    y = 178
    dr.text((X, y), "返信の立場", font=ImageFont.truetype(FB, 26), fill="#12202f", anchor="lm")
    by, bh = y + 26, 44
    x = X
    for s, n in m["stance"].items():
        if not n:
            continue
        w = IW * n / m["n"]
        dr.rectangle([x, by, x + w, by + bh], fill=COLORS[s])
        if w > 70:
            dr.text((x + w / 2, by + bh / 2), f"{pct(n, m['n'])}%", font=ImageFont.truetype(FB, 22),
                    fill="#ffffff" if s not in ("その他", "条件つき・別の提案") else "#12202f", anchor="mm")
        x += w
    # 凡例
    lx, ly = X, by + bh + 22
    fl = ImageFont.truetype(FM, 18)
    for s, n in m["stance"].items():
        lab = f"{s} {n}件"
        dr.rectangle([lx, ly - 8, lx + 16, ly + 8], fill=COLORS[s])
        dr.text((lx + 22, ly), lab, font=fl, fill="#2f3b4d", anchor="lm")
        lx += 22 + dr.textlength(lab, font=fl) + 26
    # 話題
    y = ly + 40
    dr.text((X, y), "多かった話題", font=ImageFont.truetype(FB, 26), fill="#12202f", anchor="lm")
    y += 30
    for t in m["topics"][:3]:
        dr.rounded_rectangle([X, y, X + IW, y + 54], radius=10, fill="#f0f6f6")
        head = f"{t['name']}（{pct(t['n'], m['n'])}%）"
        fh = _fit(dr, head, FM, 22, 380)
        dr.text((X + 18, y + 27), head, font=fh, fill="#0a726b", anchor="lm")
        fs = _fit(dr, t["summary"], FR, 19, IW - 420, 13)
        dr.text((X + 410, y + 27), t["summary"], font=fs, fill="#12202f", anchor="lm")
        y += 62
    fr = ImageFont.truetype(FR, 16)
    dr.text((X, H - 26), f"{BASE.replace('https://', '')}/x/{m['id']}", font=fr, fill="#5d6b7a", anchor="lm")
    # 全部集めたときは「すべて」、一部のときは「うち…集めた分」（2026-10-14 玉木代表の投稿は17件すべてだった）
    whole = m["n"] >= (p.get("replies") or 0)
    note = (f"返信{m['n']}件をすべてAIで分類（人の数ではありません）" if whole
            else f"返信{p['replies']}件のうち、いいね上位と新しい順に集めた{m['n']}件をAIで分類（人の数ではありません）")
    dr.text((W - X, H - 26), note,
            font=_fit(dr, "x" * 10, FR, 16, 9999), fill="#5d6b7a", anchor="rm")
    img.save(path, optimize=True)


def page(m):
    p = m["post"]
    url = f"{BASE}/x/{m['id']}"
    title = f"{p['author']}さんの投稿への反応マップ｜返信{m['n']}件の立場と話題"
    st = "・".join(f"{s}{pct(n, m['n'])}%" for s, n in m["stance"].items() if n)
    desc = f"Xの投稿への返信{m['n']}件を、AIで立場と話題に分けました。{st}。"
    label = f"{p['author']}さんの投稿への反応マップ（返信{m['n']}件の立場と話題）"
    share = "https://x.com/intent/post?" + urllib.parse.urlencode(dict(
        text=f"この投稿への返信{m['n']}件を、立場と話題に分けました。{st}", url=url + "#ref=x-share-xmap"))
    rows = "".join(f'<li><b>{html.escape(s)}</b> {n}件（{pct(n, m["n"])}%）</li>' for s, n in m["stance"].items())
    tops = "".join(f'<li><b>{html.escape(t["name"])}</b>（{t["n"]}件・{pct(t["n"], m["n"])}%）<br>{html.escape(t["summary"])}</li>'
                   for t in m["topics"])
    src = "・".join(f"{k} {v}件" for k, v in m["sources"].items())
    e = html.escape
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="robots" content="noindex">
<link rel="canonical" href="{e(url)}"><meta property="og:type" content="article"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(url)}.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<style>body{{margin:0;background:#f6f9fa;color:#12202f;font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.75}}
main{{max-width:880px;margin:0 auto;padding:18px 16px 40px}}h1{{font-size:clamp(20px,4vw,28px);margin:6px 0 10px}}h2{{font-size:19px;margin:22px 0 6px}}
img{{width:100%;height:auto;display:block;border-radius:12px;box-shadow:0 2px 10px rgba(18,32,47,.1)}}
.btns{{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 6px}}.btn{{display:inline-block;border-radius:999px;padding:9px 16px;font-weight:800;text-decoration:none;border:0;cursor:pointer;font-size:14.5px}}
.x{{background:#0f1419;color:#fff}}.o{{background:#fff;color:#0a726b;border:2px solid #0a9a8f}}
.note{{color:#5d6b7a;font-size:13.5px}}.panel{{background:#fff;border-radius:12px;padding:12px 18px;margin:12px 0;box-shadow:0 1px 4px rgba(18,32,47,.06)}}
blockquote{{margin:0;padding:10px 14px;border-left:4px solid #0a9a8f;background:#fff;border-radius:8px}}</style></head>
<body><main><p class="note"><a href="{BASE}/#ref=xmap">Kurage 論点AIマップ</a> › Xの反応マップ</p>
<h1>{e(p['author'])}さんの投稿への反応マップ</h1>
<blockquote>{e(p['text'])}<br><a class="note" href="{e(p['url'])}" target="_blank" rel="noopener">元の投稿を見る</a></blockquote>
<p><img src="{e(url)}.png" alt="{e(title)}" width="1200" height="630"></p>
<div class="btns"><a class="btn x" href="{e(share)}" target="_blank" rel="noopener">Xで共有</a>
<button class="btn o" type="button" data-copy="{e(label + chr(10) + url + '#ref=copy-xmap')}" onclick="cp(this)">タイトルとURLをコピー</button></div>
<h2>返信の立場</h2><div class="panel"><ul>{rows}</ul></div>
<h2>多かった話題</h2><div class="panel"><ul>{tops}</ul><p class="note">話題の名前と要約はAIが付けたものです。返信の原文や、返信した人の名前は載せていません。</p></div>
<h2>集め方と、読み方の注意</h2><div class="panel"><p>この投稿への返信 {p['replies']}件のうち、<b>{m['n']}件</b>（{e(src)}）を集め、
ローカルのAI（{e(m['model'].split(':')[0])}）で「元の投稿の主張に対する立場」と「話題」に分けました（{e(m['built_at'])} 時点）。</p>
<ul>{'<li>集めた時点の返信は<b>すべて</b>入っています。そのあとに付いた返信は入っていません</li>' if m['n'] >= (p.get('replies') or 0) else '<li><b>全部の返信ではありません。</b>いいねの多い返信と新しい返信が中心で、ほかの返信とは割合が違うことがあります</li>'}
<li>割合は<b>返信の数</b>で、人の数ではありません（同じ人の複数の返信も1件ずつ数えます）</li>
<li>立場は皮肉や反語も含めてAIが読んだもので、読み違いがあります。引用リツイートは入っていません</li></ul></div>
<p class="note">作っている会社：<a href="https://exbridge.jp/#ref=xmap">株式会社エクスブリッジ</a>（名古屋のAIシステム開発会社）。
すでにある声から話題の地図と論点を作る <a href="{BASE}/#ref=xmap">Kurage 論点AIマップ</a> の仕組みを使っています。</p>
</main><script>function cp(b){{var t=b.getAttribute("data-copy");function ok(){{b.textContent="コピーしました"}}
if(navigator.clipboard&&window.isSecureContext){{navigator.clipboard.writeText(t).then(ok)}}else{{var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();document.execCommand("copy");a.remove();ok()}}}}</script></body></html>'''

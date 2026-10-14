"""論点AIマップのカード画像（1200×630）。テーマの地図ページの OGP にする（Xに貼ると話題の内訳が見える）。"""
from PIL import Image, ImageDraw, ImageFont

from kronten.xcard import FB, FM, FR, H, W, _fit


def draw(m, path, slug):
    img = Image.new("RGB", (W, H), "#ffffff")
    dr = ImageDraw.Draw(img, "RGBA")
    dr.ellipse([-180, -240, 480, 380], fill=(230, 244, 242, 255))
    dr.ellipse([W - 460, H - 330, W + 220, H + 240], fill=(240, 246, 246, 255))
    X, IW = 56, W - 112
    tag = "論点AIマップ｜国会の発言から"
    ft = ImageFont.truetype(FM, 22)
    tw = dr.textlength(tag, font=ft)
    dr.rounded_rectangle([X, 30, X + tw + 36, 74], radius=22, fill="#e6f4f2", outline="#bfe3de")
    dr.text((X + 18, 52), tag, font=ft, fill="#0a726b", anchor="lm")
    dr.text((W - X, 52), f"{m['n']:,}件を{len(m['clusters'])}つの話題に（{m['built_at'][:10]}）", font=ImageFont.truetype(FR, 18), fill="#5d6b7a", anchor="rm")
    t = f"{m['theme']}は、国会で何が論じられてきたか"
    dr.text((X, 118), t, font=_fit(dr, t, FB, 38, IW), fill="#12202f", anchor="lm")
    cs = sorted(m["clusters"], key=lambda c: -(c.get("size") or c.get("n") or 0))[:5]
    mx = max((c.get("size") or c.get("n") or 0) for c in cs) or 1
    y = 168
    for c in cs:
        n = c.get("size") or c.get("n") or 0
        dr.rounded_rectangle([X, y, X + IW, y + 74], radius=10, fill="#f0f6f6")
        bw = int(300 * n / mx)
        dr.rectangle([X, y, X + bw, y + 6], fill="#0a9a8f")
        head = f"{c['name']}（{n}件）"
        dr.text((X + 16, y + 26), head, font=_fit(dr, head, FM, 22, IW - 32), fill="#0a726b", anchor="lm")
        pr = (c.get("propositions") or [""])[0]
        if pr:
            s = "論点：" + pr
            dr.text((X + 16, y + 54), s, font=_fit(dr, s, FR, 18, IW - 32, 12), fill="#12202f", anchor="lm")
        y += 82
    fr = ImageFont.truetype(FR, 16)
    dr.text((X, H - 22), f"kurage.exbridge.jp/kronten.php/t/{slug}", font=fr, fill="#5d6b7a", anchor="lm")
    dr.text((W - X, H - 22), "国会会議録の発言をAIで話題に分けたもの（話題名と論点はAIの要約）", font=fr, fill="#5d6b7a", anchor="rm")
    img.save(path, optimize=True)

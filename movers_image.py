"""Render movers.json as a shareable PNG (data/movers.png), 1200x1720, for Reddit and the like.
Runs after movers.py. Card pictures come from images.pokemontcg.io and are cached in data/card_images/;
when a picture cannot be fetched a grey placeholder is drawn, the post never fails on it.
"""
import json, os, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont

CODE = os.path.dirname(os.path.abspath(__file__))
W, H = 1200, 1720
BG, PANEL, INK, MUTED = (18, 21, 28), (28, 32, 42), (240, 240, 244), (150, 156, 170)
UP, DOWN, GOLD = (72, 199, 116), (235, 87, 87), (232, 184, 75)
FONTS = {  # first match wins: Linux (Docker image ships fonts-dejavu-core), then Windows
    'bold': ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf'],
    'reg': ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf'],
}


def font(kind, size):
    for p in FONTS[kind]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def card_image(setid, number, size):
    os.makedirs('card_images', exist_ok=True)
    path = f'card_images/{setid}-{number}.png'
    if not os.path.exists(path):
        try:
            req = urllib.request.Request(f'https://images.pokemontcg.io/{setid}/{number}.png',
                                         headers={'User-Agent': 'cardmarket-ledger (github.com/Veranda110/cardmarket-ledger)'})
            with urllib.request.urlopen(req, timeout=20) as r, open(path, 'wb') as out:
                out.write(r.read())
        except Exception as e:
            print(f'card image {setid} {number} not fetched: {e}', file=sys.stderr)
            return None
    try:
        im = Image.open(path).convert('RGBA')
        im.thumbnail(size)
        return im
    except Exception:
        return None


def main():
    os.chdir(os.environ.get('LEDGER_DATA', os.path.join(CODE, 'data')))
    load = lambda p: json.load(open(p, encoding='utf-8'))
    mv = load('movers.json'); pm = load('products_map.json'); meta = load('set_meta.json')
    span = (__import__('datetime').date.fromisoformat(mv['date']) - __import__('datetime').date.fromisoformat(mv['ref'])).days

    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    f_title, f_sub, f_h, f_name, f_set, f_num, f_pct, f_foot = font('bold', 52), font('reg', 24), font('bold', 34), font('bold', 34), font('reg', 24), font('reg', 28), font('bold', 44), font('reg', 20)

    d.text((60, 50), 'Cardmarket Pokémon movers', font=f_title, fill=INK)
    d.text((60, 118), f"{mv['date']}  ·  Price Trend in EUR  ·  English cards €5 to €20  ·  {span}-day change  ·  {mv['considered']:,} cards compared",
           font=f_sub, fill=MUTED)
    d.line((60, 165, W - 60, 165), fill=(50, 55, 68), width=2)

    def section(y, title, rows, color):
        d.text((60, y), title, font=f_h, fill=color)
        y += 60
        maxpct = max([abs(r['pct']) for r in rows] or [1])
        for i, r in enumerate(rows, 1):
            m = pm[str(r['pid'])]
            d.rounded_rectangle((60, y, W - 60, y + 190), radius=16, fill=PANEL)
            pic = card_image(m['setid'], m['number'], (125, 174))
            if pic:
                im.paste(pic, (76, y + 8), pic)
            else:
                d.rounded_rectangle((76, y + 8, 201, y + 182), radius=8, fill=(45, 50, 62))
            d.text((222, y + 22), str(i), font=f_h, fill=MUTED)
            d.text((262, y + 18), m['name'], font=f_name, fill=INK)
            d.text((262, y + 64), f"{meta[m['setid']]['name']}  ·  {m['number']}  ·  {m['rarity']}", font=f_set, fill=MUTED)
            d.text((262, y + 112), f"€{r['ref']:.2f}  →  €{r['now']:.2f}   ({r['chg']:+.2f})", font=f_num, fill=INK)
            # change badge and bar
            pct = f"{r['pct']:+.0f}%"
            tw = d.textlength(pct, font=f_pct)
            d.text((W - 90 - tw, y + 30), pct, font=f_pct, fill=color)
            bar_w = int(300 * abs(r['pct']) / maxpct)
            d.rounded_rectangle((W - 90 - 300, y + 110, W - 90, y + 126), radius=8, fill=(45, 50, 62))
            d.rounded_rectangle((W - 90 - bar_w, y + 110, W - 90, y + 126), radius=8, fill=color)
            y += 206
        return y

    y = section(195, 'Biggest climbers', mv['climbers'], UP)
    y = section(y + 30, 'Biggest droppers', mv['droppers'], DOWN)

    d.line((60, y + 10, W - 60, y + 10), fill=(50, 55, 68), width=2)
    foot = ("Source: Cardmarket's own daily price export. Card identity verified against the pokemon-tcg-data set list.\n"
            "Today's trend must sit within 30% of the 7-day average, so a single odd sale is not a move.\n"
            "Data, method and daily archive: github.com/Veranda110/cardmarket-ledger  ·  card pictures: pokemontcg.io")
    d.multiline_text((60, y + 30), foot, font=f_foot, fill=MUTED, spacing=10)
    im.save('movers.png', optimize=True)
    print(f'movers.png written ({W}x{H})')


if __name__ == '__main__':
    main()

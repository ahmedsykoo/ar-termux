#!/usr/bin/env python3
"""AR Termux vertical promo. Reads everything from ~/promo, writes ~/promo/final.mp4.

usage: python make_promo.py            # full render
       python make_promo.py frames T1 T2 ...   # dump PNG frames at given seconds (checks)
       python make_promo.py bench SECONDS     # render first N seconds, report fps
"""
import asyncio, os, ssl, subprocess, sys, time, urllib.parse, urllib.request, json, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features

ROOT = os.path.expanduser("~/promo")
BUILD = f"{ROOT}/build/v3"
AI = f"{ROOT}/ai"
os.makedirs(BUILD, exist_ok=True); os.makedirs(AI, exist_ok=True)
W, H, FPS = 1080, 1920, 30
SAFE_X, SAFE_BOTTOM = 120, 260
XFADE = 0.45

# palette from banner.svg / social-preview.png
BG0, BG1 = (13, 17, 23), (22, 27, 46)
ACCENT, ACCENT2 = (61, 220, 151), (76, 201, 240)
WHITE, MUTED, RED = (240, 246, 252), (159, 176, 195), (255, 92, 92)
CARD = (11, 15, 20)

SSL_CTX = ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"]) if os.environ.get("SSL_CERT_FILE") else None

# ---------------------------------------------------------------- Arabic text
RAQM = features.check("raqm")
_fonts = {}

def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        path = f"{ROOT}/Tajawal-{'Bold' if bold else 'Medium'}.ttf"
        eng = ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC
        _fonts[key] = ImageFont.truetype(path, size, layout_engine=eng)
    return _fonts[key]

def is_ar(s):
    return any("؀" <= c <= "ۿ" for c in s)

def ar(draw, xy, text, size, fill, anchor="mm", bold=True):
    """The only text path. raqm: raw text + rtl. No raqm: reshape + bidi on BASIC. Never both."""
    f = font(size, bold)
    if not is_ar(text):
        draw.text(xy, text, font=f, fill=fill, anchor=anchor)
    elif RAQM:
        draw.text(xy, text, font=f, fill=fill, anchor=anchor, direction="rtl", language="ar")
    else:
        import arabic_reshaper
        from bidi.algorithm import get_display
        plain = "".join(c for c in text if not "ً" <= c <= "ْ")  # BASIC drops harakat badly
        draw.text(xy, get_display(arabic_reshaper.reshape(plain)), font=f, fill=fill, anchor=anchor)

def text_box(text, size, bold=True):
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    kw = dict(direction="rtl", language="ar") if (RAQM and is_ar(text)) else {}
    if not RAQM and is_ar(text):
        import arabic_reshaper
        from bidi.algorithm import get_display
        text = get_display(arabic_reshaper.reshape(text))
    l, t, r, b = d.textbbox((0, 0), text, font=font(size, bold), anchor="lt", **kw)
    return r - l, b - t

def text_img(text, size, fill, bold=True, pad=12, max_w=W - 2 * SAFE_X, min_size=None):
    while text_box(text, size, bold)[0] > max_w and size > (min_size or size * 0.6): size -= 2
    w, h = text_box(text, size, bold)
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad + size // 3), (0, 0, 0, 0))
    ar(ImageDraw.Draw(im), (im.width // 2, im.height // 2), text, size, fill, "mm", bold)
    return im

# ---------------------------------------------------------------- narration
# (scene, spoken (tool names in Arabic letters), on-screen)
SCRIPT = [
 (0, "العربي في الترمينال؟ مقطّع، ومعكوس.", "العربي في الترمينال؟ مقطّع، ومعكوس."),
 (1, "علشان كده عملنا ترمكس عربي.", "علشان كده عملنا AR Termux."),
 (1, "نفس ترمكس الأصلي، بس الحروف بتتوصّل صح، ومن اليمين للشمال.", "نفس Termux الأصلي، بس الحروف بتتوصّل صح، ومن اليمين للشمال."),
 (2, "اسأل كلود كود بالعربي، والرد يوصلك مقروء وواضح.", "اسأل Claude Code بالعربي، والرد يوصلك مقروء وواضح."),
 (3, "ومع أوبن كود كمان، نفس النتيجة.", "ومع OpenCode كمان، نفس النتيجة."),
 (4, "ولما يشرحلك كود، الكود والإنجليزي بيفضلوا في مكانهم.", "ولما يشرحلك كود، الكود والإنجليزي بيفضلوا في مكانهم."),
 (4, "والجداول بتفضل سليمة.", "والجداول بتفضل سليمة."),
 (5, "التثبيت تلات خطوات:", "التثبيت تلات خطوات:"),
 (5, "نزّل الملف من صفحة الريليسز.", "نزّل الـ APK من صفحة Releases."),
 (5, "امسح ترمكس الأصلي الأول، لأن الاتنين ليهم نفس اسم الحزمة.", "امسح Termux الأصلي الأول، لأن الاتنين ليهم نفس اسم الحزمة."),
 (5, "وبعدين ثبّت، وجرّب بنفسك.", "وبعدين ثبّت، وجرّب بنفسك."),
 (6, "الرابط قدامك على الشاشة.", "الرابط قدامك على الشاشة."),
 (6, "ولو عجبك، ادعمنا بنجمة على جيت هب.", "ولو عجبك، ادعمنا بنجمة على GitHub"),
]
VOICE = "ar-EG-ShakirNeural"   # chosen over ar-SA-HamedNeural: 2.17 vs 1.92 words/s, Egyptian dialect
RATES = ["+6%","+5%","+6%","+6%","+5%","+6%","+4%","+5%","+6%","+6%","+4%","+4%","+5%"]
PITCH = ["-1Hz","+0Hz","+1Hz","-1Hz","+2Hz","+0Hz","-1Hz","+1Hz","+0Hz","-2Hz","+1Hz","+0Hz","-1Hz"]
# trim edges, shorten TTS comma pauses (~0.5s) to ~0.15s
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
        "silenceremove=stop_periods=-1:stop_duration=0.16:stop_threshold=-42dB:stop_silence=0.15,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
SR = 48000
LEAD, TAIL = 0.1, 0.3   # scene = LEAD + voice + TAIL  (= voice + 0.4s)

def sh(*a):
    subprocess.run(a, check=True, capture_output=True)

def gap_after(text):
    return 0.33 if text.strip().endswith((".", "!", "؟", ":")) else 0.2

def read_wav(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

def write_wav(p, x):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def tts_sentences():
    import edge_tts, edge_tts.communicate
    if SSL_CTX: edge_tts.communicate._SSL_CTX = SSL_CTX  # sandbox proxy CA; Termux uses certifi
    clips = []
    for i, (_, spoken, _) in enumerate(SCRIPT):
        raw, cut = f"{BUILD}/eg_{i}.mp3", f"{BUILD}/eg_{i}.wav"
        if not (os.path.exists(raw) and os.path.getsize(raw) > 1000):
            asyncio.run(edge_tts.Communicate(spoken, VOICE, rate=RATES[i], pitch=PITCH[i]).save(raw))
        if not os.path.exists(cut):
            sh("ffmpeg", "-y", "-i", raw, "-af", TRIM, "-ar", str(SR), "-ac", "1", cut)
        clips.append(read_wav(cut))
    return clips

def timeline(clips):
    """Scene durations + global sentence timings."""
    scenes, sents, t = [], [], 0.0
    for sc in range(7):
        idx = [i for i, s in enumerate(SCRIPT) if s[0] == sc]
        start = t; cur = t + LEAD
        for k, i in enumerate(idx):
            d = len(clips[i]) / SR
            sents.append(dict(i=i, scene=sc, start=cur, end=cur + d, text=SCRIPT[i][2]))
            cur += d + (gap_after(SCRIPT[i][1]) if k < len(idx) - 1 else 0)
        t = cur + TAIL
        scenes.append((start, t))
    return scenes, sents

def build_voice(clips, sents, total):
    x = np.zeros(int(total * SR) + SR, np.float32)
    for s in sents:
        a = int(s["start"] * SR); x[a:a + len(clips[s["i"]])] += clips[s["i"]]
    raw = f"{BUILD}/voice_raw.wav"; write_wav(raw, x[:int(total * SR)])
    pre = "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2"
    m = subprocess.run(["ffmpeg", "-i", raw, "-af", pre + ",loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=9:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    out = f"{BUILD}/voice.wav"
    sh("ffmpeg", "-y", "-i", raw, "-af", f"{pre},{ln}", "-ar", str(SR), "-ac", "1", out)
    return out

def build_music(total):
    """Soft pad: Am - F - C - G, 4 voices each, slow swell, then lowpass + fades in ffmpeg."""
    chords = [[110.0, 164.81, 220.0, 261.63], [87.31, 130.81, 174.61, 220.0],
              [130.81, 196.0, 261.63, 329.63], [98.0, 146.83, 196.0, 246.94]]
    n = int(total * SR); t = np.arange(n) / SR
    seg = 5.0; x = np.zeros(n, np.float32)
    for k in range(int(total / seg) + 2):
        a, b = (k * seg - 1.0), (k + 1) * seg + 1.0
        env = np.clip(np.minimum((t - a) / 1.5, (b - t) / 1.5), 0, 1) ** 2
        if not env.any(): continue
        for j, f in enumerate(chords[k % 4]):
            for det in (-0.6, 0.6):
                x += env * np.sin(2 * np.pi * (f + det) * t + j) * (0.5 if j == 0 else 0.35)
    x *= 1 + 0.08 * np.sin(2 * np.pi * 0.2 * t)
    x /= np.abs(x).max()
    raw = f"{BUILD}/music_raw.wav"; write_wav(raw, x * 0.5)
    out = f"{BUILD}/music.wav"
    sh("ffmpeg", "-y", "-i", raw, "-af",
       f"lowpass=f=1400,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5,loudnorm=I=-27:TP=-9:LRA=5",
       "-ar", str(SR), "-ac", "1", out)
    return out

def mix(voice, music, video, out):
    # music sits ~14 LU under the voice and ducks under speech
    fc = ("[1:a]asplit=2[v1][v2];[2:a]volume=1.0[m];"
          "[m][v1]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[md];"
          "[v2][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.84:level=false[a]")
    sh("ffmpeg", "-y", "-i", video, "-i", voice, "-i", music, "-filter_complex", fc,
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
       "-movflags", "+faststart", "-shortest", out)

# ---------------------------------------------------------------- AI images (free, Pollinations)
AI_NEG = ", no text, no letters, no words, no watermark, no logo, cinematic, dark, high detail"
AI_PROMPTS = {
 "hook": "close-up of a smartphone screen showing a broken glitching terminal, scattered fragmented glyph shards, red and green split lighting, dark moody background",
 "solve": "sleek smartphone floating in darkness, glowing terminal screen, flowing calligraphy-like teal and mint green light ribbons around it, deep navy background",
 "bg": "abstract dark navy space with soft teal and mint bokeh lights and faint flowing light lines, minimal, very dark",
 "install": "minimal smartphone silhouette glowing with soft mint green light on a dark surface, gentle reflections, deep navy background",
 "outro": "constellation of glowing stars forming a soft star shape over deep dark navy sky, teal and mint glow, minimal",
}

def ai_image(name, seed=7):
    out = f"{AI}/{name}.jpg"
    if not (os.path.exists(out) and os.path.getsize(out) > 20000):
        try:
            url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(AI_PROMPTS[name] + AI_NEG)
                   + f"?width=576&height=1024&seed={seed}")
            open(out, "wb").write(urllib.request.urlopen(url, timeout=180, context=SSL_CTX).read())
        except Exception as e:
            print("ai image", name, "unavailable:", e)
            return None
    return Image.open(out).convert("RGB")

def gradient_bg():
    y = np.linspace(0, 1, H)[:, None, None]; x = np.linspace(0, 1, W)[None, :, None]
    g = np.array(BG0) * (1 - (x + y) / 2) + np.array(BG1) * ((x + y) / 2)
    return Image.fromarray(g.astype(np.uint8), "RGB")

def make_bg(name, blur, bright):
    """AI image -> watermark strip cropped, cover-scaled 6% larger (for drift), blurred, graded to palette."""
    BW, BH = int(W * 1.06), int(H * 1.06)
    src = ai_image(name)
    if src is None:
        im = gradient_bg().resize((BW, BH))
    else:
        src = src.crop((0, 0, src.width, int(src.height * 0.94)))   # drop pollinations.ai mark
        s = max(BW / src.width, BH / src.height)
        src = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.LANCZOS)
        l, t = (src.width - BW) // 2, (src.height - BH) // 2
        im = src.crop((l, t, l + BW, t + BH)).filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im).astype(np.float32) * bright
    base = np.asarray(gradient_bg().resize((BW, BH))).astype(np.float32)
    a = np.maximum(a, base * 0.9)                       # keep the brand navy floor
    yy = np.linspace(0, 1, BH)[:, None, None]           # darker top/bottom for title & captions
    vign = 1 - 0.45 * (np.exp(-((yy - 0.0) / 0.18) ** 2) + np.exp(-((yy - 0.86) / 0.14) ** 2))
    a = a * vign
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

# ---------------------------------------------------------------- shared visual helpers
def ease(x):
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3

def ease_back(x):
    x = min(max(x, 0.0), 1.0); c = 1.4; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def with_alpha(img, a):
    if a >= 0.999: return img
    out = img.copy(); out.putalpha(img.getchannel("A").point(lambda v: int(v * max(a, 0))))
    return out

def paste(base, img, cx, cy, a=1.0, scale=1.0):
    if a <= 0.01: return
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    img = with_alpha(img, a)
    x, y = int(cx - img.width / 2), int(cy - img.height / 2)
    l, t = max(0, -x), max(0, -y)
    r, b = min(img.width, W - x), min(img.height, H - y)
    if r > l and b > t:
        base.alpha_composite(img.crop((l, t, r, b)), (x + l, y + t))

def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m

def shadowed(img, r=28, spread=30, opacity=150):
    pad = spread * 2
    sh_ = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    m = Image.new("L", sh_.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad + 12, pad + img.width, pad + img.height + 12), r, fill=opacity)
    sh_.putalpha(m.filter(ImageFilter.GaussianBlur(spread)))
    sh_.alpha_composite(img, (pad, pad))
    return sh_

def terminal_card(path, max_w, max_h, label):
    """Screenshot shown whole (contain), inside a rounded terminal/phone-style card."""
    shot = Image.open(path).convert("RGB")
    bar, pad, r = 58, 16, 30
    s = min((max_w - 2 * pad) / shot.width, (max_h - bar - 2 * pad) / shot.height)
    shot = shot.resize((int(shot.width * s), int(shot.height * s)), Image.LANCZOS)
    w, h = shot.width + 2 * pad, shot.height + bar + 2 * pad
    c = Image.new("RGBA", (w, h), CARD + (255,))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, w, bar), fill=(22, 27, 34, 255))
    for k, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + k * 30, bar // 2 - 8, 40 + k * 30, bar // 2 + 8), fill=col)
    ar(d, (w - 26, bar // 2 + 2), label, 30, MUTED, "rm", bold=False)
    c.paste(shot, (pad, bar + pad))
    c.putalpha(rounded_mask(w, h, r))
    ImageDraw.Draw(c).rounded_rectangle((0, 0, w - 1, h - 1), r, outline=(48, 60, 80, 255), width=2)
    return shadowed(c), s

def sweep(card, p):
    """One soft light band crossing the card (p in 0..1), masked to the card alpha."""
    if not 0 < p < 1: return card
    w, h = card.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pos = -300 + p * (w + h * 0.35 + 600)
    band = np.exp(-(((xx + yy * 0.35) - pos) / 70) ** 2) * 0.16
    a = np.asarray(card.getchannel("A")).astype(np.float32) / 255
    over = np.zeros((h, w, 4), np.uint8); over[..., :3] = 255
    over[..., 3] = (band * a * 255).astype(np.uint8)
    out = card.copy(); out.alpha_composite(Image.fromarray(over, "RGBA")); return out

def glow_sprite(size, color, alpha):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2
    a = np.exp(-(xx ** 2 + yy ** 2) / (2 * (size / 5) ** 2)) * alpha
    im = np.zeros((size, size, 4), np.uint8); im[..., :3] = color; im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im, "RGBA")

GLOW = None
DOTS = None
rng = np.random.default_rng(3)
PARTS = [(rng.uniform(140, W - 140), rng.uniform(0, H), rng.uniform(12, 28), int(rng.integers(0, 3)),
          rng.uniform(0, 6.28)) for _ in range(18)]

def ambient(base, T):
    """Soft moving light + a few slow translucent particles. T = global time."""
    global GLOW, DOTS
    if GLOW is None:
        GLOW = glow_sprite(1000, ACCENT2, 0.10)
        DOTS = [glow_sprite(s, ACCENT, 0.55) for s in (10, 14, 18)]
    gx = 40 + 40 * np.sin(T * 0.25); gy = 300 + 250 * np.sin(T * 0.17 + 1)
    base.alpha_composite(GLOW, (int(gx), int(gy)))
    for x, y0, sp, k, ph in PARTS:
        y = (y0 - sp * T) % (H + 40) - 20
        xx = x + 10 * np.sin(T * 0.5 + ph)
        d = DOTS[k]
        if 0 <= xx < W - d.width and 0 <= y < H - d.height:
            base.alpha_composite(d, (int(xx), int(y)))

def rgb_split(img, amt, rows=None):
    a = np.asarray(img.convert("RGB")).copy()
    a[..., 0] = np.roll(a[..., 0], amt, axis=1); a[..., 2] = np.roll(a[..., 2], -amt, axis=1)
    if rows:
        for y0, y1, dx in rows: a[y0:y1] = np.roll(a[y0:y1], dx, axis=1)
    return Image.fromarray(a, "RGB").convert("RGBA")

def star(d, cx, cy, r, fill):
    pts = []
    for k in range(10):
        ang = -np.pi / 2 + k * np.pi / 5; rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * np.cos(ang), cy + rr * np.sin(ang)))
    d.polygon(pts, fill=fill)

def check_badge(size=64):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=ACCENT + (255,))
    d.line([(size * .27, size * .52), (size * .44, size * .68), (size * .74, size * .34)], fill=BG0, width=7, joint="curve")
    return im

# ---------------------------------------------------------------- captions + progress
def chunks(text):
    w = text.split(); n = len(w)
    k = int(np.ceil(n / 4))                    # chunks of 3-4 words
    size = int(np.ceil(n / k)); return [" ".join(w[i:i + size]) for i in range(0, n, size)]

_cap = {}
def caption_layer(lines, cur):
    key = (tuple(lines), cur)
    if key in _cap: return _cap[key]
    size = 60
    while max(text_box(l, size)[0] for l in lines) > W - 2 * SAFE_X - 40 and size > 56: size -= 2
    lh = int(size * 1.45); h = lh * len(lines) + 34; w = W - 2 * SAFE_X
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=(8, 11, 16, 150))
    for k, l in enumerate(lines):
        ar(d, (w // 2, 17 + lh * k + lh // 2), l, size, ACCENT if k == cur else WHITE, "mm")
    _cap[key] = im; return im

def draw_caption(base, sents, T):
    for s in sents:
        if s["start"] - 0.05 <= T < s["end"] + 0.25:
            cs = chunks(s["text"]); L = sum(len(c) for c in cs)
            acc, idx = s["start"], 0
            for k, c in enumerate(cs):
                acc += (s["end"] - s["start"]) * len(c) / L
                if T < acc: idx = k; break
            else: idx = len(cs) - 1
            p0 = (idx // 2) * 2; lines = cs[p0:p0 + 2]
            layer = caption_layer(lines, idx - p0)
            a = ease((T - s["start"] + 0.05) / 0.15) * (1 - ease((T - s["end"] - 0.1) / 0.15))
            paste(base, layer, W // 2, H - SAFE_BOTTOM - layer.height // 2, a)
            return

def progress(base, p):
    d = ImageDraw.Draw(base)
    y = H - 34
    d.rounded_rectangle((SAFE_X, y, W - SAFE_X, y + 6), 3, fill=(40, 48, 64, 255))
    d.rounded_rectangle((SAFE_X, y, SAFE_X + max(6, int((W - 2 * SAFE_X) * p)), y + 6), 3, fill=ACCENT + (255,))

# ---------------------------------------------------------------- scenes
class Assets:
    def __init__(self):
        self.bg = {"hook": make_bg("hook", 2, 0.55), "solve": make_bg("solve", 6, 0.45),
                   "bg": make_bg("bg", 3, 0.55), "install": make_bg("install", 5, 0.40),
                   "outro": make_bg("outro", 2, 0.55)}
        cw = W - 2 * SAFE_X
        self.chat, _ = terminal_card(f"{ROOT}/claude-code-chat.png", cw, 900, "Claude Code")
        self.oc, _ = terminal_card(f"{ROOT}/opencode-summary.png", cw, 900, "OpenCode")
        self.explain, _ = terminal_card(f"{ROOT}/claude-code-explain.png", cw, 1080, "Claude Code")
        self.skills, self.skills_scale = terminal_card(f"{ROOT}/claude-code-skills.png", cw, 1120, "Claude Code")
        self.titles = {k: text_img(v, 92, ACCENT) for k, v in {
            1: "Termux بدعم عربي صحيح", 2: "Claude Code بالعربي", 3: "ومع OpenCode كمان",
            "4a": "الكود ثابت مكانه", "4b": "والجداول سليمة", 5: "التثبيت في 3 خطوات"}.items()}
        self.wordmark = text_img("AR Termux", 132, WHITE)
        self.check = check_badge(70)
        self.hook_panels = self._hook_panels()
        self.social = self._social()

    def _hook_panels(self):
        out = []
        pw, ph = W - 2 * SAFE_X, 420
        for kind in ("bad", "good"):
            col = RED if kind == "bad" else ACCENT
            p = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
            d.rounded_rectangle((0, 0, pw - 1, ph - 1), 30, fill=CARD + (235,), outline=col + (255,), width=4)
            label = "ترمينال عادي" if kind == "bad" else "AR Termux"
            ar(d, (pw // 2, 80), label, 64, col)
            d.line((80, 140, pw - 80, 140), fill=col + (90,), width=2)
            sent = "مرحبًا بالعربي"
            if kind == "good":
                ar(d, (pw // 2, 270), sent, 92, col)
            else:
                # what a plain terminal shows: isolated letters, left-to-right (reversed for an Arabic reader)
                chars = [c for c in sent if not "ً" <= c <= "ْ"]
                for fs in range(92, 50, -4):
                    f = ImageFont.truetype(f"{ROOT}/Tajawal-Bold.ttf", fs, layout_engine=ImageFont.Layout.BASIC)
                    ws = [d.textlength(c, font=f) + 10 for c in chars]
                    if sum(ws) < pw - 100: break
                x = (pw - sum(ws)) / 2
                for c, wch in zip(chars, ws):
                    d.text((x, 270), c, font=f, fill=col, anchor="lm"); x += wch
            out.append(shadowed(p, 30, 26, 120))
        return out

    def _social(self):
        im = Image.open(f"{ROOT}/social-preview.png").convert("RGB")
        w = W - 2 * SAFE_X; im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS).convert("RGBA")
        im.putalpha(rounded_mask(im.width, im.height, 26))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 26, outline=(48, 60, 80, 255), width=2)
        return shadowed(im)

def bg_at(A, name, t, dur):
    b = A.bg[name]; mx, my = b.width - W, b.height - H
    p = t / max(dur, 0.1)
    x = int(mx * (0.2 + 0.6 * p)); y = int(my * (0.5 + 0.3 * np.sin(p * 2)))
    return b.crop((x, y, x + W, y + H))

def title(base, img, t, y=250, t0=0.05):
    k = (t - t0) / 0.35
    if k <= 0: return
    paste(base, img, W // 2, y, ease(k * 1.6), 0.82 + 0.18 * ease_back(k))

CONTENT_TOP, CONTENT_BOT = 360, H - SAFE_BOTTOM - 200   # cards live between title and captions

def card_in(base, card, t, dur, cy, t0=0.15, sweep_at=0.9):
    k = ease((t - t0) / 0.45)
    if k <= 0: return
    z = 1 + 0.035 * min(max(t, 0) / max(dur, 0.1), 1)        # <=4% slow zoom
    drift = 6 * np.sin(t * 0.8)
    paste(base, sweep(card, (t - sweep_at) / 0.9), W // 2, cy + 40 * (1 - k) + drift, k, z)

def scene_hook(A, base, t, dur, S):
    bad, good = A.hook_panels
    paste(base, bad, W // 2, 560, ease(t / 0.3), 0.92 + 0.08 * ease_back(t / 0.3))
    k = (t - 1.1) / 0.35
    paste(base, good, W // 2, 1060, ease(k), 0.92 + 0.08 * ease_back(k))
    # glitch only here: short bursts on the broken panel, and a light split into the transition
    for a, b in ((0.08, 0.22), (0.75, 0.85), (2.3, 2.38)):
        if a <= t < b:
            return rgb_split(base, 10, [(400, 430, 26), (610, 650, -18)])
    if t > dur - 0.3:
        return rgb_split(base, int(4 + 10 * (t - dur + 0.3) / 0.3))
    return base

def scene_solve(A, base, t, dur, S):
    title(base, A.titles[1], t)
    paste(base, A.wordmark, W // 2, 560, ease(t / 0.4), 0.9 + 0.1 * ease_back(t / 0.4))
    d = ImageDraw.Draw(base)
    bw = int(220 * ease((t - 0.25) / 0.5))
    if bw > 2:
        bar = Image.new("RGBA", (bw, 10)); g = np.linspace(0, 1, bw)[None, :, None]
        arr = (np.array(ACCENT) * (1 - g) + np.array(ACCENT2) * g).repeat(10, 0)
        bar = Image.fromarray(np.dstack([arr, np.full((10, bw, 1), 255)]).astype(np.uint8), "RGBA")
        bar.putalpha(rounded_mask(bw, 10, 5)); base.alpha_composite(bar, (W // 2 - bw // 2, 650))
    s2 = S[1]["start"] - S[0]["start"] + 0.1
    items = ["حروف متصلة", "من اليمين للشمال", "الإنجليزي في مكانه"]
    for k, it in enumerate(items):
        tk = t - (s2 + 0.9 * k + 0.3)
        a = ease(tk / 0.35)
        if a <= 0: continue
        y = 840 + k * 150; x_off = 30 * (1 - a)
        layer = A.__dict__.setdefault(f"_it{k}", text_img(it, 64, WHITE))
        cx = W - SAFE_X - 70 - 24 - layer.width // 2 + 12
        paste(base, A.check, W - SAFE_X - 35 - 20 + x_off, y, a)
        paste(base, layer, cx + x_off, y + 4, a)
    return base

def scene_card(A, base, t, dur, S, card, tkey):
    title(base, A.titles[tkey], t)
    card_in(base, card, t, dur, (CONTENT_TOP + CONTENT_BOT) // 2 + 30)
    return base

def scene_code(A, base, t, dur, S):
    sw = S[1]["start"] - S[0]["start"] - 0.05 + LEAD     # switch to the table when its sentence starts
    if t < sw:
        title(base, A.titles["4a"], t)
        a_out = 1 - ease((t - sw + 0.35) / 0.35)
        k = ease((t - 0.15) / 0.45)
        z = 1 + 0.03 * t / dur
        paste(base, sweep(A.explain, (t - 0.9) / 0.9), W // 2, (CONTENT_TOP + CONTENT_BOT) // 2 + 30 + 40 * (1 - k),
              k * a_out, z)
    else:
        tt = t - sw
        title(base, A.titles["4b"], tt, t0=0.0)
        k = ease(tt / 0.4); z = 1 + 0.03 * tt / (dur - sw)
        paste(base, sweep(A.skills, (tt - 0.5) / 0.9), W // 2, (CONTENT_TOP + CONTENT_BOT) // 2 + 30 + 40 * (1 - k), k, z)
    return base

STEPS = [("نزّل الـ APK", "من صفحة Releases على GitHub"),
         ("امسح Termux الأصلي", "وكل إضافاته، قبل التثبيت"),
         ("ثبّت وجرّب", "افتح التطبيق وابدأ")]

def scene_install(A, base, t, dur, S):
    title(base, A.titles[5], t)
    if not hasattr(A, "_steps"):
        A._steps = [(text_img(a, 68, WHITE, max_w=660), text_img(b, 48, MUTED, bold=False, max_w=660)) for a, b in STEPS]
        A._badges = []
        for n in range(3):
            bd = Image.new("RGBA", (120, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(bd)
            d.ellipse((0, 0, 119, 119), fill=ACCENT + (255,))
            d.text((60, 64), str(n + 1), font=font(70), fill=BG0, anchor="mm")
            A._badges.append(bd)
    rows = [560, 860, 1160]
    d = ImageDraw.Draw(base)
    bx = W - SAFE_X - 60
    for n in range(3):
        st = S[n + 1]["start"] - S[0]["start"] + LEAD
        a = ease((t - st) / 0.4)
        if a <= 0: continue
        if n > 0:
            d.line((bx, rows[n - 1] + 64, bx, rows[n - 1] + 64 + (rows[n] - rows[n - 1] - 128) * a), fill=ACCENT + (255,), width=4)
        paste(base, A._badges[n], bx, rows[n], a, 0.7 + 0.3 * ease_back((t - st) / 0.4))
        h, sub = A._steps[n]
        right = bx - 90
        paste(base, h, right - h.width // 2 + 12 + 30 * (1 - a), rows[n] - 26, a)
        paste(base, sub, right - sub.width // 2 + 12 + 30 * (1 - a), rows[n] + 46, a)
    return base

def scene_outro(A, base, t, dur, S):
    paste(base, A.wordmark, W // 2, 300, ease(t / 0.4), 0.9 + 0.1 * ease_back(t / 0.4))
    k = ease((t - 0.25) / 0.45)
    paste(base, sweep(A.social, (t - 0.8) / 0.9), W // 2, 640 + 40 * (1 - k), k)
    if not hasattr(A, "_url"):
        url = text_img("github.com/ahmedsykoo/ar-termux", 50, WHITE)
        pill = Image.new("RGBA", (W - 2 * SAFE_X, url.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, pill.height - 1), 40,
                                               fill=(22, 27, 46, 235), outline=ACCENT + (255,), width=3)
        pill.alpha_composite(url, ((pill.width - url.width) // 2, 20))
        A._url = pill
        tt = text_img("ادعمنا بنجمة", 92, ACCENT)
        s = Image.new("RGBA", (tt.width + 130, max(tt.height, 110)), (0, 0, 0, 0))
        star(ImageDraw.Draw(s), s.width - 55, s.height // 2, 48, ACCENT + (255,))
        s.alpha_composite(tt, (0, (s.height - tt.height) // 2))
        A._star = s
    k2 = ease((t - 0.7) / 0.4)
    paste(base, A._url, W // 2, 1000 + 30 * (1 - k2), k2)
    s1 = S[1]["start"] - S[0]["start"] + LEAD
    k3 = (t - s1) / 0.35
    paste(base, A._star, W // 2, 1200, ease(k3 * 1.5), 0.82 + 0.18 * ease_back(k3))
    return base

SCENES = [("hook", scene_hook), ("solve", scene_solve),
          ("bg", lambda A, b, t, d, S: scene_card(A, b, t, d, S, A.chat, 2)),
          ("bg", lambda A, b, t, d, S: scene_card(A, b, t, d, S, A.oc, 3)),
          ("bg", scene_code), ("install", scene_install), ("outro", scene_outro)]

def render_scene(A, i, T, scenes, sents):
    s0, s1 = scenes[i]; t = T - s0; dur = s1 - s0
    name, fn = SCENES[i]
    base = bg_at(A, name, t, dur)
    ambient(base, T)
    S = [s for s in sents if s["scene"] == i]
    return fn(A, base, t, dur, S)

def frame(A, T, scenes, sents, total):
    i = next(k for k, (a, b) in enumerate(scenes) if T < b or k == len(scenes) - 1)
    img = render_scene(A, i, T, scenes, sents)
    # crossfade around each boundary
    if i + 1 < len(scenes) and T > scenes[i][1] - XFADE / 2:
        a = (T - (scenes[i][1] - XFADE / 2)) / XFADE
        img = Image.blend(img, render_scene(A, i + 1, T, scenes, sents), ease(a))
    elif i > 0 and T < scenes[i][0] + XFADE / 2:
        a = (T - (scenes[i][0] - XFADE / 2)) / XFADE
        img = Image.blend(render_scene(A, i - 1, T, scenes, sents), img, ease(a))
    draw_caption(img, sents, T)
    progress(img, T / total)
    return img.convert("RGB")

# ---------------------------------------------------------------- main
def setup():
    clips = tts_sentences()
    scenes, sents = timeline(clips)
    return clips, scenes, sents, scenes[-1][1]

def encode(A, scenes, sents, total, out, upto=None):
    n = int((upto or total) * FPS)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(n):
        p.stdin.write(frame(A, f / FPS, scenes, sents, total).tobytes())
        if f % 150 == 0: print(f"frame {f}/{n}  {f / max(time.time() - t0, 1e-3):.1f} fps", flush=True)
    p.stdin.close(); p.wait()
    return n / (time.time() - t0)

def main():
    clips, scenes, sents, total = setup()
    A = Assets()
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "frames":
        for ts in sys.argv[2:]:
            frame(A, float(ts), scenes, sents, total).save(f"{BUILD}/f_{float(ts):05.2f}.png")
        return
    if mode == "bench":
        fps = encode(A, scenes, sents, total, f"{BUILD}/bench.mp4", float(sys.argv[2]))
        print(f"render speed {fps:.1f} fps"); return
    names = ["Hook", "Solution", "Claude Code", "OpenCode", "Code + tables", "Install", "Outro"]
    for n, (a, b) in zip(names, scenes): print(f"{n:14s} {b - a:5.2f}s")
    print(f"total {total:.2f}s")
    voice = build_voice(clips, sents, total)
    music = build_music(total)
    vid = f"{BUILD}/video.mp4"
    fps = encode(A, scenes, sents, total, vid)
    print(f"render speed {fps:.1f} fps")
    mix(voice, music, vid, f"{ROOT}/final.mp4")
    print("wrote", f"{ROOT}/final.mp4")

if __name__ == "__main__":
    main()

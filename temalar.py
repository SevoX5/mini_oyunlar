"""
TEMALAR  -  oyun merkezinin arka plan / ortam temaları.

YENİ TEMA EKLEMEK İÇİN:
  1) def _benim_temam(h, ox, oy, z): ...   fonksiyonunu yaz
        h  : çizilecek yüzey (pencerenin tamamı)
        ox, oy : 1100x720'lik arayüz alanının h içindeki sol-üst köşesi
        z  : geçen toplam süre (saniye) -> animasyonlar için
  2) Aşağıdaki TEMALAR sözlüğüne bir satır ekle.
  3) ayarlar.py içindeki _M sözlüğüne  "tema.<kimlik>"  için Türkçe/İngilizce ad ekle.
Başka hiçbir yere dokunmana gerek yok; tema listesi ve önizleme otomatik güncellenir.
"""
import math
import random

import pygame

_parlama_onbellek = {}


def parlama(hedef, renk, konum, yaricap):
    """Verilen konuma yumuşak neon parıltısı (toplamalı karışım) çizer."""
    yaricap = max(4, min(260, int(yaricap) // 4 * 4))
    anahtar = (tuple(renk), yaricap)
    if anahtar not in _parlama_onbellek:
        yuzey = pygame.Surface((yaricap * 2, yaricap * 2))
        for i in range(yaricap, 0, -1):
            katsayi = (1 - i / yaricap) ** 2
            pygame.draw.circle(yuzey, tuple(int(c * katsayi) for c in renk), (yaricap, yaricap), i)
        _parlama_onbellek[anahtar] = yuzey
    hedef.blit(_parlama_onbellek[anahtar], (int(konum[0] - yaricap), int(konum[1] - yaricap)),
               special_flags=pygame.BLEND_ADD)


def karart(renk, katsayi):
    return tuple(int(c * katsayi) for c in renk)


def _gradyan(h, gen, y0, y1, c0, c1, adim=6):
    """Dikey renk geçişi."""
    for y in range(y0, y1, adim):
        t = (y - y0) / max(1, y1 - y0)
        h.fill(tuple(int(a + (b - a) * t) for a, b in zip(c0, c1)), (0, y, gen, adim))


def _yildizlar(tohum, adet, x0, x1, y0, y1):
    r = random.Random(tohum)
    return [(r.randint(x0, x1), r.randint(y0, y1), r.randint(1, 3), r.random() * 6.28) for _ in range(adet)]


def _yildiz_ciz(h, liste, ox, oy, z, alt):
    gen = h.get_width()
    for x, y, boyut, faz in liste:
        px, py = ox + x, oy + y
        if 0 <= px < gen and 0 <= py < alt:
            p = 120 + int(100 * math.sin(z * 2 + faz))
            h.fill((p, p, 255), (px, py, boyut, boyut))


def _izgara(h, orta, ufuk, z, renk_dikey, renk_yatay):
    """Ufka doğru giden synthwave ızgarası (pencerenin altına kadar uzar)."""
    gen, yuk = h.get_size()
    der = yuk - ufuk
    pygame.draw.rect(h, (6, 2, 20), (0, ufuk, gen, der))
    for i in range(-40, 41):
        pygame.draw.line(h, renk_dikey, (orta + i * 45, ufuk), (orta + i * 45 + i * 255 * der / 324, yuk), 1)
    kayma = (z * 0.35) % 1
    for k in range(int(14 * max(1.0, math.sqrt(der / 324))) + 2):
        oran = (k + kayma) / 14
        y = ufuk + 324 * oran * oran
        if y > yuk:
            break
        pygame.draw.line(h, karart(renk_yatay, min(1.0, 0.25 + oran * 0.75)), (0, y), (gen, y), 1)


PEMBE, TURKUAZ, MOR, SARI = (255, 50, 150), (0, 235, 255), (175, 95, 255), (255, 225, 70)


# ----------------------------------------------------------------- 1) varsayılan (synthwave)
def _varsayilan(h, ox, oy, z):
    gen, yuk = h.get_size()
    h.fill((8, 4, 22))
    ufuk, orta = oy + int(720 * 0.55), ox + 550
    _yildiz_ciz(h, _Y_VARSAYILAN, ox, oy, z, ufuk)
    parlama(h, PEMBE, (orta, ufuk - 30), 210)
    _izgara(h, orta, ufuk, z, (90, 30, 150), (150, 50, 220))
    pygame.draw.line(h, PEMBE, (0, ufuk), (gen, ufuk), 2)


# ----------------------------------------------------------------- 2) uzay
def _uzay(h, ox, oy, z):
    gen, yuk = h.get_size()
    h.fill((3, 5, 16))
    parlama(h, (20, 40, 110), (ox + 200, oy + 150), 260)
    parlama(h, (40, 20, 90), (ox + 900, oy + 500), 260)
    _yildiz_ciz(h, _Y_UZAY, ox, oy, z, yuk)
    px, py = ox + 880, oy + 470                                   # halkalı gezegen
    for r, renk, kayma in ((112, (30, 42, 110), 0), (104, (48, 66, 150), 6), (84, (72, 98, 190), 16)):
        pygame.draw.circle(h, renk, (px - kayma, py - kayma), r)
    pygame.draw.ellipse(h, (150, 160, 225), (px - 175, py - 32, 350, 64), 3)
    pygame.draw.ellipse(h, (90, 100, 170), (px - 190, py - 40, 380, 80), 2)
    parlama(h, (60, 80, 200), (px, py), 150)
    faz = z % 6.0                                                 # ara sıra kayan yıldız
    if faz < 0.7:
        p = faz / 0.7
        x, y = ox + 100 + p * 700, oy + 60 + p * 260
        pygame.draw.line(h, (230, 240, 255), (x, y), (x - 70, y - 26), 2)
        parlama(h, (120, 150, 255), (x, y), 16)


# ----------------------------------------------------------------- 3) neon şehir
_r = random.Random(7)
_BINALAR, _x = [], -1600
while _x < 2700:
    _w = _r.randint(60, 130)
    _BINALAR.append((_x, _w, _r.randint(140, 430), _r.choice((TURKUAZ, PEMBE, MOR, SARI)), _r.randint(0, 999)))
    _x += _w + _r.randint(0, 14)


def _neon_sehir(h, ox, oy, z):
    gen, yuk = h.get_size()
    _gradyan(h, gen, 0, yuk, (8, 4, 26), (70, 14, 80))
    parlama(h, PEMBE, (ox + 550, yuk - 200), 260)
    for x, w, hh, renk, s in _BINALAR:
        bx = ox + x
        if bx > gen or bx + w < 0:
            continue
        ust = yuk - hh
        pygame.draw.rect(h, (12, 8, 30), (bx, ust, w, hh))
        pygame.draw.rect(h, karart(renk, 0.8), (bx, ust, w, hh), 2)
        for j in range(ust + 12, yuk - 8, 16):                    # yanıp sönen pencereler
            for i in range(bx + 8, bx + w - 8, 14):
                v = ((i - bx) * 7 + (j - ust) * 13 + s) % 11
                if v < 3 or (v == 3 and math.sin(z * 3 + i + j) > 0.6):
                    h.fill(karart(renk, 0.9) if v < 2 else (255, 220, 120), (i, j, 5, 7))
        parlama(h, renk, (bx + w / 2, ust), w * 0.8)
    for n in range(90):                                           # yağmur
        x = (n * 137.5 + z * 40) % (gen + 200) - 100
        y = (n * 53 + z * 600 * (0.6 + (n % 3) * 0.2)) % yuk
        pygame.draw.line(h, (120, 150, 230), (x, y), (x - 6, y + 16), 1)


# ----------------------------------------------------------------- 4) siberpunk
_s = random.Random(11)
_AKIS = [(_s.random() * 1000, _s.uniform(60, 220), _s.randint(6, 14), _s.choice(((0, 255, 170), (255, 50, 200), (0, 200, 255))))
         for _ in range(200)]


def _siberpunk(h, ox, oy, z):
    gen, yuk = h.get_size()
    _gradyan(h, gen, 0, yuk, (5, 5, 16), (28, 6, 44))
    ufuk, orta = oy + 396, ox + 550
    parlama(h, (255, 40, 140), (orta, ufuk - 20), 240)
    _izgara(h, orta, ufuk, z, (0, 120, 150), (0, 200, 230))
    pygame.draw.line(h, TURKUAZ, (0, ufuk), (gen, ufuk), 2)
    for c in range(gen // 22 + 1):                                # düşen veri akışları
        s0, hiz, uz, renk = _AKIS[c % 200]
        bas = (s0 + z * hiz) % (yuk + uz * 12)
        for j in range(uz):
            y = bas - j * 12
            if 0 <= y < yuk:
                h.fill(karart(renk, (1 - j / uz) * 0.85), (c * 22, y, 3, 9))
    for y in range(0, yuk, 4):                                    # tarama çizgileri
        h.fill((16, 16, 16), (0, y, gen, 1), special_flags=pygame.BLEND_RGB_SUB)
    h.fill((20, 8, 34), (0, int((z * 90) % yuk), gen, 6), special_flags=pygame.BLEND_ADD)   # glitch çubuğu


# ----------------------------------------------------------------- 5) galaksi ve yıldızlar
_g = random.Random(5)
_SPIRAL = [(k // 260, k % 260, _g.uniform(-7, 7), _g.uniform(-5, 5)) for k in range(780)]
_NEBULA = [((90, 30, 160), -200, -80, 0.0), ((160, 30, 110), 220, 60, 1.7), ((30, 70, 170), 0, 160, 3.1),
           ((120, 40, 140), -300, 150, 4.2)]


def _galaksi(h, ox, oy, z):
    gen, yuk = h.get_size()
    h.fill((4, 2, 12))
    cx, cy = ox + 550, oy + 340
    for renk, dx, dy, f in _NEBULA:
        parlama(h, renk, (cx + dx + 30 * math.sin(z * 0.2 + f), cy + dy + 20 * math.cos(z * 0.25 + f)), 240)
    _yildiz_ciz(h, _Y_GALAKSI, ox, oy, z, yuk)
    for kol, i, jx, jy in _SPIRAL:                                # dönen sarmal kollar
        r, a = 10 + i * 1.9, kol * 2.0944 + i * 0.05 + z * 0.05
        t = i / 260
        h.fill((int(255 - 110 * t), int(200 - 120 * t), int(170 + 85 * t)),
               (cx + r * math.cos(a) + jx, cy + r * math.sin(a) * 0.5 + jy, 2, 2))
    parlama(h, (255, 220, 170), (cx, cy), 100)


# ----------------------------------------------------------------- 6) doğa
_d = random.Random(21)
_AGACLAR, _x = [], -1600
while _x < 2700:
    _AGACLAR.append((_x, _d.randint(90, 220), _d.randint(22, 40)))
    _x += _d.randint(45, 95)
_KOZALAKLAR = [(_d.randint(-300, 1400), _d.randint(250, 640), _d.uniform(0.4, 1.2), _d.random() * 6.28) for _ in range(36)]


def _doga(h, ox, oy, z):
    gen, yuk = h.get_size()
    ufuk = oy + 470
    _gradyan(h, gen, 0, ufuk, (12, 22, 52), (214, 120, 110))
    _yildiz_ciz(h, _Y_DOGA, ox, oy, z, ufuk - 150)
    parlama(h, (255, 240, 200), (ox + 800, oy + 130), 110)
    pygame.draw.circle(h, (240, 238, 214), (ox + 800, oy + 130), 34)
    for baz, genlik, f1, f2, renk in ((ufuk - 70, 70, 0.004, 0.011, (48, 52, 96)), (ufuk - 20, 55, 0.006, 0.017, (30, 40, 72)),
                                      (ufuk + 30, 40, 0.009, 0.023, (16, 30, 44))):
        noktalar = [(0, yuk)] + [(x, baz - genlik * (math.sin((x - ox) * f1 + baz) + 0.5 * math.sin((x - ox) * f2 + 1.3)))
                                 for x in range(0, gen + 20, 20)] + [(gen, yuk)]
        pygame.draw.polygon(h, renk, noktalar)
    for x, hh, hw in _AGACLAR:                                    # ön plandaki çam ağaçları
        ax = ox + x
        if ax < -60 or ax > gen + 60:
            continue
        pygame.draw.polygon(h, (6, 16, 16), [(ax - hw, yuk - hh * 0.45), (ax, yuk - hh), (ax + hw, yuk - hh * 0.45)])
        pygame.draw.polygon(h, (6, 16, 16), [(ax - hw * 1.4, yuk - hh * 0.08), (ax, yuk - hh * 0.72), (ax + hw * 1.4, yuk - hh * 0.08)])
        pygame.draw.rect(h, (6, 16, 16), (ax - 3, yuk - hh * 0.1, 6, hh * 0.1))
    for bx, by, hiz, faz in _KOZALAKLAR:                          # ateş böcekleri
        v = round((0.5 + 0.5 * math.sin(z * 2 + faz)) * 4) / 4
        if v > 0:
            parlama(h, (int(200 * v), int(255 * v), int(90 * v)),
                    (ox + bx + 40 * math.sin(z * hiz + faz), oy + by + 25 * math.cos(z * hiz * 0.8 + faz)), 16)


# ----------------------------------------------------------------- 7) karanlık
_k = random.Random(3)
_NOKTALAR = [(_k.randint(-1500, 2600), _k.randint(-600, 1500), _k.random() * 6.28) for _ in range(150)]


def _karanlik(h, ox, oy, z):
    gen, yuk = h.get_size()
    h.fill((9, 9, 12))
    parlama(h, (28, 28, 40), (ox + 550, oy + 360), 260)
    for x, y, f in _NOKTALAR:
        px, py = ox + x, oy + y
        if 0 <= px < gen and 0 <= py < yuk:
            p = 30 + int(25 * math.sin(z + f))
            h.fill((p, p, p + 6), (px, py, 2, 2))


_Y_VARSAYILAN = _yildizlar(1, 1000, -1500, 2600, -1000, 360)
_Y_UZAY = _yildizlar(2, 1400, -1500, 2600, -1000, 1500)
_Y_GALAKSI = _yildizlar(4, 1200, -1500, 2600, -1000, 1500)
_Y_DOGA = _yildizlar(6, 500, -1500, 2600, -1000, 330)

# kimlik -> tema.  'renkler' sadece ayarlardaki küçük renk örneği içindir.
TEMALAR = {
    "varsayilan": dict(ciz=_varsayilan, renkler=((8, 4, 22), (255, 50, 150))),
    "uzay": dict(ciz=_uzay, renkler=((3, 5, 16), (72, 98, 190))),
    "neon_sehir": dict(ciz=_neon_sehir, renkler=((8, 4, 26), (0, 235, 255))),
    "siberpunk": dict(ciz=_siberpunk, renkler=((5, 5, 16), (255, 40, 140))),
    "galaksi": dict(ciz=_galaksi, renkler=((4, 2, 12), (160, 60, 200))),
    "doga": dict(ciz=_doga, renkler=((12, 22, 52), (214, 120, 110))),
    "karanlik": dict(ciz=_karanlik, renkler=((9, 9, 12), (60, 60, 70))),
}
TEMA_SIRASI = list(TEMALAR)


def ciz(tema_kimligi, hedef, ox, oy, z):
    """Seçili temayı verilen yüzeye çizer (bilinmeyen kimlik -> varsayılan tema)."""
    TEMALAR.get(tema_kimligi, TEMALAR["varsayilan"])["ciz"](hedef, ox, oy, z)
"""
SİBER KORİDOR 3D  -  Birinci şahıs neon labirent nişancısı (raycasting)

Kurulum :  pip install pygame
Çalıştır:  python siber_koridor.py

HEDEF
  Her bölümde labirentte 3 ANAHTAR KARTI bul, robotlardan kurtul ve ASANSÖRE ulaş.
  3. bölümde asansörü koruyan PATRONU da yok etmen gerekir. 3 bölümü bitir, sistemi kurtar.

KONTROLLER
  W A S D        : yürü (SHIFT: koş)       FARE / Ok tuşları : etrafına bak
  Sol tık / SPACE: ateş                    1 / 2 / 3 / tekerlek : silah değiştir
  ESC / P        : duraklat (fareyi serbest bırakır)
"""
import math
import os
import random
import sys

import pygame

# ----------------------------------------------------------------- sabitler
GENISLIK, YUKSEKLIK = 1100, 720        # pencere boyutu
KARE_HIZI = 60                         # saniyedeki kare sayısı
SUTUN = 4                              # her ışının ekranda kapladığı piksel genişliği (büyürse hızlanır, kabalaşır)
ISIN_SAYISI = GENISLIK // SUTUN        # ekran başına atılan ışın sayısı
GORUS = 0.66                           # kamera düzleminin uzunluğu (yaklaşık 66 derecelik görüş açısı)
SIS_MESAFESI = 14.0                    # bu mesafeden sonra duvarlar karanlığa karışır
REKOR_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siber_koridor_rekor.txt")

SEVIYELER = [   # hucre: labirent büyüklüğü, dusman: robot sayısı, patron: patron var mı
    dict(hucre=6, dusman=7, patron=False),
    dict(hucre=8, dusman=12, patron=False),
    dict(hucre=9, dusman=14, patron=True),
]
HASAR_CARPANI = [1.0, 1.25, 1.5]       # bölüm ilerledikçe düşman hasarı artar

pygame.init()
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
pygame.display.set_caption("SİBER KORİDOR 3D")
saat = pygame.time.Clock()
YAZI_TIPI = "dejavusansmono,consolas,couriernew,monospace"
yazi_k = pygame.font.SysFont(YAZI_TIPI, 15, bold=True)
yazi_o = pygame.font.SysFont(YAZI_TIPI, 21, bold=True)
yazi_b = pygame.font.SysFont(YAZI_TIPI, 34, bold=True)
yazi_xb = pygame.font.SysFont(YAZI_TIPI, 72, bold=True)

TURKUAZ = (0, 235, 255)
PEMBE = (255, 50, 150)
SARI = (255, 225, 70)
YESIL = (80, 255, 150)
TURUNCU = (255, 140, 40)
MOR = (175, 95, 255)
KIRMIZI = (255, 65, 80)
BEYAZ = (255, 255, 255)

DUVAR_RENKLERI = {1: (40, 100, 220), 2: (140, 50, 200), 3: (20, 170, 170)}   # duvar türü -> ana renk
DUVAR_CIZGI = {1: TURKUAZ, 2: PEMBE, 3: YESIL}                                 # duvar türü -> neon çizgi rengi

SILAHLAR = [   # (isim, ateş aralığı, enerji maliyeti, ışın sayısı, yayılma, ışın başı hasar, renk, basılı tutunca otomatik)
    ("TABANCA", 0.28, 0, 1, 0.0, 30, TURKUAZ, False),
    ("SAÇMA", 0.85, 6, 10, 0.12, 9, SARI, False),
    ("PLAZMA", 0.11, 1, 1, 0.03, 11, YESIL, True),
]
DUSMAN_OZELLIKLERI = {   # tür: (can, sürat, yarıçap, sprite ölçeği, havada kalma, puan, ateş aralığı, tercih edilen mesafe)
    "dron": (30, 2.8, 0.28, 0.55, 0.25, 60, 0.0, 0.0),
    "nisanci": (70, 1.5, 0.30, 0.85, 0.0, 150, 1.4, 4.5),
    "agir": (220, 1.0, 0.40, 1.05, 0.0, 350, 2.2, 5.5),
    "patron": (900, 1.2, 0.55, 1.6, 0.0, 3000, 1.0, 6.5),
}


# ----------------------------------------------------------------- yardımcı fonksiyonlar
def yazi_yaz(font, metin, renk, konum, ortala=False, seffaflik=255):
    """Gölgeli yazıyı ekrana yazar. 'ortala' True ise konum yazının merkezidir."""
    resim = font.render(metin, True, renk)
    resim.set_alpha(seffaflik)
    alan = resim.get_rect(center=konum) if ortala else resim.get_rect(topleft=konum)
    golge = font.render(metin, True, (0, 0, 0))
    golge.set_alpha(seffaflik)
    ekran.blit(golge, alan.move(2, 2))
    ekran.blit(resim, alan)
    return alan


def bar_ciz(dikdortgen, oran, renk):
    """Dolu-boş çubuk (can, enerji). oran: 0 ile 1 arası."""
    x, y, genislik, yukseklik = dikdortgen
    pygame.draw.rect(ekran, (12, 12, 28), dikdortgen)
    pygame.draw.rect(ekran, renk, (x, y, int(genislik * max(0, min(1, oran))), yukseklik))
    pygame.draw.rect(ekran, (90, 100, 140), dikdortgen, 1)


def karart(renk, katsayi):
    """Rengi koyulaştırır (katsayi 0-1)."""
    return tuple(max(0, min(255, int(c * katsayi))) for c in renk)


def parlama_dairesi(yuzey, renk, merkez, yaricap, en_yuksek_alfa=150):
    """Saydam yüzeye merkezden dışa sönen yumuşak ışık çizer (sprite süslemesi)."""
    for i in range(yaricap, 0, -2):
        alfa = int(en_yuksek_alfa * (1 - i / yaricap) ** 2)
        pygame.draw.circle(yuzey, (*renk, alfa), merkez, i)


def gokyuzu_zemin_olustur():
    """Tavan ve zemin için ufukta ışıyan neon degrade arka plan resmi üretir."""
    yuzey = pygame.Surface((GENISLIK, YUKSEKLIK))
    yarim = YUKSEKLIK // 2
    for y in range(yarim):
        k = y / yarim
        pygame.draw.line(yuzey, (int(8 + 52 * k), int(2 + 12 * k), int(26 + 60 * k)), (0, y), (GENISLIK, y))
        k2 = 1 - k                                             # zemin: ufukta parlak, aşağıda koyu
        pygame.draw.line(yuzey, (int(4 + 46 * k2), int(2 + 10 * k2), int(14 + 56 * k2)),
                         (0, YUKSEKLIK - 1 - y), (GENISLIK, YUKSEKLIK - 1 - y))
    return yuzey


# ----------------------------------------------------------------- labirent üretimi
def harita_uret(hucre, uretici):
    """Rastgele labirent üretir: 0 = boş, 1-3 = duvar türü. Her çalıştırmada farklı bir harita çıkar."""
    n = hucre * 2 + 1                                          # harita kenar uzunluğu (duvarlar dahil)
    harita = [[1] * n for _ in range(n)]
    harita[1][1] = 0
    yigin = [(1, 1)]                                           # derinlik öncelikli arama için yığın
    while yigin:
        x, y = yigin[-1]
        komsular = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):      # henüz oyulmamış komşu hücreler
            nx, ny = x + dx, y + dy
            if 0 < nx < n - 1 and 0 < ny < n - 1 and harita[ny][nx] == 1:
                komsular.append((nx, ny, dx, dy))
        if komsular:
            nx, ny, dx, dy = uretici.choice(komsular)
            harita[y + dy // 2][x + dx // 2] = 0               # aradaki duvarı yık
            harita[ny][nx] = 0
            yigin.append((nx, ny))
        else:
            yigin.pop()
    for _ in range(n * 2):                                     # bazı duvarları yık: döngüler, kaçış yolları
        x, y = uretici.randrange(1, n - 1), uretici.randrange(1, n - 1)
        if harita[y][x] == 1 and (x % 2 == 1) != (y % 2 == 1):
            harita[y][x] = 0
    for _ in range(hucre // 2 + 1):                            # birkaç açık oda (3x3)
        ox, oy = uretici.randrange(0, hucre - 1) * 2 + 1, uretici.randrange(0, hucre - 1) * 2 + 1
        for yy in range(oy, oy + 3):
            for xx in range(ox, ox + 3):
                if 0 < xx < n - 1 and 0 < yy < n - 1:
                    harita[yy][xx] = 0
    for y in range(n):                                         # duvarlara bölgeye göre renk türü ver
        for x in range(n):
            if harita[y][x]:
                harita[y][x] = ((x // 3 + y // 3) % 3) + 1
    return harita


def mesafe_haritasi(harita, bx, by):
    """(bx, by) hücresinden her hücreye adım sayısını hesaplar (BFS). Ulaşılamayan hücre = -1."""
    n = len(harita)
    mesafe = [[-1] * n for _ in range(n)]
    mesafe[by][bx] = 0
    kuyruk = [(bx, by)]
    for x, y in kuyruk:                                        # kuyruk büyürken dolaşılır
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and harita[ny][nx] == 0 and mesafe[ny][nx] < 0:
                mesafe[ny][nx] = mesafe[y][x] + 1
                kuyruk.append((nx, ny))
    return mesafe


# ----------------------------------------------------------------- sprite (resim) üretimi
_sprite_onbellek = {}   # ad -> hazır sprite resmi


def sprite_olustur(ad):
    """Robotlar, eşyalar ve mermiler için kodla çizilmiş neon sprite'lar üretir (resim dosyası gerekmez)."""
    if ad in _sprite_onbellek:
        return _sprite_onbellek[ad]
    boyut = 64 if ad.startswith("orb") else 128
    s = pygame.Surface((boyut, boyut), pygame.SRCALPHA)
    if ad == "dron":                                           # uçan kamikaze robot
        parlama_dairesi(s, KIRMIZI, (64, 64), 60, 110)
        pygame.draw.polygon(s, (40, 10, 20), [(10, 56), (44, 52), (44, 76), (10, 90)])
        pygame.draw.polygon(s, (40, 10, 20), [(118, 56), (84, 52), (84, 76), (118, 90)])
        pygame.draw.polygon(s, KIRMIZI, [(10, 56), (44, 52), (44, 76), (10, 90)], 3)
        pygame.draw.polygon(s, KIRMIZI, [(118, 56), (84, 52), (84, 76), (118, 90)], 3)
        pygame.draw.circle(s, (30, 10, 20), (64, 66), 28)
        pygame.draw.circle(s, KIRMIZI, (64, 66), 28, 4)
        pygame.draw.circle(s, (255, 200, 200), (64, 66), 11)
        pygame.draw.circle(s, KIRMIZI, (64, 66), 6)
    elif ad == "nisanci":                                      # insansı silahlı robot
        parlama_dairesi(s, TURUNCU, (64, 70), 58, 90)
        pygame.draw.rect(s, (30, 18, 10), (46, 88, 14, 36))    # bacaklar
        pygame.draw.rect(s, (30, 18, 10), (68, 88, 14, 36))
        pygame.draw.rect(s, TURUNCU, (46, 88, 14, 36), 2)
        pygame.draw.rect(s, TURUNCU, (68, 88, 14, 36), 2)
        pygame.draw.polygon(s, (36, 22, 12), [(34, 50), (94, 50), (88, 92), (40, 92)])   # gövde
        pygame.draw.polygon(s, TURUNCU, [(34, 50), (94, 50), (88, 92), (40, 92)], 3)
        pygame.draw.rect(s, (36, 22, 12), (96, 56, 26, 14))    # silah kolu
        pygame.draw.rect(s, TURUNCU, (96, 56, 26, 14), 3)
        pygame.draw.circle(s, (36, 22, 12), (64, 32), 17)      # kafa
        pygame.draw.circle(s, TURUNCU, (64, 32), 17, 3)
        pygame.draw.rect(s, (255, 230, 160), (52, 28, 24, 7))  # parlayan göz çizgisi
    elif ad == "agir":                                         # iri zırhlı robot
        parlama_dairesi(s, MOR, (64, 66), 62, 100)
        pygame.draw.rect(s, (24, 14, 40), (26, 30, 76, 84))
        pygame.draw.rect(s, MOR, (26, 30, 76, 84), 4)
        pygame.draw.rect(s, (24, 14, 40), (6, 36, 24, 40))     # omuz zırhları
        pygame.draw.rect(s, (24, 14, 40), (98, 36, 24, 40))
        pygame.draw.rect(s, MOR, (6, 36, 24, 40), 3)
        pygame.draw.rect(s, MOR, (98, 36, 24, 40), 3)
        pygame.draw.circle(s, (255, 220, 255), (64, 74), 14)   # göğüs çekirdeği
        pygame.draw.circle(s, MOR, (64, 74), 14, 4)
        pygame.draw.rect(s, (255, 220, 255), (46, 42, 36, 8))  # vizör
    elif ad == "patron":                                       # ÇEKİRDEK GÖZCÜSÜ
        parlama_dairesi(s, PEMBE, (64, 64), 63, 130)
        pts = [(64 + 52 * math.cos(i * math.tau / 8 + 0.4), 64 + 52 * math.sin(i * math.tau / 8 + 0.4)) for i in range(8)]
        pygame.draw.polygon(s, (36, 8, 24), pts)
        pygame.draw.polygon(s, PEMBE, pts, 5)
        pygame.draw.polygon(s, PEMBE, [(64, 22), (100, 84), (28, 84)], 3)
        pygame.draw.circle(s, (255, 230, 245), (64, 62), 20)
        pygame.draw.circle(s, PEMBE, (64, 62), 20, 5)
        pygame.draw.circle(s, (255, 40, 100), (64, 62), 8)
        for i in range(4):
            a = i * math.pi / 2 + 0.8
            pygame.draw.circle(s, PEMBE, (64 + 56 * math.cos(a), 64 + 56 * math.sin(a)), 7, 3)
    elif ad == "kart":                                         # anahtar kartı
        parlama_dairesi(s, SARI, (64, 64), 58, 130)
        pygame.draw.rect(s, (50, 40, 10), (26, 40, 76, 50), border_radius=6)
        pygame.draw.rect(s, SARI, (26, 40, 76, 50), 4, border_radius=6)
        pygame.draw.rect(s, SARI, (34, 50, 22, 16), border_radius=3)
        pygame.draw.line(s, SARI, (34, 78), (94, 78), 3)
        pygame.draw.line(s, SARI, (66, 54), (94, 54), 3)
    elif ad == "can":                                          # sağlık paketi
        parlama_dairesi(s, KIRMIZI, (64, 64), 50, 130)
        pygame.draw.circle(s, (40, 10, 16), (64, 64), 34)
        pygame.draw.circle(s, KIRMIZI, (64, 64), 34, 4)
        pygame.draw.rect(s, BEYAZ, (54, 40, 20, 48))
        pygame.draw.rect(s, BEYAZ, (40, 54, 48, 20))
    elif ad == "enerji":                                       # enerji hücresi (cephane)
        parlama_dairesi(s, TURKUAZ, (64, 64), 50, 130)
        pygame.draw.circle(s, (6, 30, 40), (64, 64), 34)
        pygame.draw.circle(s, TURKUAZ, (64, 64), 34, 4)
        pygame.draw.polygon(s, BEYAZ, [(70, 34), (46, 68), (62, 68), (56, 94), (84, 58), (66, 58)])
    elif ad == "cikis":                                        # asansör / çıkış portalı
        parlama_dairesi(s, YESIL, (64, 64), 62, 120)
        for i, k in enumerate((56, 44, 32)):
            pygame.draw.ellipse(s, YESIL if i % 2 == 0 else BEYAZ, (64 - k * 0.6, 64 - k * 1.1, k * 1.2, k * 2.2), 4)
        pygame.draw.rect(s, YESIL, (10, 120, 108, 6))
    elif ad == "orb_kirmizi":                                  # düşman mermisi
        parlama_dairesi(s, KIRMIZI, (32, 32), 30, 200)
        pygame.draw.circle(s, BEYAZ, (32, 32), 8)
    else:                                                      # orb_mor: patron mermisi
        parlama_dairesi(s, PEMBE, (32, 32), 30, 200)
        pygame.draw.circle(s, BEYAZ, (32, 32), 8)
    _sprite_onbellek[ad] = s
    return s


# ----------------------------------------------------------------- oyun nesneleri
class Oyuncu:
    """Oyuncunun durumu: konum, bakış açısı, can, enerji, silah ve topladığı kartlar."""

    def __init__(self):
        self.x = self.y = 1.5
        self.aci = 0.0                                         # bakış yönü (radyan)
        self.can, self.enerji = 100.0, 60.0
        self.silah = 0                                         # SILAHLAR listesindeki sıra
        self.ates_bekleme = 0.0
        self.kartlar = 0                                       # toplanan anahtar kartı sayısı
        self.salinim = 0.0                                     # yürürken silahın sallanma fazı
        self.geri_tepme = 0.0                                  # ateş sonrası silahın geri tepmesi (1 -> 0)
        self.hasar_flasi = 0.0                                 # hasar alınca ekranın kızarma süresi
        self.toplama_flasi = 0.0                               # eşya alınca ekranın parlama süresi
        self.vurus_isareti = 0.0                               # düşmana isabetlenince çarpı işareti süresi
        self.yarica = 0.22                                     # çarpışma yarıçapı


class Mermi:
    """Düşmanın ateşlediği enerji küresi."""

    def __init__(self, x, y, aci, hiz, hasar, patron_mermisi=False):
        self.x, self.y, self.hasar = x, y, hasar
        self.vx, self.vy = math.cos(aci) * hiz, math.sin(aci) * hiz   # hız bileşenleri (hücre/sn)
        self.omur = 5.0
        self.sprite = "orb_mor" if patron_mermisi else "orb_kirmizi"


class Esya:
    """Yerdeki toplanabilir şey: 'can', 'enerji' veya 'kart'."""

    def __init__(self, tur, x, y):
        self.tur, self.x, self.y, self.zaman = tur, x, y, random.uniform(0, 6)


class Dusman:
    """Robot düşman: dron (kamikaze), nisanci (ateş eder), agir (üçlü atış), patron (final)."""

    def __init__(self, tur, x, y):
        (self.can, self.hiz, self.yaricap, self.olcek, self.havada, self.puan,
         self.ates_araligi, self.tercih) = DUSMAN_OZELLIKLERI[tur]
        self.tur, self.x, self.y = tur, x, y
        self.maks_can = self.can
        self.alarm = False                                     # oyuncuyu fark etti mi?
        self.bekleme = random.uniform(0.5, 1.5)                # bir sonraki ateşe kalan süre
        self.yanip_sonme = 0.0                                 # vurulunca kısa süre beyaz yanar
        self.oluyor, self.olum_sayaci = False, 0.0             # ölüm animasyonu
        self.zaman = random.uniform(0, 6)
        self.temas_bekleme = 0.0                               # dron temas hasarı aralığı
        self.atis_sayisi = 0                                   # patron için: her 3. atışta mermi halkası

    def hasar_al(self, hasar):
        self.can -= hasar
        self.yanip_sonme = 0.08
        self.alarm = True

    def ates_et(self, oyun, yon_aci):
        """Türüne göre oyuncuya doğru enerji küresi / küreler fırlatır."""
        carpan = HASAR_CARPANI[oyun.seviye]
        if self.tur == "nisanci":
            oyun.mermiler.append(Mermi(self.x, self.y, yon_aci, 5.5, 8 * carpan))
        elif self.tur == "agir":
            for sapma in (-0.18, 0, 0.18):
                oyun.mermiler.append(Mermi(self.x, self.y, yon_aci + sapma, 5.5, 10 * carpan))
        elif self.tur == "patron":
            self.atis_sayisi += 1
            for sapma in (-0.3, -0.15, 0, 0.15, 0.3):
                oyun.mermiler.append(Mermi(self.x, self.y, yon_aci + sapma, 6.0, 12 * carpan, True))
            if self.atis_sayisi % 3 == 0:                      # 360 derece mermi halkası
                for i in range(12):
                    oyun.mermiler.append(Mermi(self.x, self.y, i * math.tau / 12, 4.0, 10 * carpan, True))

    def guncelle(self, oyun, gecen):
        """Yapay zekâ: fark edince kovalar, uzaktan ateş eder; görüş yoksa yol bularak ilerler."""
        self.zaman += gecen
        self.yanip_sonme = max(0, self.yanip_sonme - gecen)
        if self.oluyor:
            self.olum_sayaci -= gecen
            return
        oyuncu = oyun.oyuncu
        dx, dy = oyuncu.x - self.x, oyuncu.y - self.y
        mesafe = math.hypot(dx, dy) or 0.001
        gorus = mesafe < 14 and oyun.gorus_var_mi(self.x, self.y, oyuncu.x, oyuncu.y)   # duvar arası boş mu?
        if not self.alarm:
            if gorus and mesafe < 10:
                self.alarm = True
            else:
                return
        yon_x, yon_y = dx / mesafe, dy / mesafe
        adim = self.hiz * gecen
        if self.tur == "dron":
            if gorus:                                          # yalpalayarak üzerine gelir
                yan = math.sin(self.zaman * 5) * 0.5
                oyun.hareket_et(self, (yon_x - yon_y * yan) * adim, (yon_y + yon_x * yan) * adim, self.yaricap)
            else:
                oyun.akisla_ilerle(self, adim)
            self.temas_bekleme -= gecen
            if mesafe < 0.6 and self.temas_bekleme <= 0:       # temas: hasar verir
                oyun.oyuncu_hasar(10 * HASAR_CARPANI[oyun.seviye])
                self.temas_bekleme = 0.7
        else:
            if gorus and mesafe < 13:
                if mesafe > self.tercih + 1:                   # çok uzaksa yaklaş
                    oyun.hareket_et(self, yon_x * adim, yon_y * adim, self.yaricap)
                elif mesafe < self.tercih - 1:                 # çok yakınsa geri çekil
                    oyun.hareket_et(self, -yon_x * adim, -yon_y * adim, self.yaricap)
                self.bekleme -= gecen
                if self.bekleme <= 0:
                    self.bekleme = self.ates_araligi
                    self.ates_et(oyun, math.atan2(dy, dx) + random.uniform(-0.04, 0.04))
            else:
                oyun.akisla_ilerle(self, adim)


# ----------------------------------------------------------------- oyunun kendisi
class Oyun:
    """Tüm oyunu yönetir: bölümler, ışın izleme çizimi, çarpışmalar, arayüz ve ekranlar."""

    def __init__(self):
        self.zemin_gokyuzu = gokyuzu_zemin_olustur()
        self.derinlik = [0.0] * ISIN_SAYISI                    # her ışının duvara olan mesafesi (sprite gizleme için)
        self.durum = "menu"        # "menu" | "oyun" | "duraklat" | "bolum_bitti" | "bitti" | "kazandi"
        self.kopya = None          # duraklatma / bitiş ekranları için son kare görüntüsü
        self.skor = self.sure = 0
        self.mesaj = ("", 0.0, BEYAZ)
        try:
            self.rekor = int(open(REKOR_DOSYASI).read().strip())
        except Exception:
            self.rekor = 0
        self.oyuncu = Oyuncu()
        self.seviye = 0
        self.seviye_baslat(0)

    # --- bölüm kurulumu
    def seviye_baslat(self, indeks):
        """Yeni rastgele labirent üretir; kartları, düşmanları ve eşyaları yerleştirir."""
        ayar = SEVIYELER[indeks]
        self.seviye = indeks
        self.harita = harita_uret(ayar["hucre"], random)
        n = len(self.harita)
        o = self.oyuncu
        o.x = o.y = 1.5
        o.aci = 0.0 if self.harita[1][2] == 0 else math.pi / 2  # açık olan yöne bakarak başla
        o.kartlar = 0
        o.can = min(100, o.can + 40) if indeks > 0 else 100
        o.enerji = max(o.enerji, 60)
        self.kesfedildi = [[False] * n for _ in range(n)]     # mini haritada gösterilecek keşfedilmiş hücreler
        mesafe = mesafe_haritasi(self.harita, 1, 1)
        bos = [(x, y) for y in range(n) for x in range(n) if self.harita[y][x] == 0 and mesafe[y][x] > 0]
        cikis = max(bos, key=lambda h: mesafe[h[1]][h[0]])     # başlangıca en uzak hücre = asansör
        self.cikis = Esya("cikis", cikis[0] + 0.5, cikis[1] + 0.5)
        uzak = [h for h in bos if mesafe[h[1]][h[0]] > 7 and h != cikis]
        random.shuffle(uzak)
        self.esyalar = [Esya("kart", x + 0.5, y + 0.5) for x, y in uzak[:3]]      # 3 anahtar kartı
        self.dusmanlar, self.mermiler = [], []
        self.patron_oldu = not ayar["patron"]
        if ayar["patron"]:                                     # patron asansörün yakınında bekler
            mesafe_cikis = mesafe_haritasi(self.harita, cikis[0], cikis[1])
            yakin = [h for h in bos if 4 <= mesafe_cikis[h[1]][h[0]] <= 7] or [cikis]
            px, py = random.choice(yakin)
            self.dusmanlar.append(Dusman("patron", px + 0.5, py + 0.5))
        agirlik = [(4, 3, 0), (4, 4, 1.5), (3, 4, 2.5)][indeks]   # (dron, nişancı, ağır) olasılıkları
        for x, y in uzak[3:3 + ayar["dusman"]]:
            tur = random.choices(["dron", "nisanci", "agir"], agirlik)[0]
            self.dusmanlar.append(Dusman(tur, x + 0.5, y + 0.5))
        for tur, adet in (("can", 4), ("enerji", 7)):          # yerlere saçılmış can ve enerji
            for _ in range(adet):
                x, y = random.choice(bos)
                self.esyalar.append(Esya(tur, x + 0.5, y + 0.5))
        self.akis = mesafe_haritasi(self.harita, 1, 1)         # düşmanların kullandığı yol haritası
        self.akis_sayaci = 0.0
        self.cikis_uyari = 0.0

    # --- harita / çarpışma yardımcıları
    def bos_mu(self, x, y, yaricap):
        """Verilen daire boş alanda mı? (dört köşe noktasına bakar)"""
        for ox in (-yaricap, yaricap):
            for oy in (-yaricap, yaricap):
                if self.harita[int(y + oy)][int(x + ox)] > 0:
                    return False
        return True

    def hareket_et(self, varlik, dx, dy, yaricap):
        """Duvara takılırsa kayarak hareket ettirir (önce x, sonra y ekseni)."""
        if self.bos_mu(varlik.x + dx, varlik.y, yaricap):
            varlik.x += dx
        if self.bos_mu(varlik.x, varlik.y + dy, yaricap):
            varlik.y += dy

    def gorus_var_mi(self, x1, y1, x2, y2):
        """İki nokta arasında duvar yoksa True (düşman ancak görüyorsa ateş eder)."""
        mesafe = math.hypot(x2 - x1, y2 - y1)
        adim = max(1, int(mesafe / 0.25))
        for i in range(1, adim):
            t = i / adim
            if self.harita[int(y1 + (y2 - y1) * t)][int(x1 + (x2 - x1) * t)] > 0:
                return False
        return True

    def duvar_mesafesi(self, x, y, dx, dy):
        """(x, y) noktasından (dx, dy) yönünde ilk duvara olan mesafe (DDA algoritması)."""
        hx, hy = int(x), int(y)
        delta_x = abs(1 / dx) if dx else 1e30                  # bir hücre ilerlemek için gereken ışın uzunluğu
        delta_y = abs(1 / dy) if dy else 1e30
        adim_x, yan_x = (1, (hx + 1 - x) * delta_x) if dx > 0 else (-1, (x - hx) * delta_x)
        adim_y, yan_y = (1, (hy + 1 - y) * delta_y) if dy > 0 else (-1, (y - hy) * delta_y)
        for _ in range(64):
            if yan_x < yan_y:
                yan_x += delta_x
                hx += adim_x
                mesafe = yan_x - delta_x
            else:
                yan_y += delta_y
                hy += adim_y
                mesafe = yan_y - delta_y
            if self.harita[hy][hx] > 0:
                return mesafe
        return 64.0

    def akisla_ilerle(self, dusman, adim):
        """Düşman oyuncuyu göremiyorsa, yol haritasında oyuncuya daha yakın komşu hücreye doğru yürür."""
        cx, cy = int(dusman.x), int(dusman.y)
        en_dusuk, en_iyi = self.akis[cy][cx], None
        if en_dusuk < 0:
            return
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d = self.akis[cy + dy][cx + dx]
            if 0 <= d < en_dusuk:
                en_dusuk, en_iyi = d, (cx + dx, cy + dy)
        hedef_x, hedef_y = (en_iyi[0] + 0.5, en_iyi[1] + 0.5) if en_iyi else (self.oyuncu.x, self.oyuncu.y)
        fx, fy = hedef_x - dusman.x, hedef_y - dusman.y
        uzunluk = math.hypot(fx, fy) or 0.001
        self.hareket_et(dusman, fx / uzunluk * adim, fy / uzunluk * adim, dusman.yaricap)

    # --- oyun olayları
    def mesaj_ver(self, metin, renk=TURKUAZ, sure=2.5):
        """Ekranın ortasında kısa bir bilgi mesajı gösterir."""
        self.mesaj = (metin, sure, renk)

    def oyuncu_hasar(self, hasar):
        """Oyuncuya hasar verir; can bitince oyun biter."""
        if self.durum != "oyun":
            return
        self.oyuncu.can -= hasar
        self.oyuncu.hasar_flasi = 0.4
        if self.oyuncu.can <= 0:
            self.bitir("bitti")

    def bitir(self, durum):
        """Oyunu 'bitti' veya 'kazandi' durumuna alır, rekoru kaydeder, fareyi serbest bırakır."""
        self.durum, self.kopya = durum, None
        self.fare_yakala(False)
        if self.skor > self.rekor:
            self.rekor = self.skor
            try:
                open(REKOR_DOSYASI, "w").write(str(self.rekor))
            except Exception:
                pass

    def fare_yakala(self, yakala):
        """Fareyi pencereye kilitler (bakış kontrolü için) ya da serbest bırakır."""
        pygame.mouse.set_visible(not yakala)
        pygame.event.set_grab(yakala)
        pygame.mouse.get_rel()                                 # birikmiş hareketi sıfırla

    def dusman_hasar(self, dusman, hasar):
        """Düşmana hasar verir; ölürse puan, eşya düşürme ve ölüm animasyonu başlatır."""
        dusman.hasar_al(hasar)
        self.oyuncu.vurus_isareti = 0.15
        if dusman.can <= 0 and not dusman.oluyor:
            dusman.oluyor, dusman.olum_sayaci = True, 0.45
            self.skor += dusman.puan
            if dusman.tur == "patron":
                self.patron_oldu = True
                self.mesaj_ver("PATRON YOK EDİLDİ! Asansöre git!", PEMBE, 3.5)
            elif random.random() < 0.35:
                self.esyalar.append(Esya(random.choice(["can", "enerji", "enerji"]), dusman.x, dusman.y))

    def oyuncu_ates(self):
        """Seçili silahla ateş eder: ışınlar duvara ya da bir düşmana çarpana kadar gider (hitscan)."""
        o = self.oyuncu
        isim, aralik, maliyet, isin, yayilma, hasar, renk, oto = SILAHLAR[o.silah]
        if o.enerji < maliyet:
            self.mesaj_ver("ENERJİ YOK!  (enerji hücresi topla / TABANCA'ya geç)", KIRMIZI, 1.0)
            o.ates_bekleme = 0.3
            return
        o.enerji -= maliyet
        o.ates_bekleme, o.geri_tepme = aralik, 1.0
        for d in self.dusmanlar:                               # silah sesi yakındaki robotları uyandırır
            if not d.oluyor and math.hypot(d.x - o.x, d.y - o.y) < 9:
                d.alarm = True
        for _ in range(isin):
            aci = o.aci + random.uniform(-yayilma, yayilma)
            dx, dy = math.cos(aci), math.sin(aci)
            en_yakin, en_t = None, self.duvar_mesafesi(o.x, o.y, dx, dy)   # duvardan öteye vurulamaz
            for d in self.dusmanlar:
                if d.oluyor:
                    continue
                vx, vy = d.x - o.x, d.y - o.y
                t = vx * dx + vy * dy                          # düşmanın ışın üzerindeki izdüşümü
                if 0 < t < en_t and abs(vx * dy - vy * dx) < d.yaricap:   # ışına dik uzaklığı yarıçaptan küçükse isabet
                    en_yakin, en_t = d, t
            if en_yakin:
                self.dusman_hasar(en_yakin, hasar)

    # --- güncelleme
    def guncelle(self, gecen):
        """Bir karelik mantık: hareket, bakış, ateş, düşmanlar, mermiler, eşyalar, çıkış."""
        o = self.oyuncu
        tuslar = pygame.key.get_pressed()
        self.sure += gecen
        fare_x, _ = pygame.mouse.get_rel()
        o.aci += fare_x * 0.0022 + ((tuslar[pygame.K_RIGHT] or tuslar[pygame.K_e]) - (tuslar[pygame.K_LEFT] or tuslar[pygame.K_q])) * 2.2 * gecen
        ileri = tuslar[pygame.K_w] - tuslar[pygame.K_s] + tuslar[pygame.K_UP] - tuslar[pygame.K_DOWN]
        yana = tuslar[pygame.K_d] - tuslar[pygame.K_a]
        hiz = 3.2 * (1.5 if tuslar[pygame.K_LSHIFT] else 1.0)
        yx, yy = math.cos(o.aci), math.sin(o.aci)              # bakış yönü
        hx, hy = ileri * yx - yana * yy, ileri * yy + yana * yx   # hareket yönü (ileri-geri + yana kayma)
        uzunluk = math.hypot(hx, hy)
        if uzunluk > 0:
            hx, hy = hx / uzunluk * hiz * gecen, hy / uzunluk * hiz * gecen
            self.hareket_et(o, hx, hy, o.yarica)
            o.salinim += gecen * hiz * 2.4
        for ad in ("ates_bekleme", "geri_tepme", "hasar_flasi", "toplama_flasi", "vurus_isareti"):
            setattr(o, ad, max(0.0, getattr(o, ad) - gecen * (4 if ad == "geri_tepme" else 1)))
        o.enerji = min(100, o.enerji + 1.5 * gecen)
        silah = SILAHLAR[o.silah]
        basili = pygame.mouse.get_pressed()[0] or tuslar[pygame.K_SPACE]
        if basili and o.ates_bekleme <= 0:
            self.oyuncu_ates()

        # keşfedilen hücreler (mini harita)
        cx, cy = int(o.x), int(o.y)
        for yy_ in range(max(0, cy - 3), min(len(self.harita), cy + 4)):
            for xx_ in range(max(0, cx - 3), min(len(self.harita), cx + 4)):
                self.kesfedildi[yy_][xx_] = True

        # düşmanlar için yol haritasını belli aralıkla yenile
        self.akis_sayaci -= gecen
        if self.akis_sayaci <= 0:
            self.akis_sayaci = 0.35
            self.akis = mesafe_haritasi(self.harita, cx, cy)
        for d in self.dusmanlar:
            d.guncelle(self, gecen)
        self.dusmanlar = [d for d in self.dusmanlar if not (d.oluyor and d.olum_sayaci <= 0)]

        # düşman mermileri
        kalan = []
        for m in self.mermiler:
            m.x += m.vx * gecen
            m.y += m.vy * gecen
            m.omur -= gecen
            if m.omur <= 0 or self.harita[int(m.y)][int(m.x)] > 0:
                continue
            if math.hypot(m.x - o.x, m.y - o.y) < 0.35:
                self.oyuncu_hasar(m.hasar)
                continue
            kalan.append(m)
        self.mermiler = kalan

        # eşya toplama
        kalan = []
        for e in self.esyalar:
            e.zaman += gecen
            if math.hypot(e.x - o.x, e.y - o.y) < 0.55:
                if e.tur == "kart":
                    o.kartlar += 1
                    self.mesaj_ver(f"ANAHTAR KARTI {o.kartlar}/3", SARI)
                    self.skor += 200
                elif e.tur == "can":
                    if o.can >= 100:
                        kalan.append(e)
                        continue
                    o.can = min(100, o.can + 30)
                    self.mesaj_ver("+30 SAĞLIK", KIRMIZI, 1.2)
                else:
                    if o.enerji >= 100:
                        kalan.append(e)
                        continue
                    o.enerji = min(100, o.enerji + 30)
                    self.mesaj_ver("+30 ENERJİ", TURKUAZ, 1.2)
                o.toplama_flasi = 0.25
            else:
                kalan.append(e)
        self.esyalar = kalan

        # çıkış / asansör
        self.cikis_uyari = max(0, self.cikis_uyari - gecen)
        if math.hypot(self.cikis.x - o.x, self.cikis.y - o.y) < 0.9:
            if o.kartlar >= 3 and self.patron_oldu:
                self.skor += 1000 + max(0, int(300 - self.sure))
                if self.seviye + 1 >= len(SEVIYELER):
                    self.skor += 2000
                    self.bitir("kazandi")
                else:
                    self.durum, self.kopya = "bolum_bitti", None
                    self.fare_yakala(False)
            elif self.cikis_uyari <= 0:
                self.cikis_uyari = 2.0
                self.mesaj_ver("Asansör kilitli! " + (f"{3 - o.kartlar} kart eksik." if o.kartlar < 3 else "Önce patronu yok et!"), KIRMIZI)

        metin, kalan_sure, renk = self.mesaj
        self.mesaj = (metin, max(0, kalan_sure - gecen), renk)

    # --- çizim: 3D sahne
    def sahneyi_ciz(self):
        """Raycasting: ekranın her sütunu için bir ışın atar, çarptığı duvarı mesafesine göre boyutlandırıp çizer."""
        o = self.oyuncu
        ekran.blit(self.zemin_gokyuzu, (0, 0))
        yon_x, yon_y = math.cos(o.aci), math.sin(o.aci)
        duzlem_x, duzlem_y = -yon_y * GORUS, yon_x * GORUS     # kameranın yan düzlemi (yöne dik)
        harita, derinlik = self.harita, self.derinlik
        yarim = YUKSEKLIK // 2
        for k in range(ISIN_SAYISI):
            kamera_x = 2 * k / ISIN_SAYISI - 1                 # -1 (sol) ... +1 (sağ)
            isin_x, isin_y = yon_x + duzlem_x * kamera_x, yon_y + duzlem_y * kamera_x
            hx, hy = int(o.x), int(o.y)
            delta_x = abs(1 / isin_x) if isin_x else 1e30
            delta_y = abs(1 / isin_y) if isin_y else 1e30
            if isin_x > 0:
                adim_x, yan_x = 1, (hx + 1 - o.x) * delta_x
            else:
                adim_x, yan_x = -1, (o.x - hx) * delta_x
            if isin_y > 0:
                adim_y, yan_y = 1, (hy + 1 - o.y) * delta_y
            else:
                adim_y, yan_y = -1, (o.y - hy) * delta_y
            while True:                                        # duvara çarpana kadar hücre hücre ilerle
                if yan_x < yan_y:
                    yan_x += delta_x
                    hx += adim_x
                    yan = 0
                else:
                    yan_y += delta_y
                    hy += adim_y
                    yan = 1
                if harita[hy][hx] > 0:
                    break
            dik = max(0.05, (yan_x - delta_x) if yan == 0 else (yan_y - delta_y))   # balık gözü olmayan dik mesafe
            derinlik[k] = dik
            vurus = (o.y + dik * isin_y) if yan == 0 else (o.x + dik * isin_x)       # duvar üzerinde çarpma noktası
            vurus -= math.floor(vurus)
            tur = harita[hy][hx]
            yukseklik = int(YUKSEKLIK / dik)                   # duvarın ekrandaki yüksekliği (yakınsa büyük)
            ust = yarim - yukseklik // 2
            sis = max(0.06, 1 - dik / SIS_MESAFESI) ** 1.3     # uzaklaştıkça kararma
            if yan == 1:
                sis *= 0.72                                    # bir yöndeki duvarlar daha karanlık: derinlik hissi
            renk = karart(DUVAR_RENKLERI[tur], sis)
            if vurus < 0.05 or vurus > 0.95:                   # panel kenarlarında neon çizgi
                renk = karart(DUVAR_CIZGI[tur], sis * 0.95)
            x = k * SUTUN
            pygame.draw.rect(ekran, renk, (x, ust, SUTUN, yukseklik))
            cizgi_renk = karart(DUVAR_CIZGI[tur], sis * 0.9)
            kalinlik = max(1, yukseklik // 30)
            pygame.draw.rect(ekran, cizgi_renk, (x, ust, SUTUN, kalinlik))                        # üst neon şerit
            pygame.draw.rect(ekran, cizgi_renk, (x, ust + yukseklik - kalinlik, SUTUN, kalinlik))  # alt neon şerit
            pygame.draw.rect(ekran, cizgi_renk, (x, ust + yukseklik // 2, SUTUN, max(1, kalinlik // 2)))   # orta çizgi

        # sprite'lar (robotlar, eşyalar, mermiler): uzaktan yakına doğru çiz
        varliklar = []
        for d in self.dusmanlar:
            olcek = d.olcek * (max(0.05, d.olum_sayaci / 0.45) if d.oluyor else 1)
            beyaz = 220 if d.oluyor else (160 if d.yanip_sonme > 0 else 0)
            kaldirma = d.havada + (math.sin(d.zaman * 3) * 0.05 if d.tur == "dron" else 0)
            varliklar.append((d.x, d.y, d.tur, olcek, kaldirma, beyaz, True))
        for e in self.esyalar:
            varliklar.append((e.x, e.y, e.tur, 0.42, 0.12 + math.sin(e.zaman * 3) * 0.05, 0, False))
        for m in self.mermiler:
            varliklar.append((m.x, m.y, m.sprite, 0.2, 0.4, 0, False))
        varliklar.append((self.cikis.x, self.cikis.y, "cikis", 1.0, 0.0, 0, False))
        varliklar.sort(key=lambda v: -((v[0] - o.x) ** 2 + (v[1] - o.y) ** 2))
        ters_det = 1.0 / (duzlem_x * yon_y - yon_x * duzlem_y)
        for vx, vy, ad, olcek, kaldirma, beyaz, sisli in varliklar:
            fx, fy = vx - o.x, vy - o.y
            yana = ters_det * (yon_y * fx - yon_x * fy)        # kamera uzayında yanal konum
            derin = ters_det * (-duzlem_y * fx + duzlem_x * fy)   # kamera uzayında derinlik
            if derin < 0.2:
                continue
            ekran_x = int(GENISLIK / 2 * (1 + yana / derin))
            boyut = min(1400, int(YUKSEKLIK / derin * olcek))
            if boyut < 4 or ekran_x + boyut // 2 < 0 or ekran_x - boyut // 2 > GENISLIK:
                continue
            zemin_y = yarim + YUKSEKLIK / (2 * derin)          # bu derinlikte zeminin ekrandaki y konumu
            sol = ekran_x - boyut // 2
            ust = int(zemin_y - boyut - kaldirma * YUKSEKLIK / derin)
            resim = pygame.transform.scale(sprite_olustur(ad), (boyut, boyut))
            if sisli:
                sis = int(255 * max(0.25, 1 - derin / (SIS_MESAFESI * 1.2)))
                resim.fill((sis, sis, sis, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if beyaz:
                resim.fill((beyaz, beyaz, beyaz, 0), special_flags=pygame.BLEND_RGB_ADD)
            x = max(0, sol) - max(0, sol) % SUTUN
            son = min(GENISLIK, sol + boyut)
            while x < son:                                     # sprite'ı sütun sütun çiz: duvar arkasında kalanı gizle
                idx = x // SUTUN
                if idx < ISIN_SAYISI and derin < derinlik[idx]:
                    bas = max(x, sol)
                    genislik = min(x + SUTUN, son) - bas
                    if genislik > 0:
                        ekran.blit(resim, (bas, ust), (bas - sol, 0, genislik, boyut))
                x += SUTUN

    def silah_ciz(self):
        """Ekranın altında elde tutulan silahı (sallanma, geri tepme ve namlu alevi ile) çizer."""
        o = self.oyuncu
        renk = SILAHLAR[o.silah][6]
        cx = GENISLIK // 2 + 210 + int(math.sin(o.salinim) * 10)
        cy = YUKSEKLIK + 10 + int(abs(math.cos(o.salinim)) * 8) + int(o.geri_tepme * 36)
        koyu = (14, 14, 30)
        if o.silah == 0:                                       # tabanca
            pygame.draw.polygon(ekran, koyu, [(cx - 50, cy), (cx + 50, cy), (cx + 34, cy - 120), (cx - 34, cy - 120)])
            pygame.draw.polygon(ekran, renk, [(cx - 50, cy), (cx + 50, cy), (cx + 34, cy - 120), (cx - 34, cy - 120)], 3)
            pygame.draw.rect(ekran, koyu, (cx - 18, cy - 210, 36, 100))
            pygame.draw.rect(ekran, renk, (cx - 18, cy - 210, 36, 100), 3)
            pygame.draw.line(ekran, renk, (cx, cy - 205), (cx, cy - 120), 2)
            namlu = (cx, cy - 214)
        elif o.silah == 1:                                     # saçma
            for ox in (-26, 26):
                pygame.draw.rect(ekran, koyu, (cx + ox - 22, cy - 240, 44, 190))
                pygame.draw.rect(ekran, renk, (cx + ox - 22, cy - 240, 44, 190), 3)
            pygame.draw.polygon(ekran, koyu, [(cx - 80, cy), (cx + 80, cy), (cx + 60, cy - 70), (cx - 60, cy - 70)])
            pygame.draw.polygon(ekran, renk, [(cx - 80, cy), (cx + 80, cy), (cx + 60, cy - 70), (cx - 60, cy - 70)], 3)
            namlu = (cx, cy - 244)
        else:                                                  # plazma tüfeği
            pygame.draw.polygon(ekran, koyu, [(cx - 60, cy), (cx + 60, cy), (cx + 30, cy - 100), (cx - 30, cy - 100)])
            pygame.draw.polygon(ekran, renk, [(cx - 60, cy), (cx + 60, cy), (cx + 30, cy - 100), (cx - 30, cy - 100)], 3)
            pygame.draw.rect(ekran, koyu, (cx - 14, cy - 250, 28, 160))
            pygame.draw.rect(ekran, renk, (cx - 14, cy - 250, 28, 160), 3)
            pygame.draw.circle(ekran, renk, (cx, cy - 150), 12 + int(math.sin(self.sure * 8) * 2))   # nabız gibi atan çekirdek
            namlu = (cx, cy - 254)
        if o.geri_tepme > 0.55:                                # namlu alevi
            for yaricap, k in ((70, 0.25), (46, 0.5), (24, 1.0)):
                pygame.draw.circle(ekran, karart(renk, k), namlu, yaricap)
            pygame.draw.circle(ekran, BEYAZ, namlu, 12)

    def minimap_ciz(self):
        """Sağ üstte, keşfedilen yerleri gösteren mini harita."""
        n = len(self.harita)
        hucre = max(4, min(9, 170 // n))
        bx, by = GENISLIK - n * hucre - 16, 16
        pygame.draw.rect(ekran, (6, 6, 16), (bx - 4, by - 4, n * hucre + 8, n * hucre + 8))
        for y in range(n):
            for x in range(n):
                if self.kesfedildi[y][x]:
                    tur = self.harita[y][x]
                    renk = karart(DUVAR_CIZGI[tur], 0.55) if tur else (22, 22, 46)
                    pygame.draw.rect(ekran, renk, (bx + x * hucre, by + y * hucre, hucre, hucre))
        for e in self.esyalar:
            if e.tur == "kart" and self.kesfedildi[int(e.y)][int(e.x)]:
                pygame.draw.circle(ekran, SARI, (bx + e.x * hucre, by + e.y * hucre), 3)
        if self.kesfedildi[int(self.cikis.y)][int(self.cikis.x)]:
            pygame.draw.circle(ekran, YESIL, (bx + self.cikis.x * hucre, by + self.cikis.y * hucre), 4, 2)
        for d in self.dusmanlar:
            if d.alarm and not d.oluyor:
                pygame.draw.circle(ekran, KIRMIZI, (bx + d.x * hucre, by + d.y * hucre), 2)
        o = self.oyuncu
        merkez = (bx + o.x * hucre, by + o.y * hucre)
        uc = (merkez[0] + math.cos(o.aci) * 7, merkez[1] + math.sin(o.aci) * 7)
        pygame.draw.circle(ekran, TURKUAZ, merkez, 3)
        pygame.draw.line(ekran, TURKUAZ, merkez, uc, 2)
        pygame.draw.rect(ekran, TURKUAZ, (bx - 4, by - 4, n * hucre + 8, n * hucre + 8), 1)

    def arayuz_ciz(self):
        """HUD: can, enerji, silahlar, görev, nişangâh, mesajlar ve hasar efektleri."""
        o = self.oyuncu
        if o.hasar_flasi > 0:                                  # hasar alınca ekran kızarır
            kirmizi = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
            kirmizi.fill((255, 0, 30, int(130 * o.hasar_flasi / 0.4)))
            ekran.blit(kirmizi, (0, 0))
        if o.toplama_flasi > 0:                                # eşya alınca ekran parlar
            parlak = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
            parlak.fill((80, 255, 200, int(60 * o.toplama_flasi / 0.25)))
            ekran.blit(parlak, (0, 0))
        orta = (GENISLIK // 2, YUKSEKLIK // 2)                 # nişangâh
        for dx, dy in ((-14, 0), (8, 0), (0, -14), (0, 8)):
            pygame.draw.line(ekran, TURKUAZ, (orta[0] + dx, orta[1] + dy), (orta[0] + dx + (6 if dx else 0), orta[1] + dy + (6 if dy else 0)), 2)
        if o.vurus_isareti > 0:                                # isabet çarpısı
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                pygame.draw.line(ekran, KIRMIZI, (orta[0] + sx * 8, orta[1] + sy * 8), (orta[0] + sx * 18, orta[1] + sy * 18), 3)
        bar_ciz((20, YUKSEKLIK - 70, 280, 18), o.can / 100, TURKUAZ if o.can > 35 else KIRMIZI)
        yazi_yaz(yazi_k, f"SAĞLIK {int(o.can)}", BEYAZ, (26, YUKSEKLIK - 69))
        bar_ciz((20, YUKSEKLIK - 44, 280, 12), o.enerji / 100, SARI)
        yazi_yaz(yazi_k, f"ENERJİ {int(o.enerji)}", SARI, (310, YUKSEKLIK - 46))
        for i, silah in enumerate(SILAHLAR):                   # silah kutuları
            kutu = pygame.Rect(20 + i * 96, YUKSEKLIK - 30, 90, 24)
            pygame.draw.rect(ekran, (14, 14, 30), kutu)
            pygame.draw.rect(ekran, silah[6] if i == o.silah else (60, 60, 90), kutu, 3 if i == o.silah else 1)
            yazi_yaz(yazi_k, f"{i + 1} {silah[0]}", silah[6] if i == o.silah else (110, 110, 140), (kutu.x + 5, kutu.y + 4))
        if self.seviye == 2 and not self.patron_oldu:          # görev paneli
            hedef = "Patronu yok et, sonra asansöre git"
        elif o.kartlar < 3:
            hedef = f"Anahtar kartı topla: {o.kartlar}/3"
        else:
            hedef = "Asansöre ulaş! (yeşil portal)"
        pygame.draw.rect(ekran, (10, 10, 26), (16, 14, 420, 52))
        pygame.draw.rect(ekran, TURKUAZ, (16, 14, 420, 52), 2)
        yazi_yaz(yazi_k, f"BÖLÜM {self.seviye + 1}/{len(SEVIYELER)}     SKOR {self.skor}", TURKUAZ, (28, 20))
        yazi_yaz(yazi_o, hedef, BEYAZ, (28, 39))
        patron = next((d for d in self.dusmanlar if d.tur == "patron" and d.alarm), None)
        if patron:
            bar_ciz((GENISLIK // 2 - 250, 80, 500, 14), patron.can / patron.maks_can, PEMBE)
            yazi_yaz(yazi_k, "ÇEKİRDEK GÖZCÜSÜ", PEMBE, (GENISLIK // 2, 108), ortala=True)
        metin, kalan, renk = self.mesaj
        if kalan > 0:
            yazi_yaz(yazi_o, metin, renk, (GENISLIK // 2, YUKSEKLIK // 2 - 120), ortala=True, seffaflik=int(255 * min(1, kalan)))
        self.minimap_ciz()

    def karartma(self, alfa=170):
        """Ekranı karartır (menü ve bitiş ekranlarında yazının okunması için)."""
        perde = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
        perde.fill((0, 0, 12, alfa))
        ekran.blit(perde, (0, 0))

    # --- ekranlar
    def menu_ciz(self, gecen):
        """Menü: arkada yavaşça dönen 3D koridor, hikâye ve kontroller."""
        self.oyuncu.aci += gecen * 0.25
        self.sure += gecen
        self.sahneyi_ciz()
        self.karartma(150)
        yazi_yaz(yazi_xb, "SİBER KORİDOR 3D", TURKUAZ, (GENISLIK // 2, 140), ortala=True)
        yazi_yaz(yazi_o, "NEO-İSTANBUL  ·  2147", PEMBE, (GENISLIK // 2, 195), ortala=True)
        hikaye = ["ÇEKİRDEK-X'in yeraltı tesisine sızdın. Koridorlar robotlarla dolu.",
                  "3 anahtar kartını bul, asansöre ulaş ve her kattan sağ çık.",
                  "Son katta çekirdeği koruyan PATRONU yok et."]
        for i, satir in enumerate(hikaye):
            yazi_yaz(yazi_o, satir, BEYAZ, (GENISLIK // 2, 262 + i * 32), ortala=True)
        kontroller = ["WASD : yürü (SHIFT koş)    FARE : bak    SOL TIK / SPACE : ateş",
                      "1-2-3 / tekerlek : silah    ESC : duraklat    Her oyun yeni bir labirent!"]
        for i, satir in enumerate(kontroller):
            yazi_yaz(yazi_k, satir, (150, 170, 210), (GENISLIK // 2, 400 + i * 26), ortala=True)
        yazi_yaz(yazi_b, "ENTER veya TIKLA  -  BAŞLA", SARI, (GENISLIK // 2, 520), ortala=True,
                 seffaflik=int(140 + 115 * math.sin(self.sure * 4)))
        yazi_yaz(yazi_k, f"REKOR: {self.rekor}", YESIL, (GENISLIK // 2, 590), ortala=True)

    def son_ekran_ciz(self, baslik, renk, alt_yazi, ipucu):
        """Oyun bitti / kazandın / bölüm bitti ekranlarını son kare üzerine çizer."""
        ekran.blit(self.kopya, (0, 0))
        self.karartma(185)
        yazi_yaz(yazi_xb, baslik, renk, (GENISLIK // 2, 210), ortala=True)
        yazi_yaz(yazi_o, alt_yazi, BEYAZ, (GENISLIK // 2, 285), ortala=True)
        yazi_yaz(yazi_b, f"SKOR {self.skor}", SARI, (GENISLIK // 2, 360), ortala=True)
        yazi_yaz(yazi_o, f"Rekor: {self.rekor}", YESIL, (GENISLIK // 2, 410), ortala=True)
        yazi_yaz(yazi_o, ipucu, TURKUAZ, (GENISLIK // 2, 500), ortala=True)

    def adim(self, gecen):
        """Ana döngünün her karede çağırdığı fonksiyon: duruma göre günceller ve çizer."""
        if self.durum == "oyun":
            self.guncelle(gecen)
        if self.durum == "oyun":
            self.sahneyi_ciz()
            self.silah_ciz()
            self.arayuz_ciz()
        elif self.durum == "menu":
            self.menu_ciz(gecen)
        else:
            if self.kopya is None:
                self.kopya = ekran.copy()
            if self.durum == "duraklat":
                ekran.blit(self.kopya, (0, 0))
                self.karartma(150)
                yazi_yaz(yazi_xb, "DURAKLATILDI", TURKUAZ, (GENISLIK // 2, 280), ortala=True)
                yazi_yaz(yazi_o, "ESC / P : devam      Q : menüye dön", BEYAZ, (GENISLIK // 2, 360), ortala=True)
            elif self.durum == "bolum_bitti":
                self.son_ekran_ciz("BÖLÜM TAMAMLANDI", YESIL, f"Bölüm {self.seviye + 1} geçildi. Daha derine iniyorsun...",
                                   "ENTER : sonraki bölüm")
            elif self.durum == "bitti":
                self.son_ekran_ciz("ÖLDÜN", KIRMIZI, "Robotlar seni yakaladı...", "R : tekrar dene      M / ESC : menü")
            else:
                self.son_ekran_ciz("SİSTEM KURTULDU", YESIL, "ÇEKİRDEK-X çöktü. Neo-İstanbul özgür!", "R : tekrar oyna      M / ESC : menü")

    # --- olaylar
    def yeni_oyun(self):
        """Sıfırdan yeni oyun başlatır."""
        self.oyuncu = Oyuncu()
        self.skor, self.sure = 0, 0
        self.seviye_baslat(0)
        self.durum, self.kopya = "oyun", None
        self.fare_yakala(True)
        self.mesaj_ver("3 anahtar kartı bul!", SARI, 3.5)

    def olay_isle(self, olay):
        """Klavye / fare / pencere olaylarını duruma göre işler."""
        if olay.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        durum = self.durum
        if olay.type == pygame.KEYDOWN:
            tus = olay.key
            if durum == "menu":
                if tus in (pygame.K_RETURN, pygame.K_SPACE):
                    self.yeni_oyun()
                elif tus == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif durum == "oyun":
                if tus in (pygame.K_ESCAPE, pygame.K_p):
                    self.durum, self.kopya = "duraklat", None
                    self.fare_yakala(False)
                elif tus in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.oyuncu.silah = tus - pygame.K_1
            elif durum == "duraklat":
                if tus in (pygame.K_ESCAPE, pygame.K_p):
                    self.durum = "oyun"
                    self.fare_yakala(True)
                elif tus == pygame.K_q:
                    self.durum = "menu"
            elif durum == "bolum_bitti":
                if tus == pygame.K_RETURN:
                    self.seviye_baslat(self.seviye + 1)
                    self.durum = "oyun"
                    self.fare_yakala(True)
                    self.mesaj_ver(f"BÖLÜM {self.seviye + 1}", SARI, 3)
            elif durum in ("bitti", "kazandi"):
                if tus == pygame.K_r:
                    self.yeni_oyun()
                elif tus in (pygame.K_ESCAPE, pygame.K_m):
                    self.durum = "menu"
        elif olay.type == pygame.MOUSEBUTTONDOWN and durum == "menu":
            self.yeni_oyun()
        elif olay.type == pygame.MOUSEWHEEL and durum == "oyun":
            self.oyuncu.silah = (self.oyuncu.silah - olay.y) % len(SILAHLAR)


def ana():
    """Programın giriş noktası: oyun döngüsünü çalıştırır."""
    oyun = Oyun()
    while True:
        gecen = min(saat.tick(KARE_HIZI) / 1000, 0.05)         # önceki kareden beri geçen süre (sn)
        for olay in pygame.event.get():
            oyun.olay_isle(olay)
        oyun.adim(gecen)
        pygame.display.flip()


if __name__ == "__main__":
    ana()
"""
SİBER KAÇIŞ  -  Neo-İstanbul, 2147
Geleceğin şehrinde robotlarla savaş, görevleri tamamla ve sistemi kurtar.



KONTROLLER
  WASD / Ok tuşları : hareket          Fare : nişan al
  Sol tık (basılı)  : ateş             SPACE : atılma / dash (hasar almazsın)
  1 / 2 / 3 / tekerlek : silah değiştir
  E (basılı tut)    : terminal hackle  ESC / P : duraklat
"""
import math
import os
import random
import sys

import pygame
from pygame import Vector2 as Vek   # Vek(x, y): konum / hız gibi iki boyutlu vektör

# ----------------------------------------------------------------- sabitler
GENISLIK, YUKSEKLIK = 1100, 720        # pencere boyutu (piksel)
KARE_HIZI = 60                         # saniyedeki kare sayısı (FPS)
DUNYA_G, DUNYA_Y = 2600, 1900          # oyun dünyasının genişliği ve yüksekliği
SOKAK_X = [600, 1100, 1600, 2100]      # dikey sokakların orta çizgisi (x)
SOKAK_Y = [500, 920, 1340]             # yatay sokakların orta çizgisi (y)
ASANSOR_KONUM = Vek(2100, 1340)        # kaçış asansörünün dünyadaki yeri

pygame.init()
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))   # gerçek pencere
pygame.display.set_caption("SİBER KAÇIŞ")
saat = pygame.time.Clock()                                # kare hızını sabitlemek için
tuval = pygame.Surface((GENISLIK, YUKSEKLIK))             # her şeyin önce çizildiği yüzey
YAZI_TIPI = "dejavusansmono,consolas,couriernew,monospace"
yazi_k = pygame.font.SysFont(YAZI_TIPI, 15, bold=True)    # küçük yazı
yazi_o = pygame.font.SysFont(YAZI_TIPI, 21, bold=True)    # orta yazı
yazi_b = pygame.font.SysFont(YAZI_TIPI, 34, bold=True)    # büyük yazı
yazi_xb = pygame.font.SysFont(YAZI_TIPI, 76, bold=True)   # çok büyük yazı (başlık)

TURKUAZ = (0, 235, 255)
PEMBE = (255, 50, 150)
SARI = (255, 225, 70)
YESIL = (80, 255, 150)
TURUNCU = (255, 140, 40)
MOR = (175, 95, 255)
KIRMIZI = (255, 65, 80)
BEYAZ = (255, 255, 255)

REKOR_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siber_kacis_rekor.txt")

GOREVLER = [   # sırayla oynanan 4 görevin başlıkları
    "Şehir ağındaki 3 terminali hackle",
    "Robot ordusunu yok et",
    "Asansöre ulaş (yeşil işaret)",
    "ANA ÇEKİRDEK'i yok et!",
]
SILAHLAR = [   # (isim, ateş aralığı sn, enerji maliyeti, renk)
    ("PLAZMA", 0.17, 0, TURKUAZ),
    ("SAÇMA", 0.62, 10, SARI),
    ("LAZER", 0.065, 1.6, YESIL),
]
DUSMAN_OZELLIKLERI = {   # tür: (can, sürat, yarıçap, renk, öldürünce puan)
    "dron": (20, 195, 12, KIRMIZI, 50),
    "nisanci": (45, 105, 16, TURUNCU, 120),
    "agir": (170, 58, 26, MOR, 300),
    "patron": (900, 75, 54, PEMBE, 3000),
}


# ----------------------------------------------------------------- yardımcı fonksiyonlar
_parlama_onbellek = {}   # (renk, yarıçap) -> daha önce üretilmiş parlama resmi


def parlama_sprite_olustur(renk, yaricap):
    """Merkezden dışa doğru sönen yumuşak ışık topu resmi üretir (tekrar kullanılsın diye saklanır)."""
    anahtar = (renk, yaricap)
    if anahtar not in _parlama_onbellek:
        yuzey = pygame.Surface((yaricap * 2, yaricap * 2))
        for i in range(yaricap, 0, -1):
            katsayi = (1 - i / yaricap) ** 2                       # dışa doğru koyulaşan oran
            pygame.draw.circle(yuzey, tuple(int(c * katsayi) for c in renk), (yaricap, yaricap), i)
        _parlama_onbellek[anahtar] = yuzey
    return _parlama_onbellek[anahtar]


def parlama_ciz(yuzey, renk, konum, yaricap):
    """Verilen konuma neon parıltısı çizer (renkleri toplayarak, yani 'ADD' karışımıyla)."""
    yaricap = max(3, min(120, int(yaricap)))
    yuzey.blit(parlama_sprite_olustur(tuple(renk), yaricap),
               (int(konum[0] - yaricap), int(konum[1] - yaricap)), special_flags=pygame.BLEND_ADD)


def cokgen_ciz(yuzey, renk, noktalar, konum, aci=0.0, kalinlik=2):
    """Merkeze göre verilen noktalardan bir çokgeni 'aci' kadar döndürüp çizer."""
    cos_a, sin_a = math.cos(aci), math.sin(aci)
    donmus = [(konum[0] + x * cos_a - y * sin_a, konum[1] + x * sin_a + y * cos_a) for x, y in noktalar]
    pygame.draw.polygon(yuzey, renk, donmus, kalinlik)


def duzgun_cokgen(kenar_sayisi, yaricap):
    """Düzgün n-gen (altıgen, sekizgen...) köşe noktalarını döndürür."""
    return [(yaricap * math.cos(i * math.tau / kenar_sayisi), yaricap * math.sin(i * math.tau / kenar_sayisi))
            for i in range(kenar_sayisi)]


def yazi_yaz(font, metin, renk, konum, ortala=False, seffaflik=255):
    """Gölgeli yazıyı tuvale yazar. 'ortala' True ise konum yazının merkezidir."""
    resim = font.render(metin, True, renk)
    resim.set_alpha(seffaflik)
    alan = resim.get_rect(center=konum) if ortala else resim.get_rect(topleft=konum)
    golge = font.render(metin, True, (0, 0, 0))
    golge.set_alpha(seffaflik)
    tuval.blit(golge, alan.move(2, 2))
    tuval.blit(resim, alan)
    return alan


def bar_ciz(dikdortgen, oran, renk):
    """Can / enerji gibi dolu-boş çubuğu çizer. oran: 0 ile 1 arası doluluk."""
    x, y, genislik, yukseklik = dikdortgen
    pygame.draw.rect(tuval, (14, 14, 30), dikdortgen)
    pygame.draw.rect(tuval, renk, (x, y, int(genislik * max(0, min(1, oran))), yukseklik))
    pygame.draw.rect(tuval, (90, 100, 140), dikdortgen, 1)


def carpismali_hareket(konum, hareket, yaricap, duvarlar):
    """Konumu 'hareket' kadar kaydırır; duvara çarparsa durdurur (önce x, sonra y ekseni)."""
    konum.x += hareket.x
    kutu = pygame.Rect(int(konum.x - yaricap), int(konum.y - yaricap), int(2 * yaricap), int(2 * yaricap))
    for i in kutu.collidelistall(duvarlar):           # x yönünde çarpılan duvarlar
        duvar = duvarlar[i]
        if hareket.x > 0:
            konum.x = duvar.left - yaricap
        elif hareket.x < 0:
            konum.x = duvar.right + yaricap
        kutu.x = int(konum.x - yaricap)
    konum.y += hareket.y
    kutu = pygame.Rect(int(konum.x - yaricap), int(konum.y - yaricap), int(2 * yaricap), int(2 * yaricap))
    for i in kutu.collidelistall(duvarlar):           # y yönünde çarpılan duvarlar
        duvar = duvarlar[i]
        if hareket.y > 0:
            konum.y = duvar.top - yaricap
        elif hareket.y < 0:
            konum.y = duvar.bottom + yaricap
        kutu.y = int(konum.y - yaricap)


def duvar_icinde_mi(nokta, duvarlar, pay=2):
    """Nokta herhangi bir duvarın (binanın) içinde mi? (mermi ve doğma noktası kontrolü)"""
    return pygame.Rect(int(nokta[0]) - pay, int(nokta[1]) - pay, 2 * pay, 2 * pay).collidelist(duvarlar) != -1


# ----------------------------------------------------------------- dünya (harita)
def dunya_olustur():
    """Şehir bloklarını (binaları) üretir. Döner: (duvar listesi, [(bina dikdörtgeni, neon rengi), ...])"""
    uretici = random.Random(11)                       # sabit tohum: harita her açılışta aynı
    duvarlar = [                                      # dünyanın dört kenarındaki görünmez sınır duvarları
        pygame.Rect(-300, -300, DUNYA_G + 600, 300), pygame.Rect(-300, DUNYA_Y, DUNYA_G + 600, 300),
        pygame.Rect(-300, -300, 300, DUNYA_Y + 600), pygame.Rect(DUNYA_G, -300, 300, DUNYA_Y + 600),
    ]
    binalar = []
    for i in range(5):                                # 5 sütun x 4 satır bina bloğu
        for j in range(4):
            if uretici.random() < 0.16:               # bazı blokları boş bırak (meydan olsun)
                continue
            x, y = 200 + i * 500, 180 + j * 420
            kenar_payi = [uretici.randint(0, 28) for _ in range(4)]   # binayı biraz küçült (sokaklar hep açık kalır)
            bina = pygame.Rect(x + kenar_payi[0], y + kenar_payi[1],
                               300 - kenar_payi[0] - kenar_payi[2], 220 - kenar_payi[1] - kenar_payi[3])
            binalar.append((bina, uretici.choice([TURKUAZ, PEMBE, MOR, TURKUAZ, SARI])))
            duvarlar.append(bina)
    return duvarlar, binalar


def dunya_yuzeyi_olustur(binalar):
    """Tüm şehri (zemin, sokak çizgileri, neon binalar) tek bir büyük resme çizer; oyunda sadece görünen kısmı gösterilir."""
    yuzey = pygame.Surface((DUNYA_G, DUNYA_Y))
    yuzey.fill((8, 8, 21))
    for x in range(0, DUNYA_G, 100):                  # zemin ızgarası
        pygame.draw.line(yuzey, (15, 15, 36), (x, 0), (x, DUNYA_Y))
    for y in range(0, DUNYA_Y, 100):
        pygame.draw.line(yuzey, (15, 15, 36), (0, y), (DUNYA_G, y))
    for x in SOKAK_X:                                 # sokak şerit çizgileri
        for y in range(0, DUNYA_Y, 70):
            pygame.draw.rect(yuzey, (30, 30, 62), (x - 3, y, 6, 32))
    for y in SOKAK_Y:
        for x in range(0, DUNYA_G, 70):
            pygame.draw.rect(yuzey, (30, 30, 62), (x, y - 3, 32, 6))
    uretici = random.Random(5)
    for bina, renk in binalar:
        pygame.draw.rect(yuzey, (11, 9, 26), bina)
        for kalinlik, katsayi in ((14, 0.07), (9, 0.14), (5, 0.3)):   # dışa doğru neon ışıması
            pygame.draw.rect(yuzey, tuple(int(c * katsayi) for c in renk), bina.inflate(kalinlik * 2, kalinlik * 2), kalinlik)
        pygame.draw.rect(yuzey, renk, bina, 3)
        pygame.draw.rect(yuzey, tuple(int(c * 0.25) for c in renk), bina.inflate(-36, -36), 1)
        for pencere_x in range(bina.left + 18, bina.right - 24, 26):  # yanık pencereler
            for pencere_y in range(bina.top + 18, bina.bottom - 28, 32):
                if uretici.random() < 0.4:
                    pencere_renk = uretici.choice([renk, (255, 220, 140), (120, 200, 255)])
                    pygame.draw.rect(yuzey, tuple(int(c * 0.55) for c in pencere_renk), (pencere_x, pencere_y, 10, 14))
    return yuzey


def minyatur_harita_olustur(binalar):
    """Sağ alttaki mini harita için küçültülmüş şehir resmini üretir."""
    olcek = 0.06
    yuzey = pygame.Surface((int(DUNYA_G * olcek), int(DUNYA_Y * olcek)))
    yuzey.fill((8, 8, 20))
    for bina, renk in binalar:
        pygame.draw.rect(yuzey, tuple(int(c * 0.35) for c in renk),
                         (bina.x * olcek, bina.y * olcek, bina.w * olcek, bina.h * olcek))
    return yuzey


def vinyet_olustur():
    """Ekran kenarlarını karartan yumuşak gölge katmanı (sinematik görünüm)."""
    kucuk = pygame.Surface((110, 72), pygame.SRCALPHA)
    for x in range(110):
        for y in range(72):
            uzaklik = math.hypot((x - 55) / 55, (y - 36) / 36)     # merkezden uzaklık
            kucuk.set_at((x, y), (0, 0, 10, int(min(255, max(0, uzaklik - 0.55) * 340))))
    return pygame.transform.smoothscale(kucuk, (GENISLIK, YUKSEKLIK))


def tarama_cizgisi_olustur():
    """Eski ekran (CRT) hissi veren ince yatay çizgiler katmanı."""
    yuzey = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
    for y in range(0, YUKSEKLIK, 3):
        pygame.draw.line(yuzey, (0, 0, 0, 38), (0, y), (GENISLIK, y))
    return yuzey


# ----------------------------------------------------------------- oyun nesneleri
class Parcacik:
    """Patlama, kıvılcım, motor izi gibi kısa ömürlü ışıklı parçacık."""

    def __init__(self, konum, hiz, renk, omur, boyut, surtunme=0.95):
        self.konum, self.hiz = Vek(konum), Vek(hiz)   # yeri ve hızı
        self.renk, self.omur, self.maks = renk, omur, omur   # omur: kalan süre, maks: başlangıç süresi
        self.boyut, self.surtunme = boyut, surtunme   # parlama boyutu, yavaşlama oranı

    def guncelle(self, gecen):
        """Hareket ettirir, yavaşlatır, ömrünü azaltır. Hâlâ yaşıyorsa True döner."""
        self.konum += self.hiz * gecen
        self.hiz *= self.surtunme ** (gecen * 60)
        self.omur -= gecen
        return self.omur > 0

    def ciz(self, yuzey, kamera):
        parlama_ciz(yuzey, self.renk, self.konum - kamera, self.boyut * (self.omur / self.maks) + 2)


class Mermi:
    """Oyuncunun ya da düşmanın attığı mermi."""

    def __init__(self, konum, hiz, hasar, dost, renk, omur=1.5, yaricap=4):
        self.konum, self.hiz, self.hasar = Vek(konum), Vek(hiz), hasar
        self.dost, self.renk, self.omur, self.yaricap = dost, renk, omur, yaricap   # dost: oyuncunun mermisi mi?

    def guncelle(self, gecen, oyun):
        """İlerletir. Duvara çarparsa veya ömrü biterse False (silinsin) döner."""
        self.konum += self.hiz * gecen
        self.omur -= gecen
        if self.omur <= 0 or duvar_icinde_mi(self.konum, oyun.duvarlar):
            if self.omur > 0:   # duvara çarptı: kıvılcım çıkar
                for _ in range(4):
                    oyun.parcaciklar.append(Parcacik(self.konum, Vek(random.uniform(-90, 90), random.uniform(-90, 90)),
                                                     self.renk, 0.3, 6))
            return False
        return True

    def ciz(self, yuzey, kamera):
        konum = self.konum - kamera
        parlama_ciz(yuzey, self.renk, konum, self.yaricap * 3.2)
        pygame.draw.line(yuzey, self.renk, konum, konum - self.hiz * 0.025, max(2, self.yaricap - 1))   # kuyruk izi
        pygame.draw.circle(yuzey, BEYAZ, konum, max(2, self.yaricap - 2))


class Esya:
    """Düşmandan düşen toplanabilir eşya: 'can' (kırmızı artı) veya 'enerji' (turkuaz şimşek)."""

    def __init__(self, konum, tur):
        self.konum, self.tur, self.omur, self.zaman = Vek(konum), tur, 14.0, 0.0
        self.renk = KIRMIZI if tur == "can" else TURKUAZ

    def guncelle(self, gecen, oyun):
        """Yaklaşınca oyuncuya doğru çekilir, değince toplanır. Hâlâ yerdeyse True döner."""
        self.zaman += gecen
        self.omur -= gecen
        fark = oyun.oyuncu.konum - self.konum
        if 0 < fark.length() < 150:                      # mıknatıs etkisi
            self.konum += fark.normalize() * 280 * gecen
        if fark.length() < 26:                           # toplandı
            if self.tur == "can":
                oyun.oyuncu.can = min(100, oyun.oyuncu.can + 25)
                oyun.yazi_ekle(self.konum, "+25 SAĞLIK", KIRMIZI)
            else:
                oyun.oyuncu.enerji = min(100, oyun.oyuncu.enerji + 45)
                oyun.yazi_ekle(self.konum, "+45 ENERJİ", TURKUAZ)
            oyun.halka_ekle(self.konum, self.renk, 40)
            return False
        return self.omur > 0

    def ciz(self, yuzey, kamera):
        konum = self.konum - kamera + Vek(0, math.sin(self.zaman * 4) * 3)   # hafifçe yukarı aşağı süzülür
        parlama_ciz(yuzey, self.renk, konum, 24)
        pygame.draw.circle(yuzey, self.renk, konum, 12, 2)
        if self.tur == "can":
            pygame.draw.rect(yuzey, BEYAZ, (konum.x - 6, konum.y - 2, 12, 4))
            pygame.draw.rect(yuzey, BEYAZ, (konum.x - 2, konum.y - 6, 4, 12))
        else:
            cokgen_ciz(yuzey, BEYAZ, [(3, -8), (-5, 1), (0, 1), (-3, 8), (5, -1), (0, -1)], konum, 0, 0)


class Terminal:
    """Hacklenecek bilgisayar terminali. E tuşuna basılı tutunca ilerleme dolar."""

    def __init__(self, konum):
        self.konum = Vek(konum)
        self.ilerleme = 0.0       # hackleme ilerlemesi: 0 ile 1 arası
        self.bitti = False        # hacklendi mi?
        self.yakin = False        # oyuncu yeterince yakın mı?

    def ciz(self, yuzey, kamera, zaman):
        konum = self.konum - kamera
        renk = YESIL if self.bitti else SARI
        parlama_ciz(yuzey, renk, konum, 46)
        pygame.draw.rect(yuzey, (12, 12, 28), (konum.x - 20, konum.y - 20, 40, 40))
        pygame.draw.rect(yuzey, renk, (konum.x - 20, konum.y - 20, 40, 40), 3)
        pygame.draw.rect(yuzey, renk, (konum.x - 12, konum.y - 12, 24, 14), 1)
        for i in range(3):
            pygame.draw.rect(yuzey, renk, (konum.x - 12 + i * 9, konum.y + 6, 6, 5))
        if self.ilerleme > 0.01 and not self.bitti:     # ilerleme halkası
            pygame.draw.arc(yuzey, BEYAZ, (konum.x - 34, konum.y - 34, 68, 68),
                            math.pi / 2 - math.tau * self.ilerleme, math.pi / 2, 5)
        if self.yakin and not self.bitti:
            yazi_yaz(yazi_k, "[E] BASILI TUT: HACKLE", SARI, (konum.x, konum.y - 52), ortala=True)


class Dusman:
    """Robot düşman. Türler: dron (kamikaze), nisanci (seri atış), agir (saçma gibi yelpaze), patron (final)."""

    def __init__(self, tur, konum, alarm=True):
        can, surat, yaricap, renk, puan = DUSMAN_OZELLIKLERI[tur]
        self.tur, self.can, self.maks_can, self.surat = tur, can, can, surat      # can: kalan, maks_can: başlangıç
        self.yaricap, self.renk, self.puan = yaricap, renk, puan
        self.konum, self.alarm = Vek(konum), alarm     # alarm: oyuncuyu fark etti mi (False ise etrafta gezinir)
        self.yanip_sonme = 0.0                         # vurulunca kısa süre beyaz yanar
        self.zaman = random.uniform(0, 9)              # animasyon / hareket için sayaç
        self.yon_acisi = 0.0                           # baktığı yön (radyan)
        self.bekleme = random.uniform(0.6, 1.6)        # bir sonraki ateşe kalan süre
        self.salvo, self.salvo_bekleme = 0, 0.0        # seri atışta kalan mermi / mermiler arası süre
        self.halka_bekleme, self.cagri_bekleme = 3.0, 6.0   # patron: halka atışı ve dron çağırma sayaçları
        self.gezinme_yonu, self.gezinme_suresi = Vek(0, 0), 0.0   # alarmsızken rastgele yürüyüş

    def hasar_al(self, hasar):
        self.can -= hasar
        self.yanip_sonme = 0.07
        self.alarm = True

    def guncelle(self, oyun, gecen):
        """Yapay zekâ: oyuncuyu kovalar, türüne göre ateş eder."""
        oyuncu = oyun.oyuncu
        hedef_vektor = oyuncu.konum - self.konum
        mesafe = hedef_vektor.length() or 0.001
        yon = hedef_vektor / mesafe                    # oyuncuya doğru birim vektör
        self.zaman += gecen
        self.yanip_sonme = max(0, self.yanip_sonme - gecen)
        if not self.alarm:                             # henüz fark etmedi: etrafta dolaş
            if mesafe < 480:
                self.alarm = True
            else:
                self.gezinme_suresi -= gecen
                if self.gezinme_suresi <= 0:
                    self.gezinme_suresi = random.uniform(1.5, 3.5)
                    aci = random.uniform(0, math.tau)
                    self.gezinme_yonu = (Vek(math.cos(aci), math.sin(aci)) * 40
                                         if random.random() < 0.7 else Vek(0, 0))
                carpismali_hareket(self.konum, self.gezinme_yonu * gecen, self.yaricap, oyun.duvarlar)
                if self.gezinme_yonu.length_squared():
                    self.yon_acisi = math.atan2(self.gezinme_yonu.y, self.gezinme_yonu.x)
                return
        self.yon_acisi = math.atan2(yon.y, yon.x)
        namlu = self.konum + yon * (self.yaricap + 6)  # mermilerin çıkış noktası
        if self.tur == "dron":
            yanlama = Vek(-yon.y, yon.x) * math.sin(self.zaman * 5) * 0.5   # zikzak
            carpismali_hareket(self.konum, (yon + yanlama) * self.surat * gecen, self.yaricap, oyun.duvarlar)
            if mesafe < self.yaricap + oyuncu.yaricap + 4:     # çarptı: kendini patlatır
                oyun.oyuncu_hasar_al(18)
                oyun.patlat(self.konum, self.renk, 22)
                self.can = 0
        elif self.tur == "nisanci":
            istenen = 1 if mesafe > 380 else -1 if mesafe < 250 else 0   # uzaksa yaklaş, yakınsa uzaklaş
            hareket = yon * istenen + Vek(-yon.y, yon.x) * math.sin(self.zaman * 1.3) * 0.8   # yanlara kayma
            carpismali_hareket(self.konum, hareket * self.surat * gecen, self.yaricap, oyun.duvarlar)
            self.bekleme -= gecen
            if self.bekleme <= 0:
                if mesafe < 700 and oyun.gorus_hatti_var_mi(self.konum, oyuncu.konum):
                    self.bekleme, self.salvo, self.salvo_bekleme = 1.7, 3, 0   # 3'lü seri atış başlat
                else:
                    self.bekleme = 0.25
            if self.salvo > 0:
                self.salvo_bekleme -= gecen
                if self.salvo_bekleme <= 0:
                    self.salvo_bekleme, self.salvo = 0.13, self.salvo - 1
                    oyun.dusman_ates_et(namlu, self.yon_acisi + random.uniform(-0.06, 0.06), 430, 8, TURUNCU)
        elif self.tur == "agir":
            if mesafe > 280:
                carpismali_hareket(self.konum, yon * self.surat * gecen, self.yaricap, oyun.duvarlar)
            self.bekleme -= gecen
            if self.bekleme <= 0:
                if mesafe < 750 and oyun.gorus_hatti_var_mi(self.konum, oyuncu.konum):
                    self.bekleme = 2.3
                    for i in range(-2, 3):                      # 5'li yelpaze atış
                        oyun.dusman_ates_et(namlu, self.yon_acisi + i * 0.17, 300, 10, MOR, 6)
                else:
                    self.bekleme = 0.3
        else:  # patron
            evre = 1 if self.can > 600 else 2 if self.can > 300 else 3    # can azaldıkça evre artar
            istenen = 1 if mesafe > 390 else -1 if mesafe < 270 else 0
            hareket = yon * istenen + Vek(-yon.y, yon.x) * math.sin(self.zaman * 0.7) * 0.9
            carpismali_hareket(self.konum, hareket * self.surat * (1 + 0.25 * (evre - 1)) * gecen,
                               self.yaricap, oyun.duvarlar)
            self.bekleme -= gecen
            if self.bekleme <= 0:                               # oyuncuya nişanlı yelpaze
                self.bekleme = 1.1 if evre < 3 else 0.8
                adet = 3 if evre == 1 else 5
                for i in range(adet):
                    oyun.dusman_ates_et(self.konum + yon * 60, self.yon_acisi + (i - (adet - 1) / 2) * 0.16, 390, 9, PEMBE)
            self.halka_bekleme -= gecen
            if self.halka_bekleme <= 0:                         # 360 derece mermi halkası
                self.halka_bekleme = 3.4 if evre < 3 else 2.6
                for i in range(20):
                    oyun.dusman_ates_et(self.konum.copy(), self.zaman + i * math.tau / 20, 230, 9, MOR, 6)
                oyun.halka_ekle(self.konum, PEMBE, 160)
            if evre >= 2:                                       # 2. evreden itibaren dron çağırır
                self.cagri_bekleme -= gecen
                if self.cagri_bekleme <= 0:
                    self.cagri_bekleme = 7
                    for _ in range(2):
                        if len(oyun.dusmanlar) < 14:
                            oyun.dusmanlar.append(Dusman("dron", self.konum + Vek(random.uniform(-70, 70), random.uniform(-70, 70))))
            if mesafe < self.yaricap + oyuncu.yaricap:          # temas hasarı
                oyun.oyuncu_hasar_al(20)

    def ciz(self, yuzey, kamera):
        konum = self.konum - kamera
        if not (-120 < konum.x < GENISLIK + 120 and -120 < konum.y < YUKSEKLIK + 120):   # ekran dışındaysa çizme
            return
        renk = BEYAZ if self.yanip_sonme > 0 else self.renk
        yaricap, aci = self.yaricap, self.yon_acisi
        yon = Vek(math.cos(aci), math.sin(aci))
        parlama_ciz(yuzey, self.renk, konum, yaricap * 2.4)
        if self.tur == "dron":
            cokgen_ciz(yuzey, renk, [(yaricap, 0), (0, -yaricap * .8), (-yaricap, 0), (0, yaricap * .8)], konum, aci, 3)
            pygame.draw.circle(yuzey, BEYAZ, konum + yon * yaricap * .35, 3)   # göz
        elif self.tur == "nisanci":
            cokgen_ciz(yuzey, renk, duzgun_cokgen(6, yaricap), konum, aci, 3)
            pygame.draw.line(yuzey, renk, konum, konum + yon * (yaricap + 11), 5)   # namlu
            pygame.draw.circle(yuzey, (10, 10, 20), konum, yaricap * .5)
            pygame.draw.circle(yuzey, renk, konum, yaricap * .5, 2)
        elif self.tur == "agir":
            cokgen_ciz(yuzey, renk, duzgun_cokgen(8, yaricap), konum, aci, 4)
            cokgen_ciz(yuzey, renk, duzgun_cokgen(8, yaricap * .6), konum, -aci, 2)
            for sapma in (-0.35, 0, 0.35):                      # üç namlu
                yon_n = Vek(math.cos(aci + sapma), math.sin(aci + sapma))
                pygame.draw.line(yuzey, renk, konum + yon_n * yaricap * .5, konum + yon_n * (yaricap + 9), 4)
        else:
            nabiz = 1 + math.sin(self.zaman * 4) * .06           # nefes alıp veren çekirdek
            cokgen_ciz(yuzey, renk, duzgun_cokgen(8, yaricap * nabiz), konum, self.zaman * .5, 4)
            cokgen_ciz(yuzey, renk, duzgun_cokgen(3, yaricap * .75), konum, -self.zaman, 3)
            cokgen_ciz(yuzey, renk, duzgun_cokgen(3, yaricap * .75), konum, -self.zaman + math.pi, 3)
            pygame.draw.circle(yuzey, BEYAZ, konum, 12 + math.sin(self.zaman * 6) * 3)
            for i in range(4):                                  # etrafında dönen 4 küre
                a = self.zaman * 1.5 + i * math.pi / 2
                pygame.draw.circle(yuzey, renk, konum + Vek(math.cos(a), math.sin(a)) * (yaricap + 16), 6, 2)
        if self.tur != "patron" and self.can < self.maks_can:   # küçük can çubuğu
            pygame.draw.rect(yuzey, (40, 10, 20), (konum.x - yaricap, konum.y - yaricap - 12, yaricap * 2, 4))
            pygame.draw.rect(yuzey, KIRMIZI, (konum.x - yaricap, konum.y - yaricap - 12, yaricap * 2 * self.can / self.maks_can, 4))


class Oyuncu:
    """Oyuncunun karakteri: hareket, atılma (dash), ateş etme, çizim."""
    yaricap = 13   # çarpışma yarıçapı

    def __init__(self):
        self.konum = Vek(600, 500)
        self.hiz, self.nisan = Vek(0, 0), Vek(1, 0)       # hareket hızı, fareye doğru nişan yönü
        self.can, self.enerji, self.silah = 100.0, 100.0, 0   # silah: SILAHLAR listesindeki sıra
        self.ates_bekleme = self.atilma_suresi = self.atilma_bekleme = self.dokunulmazlik = 0.0
        self.atilma_yonu = Vek(1, 0)

    def atilma(self, oyun):
        """SPACE: kısa süre çok hızlı ve dokunulmaz fırlar."""
        if self.atilma_bekleme > 0 or self.atilma_suresi > 0:
            return
        self.atilma_yonu = self.hiz.normalize() if self.hiz.length() > 30 else Vek(self.nisan)
        self.atilma_suresi, self.atilma_bekleme = 0.16, 1.1
        self.dokunulmazlik = max(self.dokunulmazlik, 0.28)
        oyun.halka_ekle(self.konum, TURKUAZ, 70)

    def ates_et(self, oyun):
        """Seçili silahla ateş eder; enerji yetmiyorsa ateş etmez."""
        isim, aralik, maliyet, renk = SILAHLAR[self.silah]
        if self.enerji < maliyet:
            return
        self.enerji -= maliyet
        self.ates_bekleme = aralik
        temel_aci = math.atan2(self.nisan.y, self.nisan.x)
        namlu = self.konum + self.nisan * 22               # mermi çıkış noktası
        sarsinti = 1.0
        if self.silah == 0:      # plazma: tek hızlı mermi
            oyun.mermiler.append(Mermi(namlu, self.nisan * 950, 14, True, renk, 1.1, 4))
        elif self.silah == 1:    # saçma: 8 saçma, kısa menzil
            for _ in range(8):
                aci = temel_aci + random.uniform(-0.3, 0.3)
                oyun.mermiler.append(Mermi(namlu, Vek(math.cos(aci), math.sin(aci)) * random.uniform(720, 900), 9, True, renk, 0.42, 3))
            sarsinti = 5
        else:                    # lazer: çok seri, düşük hasarlı
            aci = temel_aci + random.uniform(-0.02, 0.02)
            oyun.mermiler.append(Mermi(namlu, Vek(math.cos(aci), math.sin(aci)) * 1400, 6, True, renk, 0.8, 3))
            sarsinti = 0.7
        oyun.sarsinti = max(oyun.sarsinti, sarsinti)
        oyun.parcaciklar.append(Parcacik(namlu, Vek(0, 0), renk, 0.09, 20, 0.9))   # namlu parlaması

    def guncelle(self, oyun, gecen, tuslar, fare):
        """Hareket, nişan, atılma ve otomatik ateşi işler."""
        hareket = Vek((tuslar[pygame.K_d] or tuslar[pygame.K_RIGHT]) - (tuslar[pygame.K_a] or tuslar[pygame.K_LEFT]),
                      (tuslar[pygame.K_s] or tuslar[pygame.K_DOWN]) - (tuslar[pygame.K_w] or tuslar[pygame.K_UP]))
        fark = fare - self.konum
        if fark.length() > 1:
            self.nisan = fark.normalize()
        self.ates_bekleme -= gecen
        self.atilma_bekleme = max(0, self.atilma_bekleme - gecen)
        self.dokunulmazlik = max(0, self.dokunulmazlik - gecen)
        if self.atilma_suresi > 0:                        # atılma sırasında hızlı ve izli hareket
            self.atilma_suresi -= gecen
            carpismali_hareket(self.konum, self.atilma_yonu * 900 * gecen, self.yaricap, oyun.duvarlar)
            oyun.parcaciklar.append(Parcacik(self.konum, Vek(0, 0), TURKUAZ, 0.35, 16, 0.9))
        else:
            if hareket.length() > 0:
                hareket = hareket.normalize()
            self.hiz = self.hiz.lerp(hareket * 270, min(1, 14 * gecen))   # yumuşak hızlanma
            carpismali_hareket(self.konum, self.hiz * gecen, self.yaricap, oyun.duvarlar)
        self.enerji = min(100, self.enerji + 5 * gecen)   # enerji yavaşça dolar
        if pygame.mouse.get_pressed()[0] and self.ates_bekleme <= 0 and self.atilma_suresi <= 0:
            self.ates_et(oyun)

    def ciz(self, yuzey, kamera):
        if self.dokunulmazlik > 0 and self.atilma_suresi <= 0 and int(self.dokunulmazlik * 30) % 2:
            return                                         # hasar alınca yanıp sönme
        konum = self.konum - kamera
        parlama_ciz(yuzey, TURKUAZ, konum, 46)
        pygame.draw.circle(yuzey, (8, 28, 44), konum, self.yaricap)
        pygame.draw.circle(yuzey, TURKUAZ, konum, self.yaricap, 3)
        pygame.draw.line(yuzey, SILAHLAR[self.silah][3], konum, konum + self.nisan * 26, 6)   # silah namlusu
        pygame.draw.circle(yuzey, BEYAZ, konum + self.nisan * 5, 4)


# ----------------------------------------------------------------- oyunun kendisi
class Oyun:
    """Tüm oyun durumunu tutar: menü, oynama, duraklatma, bitiş ekranları ve görev akışı."""

    def __init__(self):
        self.duvarlar, self.binalar = dunya_olustur()
        self.dunya = dunya_yuzeyi_olustur(self.binalar)           # önceden çizilmiş büyük şehir resmi
        self.harita_kucuk = minyatur_harita_olustur(self.binalar)
        self.vinyet, self.tarama = vinyet_olustur(), tarama_cizgisi_olustur()
        self.yagmur = [[random.uniform(0, GENISLIK), random.uniform(0, YUKSEKLIK),
                        random.uniform(700, 1000), random.uniform(10, 22)] for _ in range(140)]   # [x, y, hız, uzunluk]
        try:
            self.rekor = int(open(REKOR_DOSYASI).read().strip())
        except Exception:
            self.rekor = 0
        self.durum, self.zaman, self.goruntu_kopya, self.kamera = "menu", 0.0, None, Vek(0, 0)
        # durum: "menu" | "oyun" | "duraklat" | "bitti" | "kazandi"
        self.sifirla()

    def sifirla(self):
        """Yeni oyun için her şeyi başa alır."""
        self.oyuncu = Oyuncu()
        self.dusmanlar, self.mermiler, self.parcaciklar = [], [], []
        self.esyalar, self.halkalar, self.yazilar = [], [], []     # halkalar: şok dalgası, yazilar: uçan puan yazıları
        self.terminaller = [Terminal(Vek(2100, 500)), Terminal(Vek(1100, 920)), Terminal(Vek(600, 1340))]
        self.gorev = self.hacklenen = self.oldurme = self.gorev_oldurme = self.skor = 0
        self.sarsinti = self.hasar_efekti = self.zafer_sayaci = self.sure = 0.0
        self.afis = ("", 0.0, BEYAZ)                               # ekran ortasındaki büyük yazı: (metin, süre, renk)
        self.dogma_sayaci = 3.0                                    # yeni düşman doğmasına kalan süre
        self.kamera = self.oyuncu.konum - Vek(GENISLIK / 2, YUKSEKLIK / 2)
        for _ in range(14):                                        # başlangıçta sokaklarda devriye gezen robotlar
            self.dusman_dogur(alarm=False, en_az_uzaklik=450)

    # --- küçük yardımcılar
    def yazi_ekle(self, konum, metin, renk):
        """Konumdan yukarı süzülüp kaybolan küçük yazı (örn. +100)."""
        self.yazilar.append([Vek(konum), metin, 1.0, renk])

    def halka_ekle(self, konum, renk, boyut):
        """Genişleyip sönen şok dalgası halkası ekler."""
        self.halkalar.append([Vek(konum), 6.0, boyut, 0.5, 0.5, renk])   # [konum, başlangıç, bitiş yarıçapı, kalan süre, toplam süre, renk]

    def afis_ayarla(self, metin, renk=TURKUAZ, sure=3.0):
        """Ekran ortasında büyük bir duyuru yazısı gösterir."""
        self.afis = (metin, sure, renk)

    def patlat(self, konum, renk, adet=30, hiz=320):
        """Parçacık + halka + ekran sarsıntısı ile patlama efekti."""
        for _ in range(adet):
            aci, ivme = random.uniform(0, math.tau), random.uniform(40, hiz)
            self.parcaciklar.append(Parcacik(konum, Vek(math.cos(aci), math.sin(aci)) * ivme, renk,
                                             random.uniform(0.3, 0.9), random.uniform(7, 15)))
        self.halka_ekle(konum, renk, 50 + adet)
        self.sarsinti = max(self.sarsinti, min(16, adet / 3))

    def gorus_hatti_var_mi(self, a, b):
        """a ile b arasında duvar yoksa True (düşman ancak görüyorsa ateş eder)."""
        fark = b - a
        adim = int(fark.length() // 30) + 1
        return not any(duvar_icinde_mi(a + fark * (i / adim), self.duvarlar) for i in range(1, adim))

    def dusman_ates_et(self, konum, aci, hiz, hasar, renk, yaricap=5):
        """Düşman mermisi oluşturur."""
        self.mermiler.append(Mermi(konum, Vek(math.cos(aci), math.sin(aci)) * hiz, hasar, False, renk, 4.0, yaricap))

    def sokak_noktasi(self, en_az_uzaklik=700, yakin=None):
        """Sokaklar üzerinde, oyuncudan yeterince uzak, duvar içinde olmayan rastgele bir nokta bulur."""
        for _ in range(60):
            if random.random() < 0.5:
                nokta = Vek(random.choice(SOKAK_X) + random.uniform(-70, 70), random.uniform(60, DUNYA_Y - 60))
            else:
                nokta = Vek(random.uniform(60, DUNYA_G - 60), random.choice(SOKAK_Y) + random.uniform(-70, 70))
            if duvar_icinde_mi(nokta, self.duvarlar, 30) or (nokta - self.oyuncu.konum).length() < en_az_uzaklik:
                continue
            if yakin is not None and (nokta - yakin).length() > 650:   # 'yakin' verilmişse ona yakın olsun
                continue
            return nokta
        return None

    def dusman_dogur(self, alarm=True, en_az_uzaklik=700, yakin=None):
        """Göreve göre rastgele türde bir düşman doğurur."""
        nokta = self.sokak_noktasi(en_az_uzaklik, yakin)
        if nokta is None:
            return
        agirliklar = [(4, 3, 0.5), (3, 4, 1.5), (3, 4, 2.5), (3, 4, 2.5)][self.gorev]   # (dron, nişancı, ağır) olasılıkları
        tur = random.choices(["dron", "nisanci", "agir"], agirliklar)[0]
        self.dusmanlar.append(Dusman(tur, nokta, alarm))

    def patron(self):
        """Sahnedeki patronu döndürür (yoksa None)."""
        return next((d for d in self.dusmanlar if d.tur == "patron"), None)

    def oyuncu_hasar_al(self, hasar):
        """Oyuncuya hasar verir; can biterse oyun biter."""
        oyuncu = self.oyuncu
        if oyuncu.dokunulmazlik > 0 or self.zafer_sayaci > 0 or self.durum != "oyun":
            return
        oyuncu.can -= hasar
        oyuncu.dokunulmazlik = 0.3
        self.sarsinti = max(self.sarsinti, 10)
        self.hasar_efekti = 0.4
        for _ in range(10):
            self.parcaciklar.append(Parcacik(oyuncu.konum, Vek(random.uniform(-200, 200), random.uniform(-200, 200)), KIRMIZI, 0.5, 9))
        if oyuncu.can <= 0:
            self.bitir("bitti")

    def bitir(self, durum):
        """Oyunu 'bitti' ya da 'kazandi' durumuna alır ve rekoru kaydeder."""
        self.durum = durum
        self.goruntu_kopya = None
        if self.skor > self.rekor:
            self.rekor = self.skor
            try:
                open(REKOR_DOSYASI, "w").write(str(self.rekor))
            except Exception:
                pass

    def oldur(self, dusman):
        """Düşmanı yok eder: puan, patlama, eşya düşürme; patronsa zafer sayacını başlatır."""
        self.dusmanlar.remove(dusman)
        self.skor += dusman.puan
        self.oldurme += 1
        if self.gorev == 1:
            self.gorev_oldurme += 1
        self.patlat(dusman.konum, dusman.renk, 60 if dusman.tur == "patron" else 26 + dusman.yaricap // 2)
        self.yazi_ekle(dusman.konum, f"+{dusman.puan}", dusman.renk)
        if dusman.tur == "patron":
            for _ in range(14):
                self.patlat(dusman.konum + Vek(random.uniform(-80, 80), random.uniform(-80, 80)),
                            random.choice([PEMBE, MOR, SARI]), 40)
            self.dusmanlar.clear()
            self.mermiler = [m for m in self.mermiler if m.dost]
            self.zafer_sayaci = 2.4
            self.afis_ayarla("ÇEKİRDEK ÇÖKTÜ!", PEMBE, 3)
        elif random.random() < 0.3:                        # %30 ihtimalle eşya düşer
            self.esyalar.append(Esya(dusman.konum, random.choice(["can", "can", "enerji"])))

    def gorevi_tamamla(self):
        """Mevcut görevi bitirir, ödül verir, sonraki göreve geçer."""
        self.skor += 500
        self.oyuncu.can = min(100, self.oyuncu.can + 50)
        self.oyuncu.enerji = 100
        self.gorev += 1
        self.gorev_oldurme = 0
        self.afis_ayarla(f"GÖREV {self.gorev} TAMAMLANDI", YESIL)
        if self.gorev == 3:                                # son görev: patron doğar
            self.dusmanlar.clear()
            self.dusmanlar.append(Dusman("patron", Vek(2100, 900), True))
            self.afis_ayarla("ANA ÇEKİRDEK UYANDI!", PEMBE, 3.5)
            self.sarsinti = 14

    def hedef_konum(self):
        """Ekrandaki sarı ok için şu anki görev hedefinin yerini döndürür."""
        if self.gorev == 0:
            kalan = [t.konum for t in self.terminaller if not t.bitti]
            return min(kalan, key=lambda q: (q - self.oyuncu.konum).length()) if kalan else None
        if self.gorev == 2:
            return ASANSOR_KONUM
        if self.gorev == 3 and self.patron():
            return self.patron().konum
        return None

    # --- olaylar
    def baslat(self):
        """Menüden oyunu başlatır."""
        self.sifirla()
        self.durum, self.goruntu_kopya = "oyun", None
        self.afis_ayarla("GÖREV 1: " + GOREVLER[0], TURKUAZ, 3.5)

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
                    self.baslat()
                elif tus == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif durum == "oyun":
                if tus in (pygame.K_ESCAPE, pygame.K_p):
                    self.durum, self.goruntu_kopya = "duraklat", None
                elif tus == pygame.K_SPACE:
                    self.oyuncu.atilma(self)
                elif tus in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.oyuncu.silah = tus - pygame.K_1
                elif tus == pygame.K_TAB:
                    self.oyuncu.silah = (self.oyuncu.silah + 1) % 3
            elif durum == "duraklat":
                if tus in (pygame.K_ESCAPE, pygame.K_p):
                    self.durum = "oyun"
                elif tus == pygame.K_q:
                    self.durum = "menu"
            elif durum in ("bitti", "kazandi"):
                if tus == pygame.K_r:
                    self.baslat()
                elif tus in (pygame.K_ESCAPE, pygame.K_m):
                    self.durum = "menu"
        elif olay.type == pygame.MOUSEBUTTONDOWN and durum == "menu":
            self.baslat()
        elif olay.type == pygame.MOUSEWHEEL and durum == "oyun":
            self.oyuncu.silah = (self.oyuncu.silah - olay.y) % 3

    # --- mantık güncellemesi
    def guncelle(self, gecen):
        """Bir karelik oyun mantığı: hareket, hackleme, görev ilerleyişi, çarpışmalar, kamera."""
        oyuncu, tuslar = self.oyuncu, pygame.key.get_pressed()
        self.sure += gecen
        fare = Vek(pygame.mouse.get_pos()) + self.kamera      # fare konumunun dünyadaki karşılığı
        oyuncu.guncelle(self, gecen, tuslar, fare)

        # hackleme
        hacklenen_terminal = None
        for terminal in self.terminaller:
            terminal.yakin = (terminal.konum - oyuncu.konum).length() < 90
        if self.gorev == 0 and tuslar[pygame.K_e]:
            hacklenen_terminal = next((t for t in self.terminaller if t.yakin and not t.bitti), None)
        for terminal in self.terminaller:
            if terminal is hacklenen_terminal:
                terminal.ilerleme += gecen / 3.0                  # 3 saniyede tamamlanır
                if random.random() < 0.5:
                    self.parcaciklar.append(Parcacik(terminal.konum, Vek(random.uniform(-80, 80), random.uniform(-80, 80)), SARI, 0.4, 6))
                if terminal.ilerleme >= 1:
                    terminal.bitti = True
                    self.hacklenen += 1
                    self.skor += 200
                    self.patlat(terminal.konum, YESIL, 30)
                    self.afis_ayarla(f"TERMİNAL HACKLENDİ  {self.hacklenen}/3", YESIL, 2.2)
                    for _ in range(3):                            # alarm: yakında 3 robot doğar
                        self.dusman_dogur(True, 300, terminal.konum)
            elif not terminal.bitti:
                terminal.ilerleme = max(0, terminal.ilerleme - gecen * 0.3)

        # görev ilerleyişi
        if self.zafer_sayaci <= 0:
            if self.gorev == 0 and self.hacklenen >= 3:
                self.gorevi_tamamla()
            elif self.gorev == 1 and self.gorev_oldurme >= 20:
                self.gorevi_tamamla()
            elif self.gorev == 2 and (oyuncu.konum - ASANSOR_KONUM).length() < 90:
                self.gorevi_tamamla()

        # takviye düşmanlar: (doğma aralığı sn, aynı anda en fazla düşman)
        aralik, ust_sinir = [(6, 12), (2.0, 16), (2.6, 16), (99, 0)][self.gorev]
        self.dogma_sayaci -= gecen
        if self.dogma_sayaci <= 0:
            self.dogma_sayaci = aralik
            if len(self.dusmanlar) < ust_sinir:
                self.dusman_dogur()

        # düşmanlar
        for dusman in self.dusmanlar:
            dusman.guncelle(self, gecen)
        liste = self.dusmanlar
        for i in range(len(liste)):                               # düşmanlar birbirinin üstüne binmesin
            for j in range(i + 1, len(liste)):
                a, b = liste[i], liste[j]
                fark = a.konum - b.konum
                uzaklik, en_az = fark.length(), a.yaricap + b.yaricap
                if 0 < uzaklik < en_az:
                    itme = fark / uzaklik * (en_az - uzaklik) * 0.5
                    carpismali_hareket(a.konum, itme, a.yaricap, self.duvarlar)
                    carpismali_hareket(b.konum, -itme, b.yaricap, self.duvarlar)

        # mermiler
        hayatta = []
        for mermi in self.mermiler:
            if not mermi.guncelle(gecen, self):
                continue
            if mermi.dost:                                        # oyuncu mermisi bir düşmana değdi mi?
                vurulan = next((d for d in self.dusmanlar if (d.konum - mermi.konum).length() < d.yaricap + mermi.yaricap), None)
                if vurulan:
                    vurulan.hasar_al(mermi.hasar)
                    for _ in range(3):
                        self.parcaciklar.append(Parcacik(mermi.konum, Vek(random.uniform(-150, 150), random.uniform(-150, 150)), mermi.renk, 0.3, 6))
                    continue
            elif (mermi.konum - oyuncu.konum).length() < oyuncu.yaricap + mermi.yaricap:   # düşman mermisi oyuncuya değdi
                self.oyuncu_hasar_al(mermi.hasar)
                if oyuncu.dokunulmazlik > 0 and oyuncu.atilma_suresi > 0:   # atılırken içinden geçer
                    hayatta.append(mermi)
                continue
            hayatta.append(mermi)
        self.mermiler = hayatta
        for dusman in [d for d in self.dusmanlar if d.can <= 0]:
            self.oldur(dusman)

        self.esyalar = [e for e in self.esyalar if e.guncelle(gecen, self)]
        self.parcaciklar = [p for p in self.parcaciklar if p.guncelle(gecen)]
        for halka in self.halkalar:
            halka[3] -= gecen
        self.halkalar = [h for h in self.halkalar if h[3] > 0]
        for yazi in self.yazilar:
            yazi[2] -= gecen
            yazi[0].y -= 40 * gecen
        self.yazilar = [y for y in self.yazilar if y[2] > 0]
        self.sarsinti = max(0, self.sarsinti - 35 * gecen)
        self.hasar_efekti = max(0, self.hasar_efekti - gecen)
        metin, kalan, renk = self.afis
        self.afis = (metin, max(0, kalan - gecen), renk)
        if self.zafer_sayaci > 0:                                 # patron öldü: ekranda havai fişek patlamaları
            self.zafer_sayaci -= gecen
            if random.random() < 0.3:
                self.patlat(self.kamera + Vek(random.uniform(0, GENISLIK), random.uniform(0, YUKSEKLIK)),
                            random.choice([PEMBE, SARI, TURKUAZ]), 20)
            if self.zafer_sayaci <= 0:
                self.skor += 2000
                self.bitir("kazandi")

        # kamera oyuncuyu yumuşakça takip eder
        hedef = oyuncu.konum - Vek(GENISLIK / 2, YUKSEKLIK / 2)
        self.kamera += (hedef - self.kamera) * min(1, 8 * gecen)
        self.kamera.x = max(0, min(DUNYA_G - GENISLIK, self.kamera.x))
        self.kamera.y = max(0, min(DUNYA_Y - YUKSEKLIK, self.kamera.y))

    # --- çizim
    def efektleri_ciz(self, gecen):
        """Yağmur, vinyet ve tarama çizgisi gibi ekran üstü efektleri çizer."""
        for damla in self.yagmur:
            damla[1] += damla[2] * gecen
            damla[0] -= damla[2] * 0.12 * gecen
            if damla[1] > YUKSEKLIK:
                damla[0], damla[1] = random.uniform(0, GENISLIK + 200), -20
            pygame.draw.line(tuval, (70, 100, 150), (damla[0], damla[1]), (damla[0] + damla[3] * 0.12, damla[1] + damla[3]), 1)
        tuval.blit(self.vinyet, (0, 0))
        tuval.blit(self.tarama, (0, 0))

    def oyunu_ciz(self, gecen):
        """Oynama ekranını çizer: şehir, nesneler, efektler ve arayüz."""
        kamera = Vek(int(self.kamera.x), int(self.kamera.y))
        oyuncu = self.oyuncu
        tuval.blit(self.dunya, (0, 0), pygame.Rect(int(kamera.x), int(kamera.y), GENISLIK, YUKSEKLIK))
        for terminal in self.terminaller:
            terminal.ciz(tuval, kamera, self.zaman)
        asansor = ASANSOR_KONUM - kamera                          # asansör platformu
        asansor_renk = YESIL if self.gorev >= 2 else (90, 30, 40)
        nabiz = 1 + math.sin(self.sure * 3) * 0.08
        parlama_ciz(tuval, asansor_renk, asansor, 90 * nabiz)
        pygame.draw.circle(tuval, asansor_renk, asansor, int(66 * nabiz), 3)
        cokgen_ciz(tuval, asansor_renk, duzgun_cokgen(6, 44), asansor, self.sure * 0.6, 2)
        yazi_yaz(yazi_k, "ASANSÖR" if self.gorev >= 2 else "ASANSÖR (KİLİTLİ)", asansor_renk, (asansor.x, asansor.y + 84), ortala=True)
        for esya in self.esyalar:
            esya.ciz(tuval, kamera)
        for dusman in self.dusmanlar:
            dusman.ciz(tuval, kamera)
        for mermi in self.mermiler:
            mermi.ciz(tuval, kamera)
        oyuncu.ciz(tuval, kamera)
        for parcacik in self.parcaciklar:
            parcacik.ciz(tuval, kamera)
        for halka in self.halkalar:
            oran = halka[3] / halka[4]                            # halkanın kalan ömür oranı (söndükçe azalır)
            yaricap = int(halka[1] + (halka[2] - halka[1]) * (1 - oran))
            pygame.draw.circle(tuval, tuple(int(c * oran) for c in halka[5]), halka[0] - kamera, max(2, yaricap), 3)
        for yazi in self.yazilar:
            yazi_yaz(yazi_k, yazi[1], yazi[3], yazi[0] - kamera, ortala=True, seffaflik=int(255 * min(1, yazi[2] * 2)))
        hedef = self.hedef_konum()                                # görev hedefini gösteren sarı ok
        if hedef is not None and (hedef - oyuncu.konum).length() > 170:
            yon = (hedef - oyuncu.konum).normalize()
            cokgen_ciz(tuval, SARI, [(11, 0), (-6, -8), (-6, 8)], oyuncu.konum - kamera + yon * 74, math.atan2(yon.y, yon.x), 0)

        self.efektleri_ciz(gecen)
        if self.hasar_efekti > 0:                                 # hasar alınca ekran kızarır
            kirmizi = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
            kirmizi.fill((255, 0, 30, int(110 * self.hasar_efekti / 0.4)))
            tuval.blit(kirmizi, (0, 0))
        self.arayuz_ciz()

    def arayuz_ciz(self):
        """HUD: can/enerji, silahlar, görev paneli, skor, patron çubuğu, mini harita."""
        oyuncu = self.oyuncu
        can_renk = TURKUAZ if oyuncu.can > 35 else KIRMIZI
        bar_ciz((20, 20, 270, 16), oyuncu.can / 100, can_renk)
        yazi_yaz(yazi_k, f"SAĞLIK {int(oyuncu.can)}", BEYAZ, (26, 20))
        bar_ciz((20, 42, 270, 9), oyuncu.enerji / 100, SARI)
        for i, (isim, _, maliyet, renk) in enumerate(SILAHLAR):   # silah kutuları
            kutu = pygame.Rect(20 + i * 92, 60, 86, 26)
            pygame.draw.rect(tuval, (14, 14, 30), kutu)
            pygame.draw.rect(tuval, renk if i == oyuncu.silah else (60, 60, 90), kutu, 3 if i == oyuncu.silah else 1)
            yazi_yaz(yazi_k, f"{i + 1} {isim}", renk if i == oyuncu.silah else (110, 110, 140), (kutu.x + 6, kutu.y + 5))
        bar_ciz((20, 94, 130, 6), 1 - oyuncu.atilma_bekleme / 1.1, TURKUAZ if oyuncu.atilma_bekleme <= 0 else (60, 90, 120))
        yazi_yaz(yazi_k, "DASH" if oyuncu.atilma_bekleme > 0 else "DASH HAZIR", TURKUAZ, (158, 90))
        ilerleme = ""                                             # görev sayacı yazısı
        if self.gorev == 0:
            ilerleme = f"  [{self.hacklenen}/3]"
        elif self.gorev == 1:
            ilerleme = f"  [{self.gorev_oldurme}/20]"
        pygame.draw.rect(tuval, (10, 10, 26), (GENISLIK // 2 - 270, 14, 540, 52))
        pygame.draw.rect(tuval, TURKUAZ, (GENISLIK // 2 - 270, 14, 540, 52), 2)
        yazi_yaz(yazi_k, f"GÖREV {self.gorev + 1}/4", TURKUAZ, (GENISLIK // 2, 24), ortala=True)
        yazi_yaz(yazi_o, GOREVLER[self.gorev] + ilerleme, BEYAZ, (GENISLIK // 2, 46), ortala=True)
        yazi_yaz(yazi_o, f"SKOR {self.skor}", BEYAZ, (GENISLIK - 250, 18))
        yazi_yaz(yazi_k, f"REKOR {self.rekor}", YESIL, (GENISLIK - 250, 46))
        patron = self.patron()
        if patron:
            bar_ciz((GENISLIK // 2 - 300, 78, 600, 14), patron.can / patron.maks_can, PEMBE)
            yazi_yaz(yazi_k, "ANA ÇEKİRDEK", PEMBE, (GENISLIK // 2, 106), ortala=True)
        metin, kalan, renk = self.afis                            # büyük duyuru yazısı
        if kalan > 0:
            yazi_yaz(yazi_b, metin, renk, (GENISLIK // 2, YUKSEKLIK // 2 - 150), ortala=True, seffaflik=int(255 * min(1, kalan)))
        # mini harita
        hx, hy = GENISLIK - 176, YUKSEKLIK - 136
        olcek = 0.06
        pygame.draw.rect(tuval, (6, 6, 16), (hx - 4, hy - 4, 164, 122))
        tuval.blit(self.harita_kucuk, (hx, hy))
        for terminal in self.terminaller:
            pygame.draw.circle(tuval, YESIL if terminal.bitti else SARI, (hx + terminal.konum.x * olcek, hy + terminal.konum.y * olcek), 3)
        if self.gorev >= 2:
            pygame.draw.circle(tuval, YESIL, (hx + ASANSOR_KONUM.x * olcek, hy + ASANSOR_KONUM.y * olcek), 4, 1)
        for dusman in self.dusmanlar:
            if dusman.alarm or (dusman.konum - oyuncu.konum).length() < 600:
                pygame.draw.circle(tuval, KIRMIZI, (hx + dusman.konum.x * olcek, hy + dusman.konum.y * olcek), 2 if dusman.tur != "patron" else 5)
        pygame.draw.circle(tuval, TURKUAZ, (hx + oyuncu.konum.x * olcek, hy + oyuncu.konum.y * olcek), 3)
        pygame.draw.rect(tuval, TURKUAZ, (hx - 4, hy - 4, 164, 122), 1)
        gorunen = pygame.Rect(hx + self.kamera.x * olcek, hy + self.kamera.y * olcek, GENISLIK * olcek, YUKSEKLIK * olcek)
        pygame.draw.rect(tuval, (90, 110, 150), gorunen, 1)       # kameranın baktığı alan

    def menu_ciz(self, gecen):
        """Başlangıç menüsü: hareketli şehir arka planı, hikâye ve kontroller."""
        self.zaman += gecen
        kamera = Vek(int(900 + 300 * math.sin(self.zaman * 0.1)), int(600 + 200 * math.cos(self.zaman * 0.13)))
        tuval.blit(self.dunya, (0, 0), pygame.Rect(int(kamera.x), int(kamera.y), GENISLIK, YUKSEKLIK))
        karanlik = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
        karanlik.fill((0, 0, 12, 170))
        tuval.blit(karanlik, (0, 0))
        self.efektleri_ciz(gecen)
        bozulma = int(self.zaman * 10) % 40 < 3                   # arada bir başlıkta glitch efekti
        merkez = (GENISLIK // 2, 150)
        if bozulma:
            yazi_yaz(yazi_xb, "SİBER KAÇIŞ", PEMBE, (merkez[0] - 6, merkez[1]), ortala=True)
            yazi_yaz(yazi_xb, "SİBER KAÇIŞ", YESIL, (merkez[0] + 6, merkez[1] + 2), ortala=True)
        yazi_yaz(yazi_xb, "SİBER KAÇIŞ", TURKUAZ, merkez, ortala=True)
        yazi_yaz(yazi_o, "NEO-İSTANBUL  ·  2147", PEMBE, (GENISLIK // 2, 205), ortala=True)
        hikaye = ["Şehrin yapay zekâsı ÇEKİRDEK-X kontrolü ele geçirdi.",
                  "Robot orduları sokaklara hâkim. Son özgür hacker sensin.",
                  "Terminalleri hackle, ordusunu yok et, çekirdeğe in ve sistemi kurtar."]
        for i, satir in enumerate(hikaye):
            yazi_yaz(yazi_o, satir, BEYAZ, (GENISLIK // 2, 270 + i * 32), ortala=True)
        kontroller = ["WASD : hareket      FARE : nişan / ateş      SPACE : dash",
                      "1-2-3 / tekerlek : silah      E (basılı) : hackle      ESC : duraklat"]
        for i, satir in enumerate(kontroller):
            yazi_yaz(yazi_k, satir, (150, 170, 210), (GENISLIK // 2, 410 + i * 26), ortala=True)
        saydamlik = int(140 + 115 * math.sin(self.zaman * 4))     # yanıp sönen başlat yazısı
        yazi_yaz(yazi_b, "ENTER veya TIKLA  -  BAŞLA", SARI, (GENISLIK // 2, 540), ortala=True, seffaflik=saydamlik)
        yazi_yaz(yazi_k, f"REKOR: {self.rekor}", YESIL, (GENISLIK // 2, 600), ortala=True)

    def son_ekran_ciz(self, baslik, renk, alt_yazi):
        """Oyun bitti / kazandın ekranı (son kare karartılıp üstüne yazılır)."""
        tuval.blit(self.goruntu_kopya, (0, 0))
        karanlik = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
        karanlik.fill((0, 0, 10, 180))
        tuval.blit(karanlik, (0, 0))
        yazi_yaz(yazi_xb, baslik, renk, (GENISLIK // 2, 210), ortala=True)
        yazi_yaz(yazi_o, alt_yazi, BEYAZ, (GENISLIK // 2, 285), ortala=True)
        dakika, saniye = int(self.sure // 60), int(self.sure % 60)
        yazi_yaz(yazi_b, f"SKOR {self.skor}", SARI, (GENISLIK // 2, 360), ortala=True)
        yazi_yaz(yazi_o, f"Yok edilen robot: {self.oldurme}    Süre: {dakika:02d}:{saniye:02d}    Rekor: {self.rekor}",
                 BEYAZ, (GENISLIK // 2, 415), ortala=True)
        yazi_yaz(yazi_o, "R : tekrar oyna      M / ESC : menü", TURKUAZ, (GENISLIK // 2, 500), ortala=True)

    def adim(self, gecen):
        """Ana döngünün her karede çağırdığı fonksiyon: duruma göre günceller ve çizer."""
        if self.durum == "oyun":
            self.guncelle(gecen)
        if self.durum == "oyun":
            self.oyunu_ciz(gecen)
        elif self.durum == "menu":
            self.menu_ciz(gecen)
        else:
            if self.goruntu_kopya is None:                        # son kareyi bir kez sakla
                self.goruntu_kopya = tuval.copy()
            if self.durum == "duraklat":
                tuval.blit(self.goruntu_kopya, (0, 0))
                karanlik = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
                karanlik.fill((0, 0, 10, 150))
                tuval.blit(karanlik, (0, 0))
                yazi_yaz(yazi_xb, "DURAKLATILDI", TURKUAZ, (GENISLIK // 2, 280), ortala=True)
                yazi_yaz(yazi_o, "ESC / P : devam      Q : menüye dön", BEYAZ, (GENISLIK // 2, 360), ortala=True)
            elif self.durum == "bitti":
                self.son_ekran_ciz("SİSTEM ÇÖKTÜ", KIRMIZI, "Robotlar şehri ele geçirdi...")
            else:
                self.son_ekran_ciz("ŞEHİR KURTULDU", YESIL, "ÇEKİRDEK-X yok edildi. Neo-İstanbul özgür!")
        kayma_x = random.uniform(-self.sarsinti, self.sarsinti) if self.sarsinti and self.durum == "oyun" else 0
        kayma_y = random.uniform(-self.sarsinti, self.sarsinti) if self.sarsinti and self.durum == "oyun" else 0
        ekran.fill((0, 0, 0))
        ekran.blit(tuval, (kayma_x, kayma_y))                     # ekran sarsıntısı: tuvali hafifçe kaydırarak göster


def ana():
    """Programın giriş noktası: oyun döngüsünü çalıştırır."""
    oyun = Oyun()
    while True:
        gecen = min(saat.tick(KARE_HIZI) / 1000, 0.033)           # önceki kareden beri geçen süre (sn)
        for olay in pygame.event.get():
            oyun.olay_isle(olay)
        oyun.adim(gecen)
        pygame.display.flip()


if __name__ == "__main__":
    ana()
"""
OYUN MERKEZİ  -  Kayıt ol / Giriş yap  ->  oyun ikonları  ->  oyunu başlat

çalıştırmak için unutma://diğer sürümlerde çalışmıyor 
py -3.12 oyun_merkezi.py

Bu dosya, aşağıdaki oyun dosyalarıyla AYNI KLASÖRDE olmalı:
    neon_storm.py     siber_kacis.py
Kullanıcılar 'kullanicilar.json' dosyasında saklanır (şifreler karıştırılarak / hash'lenerek).

Aynı klasörde olması gerekenler:
    ayarlar.py  temalar.py  oyun_baslatici.py  (neon_storm.py  siber_kacis.py)
Ayarlar 'ayarlar.json' dosyasında, kullanıcıya özel saklanır.
"""
import array
import hashlib
import json
import math
import os
import random
import secrets
import subprocess
import sys
import time
import types

import pygame

import ayarlar
import temalar
from ayarlar import t

GENISLIK, YUKSEKLIK = 1100, 720                       # MANTIKSAL çözünürlük (çizimler hep bu boyuta göre yapılır)
MIN_GENISLIK, MIN_YUKSEKLIK = 640, 420                # pencerenin küçülebileceği en küçük boyut
KARE_HIZI = 60                                        # saniyedeki kare sayısı
KLASOR = os.path.dirname(os.path.abspath(__file__))   # bu dosyanın bulunduğu klasör
VERITABANI = os.path.join(KLASOR, "kullanicilar.json")  # kullanıcıların saklandığı dosya

TURKUAZ = (0, 235, 255)
PEMBE = (255, 50, 150)
SARI = (255, 225, 70)
YESIL = (80, 255, 150)
TURUNCU = (255, 140, 40)
MOR = (175, 95, 255)
KIRMIZI = (255, 80, 90)
BEYAZ = (255, 255, 255)

OYUNLAR = [
    dict(kimlik="neon", dosya="neon_storm.py", renk=TURKUAZ),
    dict(kimlik="siber", dosya="siber_kacis.py", renk=PEMBE,
         rekor="siber_kacis_rekor.txt"),
    dict(kimlik="flappy", dosya="flappy_bird.py", renk=SARI),
]
AYAR = ayarlar.AyarDeposu()                           # kullanıcıya özel ayarlar (ayarlar.json)

pygame.mixer.pre_init(44100, -16, 1, 512)             # ses sistemi: pygame.init'ten ÖNCE ayarlanmalı
pygame.init()
pygame.key.start_text_input()                         # Türkçe karakterli yazı girişi (TEXTINPUT olayı) için
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK), pygame.RESIZABLE)   # RESIZABLE: fareyle boyutlanır
pygame.display.set_caption(t("app.baslik"))
try:                                                  # pencere çok küçülmesin (pygame 2.x)
    from pygame._sdl2.video import Window
    Window.from_display_module().minimum_size = (MIN_GENISLIK, MIN_YUKSEKLIK)
except Exception:
    pass
saat = pygame.time.Clock()
tuval = pygame.Surface((GENISLIK, YUKSEKLIK))         # her şeyin önce çizildiği (sabit boyutlu) yüzey
YAZI_TIPI = "dejavusansmono,consolas,couriernew,monospace"
yazi_k = pygame.font.SysFont(YAZI_TIPI, 15, bold=True)   # küçük
yazi_o = pygame.font.SysFont(YAZI_TIPI, 20, bold=True)   # orta
yazi_b = pygame.font.SysFont(YAZI_TIPI, 32, bold=True)   # büyük
yazi_xb = pygame.font.SysFont(YAZI_TIPI, 64, bold=True)  # çok büyük (başlık)


# ----------------------------------------------------------------- sesler
_sesler = {}   # ad -> pygame.mixer.Sound


def ses_uret(frekanslar, sure, seviye=0.35, azalma=7.0):
    """Verilen frekansları sırayla çalan kısa, sönümlü bir ses üretir (dosya gerekmez)."""
    hz, bicim, kanal = pygame.mixer.get_init()
    n = int(hz * sure)
    veri = array.array("h")
    faz = 0.0
    for i in range(n):
        f = frekanslar[min(len(frekanslar) - 1, i * len(frekanslar) // n)]
        faz += math.tau * f / hz                       # faz biriktirme: frekans değişirken "çıt" olmaz
        zarf = math.exp(-azalma * i / n) * min(1.0, i / 80)   # hızlı giriş, yumuşak sönüş
        ornek = int(32767 * seviye * zarf * math.sin(faz))
        veri.extend([ornek] * kanal)
    return pygame.mixer.Sound(buffer=veri.tobytes())


def sesleri_hazirla():
    """Tüm menü seslerini üretir. Ses kartı yoksa sessizce atlar (oyun yine çalışır)."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(44100, -16, 1, 512)
        if pygame.mixer.get_init()[1] != -16:          # sadece 16 bit işaretli formatı destekliyoruz
            return
        _sesler["tik"] = ses_uret([1300, 850], 0.07)                   # genel tıklama
        _sesler["oyna"] = ses_uret([520, 780, 1040], 0.22, 0.35, 4.0)  # oyun başlatma
        _sesler["basari"] = ses_uret([660, 880, 1320], 0.30, 0.35, 4.5)
        _sesler["hata"] = ses_uret([220, 165], 0.25, 0.4, 3.5)
    except Exception:
        _sesler.clear()


def ses_cal(ad):
    """Adı verilen sesi çalar (ses yoksa hiçbir şey yapmaz)."""
    ses = _sesler.get(ad)
    if ses and AYAR.al("ses"):
        ses.play()


sesleri_hazirla()


# ----------------------------------------------------------------- kullanıcı veritabanı
def veritabani_yukle():
    """kullanicilar.json dosyasını okur; yoksa ya da bozuksa boş sözlük döndürür."""
    try:
        with open(VERITABANI, encoding="utf-8") as dosya:
            return json.load(dosya)
    except Exception:
        return {}


def veritabani_kaydet(veri):
    """Kullanıcı sözlüğünü kullanicilar.json dosyasına yazar."""
    gecici = VERITABANI + ".tmp"
    with open(gecici, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False, indent=2)
    os.replace(gecici, VERITABANI)                    # yazma yarıda kesilse bile hesaplar bozulmaz


def sifre_karistir(sifre, tuz_hex):
    """Şifreyi 'tuz' ile PBKDF2 yöntemiyle geri döndürülemez şekilde karıştırır (hash)."""
    return hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), bytes.fromhex(tuz_hex), 150_000).hex()


def kayit_ol(kullanici_adi, sifre, sifre_tekrar):
    """Yeni kullanıcı kaydeder. Döner: (başarılı mı, mesaj, kullanıcı adı)"""
    kullanici_adi = kullanici_adi.strip()
    if len(kullanici_adi) < 3:
        return False, "hata.ad_kisa", None
    if len(kullanici_adi) > 16:
        return False, "hata.ad_uzun", None
    if len(sifre) < 6:
        return False, "hata.sifre_kisa", None
    if sifre != sifre_tekrar:
        return False, "hata.sifre_uyusmuyor", None
    veri = veritabani_yukle()
    if kullanici_adi.lower() in veri:                 # büyük/küçük harf fark etmeden aynı ad var mı?
        return False, "hata.ad_alinmis", None
    tuz = secrets.token_hex(16)                       # her kullanıcıya özel rastgele tuz
    veri[kullanici_adi.lower()] = dict(ad=kullanici_adi, tuz=tuz, karisim=sifre_karistir(sifre, tuz),
                                       olusturma=int(time.time()))
    try:
        veritabani_kaydet(veri)
    except OSError:
        return False, "hata.yazilamadi", None
    return True, "ok.kayit", kullanici_adi


def giris_yap(kullanici_adi, sifre):
    """Kullanıcı adı ve şifreyi kontrol eder. Döner: (başarılı mı, mesaj, kullanıcı adı)"""
    kayit = veritabani_yukle().get(kullanici_adi.strip().lower())
    if kayit:   # eski sürümde kaydedilmiş hesaplar (name/salt/hash alanları) da çalışsın
        tuz = kayit.get("tuz", kayit.get("salt"))
        karisim = kayit.get("karisim", kayit.get("hash"))
        ad = kayit.get("ad", kayit.get("name"))
    if not kayit or not secrets.compare_digest(karisim, sifre_karistir(sifre, tuz)):
        return False, "hata.giris", None
    return True, "ok.giris", ad


def kullanici_adi_degistir(eski_ad, yeni_ad):
    """Hesabın görünen/giriş adını değiştirir; şifre ve diğer hesap verileri aynen korunur.
    Döner: (başarılı mı, mesaj anahtarı, yeni ad)"""
    yeni_ad = yeni_ad.strip()
    if len(yeni_ad) < 3:
        return False, "hata.ad_kisa", None
    if len(yeni_ad) > 16:
        return False, "hata.ad_uzun", None
    veri = veritabani_yukle()
    eski_k, yeni_k = eski_ad.lower(), yeni_ad.lower()
    kayit = veri.get(eski_k)
    if not kayit:
        return False, "hata.hesap_yok", None
    if yeni_k != eski_k and yeni_k in veri:
        return False, "hata.ad_alinmis", None
    kayit = dict(kayit)
    kayit["ad"] = yeni_ad
    if "name" in kayit:                               # eski sürüm alanı varsa o da güncellensin
        kayit["name"] = yeni_ad
    del veri[eski_k]
    veri[yeni_k] = kayit
    try:
        veritabani_kaydet(veri)
    except OSError:
        return False, "hata.yazilamadi", None
    return True, "ok.profil", yeni_ad


# ----------------------------------------------------------------- çizim yardımcıları
_parlama_onbellek = {}   # (renk, yarıçap) -> hazır parlama resmi


def parlama_sprite_olustur(renk, yaricap):
    """Merkezden dışa doğru sönen yumuşak ışık topu resmi üretir."""
    anahtar = (renk, yaricap)
    if anahtar not in _parlama_onbellek:
        yuzey = pygame.Surface((yaricap * 2, yaricap * 2))
        for i in range(yaricap, 0, -1):
            katsayi = (1 - i / yaricap) ** 2
            pygame.draw.circle(yuzey, tuple(int(c * katsayi) for c in renk), (yaricap, yaricap), i)
        _parlama_onbellek[anahtar] = yuzey
    return _parlama_onbellek[anahtar]


def parlama_ciz(yuzey, renk, konum, yaricap):
    """Verilen konuma neon parıltısı çizer."""
    yaricap = max(3, min(220, int(yaricap)))
    yuzey.blit(parlama_sprite_olustur(tuple(renk), yaricap), (int(konum[0] - yaricap), int(konum[1] - yaricap)),
               special_flags=pygame.BLEND_ADD)


def cokgen_ciz(yuzey, renk, noktalar, konum, aci=0.0, kalinlik=2):
    """Merkeze göre noktalardan çokgeni döndürüp çizer."""
    cos_a, sin_a = math.cos(aci), math.sin(aci)
    pygame.draw.polygon(yuzey, renk, [(konum[0] + x * cos_a - y * sin_a, konum[1] + x * sin_a + y * cos_a)
                                      for x, y in noktalar], kalinlik)


def duzgun_cokgen(kenar_sayisi, yaricap):
    """Düzgün n-gen köşe noktalarını döndürür."""
    return [(yaricap * math.cos(i * math.tau / kenar_sayisi), yaricap * math.sin(i * math.tau / kenar_sayisi))
            for i in range(kenar_sayisi)]


def yazi_yaz(font, metin, renk, konum, ortala=False, seffaflik=255, yuzey=None):
    """Gölgeli yazı yazar. 'ortala' True ise konum yazının merkezidir."""
    hedef = yuzey or tuval
    resim = font.render(metin, True, renk)
    resim.set_alpha(seffaflik)
    alan = resim.get_rect(center=konum) if ortala else resim.get_rect(topleft=konum)
    golge = font.render(metin, True, (0, 0, 0))
    golge.set_alpha(seffaflik)
    hedef.blit(golge, alan.move(2, 2))
    hedef.blit(resim, alan)
    return alan


def satirlara_bol(metin, font, genislik):
    """Uzun metni verilen piksel genişliğine sığacak satırlara böler."""
    satirlar, anlik = [], ""
    for kelime in metin.split():
        deneme = (anlik + " " + kelime).strip()
        if font.size(deneme)[0] <= genislik:
            anlik = deneme
        else:
            satirlar.append(anlik)
            anlik = kelime
    return satirlar + [anlik]


def panel_ciz(dikdortgen, seffaflik=215, renk=(14, 10, 34)):
    """Yarı saydam koyu panel (kart arka planı) çizer."""
    yuzey = pygame.Surface(dikdortgen.size, pygame.SRCALPHA)
    yuzey.fill((*renk, seffaflik))
    tuval.blit(yuzey, dikdortgen.topleft)


def karart(renk, katsayi):
    """Rengi koyulaştırır (katsayi 0-1 arası)."""
    return tuple(int(c * katsayi) for c in renk)



def ikon_olustur(oyun_kimligi, boyut=(300, 190)):
    """Oyun kartlarının üstündeki ikon resmini kodla çizer (resim dosyası gerekmez)."""
    genislik, yukseklik = boyut
    yuzey = pygame.Surface(boyut)
    uretici = random.Random(3)                         # sabit tohum: ikon hep aynı görünür
    if oyun_kimligi == "neon":                         # Neon Storm: uzay gemisi, düşmanlar, yıldızlar
        yuzey.fill((6, 4, 20))
        for _ in range(60):
            parlaklik = uretici.randint(70, 220)
            yuzey.fill((parlaklik, parlaklik, 255), (uretici.randint(0, genislik), uretici.randint(0, yukseklik), 2, uretici.randint(2, 5)))
        for x, y in ((70, 40), (150, 28), (230, 50), (110, 70), (200, 80)):    # pembe düşmanlar
            parlama_ciz(yuzey, PEMBE, (x, y), 30)
            cokgen_ciz(yuzey, PEMBE, [(0, 14), (14, -12), (-14, -12)], (x, y), 0, 3)
        for x in (150, 120, 180):                                              # mermiler
            pygame.draw.line(yuzey, TURKUAZ, (x, 120 if x == 150 else 135), (x, 98 if x == 150 else 115), 4)
            parlama_ciz(yuzey, TURKUAZ, (x, 110), 14)
        parlama_ciz(yuzey, TURKUAZ, (150, 150), 60)                            # oyuncunun gemisi
        cokgen_ciz(yuzey, TURKUAZ, [(0, -24), (18, 18), (0, 9), (-18, 18)], (150, 150), 0, 3)
        parlama_ciz(yuzey, TURUNCU, (150, 176), 16)
        
    elif oyun_kimligi == "flappy":
        # Flappy Bird: gökyüzü, borular ve kuş
        yuzey.fill((80, 190, 245))

        # Bulutlar
        for x, y in ((45, 35), (220, 55), (140, 100)):
            pygame.draw.circle(yuzey, BEYAZ, (x, y), 15)
            pygame.draw.circle(yuzey, BEYAZ, (x + 18, y - 5), 19)
            pygame.draw.circle(yuzey, BEYAZ, (x + 35, y), 14)

        # Üst boru
        pygame.draw.rect(yuzey, (40, 190, 75), (225, 0, 38, 65))
        pygame.draw.rect(yuzey, (20, 130, 50), (225, 0, 38, 65), 3)
        pygame.draw.rect(yuzey, (40, 190, 75), (218, 55, 52, 14))
        pygame.draw.rect(yuzey, (20, 130, 50), (218, 55, 52, 14), 3)

        # Alt boru
        pygame.draw.rect(yuzey, (40, 190, 75), (225, 125, 38, 65))
        pygame.draw.rect(yuzey, (20, 130, 50), (225, 125, 38, 65), 3)
        pygame.draw.rect(yuzey, (40, 190, 75), (218, 125, 52, 14))
        pygame.draw.rect(yuzey, (20, 130, 50), (218, 125, 52, 14), 3)

        # Kuş
        pygame.draw.circle(yuzey, SARI, (125, 95), 24)
        pygame.draw.circle(yuzey, (230, 160, 20), (125, 95), 24, 2)
        pygame.draw.circle(yuzey, BEYAZ, (135, 86), 9)
        pygame.draw.circle(yuzey, (10, 10, 20), (138, 86), 4)
        pygame.draw.polygon(yuzey, TURUNCU, [
            (147, 96), (169, 103), (147, 109)
        ])
        pygame.draw.ellipse(yuzey, (245, 180, 30), (105, 98, 23, 12))

        # Zemin
        pygame.draw.rect(yuzey, (220, 190, 100), (0, 175, genislik, 15))
        pygame.draw.rect(yuzey, (60, 180, 70), (0, 175, genislik, 5))

    
    else:                                              # Siber Kaçış: neon binalar, robotlar, oyuncu
        yuzey.fill((8, 8, 21))
        for x in range(0, genislik, 30):
            pygame.draw.line(yuzey, (16, 16, 40), (x, 0), (x, yukseklik))
        for y in range(0, yukseklik, 30):
            pygame.draw.line(yuzey, (16, 16, 40), (0, y), (genislik, y))
        for bina, renk in ((pygame.Rect(8, 12, 80, 60), TURKUAZ), (pygame.Rect(212, 8, 80, 70), MOR),
                           (pygame.Rect(10, 118, 90, 64), MOR), (pygame.Rect(205, 122, 85, 60), TURKUAZ)):
            for kalinlik, katsayi in ((10, 0.1), (6, 0.25)):
                pygame.draw.rect(yuzey, karart(renk, katsayi), bina.inflate(kalinlik * 2, kalinlik * 2), kalinlik)
            pygame.draw.rect(yuzey, (11, 9, 26), bina)
            pygame.draw.rect(yuzey, renk, bina, 2)
        for x, y in ((120, 40), (180, 120)):           # turuncu robotlar
            parlama_ciz(yuzey, TURUNCU, (x, y), 34)
            cokgen_ciz(yuzey, TURUNCU, duzgun_cokgen(6, 15), (x, y), 0.3, 3)
            pygame.draw.line(yuzey, TURUNCU, (x, y), (x + 20, y + 6), 4)
        parlama_ciz(yuzey, TURKUAZ, (150, 92), 44)     # oyuncu
        pygame.draw.circle(yuzey, (8, 28, 44), (150, 92), 13)
        pygame.draw.circle(yuzey, TURKUAZ, (150, 92), 13, 3)
        pygame.draw.line(yuzey, TURKUAZ, (150, 92), (178, 80), 6)
        pygame.draw.line(yuzey, SARI, (186, 76), (240, 54), 2)
        parlama_ciz(yuzey, SARI, (186, 76), 12)
        parlama_ciz(yuzey, YESIL, (270, 160), 18)
    return yuzey


# ----------------------------------------------------------------- uygulama
class Uygulama:
    """Giriş/kayıt ekranını, oyun menüsünü ve oyun başlatmayı yöneten ana sınıf."""

    def __init__(self):
        self.durum = "giris"            # "giris" (giriş/kayıt) | "menu" (oyun kartları) | "oyun_acik"
        self.mod = "giris"              # giriş ekranındaki sekme: "giris" | "kayit"
        self.degerler = ["", "", ""]    # yazılan metinler: [kullanıcı adı, şifre, şifre tekrar]
        self.odak = 0                   # hangi giriş kutusu seçili (0, 1, 2)
        self.sifre_goster = False       # "Şifreyi göster" kutusu işaretli mi
        self.mesaj = ("", BEYAZ)        # giriş ekranındaki hata / bilgi mesajı: (metin, renk)
        self.kullanici = None           # giriş yapmış kullanıcının adı
        self.zaman = 0.0                # animasyonlar için geçen toplam süre
        self.fare = (0, 0)              # son fare konumu (MANTIKSAL koordinat; üzerine gelme efektleri için)
        self.fx = self.fy = 1.0         # büyük tuvalin pencereye göre ölçek oranları
        self.ofset = (0, 0)             # 1100x720'lik oyun alanının büyük tuval içindeki sol-üst konumu
        self.buyuk = None               # pencerenin TAMAMINI kaplayan tuval (arka plan buraya çizilir)
        self.surec = None               # çalışan oyunun işlemi (subprocess)
        self.acik_oyun = None           # şu an açık olan oyunun bilgisi
        self.bildirim = ("", 0.0, BEYAZ)  # alttaki geçici bildirim: (metin, kalan süre, renk)
        self.ikonlar = {o["kimlik"]: ikon_olustur(o["kimlik"]) for o in OYUNLAR}
        self.uzerinde = [0.0] * (len(OYUNLAR) + 1)    # her kartın "üzerine gelme" animasyon oranı (0-1)
        self.bg_zaman = 0.0             # tema animasyonu için süre (ayardan kapatılınca durur)
        cizim = types.SimpleNamespace(      # ayarlar.py'nin kullandığı çizim/olay yardımcıları
            yazi=yazi_yaz, panel=panel_ciz, parlama=parlama_ciz, dugme=self.dugme_ciz, ses=ses_cal,
            fk=yazi_k, fo=yazi_o, fb=yazi_b, tuval=lambda: tuval, fare=lambda: self.fare,
            mantiksal=self.mantiksal, kullanici=lambda: self.kullanici, kullanici_ata=self.kullanici_ata,
            adi_degistir=kullanici_adi_degistir, tam_ekran=pygame.display.toggle_fullscreen,
            geri=self.ayarlardan_don, dil_degisti=self.dil_degisti)
        self.ayarlar_ekrani = ayarlar.AyarlarEkrani(AYAR, cizim, temalar)

    # --- pencere boyutlandırma
    def mantiksal(self, konum):
        """Pencere (piksel) koordinatını 1100x720'lik oyun alanının koordinatına çevirir.
        Böylece pencere ne kadar büyük/küçük olursa olsun tıklamalar doğru yere denk gelir."""
        return (int(konum[0] / self.fx - self.ofset[0]), int(konum[1] / self.fy - self.ofset[1]))

    def tuval_hazirla(self):
        """Pencere boyutuna göre büyük tuvali hazırlar. Arayüz (1100x720) bunun ortasındaki bir alt yüzeye
        çizilir; arka plan ise tuvalin tamamına çizilir, böylece yanlarda/üstte siyah boşluk kalmaz.
        Pencere simge durumundaysa False döner."""
        global tuval
        pencere = pygame.display.get_surface()
        pw, ph = pencere.get_size()
        if pw < 2 or ph < 2:
            return False
        oran = min(pw / GENISLIK, ph / YUKSEKLIK)
        gen = max(GENISLIK, math.ceil(pw / oran))
        yuk = max(YUKSEKLIK, math.ceil(ph / oran))
        if self.buyuk is None or self.buyuk.get_size() != (gen, yuk):
            self.buyuk = pygame.Surface((gen, yuk))
        self.ofset = ((gen - GENISLIK) // 2, (yuk - YUKSEKLIK) // 2)
        self.fx, self.fy = pw / gen, ph / yuk
        tuval = self.buyuk.subsurface(pygame.Rect(self.ofset, (GENISLIK, YUKSEKLIK)))   # tüm arayüz çizimleri buraya
        return True

    def pencereye_ciz(self):
        """Büyük tuvali pencere boyutuna ölçekleyip ekrana koyar."""
        pencere = pygame.display.get_surface()
        pw, ph = pencere.get_size()
        if self.buyuk.get_size() == (pw, ph):
            pencere.blit(self.buyuk, (0, 0))
        else:
            pencere.blit(pygame.transform.smoothscale(self.buyuk, (pw, ph)), (0, 0))

    # --- yerleşim hesapları
    def kutu_sayisi(self):
        """Giriş sekmesinde 2, kayıt sekmesinde 3 kutu var."""
        return 2 if self.mod == "giris" else 3

    def giris_yerlesimi(self):
        """Giriş/kayıt ekranındaki tüm elemanların dikdörtgenlerini hesaplar (çizim ve tıklama aynısını kullanır)."""
        n = self.kutu_sayisi()
        orta = GENISLIK // 2
        kart = pygame.Rect(orta - 235, 70, 470, 150 + n * 72 + 130)
        yerlesim = {"kart": kart}
        yerlesim["sekme_giris"] = pygame.Rect(kart.x + 35, kart.y + 88, 190, 38)
        yerlesim["sekme_kayit"] = pygame.Rect(kart.x + 245, kart.y + 88, 190, 38)
        yerlesim["kutular"] = [pygame.Rect(kart.x + 35, kart.y + 165 + i * 72, 400, 40) for i in range(n)]
        y = kart.y + 165 + n * 72 - 18
        yerlesim["onay_kutusu"] = pygame.Rect(kart.x + 35, y, 18, 18)
        yerlesim["mesaj"] = (orta, y + 42)
        yerlesim["gonder"] = pygame.Rect(kart.x + 35, y + 62, 400, 46)
        return yerlesim

    def etiketler(self):
        return [t("et.kullanici"), t("et.sifre"), t("et.sifre2")][: self.kutu_sayisi()]

    def kart_dikdortgenleri(self):
        """Menüdeki 3 kartın (2 oyun + 1 'yakında') dikdörtgenleri."""
        genislik, yukseklik, bosluk = 300, 380, 40
        baslangic_x = (GENISLIK - (3 * genislik + 2 * bosluk)) // 2
        return [pygame.Rect(baslangic_x + i * (genislik + bosluk), 215, genislik, yukseklik) for i in range(3)]

    def cikis_dikdortgeni(self):
        return pygame.Rect(GENISLIK - 246, 24, 160, 40)

    def ayar_dikdortgeni(self):
        return pygame.Rect(GENISLIK - 70, 24, 44, 40)

    def profil_dikdortgeni(self):
        return pygame.Rect(24, 12, 340, 62)

    # --- işlemler
    def sekme_degistir(self, yeni_mod):
        """Giriş <-> Kayıt sekmesi arasında geçer."""
        if yeni_mod != self.mod:
            ses_cal("tik")
            self.mod = yeni_mod
            self.degerler[1] = self.degerler[2] = ""
            self.odak = min(self.odak, self.kutu_sayisi() - 1)
            self.mesaj = ("", BEYAZ)

    def gonder(self):
        """Gönder düğmesi / ENTER: giriş veya kayıt işlemini yapar."""
        v = self.degerler
        if self.mod == "giris":
            basarili, mesaj, ad = giris_yap(v[0], v[1])
        else:
            basarili, mesaj, ad = kayit_ol(v[0], v[1], v[2])
        if basarili:
            ses_cal("basari")
            self.kullanici_ata(ad)
            AYAR.kullanici_sec(ad)                         # bu kullanıcının dil/tema/tuş ayarlarını yükle
            self.dil_degisti()
            self.durum = "menu"
            self.degerler = ["", "", ""]
            self.mesaj = ("", BEYAZ)
            self.bildirim = (t("bildirim.giris" if self.mod == "giris" else "bildirim.kayit", ad=ad), 3.0, YESIL)
        else:
            ses_cal("hata")
            self.mesaj = (mesaj, KIRMIZI)                  # mesaj bir dil anahtarı; çizerken çevrilir

    def kullanici_ata(self, ad):
        self.kullanici = ad

    def dil_degisti(self):
        """Dil değişince pencere başlığını yeniler (tüm yazılar zaten her karede t() ile çizilir)."""
        pygame.display.set_caption(t("app.baslik"))

    def ayarlar_ac(self, sekme="genel"):
        ses_cal("tik")
        self.ayarlar_ekrani.ac(sekme)
        self.durum = "ayarlar"

    def ayarlardan_don(self):
        self.durum = "menu"

    def oyunu_baslat(self, oyun):
        """Seçilen oyunu ayrı bir işlem olarak açar; oyun kapanınca menüye dönülür."""
        yol = os.path.join(KLASOR, oyun["dosya"])
        if not os.path.exists(yol):
            ses_cal("hata")
            self.bildirim = (t("hata.dosya", dosya=oyun["dosya"]), 4.0, KIRMIZI)
            return
        try:
            baslatici = os.path.join(KLASOR, "oyun_baslatici.py")   # kullanıcının tuş ayarlarını oyuna uygular
            komut = [sys.executable, baslatici, yol, oyun["kimlik"]] if os.path.exists(baslatici) else [sys.executable, yol]
            ortam = dict(os.environ, OYUN_MERKEZI_KULLANICI=self.kullanici or "")
            self.surec = subprocess.Popen(komut, cwd=KLASOR, env=ortam)
        except OSError as hata:
            ses_cal("hata")
            self.bildirim = (t("hata.baslatilamadi", hata=hata), 4.0, KIRMIZI)
            return
        ses_cal("oyna")
        self.acik_oyun = oyun
        self.durum = "oyun_acik"

    def kapat(self):
        """Açık oyun varsa kapatıp programdan çıkar."""
        if self.surec and self.surec.poll() is None:
            self.surec.terminate()
        pygame.quit()
        sys.exit()

    # --- olaylar
    def olay_isle(self, olay):
        """Tüm pygame olaylarını duruma göre ilgili fonksiyona yönlendirir."""
        if olay.type == pygame.QUIT:
            self.kapat()
        if olay.type == pygame.MOUSEMOTION:
            self.fare = self.mantiksal(olay.pos)
        if olay.type == pygame.KEYDOWN and olay.key == pygame.K_F11:   # tam ekran aç/kapat
            pygame.display.toggle_fullscreen()
            return
        if self.durum == "giris":
            self.giris_olayi(olay)
        elif self.durum == "menu":
            self.menu_olayi(olay)
        elif self.durum == "ayarlar":
            self.ayarlar_ekrani.olay(olay)

    def giris_olayi(self, olay):
        """Giriş/kayıt ekranı: yazı yazma, TAB, ENTER ve tıklamalar."""
        n = self.kutu_sayisi()
        if olay.type == pygame.TEXTINPUT:                  # yazılan karakter (Türkçe karakterler dahil)
            harf = olay.text
            if self.odak == 0:                             # kullanıcı adında sadece harf, rakam ve _ - .
                harf = "".join(c for c in harf if c.isalnum() or c in "_-.")
                if len(self.degerler[0]) < 16:
                    self.degerler[0] += harf[: 16 - len(self.degerler[0])]
            elif len(self.degerler[self.odak]) < 32:
                self.degerler[self.odak] += harf
            self.mesaj = ("", BEYAZ)
        elif olay.type == pygame.KEYDOWN:
            if olay.key == pygame.K_BACKSPACE:
                self.degerler[self.odak] = self.degerler[self.odak][:-1]
            elif olay.key == pygame.K_TAB:
                adim = -1 if olay.mod & pygame.KMOD_SHIFT else 1
                self.odak = (self.odak + adim) % n
            elif olay.key == pygame.K_DOWN:
                self.odak = min(n - 1, self.odak + 1)
            elif olay.key == pygame.K_UP:
                self.odak = max(0, self.odak - 1)
            elif olay.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.odak < n - 1:
                    self.odak += 1                         # son kutuya gelene kadar ENTER sonraki kutuya geçer
                else:
                    self.gonder()
        elif olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
            konum = self.mantiksal(olay.pos)               # pencere koordinatı -> mantıksal koordinat
            yerlesim = self.giris_yerlesimi()
            if yerlesim["sekme_giris"].collidepoint(konum):
                self.sekme_degistir("giris")
            elif yerlesim["sekme_kayit"].collidepoint(konum):
                self.sekme_degistir("kayit")
            elif yerlesim["gonder"].collidepoint(konum):
                self.gonder()                              # sesi (başarı/hata) gonder() kendisi çalar
            elif yerlesim["onay_kutusu"].inflate(160, 10).collidepoint(konum):
                ses_cal("tik")
                self.sifre_goster = not self.sifre_goster
            else:
                for i, kutu in enumerate(yerlesim["kutular"]):
                    if kutu.collidepoint(konum):
                        if self.odak != i:
                            ses_cal("tik")
                        self.odak = i

    def menu_olayi(self, olay):
        """Oyun menüsü: karta tıklayınca oyun açılır, çıkış düğmesi hesaptan çıkarır."""
        if olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
            konum = self.mantiksal(olay.pos)
            if self.ayar_dikdortgeni().collidepoint(konum):
                self.ayarlar_ac("genel")
                return
            if self.profil_dikdortgeni().collidepoint(konum):
                self.ayarlar_ac("profil")
                return
            if self.cikis_dikdortgeni().collidepoint(konum):
                ses_cal("tik")
                self.durum, self.kullanici = "giris", None
                AYAR.kullanici_sec(None)                   # çıkışta kişisel ayarlar bırakılır, genel dil/tema kalır
                self.dil_degisti()
                self.mod, self.odak = "giris", 0
                self.mesaj = ("cikis.yapildi", TURKUAZ)
                return
            for i, kart in enumerate(self.kart_dikdortgenleri()[: len(OYUNLAR)]):
                if kart.collidepoint(konum):
                    self.oyunu_baslat(OYUNLAR[i])
        elif olay.type == pygame.KEYDOWN and olay.key in (
            pygame.K_1, pygame.K_2, pygame.K_3
        ):
            indeks = olay.key - pygame.K_1
            if indeks < len(OYUNLAR):
                self.oyunu_baslat(OYUNLAR[indeks])

    # --- çizim
    def arka_plan_ciz(self):
        """Seçili temayı pencerenin tamamına çizer (arayüz ortada, arka plan her yöne uzar)."""
        temalar.ciz(AYAR.al("tema"), self.buyuk, self.ofset[0], self.ofset[1], self.bg_zaman)

    def kutu_ciz(self, dikdortgen, etiket, deger, odakta, gizli):
        """Tek bir yazı giriş kutusunu çizer (şifre kutularında noktalar gösterilir)."""
        yazi_yaz(yazi_k, etiket, (150, 170, 210), (dikdortgen.x, dikdortgen.y - 20))
        pygame.draw.rect(tuval, (8, 8, 22), dikdortgen)
        kenar_renk = TURKUAZ if odakta else (70, 80, 120)
        if odakta:
            parlama_ciz(tuval, TURKUAZ, dikdortgen.center, 4)
        pygame.draw.rect(tuval, kenar_renk, dikdortgen, 2)
        gosterilen = ("•" * len(deger)) if (gizli and not self.sifre_goster) else deger
        while gosterilen and yazi_o.size(gosterilen)[0] > dikdortgen.w - 24:   # sığmıyorsa baştan kırp
            gosterilen = gosterilen[1:]
        alan = yazi_yaz(yazi_o, gosterilen, BEYAZ, (dikdortgen.x + 12, dikdortgen.y + 9))
        if odakta and int(self.zaman * 2) % 2 == 0:            # yanıp sönen imleç
            pygame.draw.rect(tuval, TURKUAZ, (alan.right + 2, dikdortgen.y + 8, 2, 24))

    def dugme_ciz(self, dikdortgen, metin, renk, uzerinde):
        """Neon düğme çizer; fare üzerindeyse parlar."""
        parlaklik = 1.0 if uzerinde else 0.75
        pygame.draw.rect(tuval, karart(renk, 0.45 if uzerinde else 0.28), dikdortgen)
        pygame.draw.rect(tuval, karart(renk, parlaklik), dikdortgen, 3)
        if uzerinde:
            parlama_ciz(tuval, renk, dikdortgen.center, dikdortgen.w // 2)
        yazi_yaz(yazi_o, metin, BEYAZ, dikdortgen.center, ortala=True)

    def giris_ciz(self):
        """Giriş / kayıt ekranını çizer."""
        yerlesim = self.giris_yerlesimi()
        kart = yerlesim["kart"]
        panel_ciz(kart, 225)
        pygame.draw.rect(tuval, TURKUAZ, kart, 2)
        yazi_yaz(yazi_b, t("app.baslik"), TURKUAZ, (kart.centerx, kart.y + 42), ortala=True)
        yazi_yaz(yazi_k, t("giris.alt"), (150, 170, 210), (kart.centerx, kart.y + 70), ortala=True)
        for anahtar, etiket, mod in (("sekme_giris", t("sekme.giris"), "giris"), ("sekme_kayit", t("sekme.kayit"), "kayit")):
            dikdortgen = yerlesim[anahtar]
            aktif = self.mod == mod
            pygame.draw.rect(tuval, TURKUAZ if aktif else (24, 24, 50), dikdortgen)
            pygame.draw.rect(tuval, TURKUAZ if aktif else (70, 80, 120), dikdortgen, 2)
            yazi_yaz(yazi_o, etiket, (5, 10, 25) if aktif else (150, 170, 210), dikdortgen.center, ortala=True)
        for i, kutu in enumerate(yerlesim["kutular"]):
            self.kutu_ciz(kutu, self.etiketler()[i], self.degerler[i], self.odak == i, i > 0)
        onay = yerlesim["onay_kutusu"]                         # "Şifreyi göster" kutusu
        pygame.draw.rect(tuval, (70, 80, 120), onay, 2)
        if self.sifre_goster:
            pygame.draw.rect(tuval, TURKUAZ, onay.inflate(-8, -8))
        yazi_yaz(yazi_k, t("sifre.goster"), (150, 170, 210), (onay.right + 10, onay.y + 1))
        metin, renk = self.mesaj
        if metin:
            yazi_yaz(yazi_k, t(metin), renk, yerlesim["mesaj"], ortala=True)
        self.dugme_ciz(yerlesim["gonder"], t("sekme.giris") if self.mod == "giris" else t("sekme.kayit"), YESIL,
                       yerlesim["gonder"].collidepoint(self.fare))
        yazi_yaz(yazi_k, t("ipucu.giris"), (100, 110, 150),
                 (kart.centerx, kart.bottom + 24), ortala=True)

    def menu_ciz(self, gecen):
        """Oyun kartlarının olduğu ana menüyü çizer."""
        parlama_ciz(tuval, ayarlar.AVATAR_RENKLER[AYAR.al("avatar") % ayarlar.AVATAR_SAYISI], (50, 44), 40)
        ayarlar.avatar_ciz(tuval, AYAR.al("avatar"), (50, 44), 24)
        yazi_yaz(yazi_k, t("menu.oyuncu"), (150, 170, 210), (88, 20))
        yazi_yaz(yazi_b, self.kullanici or "", BEYAZ, (88, 36))
        self.dugme_ciz(self.cikis_dikdortgeni(), t("menu.cikis"), KIRMIZI, self.cikis_dikdortgeni().collidepoint(self.fare))
        ayar = self.ayar_dikdortgeni()                          # ayarlar simgesi (dişli, kodla çizilir)
        uzerinde = ayar.collidepoint(self.fare)
        self.dugme_ciz(ayar, " ", TURKUAZ, uzerinde)
        dis_r = 14 + (2 if uzerinde else 0)
        for k in range(8):
            aci = k * math.pi / 4 + self.zaman * (0.8 if uzerinde else 0)
            pygame.draw.line(tuval, BEYAZ, (ayar.centerx + math.cos(aci) * (dis_r - 3), ayar.centery + math.sin(aci) * (dis_r - 3)),
                             (ayar.centerx + math.cos(aci) * (dis_r + 3), ayar.centery + math.sin(aci) * (dis_r + 3)), 4)
        pygame.draw.circle(tuval, BEYAZ, ayar.center, dis_r - 3, 3)
        pygame.draw.circle(tuval, BEYAZ, ayar.center, 4)
        for kayma, renk in ((-3, PEMBE), (3, TURKUAZ)):        # başlıkta renkli gölge (glitch hissi)
            yazi_yaz(yazi_xb, t("app.baslik"), renk, (GENISLIK // 2 + kayma, 120), ortala=True, seffaflik=140)
        yazi_yaz(yazi_xb, t("app.baslik"), BEYAZ, (GENISLIK // 2, 120), ortala=True)
        yazi_yaz(yazi_o, t("menu.sec"), (170, 190, 230), (GENISLIK // 2, 172), ortala=True)
        for i, kart0 in enumerate(self.kart_dikdortgenleri()):
            oyun_mu = i < len(OYUNLAR)                         # son kart oyun değil, "yakında" yer tutucusu
            fare_uzerinde = oyun_mu and kart0.collidepoint(self.fare) and self.durum == "menu"
            self.uzerinde[i] += ((1.0 if fare_uzerinde else 0.0) - self.uzerinde[i]) * min(1, 12 * gecen)   # yumuşak geçiş
            oran = self.uzerinde[i]
            kart = kart0.move(0, -int(12 * oran))               # üzerine gelince kart hafifçe yukarı kalkar
            if oyun_mu:
                oyun = OYUNLAR[i]
                renk = oyun["renk"]
                if oran > 0.02:
                    parlama_ciz(tuval, renk, kart.center, 150 + 60 * oran)
                panel_ciz(kart, 235)
                tuval.blit(self.ikonlar[oyun["kimlik"]], (kart.x, kart.y))
                pygame.draw.line(tuval, renk, (kart.x, kart.y + 190), (kart.right, kart.y + 190), 2)
                pygame.draw.rect(tuval, karart(renk, 0.45 + 0.55 * oran), kart, 3 if oran > 0.5 else 2)
                yazi_yaz(yazi_b, t("oyun." + oyun["kimlik"] + ".baslik"), renk, (kart.centerx, kart.y + 222), ortala=True)
                for j, satir in enumerate(satirlara_bol(t("oyun." + oyun["kimlik"] + ".aciklama"), yazi_k, kart.w - 40)[:4]):
                    yazi_yaz(yazi_k, satir, (190, 200, 230), (kart.centerx, kart.y + 256 + j * 20), ortala=True)
                if oyun.get("rekor"):                           # oyunun rekor dosyası varsa göster
                    try:
                        en_iyi = open(os.path.join(KLASOR, oyun["rekor"])).read().strip()
                        metin = f"{t('menu.rekor')}: {en_iyi}"
                        gen = yazi_k.size(metin)[0]
                        rozet = pygame.Rect(kart.right - gen - 22, kart.y + 8, gen + 16, 24)
                        panel_ciz(rozet, 200)
                        pygame.draw.rect(tuval, YESIL, rozet, 1)
                        yazi_yaz(yazi_k, metin, YESIL, rozet.center, ortala=True)
                    except Exception:
                        pass
                dugme = pygame.Rect(kart.x + 40, kart.bottom - 58, kart.w - 80, 40)
                self.dugme_ciz(dugme, f"{t('menu.oyna')}  [{i + 1}]", renk, fare_uzerinde)
            else:                                               # "YAKINDA" kartı: kesik çizgili çerçeve
                panel_ciz(kart, 120)
                for x in range(kart.x, kart.right, 16):
                    pygame.draw.line(tuval, (70, 70, 110), (x, kart.y), (min(x + 8, kart.right), kart.y))
                    pygame.draw.line(tuval, (70, 70, 110), (x, kart.bottom), (min(x + 8, kart.right), kart.bottom))
                for y in range(kart.y, kart.bottom, 16):
                    pygame.draw.line(tuval, (70, 70, 110), (kart.x, y), (kart.x, min(y + 8, kart.bottom)))
                    pygame.draw.line(tuval, (70, 70, 110), (kart.right, y), (kart.right, min(y + 8, kart.bottom)))
                yazi_yaz(yazi_xb, "?", (80, 90, 130), (kart.centerx, kart.y + 130), ortala=True)
                yazi_yaz(yazi_b, t("menu.yakinda"), (110, 120, 160), (kart.centerx, kart.y + 222), ortala=True)
                yazi_yaz(yazi_k, t("menu.yeni"), (90, 100, 140), (kart.centerx, kart.y + 262), ortala=True)

    def oyun_acik_ciz(self):
        """Oyun çalışırken menünün üstüne bilgi perdesi koyar."""
        perde = pygame.Surface(self.buyuk.get_size(), pygame.SRCALPHA)
        perde.fill((0, 0, 12, 200))
        self.buyuk.blit(perde, (0, 0))
        oyun = self.acik_oyun
        yazi_yaz(yazi_b, t("oyun.acik", oyun=t("oyun." + oyun["kimlik"] + ".baslik")), oyun["renk"], (GENISLIK // 2, YUKSEKLIK // 2 - 30), ortala=True)
        yazi_yaz(yazi_o, t("oyun.donus"), BEYAZ, (GENISLIK // 2, YUKSEKLIK // 2 + 20), ortala=True)

    def adim(self, gecen):
        """Her karede çağrılır: oyun kapandı mı bakar, ekranı çizer."""
        self.zaman += gecen
        if AYAR.al("animasyon"):
            self.bg_zaman += gecen
        if not self.tuval_hazirla():                            # pencere simge durumunda: çizme
            return
        if self.durum == "oyun_acik" and self.surec and self.surec.poll() is not None:   # oyun kapandı
            cikis_kodu = self.surec.returncode
            self.surec, self.durum = None, "menu"
            if cikis_kodu not in (0, None):
                self.bildirim = (t("hata.kapandi"), 4.0, KIRMIZI)
        self.arka_plan_ciz()
        if self.durum == "giris":
            self.giris_ciz()
        elif self.durum == "ayarlar":
            self.ayarlar_ekrani.ciz(self.bg_zaman)
        else:
            self.menu_ciz(gecen)
            if self.durum == "oyun_acik":
                self.oyun_acik_ciz()
        metin, kalan, renk = self.bildirim                      # alttaki geçici bildirim kutusu
        if kalan > 0:
            self.bildirim = (metin, kalan - gecen, renk)
            kutu = pygame.Rect(0, 0, yazi_o.size(metin)[0] + 40, 44)
            kutu.midbottom = (GENISLIK // 2, YUKSEKLIK - 24)
            panel_ciz(kutu, 235)
            pygame.draw.rect(tuval, renk, kutu, 2)
            yazi_yaz(yazi_o, metin, renk, kutu.center, ortala=True, seffaflik=int(255 * min(1, kalan)))
        if AYAR.al("fps"):
            yazi_yaz(yazi_k, f"FPS {saat.get_fps():.0f}", YESIL, (10, YUKSEKLIK - 24))
        self.pencereye_ciz()                                    # tuvali pencere boyutuna ölçekleyip ekrana koy


def ana():
    """Programın giriş noktası."""
    uygulama = Uygulama()
    while True:
        gecen = min(saat.tick(KARE_HIZI) / 1000, 0.033)         # önceki kareden beri geçen süre (sn)
        for olay in pygame.event.get():
            uygulama.olay_isle(olay)
        uygulama.adim(gecen)
        pygame.display.flip()


if __name__ == "__main__":
    ana()
    
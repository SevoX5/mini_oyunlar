"""
OYUN MERKEZİ  -  Kayıt ol / Giriş yap  ->  oyun ikonları  ->  oyunu başlat

Kurulum :  pip install pygame
py -3.12 oyun_merkezi.py

Bu dosya, aşağıdaki oyun dosyalarıyla AYNI KLASÖRDE olmalı:
    neon_storm.py     siber_kacis.py
Kullanıcılar 'kullanicilar.json' dosyasında saklanır (şifreler karıştırılarak / hash'lenerek).
"""
import hashlib
import json
import math
import os
import random
import secrets
import subprocess
import sys
import time

import pygame

GENISLIK, YUKSEKLIK = 1100, 720                       # pencere boyutu
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

OYUNLAR = [   # menüde kart olarak görünen oyunlar (yeni oyun eklemek için buraya bir satır ekle)
    dict(kimlik="neon", baslik="NEON STORM", dosya="neon_storm.py", renk=TURKUAZ,
         aciklama="Neon uzayda dalga dalga düşmanı yok et, güçlen ve boss'u devir."),
    dict(kimlik="siber", baslik="SİBER KAÇIŞ", dosya="siber_kacis.py", renk=PEMBE,
         aciklama="Geleceğin şehrinde robotlarla savaş, görevleri tamamla ve sistemi kurtar.",
         rekor="siber_kacis_rekor.txt"),
]

pygame.init()
pygame.key.start_text_input()                         # Türkçe karakterli yazı girişi (TEXTINPUT olayı) için
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
pygame.display.set_caption("OYUN MERKEZİ")
saat = pygame.time.Clock()
tuval = pygame.Surface((GENISLIK, YUKSEKLIK))         # her şeyin önce çizildiği yüzey
YAZI_TIPI = "dejavusansmono,consolas,couriernew,monospace"
yazi_k = pygame.font.SysFont(YAZI_TIPI, 15, bold=True)   # küçük
yazi_o = pygame.font.SysFont(YAZI_TIPI, 20, bold=True)   # orta
yazi_b = pygame.font.SysFont(YAZI_TIPI, 32, bold=True)   # büyük
yazi_xb = pygame.font.SysFont(YAZI_TIPI, 64, bold=True)  # çok büyük (başlık)


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
    with open(VERITABANI, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False, indent=2)


def sifre_karistir(sifre, tuz_hex):
    """Şifreyi 'tuz' ile PBKDF2 yöntemiyle geri döndürülemez şekilde karıştırır (hash)."""
    return hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), bytes.fromhex(tuz_hex), 150_000).hex()


def kayit_ol(kullanici_adi, sifre, sifre_tekrar):
    """Yeni kullanıcı kaydeder. Döner: (başarılı mı, mesaj, kullanıcı adı)"""
    kullanici_adi = kullanici_adi.strip()
    if len(kullanici_adi) < 3:
        return False, "Kullanıcı adı en az 3 karakter olmalı.", None
    if len(kullanici_adi) > 16:
        return False, "Kullanıcı adı en fazla 16 karakter olabilir.", None
    if len(sifre) < 6:
        return False, "Şifre en az 6 karakter olmalı.", None
    if sifre != sifre_tekrar:
        return False, "Şifreler birbiriyle uyuşmuyor.", None
    veri = veritabani_yukle()
    if kullanici_adi.lower() in veri:                 # büyük/küçük harf fark etmeden aynı ad var mı?
        return False, "Bu kullanıcı adı zaten alınmış.", None
    tuz = secrets.token_hex(16)                       # her kullanıcıya özel rastgele tuz
    veri[kullanici_adi.lower()] = dict(ad=kullanici_adi, tuz=tuz, karisim=sifre_karistir(sifre, tuz),
                                       olusturma=int(time.time()))
    try:
        veritabani_kaydet(veri)
    except OSError:
        return False, "Kayıt dosyası yazılamadı (klasör izni?).", None
    return True, "Kayıt başarılı!", kullanici_adi


def giris_yap(kullanici_adi, sifre):
    """Kullanıcı adı ve şifreyi kontrol eder. Döner: (başarılı mı, mesaj, kullanıcı adı)"""
    kayit = veritabani_yukle().get(kullanici_adi.strip().lower())
    if kayit:   # eski sürümde kaydedilmiş hesaplar (name/salt/hash alanları) da çalışsın
        tuz = kayit.get("tuz", kayit.get("salt"))
        karisim = kayit.get("karisim", kayit.get("hash"))
        ad = kayit.get("ad", kayit.get("name"))
    if not kayit or not secrets.compare_digest(karisim, sifre_karistir(sifre, tuz)):
        return False, "Kullanıcı adı veya şifre hatalı.", None
    return True, "Giriş başarılı!", ad


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
        self.fare = (0, 0)              # son fare konumu (üzerine gelme efektleri için)
        self.surec = None               # çalışan oyunun işlemi (subprocess)
        self.acik_oyun = None           # şu an açık olan oyunun bilgisi
        self.bildirim = ("", 0.0, BEYAZ)  # alttaki geçici bildirim: (metin, kalan süre, renk)
        self.ikonlar = {o["kimlik"]: ikon_olustur(o["kimlik"]) for o in OYUNLAR}
        self.uzerinde = [0.0] * (len(OYUNLAR) + 1)    # her kartın "üzerine gelme" animasyon oranı (0-1)
        self.yildizlar = [(random.randint(0, GENISLIK), random.randint(0, int(YUKSEKLIK * 0.5)), random.randint(1, 3))
                          for _ in range(90)]
        self.izgara_kayma = 0.0         # arka plandaki ızgaranın hareket miktarı

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
        return ["KULLANICI ADI", "ŞİFRE", "ŞİFRE (TEKRAR)"][: self.kutu_sayisi()]

    def kart_dikdortgenleri(self):
        """Menüdeki 3 kartın (2 oyun + 1 'yakında') dikdörtgenleri."""
        genislik, yukseklik, bosluk = 300, 380, 40
        baslangic_x = (GENISLIK - (3 * genislik + 2 * bosluk)) // 2
        return [pygame.Rect(baslangic_x + i * (genislik + bosluk), 215, genislik, yukseklik) for i in range(3)]

    def cikis_dikdortgeni(self):
        return pygame.Rect(GENISLIK - 190, 24, 160, 40)

    # --- işlemler
    def sekme_degistir(self, yeni_mod):
        """Giriş <-> Kayıt sekmesi arasında geçer."""
        if yeni_mod != self.mod:
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
            self.kullanici = ad
            self.durum = "menu"
            self.degerler = ["", "", ""]
            self.mesaj = ("", BEYAZ)
            self.bildirim = (f"Hoş geldin, {ad}!" if self.mod == "giris" else f"Kayıt başarılı! Hoş geldin, {ad}!", 3.0, YESIL)
        else:
            self.mesaj = (mesaj, KIRMIZI)

    def oyunu_baslat(self, oyun):
        """Seçilen oyunu ayrı bir işlem olarak açar; oyun kapanınca menüye dönülür."""
        yol = os.path.join(KLASOR, oyun["dosya"])
        if not os.path.exists(yol):
            self.bildirim = (f"{oyun['dosya']} bulunamadı! Bu dosyayla aynı klasörde olmalı.", 4.0, KIRMIZI)
            return
        try:
            self.surec = subprocess.Popen([sys.executable, yol], cwd=KLASOR)
        except OSError as hata:
            self.bildirim = (f"Oyun başlatılamadı: {hata}", 4.0, KIRMIZI)
            return
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
            self.fare = olay.pos
        if self.durum == "giris":
            self.giris_olayi(olay)
        elif self.durum == "menu":
            self.menu_olayi(olay)

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
            yerlesim = self.giris_yerlesimi()
            if yerlesim["sekme_giris"].collidepoint(olay.pos):
                self.sekme_degistir("giris")
            elif yerlesim["sekme_kayit"].collidepoint(olay.pos):
                self.sekme_degistir("kayit")
            elif yerlesim["gonder"].collidepoint(olay.pos):
                self.gonder()
            elif yerlesim["onay_kutusu"].inflate(160, 10).collidepoint(olay.pos):
                self.sifre_goster = not self.sifre_goster
            else:
                for i, kutu in enumerate(yerlesim["kutular"]):
                    if kutu.collidepoint(olay.pos):
                        self.odak = i

    def menu_olayi(self, olay):
        """Oyun menüsü: karta tıklayınca oyun açılır, çıkış düğmesi hesaptan çıkarır."""
        if olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
            if self.cikis_dikdortgeni().collidepoint(olay.pos):
                self.durum, self.kullanici = "giris", None
                self.mod, self.odak = "giris", 0
                self.mesaj = ("Çıkış yapıldı.", TURKUAZ)
                return
            for i, kart in enumerate(self.kart_dikdortgenleri()[: len(OYUNLAR)]):
                if kart.collidepoint(olay.pos):
                    self.oyunu_baslat(OYUNLAR[i])
        elif olay.type == pygame.KEYDOWN and olay.key in (pygame.K_1, pygame.K_2):   # kısayol: 1 ve 2
            self.oyunu_baslat(OYUNLAR[olay.key - pygame.K_1])

    # --- çizim
    def arka_plan_ciz(self, gecen):
        """Synthwave tarzı hareketli arka plan: yıldızlar, güneş ışıltısı ve ilerleyen ızgara."""
        self.izgara_kayma = (self.izgara_kayma + gecen * 0.35) % 1
        tuval.fill((8, 4, 22))
        ufuk = int(YUKSEKLIK * 0.55)                           # ufuk çizgisinin y konumu
        for x, y, boyut in self.yildizlar:
            parlaklik = 120 + int(100 * math.sin(self.zaman * 2 + x))
            tuval.fill((parlaklik, parlaklik, 255), (x, y, boyut, boyut))
        parlama_ciz(tuval, PEMBE, (GENISLIK // 2, ufuk - 30), 210)
        pygame.draw.rect(tuval, (6, 2, 20), (0, ufuk, GENISLIK, YUKSEKLIK - ufuk))
        for i in range(-16, 17):                               # ufka yaklaşan dikey çizgiler
            pygame.draw.line(tuval, (90, 30, 150), (GENISLIK // 2 + i * 45, ufuk), (GENISLIK // 2 + i * 300, YUKSEKLIK), 1)
        for k in range(14):                                    # bize doğru akan yatay çizgiler
            oran = (k + self.izgara_kayma) / 14
            y = ufuk + (YUKSEKLIK - ufuk) * oran * oran
            pygame.draw.line(tuval, karart((150, 50, 220), 0.25 + oran * 0.75), (0, y), (GENISLIK, y), 1)
        pygame.draw.line(tuval, PEMBE, (0, ufuk), (GENISLIK, ufuk), 2)

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
        yazi_yaz(yazi_b, "OYUN MERKEZİ", TURKUAZ, (kart.centerx, kart.y + 42), ortala=True)
        yazi_yaz(yazi_k, "Oynamak için giriş yap veya kayıt ol", (150, 170, 210), (kart.centerx, kart.y + 70), ortala=True)
        for anahtar, etiket, mod in (("sekme_giris", "GİRİŞ YAP", "giris"), ("sekme_kayit", "KAYIT OL", "kayit")):
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
        yazi_yaz(yazi_k, "Şifreyi göster", (150, 170, 210), (onay.right + 10, onay.y + 1))
        metin, renk = self.mesaj
        if metin:
            yazi_yaz(yazi_k, metin, renk, yerlesim["mesaj"], ortala=True)
        self.dugme_ciz(yerlesim["gonder"], "GİRİŞ YAP" if self.mod == "giris" else "KAYIT OL", YESIL,
                       yerlesim["gonder"].collidepoint(self.fare))
        yazi_yaz(yazi_k, "TAB: sonraki alan   ENTER: gönder", (100, 110, 150), (kart.centerx, kart.bottom + 24), ortala=True)

    def menu_ciz(self, gecen):
        """Oyun kartlarının olduğu ana menüyü çizer."""
        yazi_yaz(yazi_k, "OYUNCU", (150, 170, 210), (30, 22))
        yazi_yaz(yazi_b, self.kullanici or "", BEYAZ, (30, 38))
        self.dugme_ciz(self.cikis_dikdortgeni(), "ÇIKIŞ YAP", KIRMIZI, self.cikis_dikdortgeni().collidepoint(self.fare))
        for kayma, renk in ((-3, PEMBE), (3, TURKUAZ)):        # başlıkta renkli gölge (glitch hissi)
            yazi_yaz(yazi_xb, "OYUN MERKEZİ", renk, (GENISLIK // 2 + kayma, 120), ortala=True, seffaflik=140)
        yazi_yaz(yazi_xb, "OYUN MERKEZİ", BEYAZ, (GENISLIK // 2, 120), ortala=True)
        yazi_yaz(yazi_o, "Bir oyun seç ve oynamaya başla", (170, 190, 230), (GENISLIK // 2, 172), ortala=True)
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
                yazi_yaz(yazi_b, oyun["baslik"], renk, (kart.centerx, kart.y + 222), ortala=True)
                for j, satir in enumerate(satirlara_bol(oyun["aciklama"], yazi_k, kart.w - 40)[:4]):
                    yazi_yaz(yazi_k, satir, (190, 200, 230), (kart.centerx, kart.y + 256 + j * 20), ortala=True)
                if oyun.get("rekor"):                           # oyunun rekor dosyası varsa göster
                    try:
                        en_iyi = open(os.path.join(KLASOR, oyun["rekor"])).read().strip()
                        yazi_yaz(yazi_k, f"REKOR: {en_iyi}", YESIL, (kart.centerx, kart.bottom - 78), ortala=True)
                    except Exception:
                        pass
                dugme = pygame.Rect(kart.x + 40, kart.bottom - 58, kart.w - 80, 40)
                self.dugme_ciz(dugme, f"OYNA  [{i + 1}]", renk, fare_uzerinde)
            else:                                               # "YAKINDA" kartı: kesik çizgili çerçeve
                panel_ciz(kart, 120)
                for x in range(kart.x, kart.right, 16):
                    pygame.draw.line(tuval, (70, 70, 110), (x, kart.y), (min(x + 8, kart.right), kart.y))
                    pygame.draw.line(tuval, (70, 70, 110), (x, kart.bottom), (min(x + 8, kart.right), kart.bottom))
                for y in range(kart.y, kart.bottom, 16):
                    pygame.draw.line(tuval, (70, 70, 110), (kart.x, y), (kart.x, min(y + 8, kart.bottom)))
                    pygame.draw.line(tuval, (70, 70, 110), (kart.right, y), (kart.right, min(y + 8, kart.bottom)))
                yazi_yaz(yazi_xb, "?", (80, 90, 130), (kart.centerx, kart.y + 130), ortala=True)
                yazi_yaz(yazi_b, "YAKINDA", (110, 120, 160), (kart.centerx, kart.y + 222), ortala=True)
                yazi_yaz(yazi_k, "Yeni oyunlar buraya eklenecek", (90, 100, 140), (kart.centerx, kart.y + 262), ortala=True)

    def oyun_acik_ciz(self):
        """Oyun çalışırken menünün üstüne bilgi perdesi koyar."""
        perde = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
        perde.fill((0, 0, 12, 200))
        tuval.blit(perde, (0, 0))
        oyun = self.acik_oyun
        yazi_yaz(yazi_b, f"{oyun['baslik']} AÇIK", oyun["renk"], (GENISLIK // 2, YUKSEKLIK // 2 - 30), ortala=True)
        yazi_yaz(yazi_o, "Oyunu kapattığında buraya geri döneceksin.", BEYAZ, (GENISLIK // 2, YUKSEKLIK // 2 + 20), ortala=True)

    def adim(self, gecen):
        """Her karede çağrılır: oyun kapandı mı bakar, ekranı çizer."""
        self.zaman += gecen
        if self.durum == "oyun_acik" and self.surec and self.surec.poll() is not None:   # oyun kapandı
            cikis_kodu = self.surec.returncode
            self.surec, self.durum = None, "menu"
            if cikis_kodu not in (0, None):
                self.bildirim = ("Oyun beklenmedik şekilde kapandı. pygame kurulu mu?", 4.0, KIRMIZI)
        self.arka_plan_ciz(gecen)
        if self.durum == "giris":
            self.giris_ciz()
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
        ekran.blit(tuval, (0, 0))


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
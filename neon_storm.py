"""
NEON STORM - 2D uzay shooter

SES: Tüm sesler ve müzik oyun açılırken kodla üretilir (ekstra dosya / kütüphane gerekmez).

Kontroller:
  Hareket : WASD / Ok tuşları  (veya fare)
  Ateş    : SPACE / Sol tık (basılı tut)
  Yeniden : R     Çıkış: ESC     Ses aç/kapat: N
"""
import math
import random
import sys
from array import array

import pygame

GENISLIK, YUKSEKLIK = 900, 700   # pencere boyutu
KARE_HIZI = 60                   # saniyedeki kare sayısı

pygame.mixer.pre_init(22050, -16, 1, 512)   # ses sistemi ayarı (pygame.init'ten ÖNCE olmalı)
pygame.init()
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))   # gerçek pencere
pygame.display.set_caption("NEON STORM")
saat = pygame.time.Clock()                                # kare hızını sabitlemek için
tuval = pygame.Surface((GENISLIK, YUKSEKLIK))             # her şey önce buraya çizilir (sarsıntı için)
yazi_tipi = pygame.font.SysFont("consolas", 22, bold=True)   # skor / seviye yazıları
buyuk_yazi = pygame.font.SysFont("consolas", 64, bold=True)  # "OYUN BİTTİ" gibi büyük yazılar
kucuk_yazi = pygame.font.SysFont("consolas", 15, bold=True)  # ses durumu yazısı

TURKUAZ = (0, 230, 255)
PEMBE = (255, 60, 160)
SARI = (255, 220, 60)
YESIL = (80, 255, 140)
TURUNCU = (255, 130, 40)
MOR = (170, 90, 255)
BEYAZ = (255, 255, 255)


# ----------------------------------------------------------------- ses sistemi
class Ses:
    """Tüm ses efektlerini ve arka plan müziğini kodla üretir ve çalar.
    Ses kartı yoksa ya da ses açılamazsa oyun hata vermeden sessiz çalışmaya devam eder."""

    # efekt adı -> aynı efektin art arda çalınabilmesi için en kısa aralık (saniye)
    BEKLEME = {"vurus": 0.05, "dusman_ates": 0.08, "patlama": 0.06, "hasar": 0.2, "guc": 0.1}

    def __init__(self):
        self.acik = False                  # ses sistemi çalışıyor mu?
        self.sessiz = False                # oyuncu N ile kapattı mı?
        self.sesler, self.son_calma = {}, {}
        self.muzik, self.muzik_kanali, self.muzik_seviye = None, None, 0.35
        self.hiz, self.kanal = 22050, 1
        try:
            ayar = pygame.mixer.get_init()
            if not ayar:
                pygame.mixer.init(22050, -16, 1, 512)
                ayar = pygame.mixer.get_init()
            if not ayar or ayar[1] != -16:     # sadece 16 bit işaretli formatı destekliyoruz
                return
            self.hiz, _, self.kanal = ayar
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)       # 0. kanal sadece müzik için ayrıldı
            self.efektleri_uret()
            self.muzik = self.muzik_uret()
            self.muzik_kanali = pygame.mixer.Channel(0)
            self.acik = True
        except Exception as hata:
            print("Ses başlatılamadı, oyun sessiz çalışacak:", hata)
            self.acik = False

    # --- ses sentezi
    def _ton(self, sure, f0, f1=None, dalga="kare", gurultu=0.0, guc=2.0, ses=0.5, filtre=1.0):
        """Tek bir ses parçası üretir (örnek listesi döner).
        f0 -> f1: başlangıç ve bitiş frekansı (kayan ses), dalga: kare/testere/ucgen/sinus,
        gurultu: 0-1 arası beyaz gürültü karışımı, guc: sönme hızı, filtre: küçük değer = boğuk ses."""
        f1 = f0 if f1 is None else f1
        n = max(1, int(sure * self.hiz))
        atak = max(1, int(0.004 * self.hiz))          # patlamasın diye 4 ms yumuşak başlangıç
        faz, y, cikti = 0.0, 0.0, []
        for i in range(n):
            k = i / n
            f = f0 * (f1 / f0) ** k
            faz = (faz + f / self.hiz) % 1.0
            if dalga == "kare":
                s = 1.0 if faz < 0.5 else -1.0
            elif dalga == "testere":
                s = 2 * faz - 1
            elif dalga == "ucgen":
                s = 4 * abs(faz - 0.5) - 1
            else:
                s = math.sin(math.tau * faz)
            if gurultu:
                s = s * (1 - gurultu) + random.uniform(-1, 1) * gurultu
            y += filtre * (s - y)
            zarf = min(1.0, i / atak) * (1 - k) ** guc
            cikti.append(y * zarf * ses)
        return cikti

    def _miks(self, toplam, parcalar, dongu=False):
        """(başlangıç sn, örnekler) çiftlerini tek bir listede üst üste bindirir."""
        n = int(toplam * self.hiz)
        tampon = [0.0] * n
        for bas, veri in parcalar:
            b = int(bas * self.hiz)
            for i, v in enumerate(veri):
                j = b + i
                if j >= n:
                    if not dongu:
                        break
                    j %= n
                tampon[j] += v
        return tampon

    def _sese_cevir(self, tampon, seviye=1.0):
        """Örnek listesini en yüksek noktası sınırın altında kalacak şekilde pygame Sound'a çevirir."""
        en_buyuk = max(1e-6, max(abs(v) for v in tampon))
        k = 0.9 / en_buyuk
        veri = array("h", [int(max(-1.0, min(1.0, v * k)) * 32767) for v in tampon])
        if self.kanal == 2:                           # stereo açılmışsa her örneği iki kez yaz
            stereo = array("h")
            for v in veri:
                stereo.append(v)
                stereo.append(v)
            veri = stereo
        sesim = pygame.mixer.Sound(buffer=veri.tobytes())
        sesim.set_volume(seviye)
        return sesim

    def _arpej(self, notalar, aralik, dalga="ucgen", sure=0.2, ses=0.5):
        """Notaları (Hz) peş peşe, birbirine karışarak çalan kısa melodi."""
        toplam = aralik * len(notalar) + sure
        return self._miks(toplam, [(i * aralik, self._ton(sure, f, f, dalga, 0, 1.3, ses, 0.7))
                                   for i, f in enumerate(notalar)])

    def efektleri_uret(self):
        """Oyundaki bütün ses efektlerini üretir ve 'sesler' sözlüğüne koyar."""
        t, m = self._ton, self._miks
        yap = {
            "ates": (t(0.09, 1400, 500, "kare", 0.03, 2.0, 0.6, 0.6), 0.16),          # oyuncu lazeri
            "dusman_ates": (t(0.14, 600, 220, "ucgen", 0.12, 1.5, 0.7, 0.8), 0.22),
            "vurus": (t(0.05, 900, 500, "kare", 0.5, 2.0, 0.6, 0.8), 0.16),           # düşmana isabet
            "patlama": (m(0.5, [(0, t(0.45, 1, 1, "kare", 1.0, 2.0, 1.0, 0.14)),
                                (0, t(0.35, 110, 40, "sinus", 0, 1.5, 0.9))]), 0.45),  # düşman öldü
            "hasar": (m(1.0, [(0, t(0.9, 1, 1, "kare", 1.0, 1.6, 1.0, 0.08)),
                              (0, t(0.7, 90, 28, "sinus", 0, 1.3, 1.0)),
                              (0, t(0.5, 500, 70, "testere", 0.3, 1.8, 0.5, 0.2))]), 0.7),   # oyuncu can kaybetti
            "kalkan_kir": (m(0.4, [(0, t(0.35, 1600, 200, "kare", 0.4, 1.5, 0.8, 0.6)),
                                   (0, t(0.2, 150, 60, "sinus", 0, 1.5, 0.8))]), 0.45),
            "silah_yukselt": (self._arpej([392, 523, 659, 784], 0.06, "kare", 0.18, 0.5), 0.35),
            "kalkan_al": (self._arpej([440, 660, 880, 1320], 0.07, "ucgen", 0.4, 0.6), 0.40),
            "seviye": (self._arpej([523, 659, 784, 1047, 1319], 0.1, "kare", 0.6, 0.4), 0.40),
            "oyun_bitti": (self._arpej([392, 330, 262, 196], 0.32, "testere", 0.8, 0.5), 0.55),
            "baslat": (t(0.3, 300, 1400, "kare", 0, 1.0, 0.6, 0.6), 0.35),
        }
        for isim, (tampon, seviye) in yap.items():
            self.sesler[isim] = self._sese_cevir(tampon, seviye)

    def muzik_uret(self):
        """Dm - Bb - F - C akor dizisi üzerinde, kendini tekrar eden uzay synthwave müziği üretir."""
        tempo = 128
        vurus = 60 / tempo                     # bir vuruşun süresi (sn)
        adim = vurus / 4                       # 16'lık nota
        olcu = vurus * 4
        toplam = olcu * 4
        nota = lambda midi: 440 * 2 ** ((midi - 69) / 12)   # MIDI nota numarasından frekansa
        basslar = [38, 34, 41, 36]                          # D2, Bb1, F2, C2
        akorlar = [[62, 65, 69, 74], [58, 62, 65, 70], [60, 65, 69, 72], [60, 64, 67, 72]]
        desen = [0, 1, 2, 3, 2, 1, 2, 3]                    # arpej sırası
        onbellek = {}

        def parca(*arg):                                    # aynı sesi tekrar tekrar üretmemek için sakla
            if arg not in onbellek:
                onbellek[arg] = self._ton(*arg)
            return onbellek[arg]

        parcalar = []
        for o in range(4):
            bas_f = nota(basslar[o])
            for s in range(16):
                zaman = o * olcu + s * adim
                if s % 4 == 0:                              # bas davul
                    parcalar.append((zaman, parca(0.2, 130, 45, "sinus", 0, 1.5, 1.0, 1.0)))
                if s in (4, 12):                            # trampet
                    parcalar.append((zaman, parca(0.13, 1, 1, "kare", 1.0, 1.5, 0.5, 0.5)))
                if s % 4 == 2:                              # hi-hat
                    parcalar.append((zaman, parca(0.04, 1, 1, "kare", 1.0, 2.0, 0.22, 0.9)))
                if s % 2 == 0:                              # bas gitar
                    parcalar.append((zaman, parca(adim * 1.8, bas_f, bas_f, "testere", 0, 1.0, 0.55, 0.15)))
                f = nota(akorlar[o][desen[s % 8]])          # arpej
                parcalar.append((zaman, parca(adim * 1.6, f, f, "kare", 0, 2.0, 0.16, 0.5)))
        return self._sese_cevir(self._miks(toplam, parcalar, dongu=True))

    # --- çalma
    def cal(self, isim, bekleme=None):
        """Efekti çalar. 'bekleme': aynı efektin tekrar çalınabilmesi için gereken en kısa süre (sn)."""
        if not self.acik or self.sessiz:
            return
        sesim = self.sesler.get(isim)
        if sesim is None:
            return
        aralik = self.BEKLEME.get(isim, 0.0) if bekleme is None else bekleme
        simdi = pygame.time.get_ticks()
        if simdi - self.son_calma.get(isim, -10000) < aralik * 1000:
            return
        self.son_calma[isim] = simdi
        sesim.play()

    def muzik_baslat(self):
        """Müziği sonsuz döngüde başlatır."""
        if self.acik and self.muzik_kanali:
            self.muzik_kanali.play(self.muzik, loops=-1)
            self.muzik_seviye_ayarla(self.muzik_seviye)

    def muzik_seviye_ayarla(self, seviye):
        """Müziğin sesini ayarlar (sessiz moddaysa 0 kalır)."""
        self.muzik_seviye = seviye
        if self.acik and self.muzik_kanali:
            self.muzik_kanali.set_volume(0.0 if self.sessiz else seviye)

    def sesi_ac_kapat(self):
        """N tuşu: bütün sesleri kapatır / açar."""
        if not self.acik:
            return
        self.sessiz = not self.sessiz
        self.muzik_seviye_ayarla(self.muzik_seviye)
        if self.sessiz:
            for kanal_no in range(1, pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(kanal_no).stop()


ses = Ses()

_parlama_onbellek = {}   # (renk, yarıçap) -> hazır parlama resmi (her seferinde yeniden çizmemek için)


def parlama_sprite_olustur(renk, yaricap):
    """Merkezden dışa doğru sönen yumuşak ışık topu resmi üretir."""
    anahtar = (renk, yaricap)
    if anahtar not in _parlama_onbellek:
        yuzey = pygame.Surface((yaricap * 2, yaricap * 2))
        for i in range(yaricap, 0, -1):
            katsayi = (1 - i / yaricap) ** 2          # dışa doğru koyulaşan oran
            pygame.draw.circle(yuzey, tuple(int(c * katsayi) for c in renk), (yaricap, yaricap), i)
        _parlama_onbellek[anahtar] = yuzey
    return _parlama_onbellek[anahtar]


def parlama_ciz(yuzey, renk, konum, yaricap):
    """Verilen konuma neon parıltısı çizer (renkleri toplayarak)."""
    yaricap = max(2, int(yaricap))
    yuzey.blit(parlama_sprite_olustur(renk, yaricap), (konum[0] - yaricap, konum[1] - yaricap),
               special_flags=pygame.BLEND_ADD)


def cokgen_ciz(yuzey, renk, noktalar, konum, aci=0, kalinlik=2):
    """Merkeze göre verilen noktalardan çokgeni 'aci' kadar döndürüp çizer (gemiler, düşmanlar)."""
    cos_a, sin_a = math.cos(aci), math.sin(aci)
    donmus = [(konum[0] + x * cos_a - y * sin_a, konum[1] + x * sin_a + y * cos_a) for x, y in noktalar]
    pygame.draw.polygon(yuzey, renk, donmus, kalinlik)


class Yildiz:
    """Arka plandaki kayan yıldız. 'derinlik' büyüdükçe yıldız daha yakın: daha hızlı, parlak ve büyük."""

    def __init__(self):
        self.x = random.uniform(0, GENISLIK)
        self.y = random.uniform(0, YUKSEKLIK)
        self.derinlik = random.uniform(0.2, 1.0)

    def guncelle(self, gecen, ek_hiz):
        """Aşağı kaydırır; ekrandan çıkınca tepeden yeniden başlatır."""
        self.y += (60 + ek_hiz) * self.derinlik * gecen
        if self.y > YUKSEKLIK:
            self.y, self.x = 0, random.uniform(0, GENISLIK)

    def ciz(self, yuzey):
        parlaklik = int(60 + 180 * self.derinlik)
        yuzey.fill((parlaklik, parlaklik, min(255, parlaklik + 30)),
                   (self.x, self.y, 1 + self.derinlik * 2, 1 + self.derinlik * 3))


class Parcacik:
    """Patlama ve motor alevi için kısa ömürlü ışıklı parçacık."""

    def __init__(self, konum, hiz, renk, omur, boyut):
        self.konum = pygame.Vector2(konum)   # yeri
        self.hiz = pygame.Vector2(hiz)       # hızı
        self.renk, self.omur, self.maks_omur, self.boyut = renk, omur, omur, boyut   # omur: kalan süre

    def guncelle(self, gecen):
        """Hareket ettirir, yavaşlatır; hâlâ yaşıyorsa True döner."""
        self.konum += self.hiz * gecen
        self.hiz *= 0.985
        self.omur -= gecen
        return self.omur > 0

    def ciz(self, yuzey):
        parlama_ciz(yuzey, self.renk, self.konum, self.boyut * (self.omur / self.maks_omur) + 2)


class Mermi:
    """Oyuncunun ve düşmanların mermisi."""

    def __init__(self, konum, hiz, renk, dost, yaricap=5):
        self.konum, self.hiz = pygame.Vector2(konum), pygame.Vector2(hiz)
        self.renk, self.dost, self.yaricap = renk, dost, yaricap   # dost: oyuncunun mermisi mi?

    def guncelle(self, gecen):
        """İlerletir; ekranın dışına çıktıysa False (silinsin) döner."""
        self.konum += self.hiz * gecen
        return -30 < self.konum.x < GENISLIK + 30 and -30 < self.konum.y < YUKSEKLIK + 30

    def ciz(self, yuzey):
        parlama_ciz(yuzey, self.renk, self.konum, self.yaricap * 3)
        pygame.draw.circle(yuzey, BEYAZ, self.konum, max(2, self.yaricap - 2))


class Dusman:
    """Uzay düşmanı. tur: 0 = düz inen, 1 = zikzak yapan, 2 = nişan alıp ateş eden."""

    def __init__(self, tur):
        self.tur = tur
        self.konum = pygame.Vector2(random.uniform(60, GENISLIK - 60), -40)   # üstten girer
        self.zaman = random.uniform(0, 6)       # hareket / animasyon sayacı
        self.baslangic_x = self.konum.x         # zikzak ve salınım için merkez çizgisi
        self.bekleme = random.uniform(0.5, 1.5) # bir sonraki ateşe kalan süre
        if tur == 0:
            self.can, self.yaricap, self.renk = 1, 18, PEMBE
        elif tur == 1:
            self.can, self.yaricap, self.renk = 2, 20, TURUNCU
        else:
            self.can, self.yaricap, self.renk = 4, 26, SARI
        self.maks_can = self.can
        self.yanip_sonme = 0                    # vurulunca kısa süre beyaz yanar

    def guncelle(self, gecen, oyuncu, mermiler):
        """Türüne göre hareket eder / ateş eder; ekranın altından çıktıysa False döner."""
        self.zaman += gecen
        self.yanip_sonme = max(0, self.yanip_sonme - gecen)
        if self.tur == 0:                       # düz aşağı iner
            self.konum.y += 140 * gecen
        elif self.tur == 1:                     # sinüs dalgası gibi sağa sola salınır
            self.konum.y += 110 * gecen
            self.konum.x = self.baslangic_x + math.sin(self.zaman * 3) * 110
        else:                                   # y=110'da durur, yana salınır, oyuncuya ateş eder
            if self.konum.y < 110:
                self.konum.y += 120 * gecen
            self.konum.x = self.baslangic_x + math.sin(self.zaman * 1.2) * 200
            self.bekleme -= gecen
            if self.bekleme <= 0:
                self.bekleme = 1.4
                yon = (oyuncu.konum - self.konum).normalize()   # oyuncuya doğru yön
                mermiler.append(Mermi(self.konum, yon * 280, TURUNCU, False))
                ses.cal("dusman_ates")
        self.konum.x = max(self.yaricap, min(GENISLIK - self.yaricap, self.konum.x))
        return self.konum.y < YUKSEKLIK + 60

    def ciz(self, yuzey):
        renk = BEYAZ if self.yanip_sonme > 0 else self.renk
        parlama_ciz(yuzey, self.renk, self.konum, self.yaricap * 2)
        r = self.yaricap
        if self.tur == 0:       # ters üçgen
            cokgen_ciz(yuzey, renk, [(0, r), (r, -r), (-r, -r)], self.konum, 0, 3)
        elif self.tur == 1:     # dönen elmas
            cokgen_ciz(yuzey, renk, [(0, r), (r, 0), (0, -r), (-r, 0)], self.konum, self.zaman * 2, 3)
        else:                   # dönen kare + merkez halka
            cokgen_ciz(yuzey, renk, [(r, r), (r, -r), (-r, -r), (-r, r)], self.konum, self.zaman, 3)
            pygame.draw.circle(yuzey, renk, self.konum, 6, 2)


class GucArtirma:
    """Düşmandan düşen güç artırma: 'W' = silah güçlenir, 'S' = kalkan verir."""

    def __init__(self, konum, tur):
        self.konum, self.tur, self.zaman = pygame.Vector2(konum), tur, 0
        self.renk = YESIL if tur == "W" else TURKUAZ

    def guncelle(self, gecen):
        """Aşağı düşer; ekrandan çıkınca False döner."""
        self.zaman += gecen
        self.konum.y += 90 * gecen
        return self.konum.y < YUKSEKLIK + 30

    def ciz(self, yuzey):
        parlama_ciz(yuzey, self.renk, self.konum, 26 + math.sin(self.zaman * 6) * 4)
        pygame.draw.circle(yuzey, self.renk, self.konum, 14, 2)
        harf = yazi_tipi.render(self.tur, True, BEYAZ)
        yuzey.blit(harf, harf.get_rect(center=self.konum))


class Oyuncu:
    """Oyuncunun uzay gemisi."""

    def __init__(self):
        self.konum = pygame.Vector2(GENISLIK / 2, YUKSEKLIK - 100)
        self.can, self.silah_seviyesi = 3, 1    # can: kalan can sayısı, silah_seviyesi: 1-3 (mermi sayısı)
        self.kalkan = 0                         # kalkanın kalan süresi (sn)
        self.dokunulmazlik = 0                  # hasar sonrası kısa süre dokunulmazlık
        self.ates_bekleme = 0                   # bir sonraki ateşe kalan süre
        self.yaricap = 14                       # çarpışma yarıçapı

    def guncelle(self, gecen, tuslar, mermiler, parcaciklar):
        """Klavye / fare ile hareket, otomatik ateş ve motor alevi."""
        yon = pygame.Vector2(
            (tuslar[pygame.K_d] or tuslar[pygame.K_RIGHT]) - (tuslar[pygame.K_a] or tuslar[pygame.K_LEFT]),
            (tuslar[pygame.K_s] or tuslar[pygame.K_DOWN]) - (tuslar[pygame.K_w] or tuslar[pygame.K_UP]),
        )
        if yon.length() > 0:                    # klavye varsa klavye ile hareket
            self.konum += yon.normalize() * 400 * gecen
        elif pygame.mouse.get_rel() != (0, 0) or pygame.mouse.get_focused():
            fare = pygame.Vector2(pygame.mouse.get_pos())   # klavye yoksa fareyi yumuşakça takip et
            if pygame.mouse.get_pressed()[0] or (fare - self.konum).length() > 3 and pygame.mouse.get_rel() != (0, 0):
                self.konum += (fare - self.konum) * min(1, 10 * gecen)
        self.konum.x = max(20, min(GENISLIK - 20, self.konum.x))   # ekran dışına çıkma
        self.konum.y = max(20, min(YUKSEKLIK - 20, self.konum.y))
        self.ates_bekleme -= gecen
        self.kalkan = max(0, self.kalkan - gecen)
        self.dokunulmazlik = max(0, self.dokunulmazlik - gecen)
        if (tuslar[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]) and self.ates_bekleme <= 0:
            self.ates_bekleme = 0.13
            ses.cal("ates", 0)
            acilar = {1: [0], 2: [-0.08, 0.08], 3: [-0.2, 0, 0.2]}[min(3, self.silah_seviyesi)]   # seviyeye göre yelpaze
            for aci in acilar:
                hiz = pygame.Vector2(0, -720).rotate_rad(aci)
                mermiler.append(Mermi(self.konum + (0, -18), hiz, TURKUAZ, True, 4))
        parcaciklar.append(Parcacik(self.konum + (random.uniform(-4, 4), 14),     # motor alevi
                                    (random.uniform(-30, 30), 220), TURUNCU, 0.35, 8))

    def ciz(self, yuzey):
        if self.dokunulmazlik > 0 and int(self.dokunulmazlik * 14) % 2:
            return                                # hasar alınca yanıp sönme
        parlama_ciz(yuzey, TURKUAZ, self.konum, 40)
        cokgen_ciz(yuzey, TURKUAZ, [(0, -22), (16, 16), (0, 8), (-16, 16)], self.konum, 0, 3)
        if self.kalkan > 0:
            parlama_ciz(yuzey, TURKUAZ, self.konum, 44)
            pygame.draw.circle(yuzey, TURKUAZ, self.konum, 30, 2)


def patlat(parcaciklar, konum, renk, adet=28, en_yuksek_hiz=300):
    """Verilen yerde renkli parçacık patlaması oluşturur."""
    for _ in range(adet):
        aci = random.uniform(0, math.tau)
        hiz = random.uniform(40, en_yuksek_hiz)
        parcaciklar.append(Parcacik(konum, (math.cos(aci) * hiz, math.sin(aci) * hiz), renk,
                                    random.uniform(0.3, 0.9), random.uniform(6, 14)))


def ana():
    """Oyunun ana döngüsü: olaylar, güncelleme, çarpışmalar, çizim."""
    yildizlar = [Yildiz() for _ in range(120)]
    rekor = 0

    def sifirla():
        """Yeni oyun için başlangıç durumunu döndürür."""
        # oyuncu, mermiler, düşmanlar, parçacıklar, güç artırmalar, skor, doğma sayacı, sarsıntı
        return Oyuncu(), [], [], [], [], 0, 0.5, 0.0

    oyuncu, mermiler, dusmanlar, parcaciklar, guc_artirmalar, skor, dogma_sayaci, sarsinti = sifirla()
    durum = "oyun"   # "oyun" veya "bitti"
    onceki_seviye = 1                      # seviye atlayınca ses çalmak için
    ses.muzik_baslat()
    ses.muzik_seviye_ayarla(0.35)

    while True:
        gecen = min(saat.tick(KARE_HIZI) / 1000, 0.033)   # önceki kareden beri geçen süre (sn)
        for olay in pygame.event.get():
            if olay.type == pygame.QUIT or (olay.type == pygame.KEYDOWN and olay.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if olay.type == pygame.KEYDOWN and olay.key == pygame.K_n:   # N: sesi aç / kapat
                ses.sesi_ac_kapat()
            if olay.type == pygame.KEYDOWN and olay.key == pygame.K_r and durum == "bitti":
                oyuncu, mermiler, dusmanlar, parcaciklar, guc_artirmalar, skor, dogma_sayaci, sarsinti = sifirla()
                durum = "oyun"
                ses.cal("baslat", 0)
                ses.muzik_seviye_ayarla(0.35)

        seviye = 1 + skor // 1500                         # skor arttıkça seviye yükselir
        if seviye > onceki_seviye and durum == "oyun":
            ses.cal("seviye", 0)
        onceki_seviye = seviye
        for yildiz in yildizlar:
            yildiz.guncelle(gecen, seviye * 15)

        if durum == "oyun":
            tuslar = pygame.key.get_pressed()
            oyuncu.guncelle(gecen, tuslar, mermiler, parcaciklar)

            # düşman doğurma: seviye arttıkça daha sık, daha zor türler
            dogma_sayaci -= gecen
            if dogma_sayaci <= 0:
                dogma_sayaci = max(0.35, 1.1 - seviye * 0.07)
                tur = random.choices([0, 1, 2], [5, 3 + seviye * 0.3, 1 + seviye * 0.4])[0]
                dusmanlar.append(Dusman(tur))

            mermiler[:] = [m for m in mermiler if m.guncelle(gecen)]
            dusmanlar[:] = [d for d in dusmanlar if d.guncelle(gecen, oyuncu, mermiler)]
            guc_artirmalar[:] = [g for g in guc_artirmalar if g.guncelle(gecen)]

            # oyuncunun mermisi bir düşmana değdi mi?
            for mermi in [m for m in mermiler if m.dost]:
                for dusman in dusmanlar:
                    if (mermi.konum - dusman.konum).length() < dusman.yaricap + mermi.yaricap:
                        dusman.can -= 1
                        dusman.yanip_sonme = 0.06
                        patlat(parcaciklar, mermi.konum, TURKUAZ, 4, 120)
                        if mermi in mermiler:
                            mermiler.remove(mermi)
                        if dusman.can <= 0:                # düşman öldü
                            patlat(parcaciklar, dusman.konum, dusman.renk, 30, 300)
                            ses.cal("patlama")
                            sarsinti = max(sarsinti, 5)
                            skor += 100 * dusman.maks_can
                            if random.random() < 0.12:     # %12 ihtimalle güç artırma düşer
                                guc_artirmalar.append(GucArtirma(dusman.konum, random.choice("WS")))
                            dusmanlar.remove(dusman)
                        else:
                            ses.cal("vurus")               # öldürmeyen isabet
                        break

            # oyuncu hasar alıyor mu? (düşman mermisi veya düşmanla çarpışma)
            if oyuncu.dokunulmazlik <= 0:
                vuruldu = any((m.konum - oyuncu.konum).length() < oyuncu.yaricap + m.yaricap for m in mermiler if not m.dost)
                vuruldu = vuruldu or any((d.konum - oyuncu.konum).length() < oyuncu.yaricap + d.yaricap for d in dusmanlar)
                if vuruldu:
                    if oyuncu.kalkan > 0:                  # kalkan hasarı yutar
                        oyuncu.kalkan = 0
                        oyuncu.dokunulmazlik = 1.0
                        patlat(parcaciklar, oyuncu.konum, TURKUAZ, 30)
                        ses.cal("kalkan_kir", 0)
                    else:
                        oyuncu.can -= 1
                        oyuncu.dokunulmazlik = 2.0
                        oyuncu.silah_seviyesi = max(1, oyuncu.silah_seviyesi - 1)
                        sarsinti = 22
                        patlat(parcaciklar, oyuncu.konum, TURKUAZ, 60, 400)
                        mermiler[:] = [m for m in mermiler if m.dost]   # ekrandaki düşman mermilerini temizle
                        if oyuncu.can <= 0:
                            durum = "bitti"
                            rekor = max(rekor, skor)
                            ses.cal("oyun_bitti", 0)
                            ses.muzik_seviye_ayarla(0.10)
                        else:
                            ses.cal("hasar", 0)

            for guc in guc_artirmalar[:]:                  # güç artırma toplama
                if (guc.konum - oyuncu.konum).length() < 32:
                    if guc.tur == "W":
                        oyuncu.silah_seviyesi = min(3, oyuncu.silah_seviyesi + 1)
                        ses.cal("silah_yukselt", 0)
                    else:
                        oyuncu.kalkan = 8
                        ses.cal("kalkan_al", 0)
                    patlat(parcaciklar, guc.konum, guc.renk, 20, 200)
                    guc_artirmalar.remove(guc)

        parcaciklar[:] = [p for p in parcaciklar if p.guncelle(gecen)]
        sarsinti = max(0, sarsinti - 40 * gecen)

        # --- çizim
        tuval.fill((6, 4, 18))
        for yildiz in yildizlar:
            yildiz.ciz(tuval)
        for guc in guc_artirmalar:
            guc.ciz(tuval)
        for dusman in dusmanlar:
            dusman.ciz(tuval)
        for mermi in mermiler:
            mermi.ciz(tuval)
        if durum == "oyun":
            oyuncu.ciz(tuval)
        for parcacik in parcaciklar:
            parcacik.ciz(tuval)

        tuval.blit(yazi_tipi.render(f"SKOR {skor}", True, BEYAZ), (16, 12))
        tuval.blit(yazi_tipi.render(f"SEVİYE {seviye}", True, SARI), (GENISLIK // 2 - 50, 12))
        tuval.blit(yazi_tipi.render(f"REKOR {rekor}", True, YESIL), (GENISLIK - 170, 12))
        for i in range(max(0, oyuncu.can)):                # kalan canlar (küçük gemi simgeleri)
            cokgen_ciz(tuval, TURKUAZ, [(0, -9), (7, 7), (0, 3), (-7, 7)], (24 + i * 26, 56), 0, 2)
        if ses.acik:                                       # sol altta ses durumu
            tuval.blit(kucuk_yazi.render("N : SES KAPALI" if ses.sessiz else "N : SES AÇIK", True, (110, 120, 160)),
                       (16, YUKSEKLIK - 26))

        if durum == "bitti":
            yazi = buyuk_yazi.render("OYUN BİTTİ", True, PEMBE)
            tuval.blit(yazi, yazi.get_rect(center=(GENISLIK / 2, YUKSEKLIK / 2 - 30)))
            yazi = yazi_tipi.render("Yeniden başlamak için R", True, BEYAZ)
            tuval.blit(yazi, yazi.get_rect(center=(GENISLIK / 2, YUKSEKLIK / 2 + 30)))

        kayma_x, kayma_y = ((random.uniform(-sarsinti, sarsinti), random.uniform(-sarsinti, sarsinti))
                            if sarsinti else (0, 0))      # ekran sarsıntısı: tuvali rastgele kaydır
        ekran.fill((0, 0, 0))
        ekran.blit(tuval, (kayma_x, kayma_y))
        pygame.display.flip()


if __name__ == "__main__":
    ana()

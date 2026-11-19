"""
NEON STORM - 2D uzay shooter


Kontroller:
  Hareket : WASD / Ok tuşları  (veya fare)
  Ateş    : SPACE / Sol tık (basılı tut)
  Yeniden : R     Çıkış: ESC
"""
import math
import random
import sys

import pygame

GENISLIK, YUKSEKLIK = 900, 700   # pencere boyutu
KARE_HIZI = 60                   # saniyedeki kare sayısı

pygame.init()
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))   # gerçek pencere
pygame.display.set_caption("NEON STORM")
saat = pygame.time.Clock()                                # kare hızını sabitlemek için
tuval = pygame.Surface((GENISLIK, YUKSEKLIK))             # her şey önce buraya çizilir (sarsıntı için)
yazi_tipi = pygame.font.SysFont("consolas", 22, bold=True)   # skor / seviye yazıları
buyuk_yazi = pygame.font.SysFont("consolas", 64, bold=True)  # "OYUN BİTTİ" gibi büyük yazılar

TURKUAZ = (0, 230, 255)
PEMBE = (255, 60, 160)
SARI = (255, 220, 60)
YESIL = (80, 255, 140)
TURUNCU = (255, 130, 40)
MOR = (170, 90, 255)
BEYAZ = (255, 255, 255)

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

    while True:
        gecen = min(saat.tick(KARE_HIZI) / 1000, 0.033)   # önceki kareden beri geçen süre (sn)
        for olay in pygame.event.get():
            if olay.type == pygame.QUIT or (olay.type == pygame.KEYDOWN and olay.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if olay.type == pygame.KEYDOWN and olay.key == pygame.K_r and durum == "bitti":
                oyuncu, mermiler, dusmanlar, parcaciklar, guc_artirmalar, skor, dogma_sayaci, sarsinti = sifirla()
                durum = "oyun"

        seviye = 1 + skor // 1500                         # skor arttıkça seviye yükselir
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
                            sarsinti = max(sarsinti, 5)
                            skor += 100 * dusman.maks_can
                            if random.random() < 0.12:     # %12 ihtimalle güç artırma düşer
                                guc_artirmalar.append(GucArtirma(dusman.konum, random.choice("WS")))
                            dusmanlar.remove(dusman)
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

            for guc in guc_artirmalar[:]:                  # güç artırma toplama
                if (guc.konum - oyuncu.konum).length() < 32:
                    if guc.tur == "W":
                        oyuncu.silah_seviyesi = min(3, oyuncu.silah_seviyesi + 1)
                    else:
                        oyuncu.kalkan = 8
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
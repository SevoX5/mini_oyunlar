"""
OYUN BAŞLATICI  -  oyun_merkezi.py oyunları bu dosya üzerinden açar.

Kullanım (oyun merkezi otomatik yapar):   python oyun_baslatici.py <oyun_dosyasi.py> <oyun_kimligi>

Ne yapar? Kullanıcının ayarlardan seçtiği tuşları okur ve oyun açılmadan önce pygame'in klavye girişini
"çevirir": kullanıcı örneğin SOL yerine J tuşunu seçtiyse, J'ye basıldığında oyun SOL tuşuna basılmış gibi görür.
Böylece oyun dosyalarını değiştirmeden tuş atamaları gerçekten çalışır. Ayarlarda değişiklik yapılmamışsa
hiçbir şeye dokunulmaz, oyun eskisi gibi çalışır.
"""
import os
import runpy
import sys

import pygame

KLASOR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KLASOR)
import ayarlar  # noqa: E402


class TusDizisi:
    """pygame.key.get_pressed() sonucunun yerine geçen, tuşları çeviren nesne."""

    def __init__(self, gercek, acik, engel):
        self.gercek, self.acik, self.engel = gercek, acik, engel

    def __getitem__(self, tus):
        if tus in self.acik:
            return True
        if tus in self.engel:
            return False
        return self.gercek[tus]


def kopru_kur(esle, engel):
    orijinal_basili = pygame.key.get_pressed
    orijinal_al, orijinal_bak = pygame.event.get, pygame.event.poll
    bekleyen = []

    def basili():
        gercek = orijinal_basili()
        acik = set()
        for kod, yerli in esle.items():
            if gercek[kod]:
                acik.update(yerli)
        return TusDizisi(gercek, acik, engel)

    def cevir(olay):
        if olay.type in (pygame.KEYDOWN, pygame.KEYUP):
            if olay.key in esle:                                   # kullanıcının tuşu -> oyunun beklediği tuş
                return [pygame.event.Event(olay.type, {**olay.dict, "key": esle[olay.key][0]})]
            if olay.key in engel:                                  # eski (artık atanmamış) tuş kapalı
                return []
        return [olay]

    def al(*arg, **kw):
        sonuc = []
        for olay in orijinal_al(*arg, **kw):
            sonuc.extend(cevir(olay))
        return sonuc

    def bak():
        while not bekleyen:
            olay = orijinal_bak()
            if olay.type == pygame.NOEVENT:
                return olay
            bekleyen.extend(cevir(olay))
        return bekleyen.pop(0)

    pygame.key.get_pressed, pygame.event.get, pygame.event.poll = basili, al, bak


def main():
    if len(sys.argv) < 3:
        sys.exit("Kullanım: python oyun_baslatici.py <oyun_dosyasi.py> <oyun_kimligi>")
    dosya, kimlik = os.path.abspath(sys.argv[1]), sys.argv[2]
    pygame.display.init()                                          # tuş adlarını çözmek için gerekli
    try:
        esle, engel = ayarlar.tus_donusumu(os.environ.get("OYUN_MERKEZI_KULLANICI", ""), kimlik)
    except Exception:
        esle, engel = {}, set()                                    # ayar okunamazsa oyun yine de açılsın
    if esle or engel:
        kopru_kur(esle, engel)
    sys.argv = [dosya]
    sys.path.insert(0, os.path.dirname(dosya))
    runpy.run_path(dosya, run_name="__main__")


if __name__ == "__main__":
    main()
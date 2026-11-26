"""
AYARLAR SİSTEMİ  (oyun_merkezi.py tarafından kullanılır)

İçinde:
  * t()            : çok dilli metin (Türkçe / English)  -> yeni dil/metin eklemek için _M sözlüğü
  * AyarDeposu     : kullanıcıya özel ayarların 'ayarlar.json' içinde saklanması
  * avatar_ciz()   : kodla çizilen avatarlar
  * OYUN_KONTROLLERI / tus_donusumu() : oyun başına tuş atamaları (oyun_baslatici.py bunu okur)
  * AyarlarEkrani  : sekmeli ayarlar arayüzü (Genel, Görünüm, Dil, Profil, Kontroller)

Yeni oyun eklemek -> OYUN_KONTROLLERI'ne bir satır. Yeni tema -> temalar.py. Yeni metin -> _M.
"""
import copy
import json
import math
import os

import pygame

KLASOR = os.path.dirname(os.path.abspath(__file__))
AYAR_DOSYASI = os.path.join(KLASOR, "ayarlar.json")

TURKUAZ, PEMBE, SARI, YESIL = (0, 235, 255), (255, 50, 150), (255, 225, 70), (80, 255, 150)
TURUNCU, MOR, KIRMIZI, BEYAZ = (255, 140, 40), (175, 95, 255), (255, 80, 90), (255, 255, 255)
SOLUK = (150, 170, 210)

# ----------------------------------------------------------------- diller
# "anahtar": (Türkçe, English)
_M = {
    "app.baslik": ("OYUN MERKEZİ", "GAME HUB"),
    "giris.alt": ("Oynamak için giriş yap veya kayıt ol", "Log in or sign up to play"),
    "sekme.giris": ("GİRİŞ YAP", "LOG IN"), "sekme.kayit": ("KAYIT OL", "SIGN UP"),
    "et.kullanici": ("KULLANICI ADI", "USERNAME"), "et.sifre": ("ŞİFRE", "PASSWORD"),
    "et.sifre2": ("ŞİFRE (TEKRAR)", "PASSWORD (AGAIN)"),
    "sifre.goster": ("Şifreyi göster", "Show password"),
    "ipucu.giris": ("TAB: sonraki alan   ENTER: gönder   F11: tam ekran", "TAB: next field   ENTER: submit   F11: fullscreen"),
    "hata.ad_kisa": ("Kullanıcı adı en az 3 karakter olmalı.", "Username must be at least 3 characters."),
    "hata.ad_uzun": ("Kullanıcı adı en fazla 16 karakter olabilir.", "Username can be at most 16 characters."),
    "hata.sifre_kisa": ("Şifre en az 6 karakter olmalı.", "Password must be at least 6 characters."),
    "hata.sifre_uyusmuyor": ("Şifreler birbiriyle uyuşmuyor.", "Passwords do not match."),
    "hata.ad_alinmis": ("Bu kullanıcı adı zaten alınmış.", "This username is already taken."),
    "hata.yazilamadi": ("Kayıt dosyası yazılamadı (klasör izni?).", "Could not write the save file (folder permission?)."),
    "hata.giris": ("Kullanıcı adı veya şifre hatalı.", "Wrong username or password."),
    "hata.hesap_yok": ("Hesap bulunamadı.", "Account not found."),
    "bildirim.giris": ("Hoş geldin, {ad}!", "Welcome, {ad}!"),
    "bildirim.kayit": ("Kayıt başarılı! Hoş geldin, {ad}!", "Registration successful! Welcome, {ad}!"),
    "cikis.yapildi": ("Çıkış yapıldı.", "Logged out."),
    "menu.oyuncu": ("OYUNCU", "PLAYER"), "menu.cikis": ("ÇIKIŞ YAP", "LOG OUT"),
    "menu.sec": ("Bir oyun seç ve oynamaya başla", "Pick a game and start playing"),
    "menu.oyna": ("OYNA", "PLAY"), "menu.yakinda": ("YAKINDA", "COMING SOON"),
    "menu.yeni": ("Yeni oyunlar buraya eklenecek", "New games will be added here"),
    "menu.rekor": ("REKOR", "RECORD"),
    "oyun.neon.baslik": ("NEON STORM", "NEON STORM"), "oyun.siber.baslik": ("SİBER KAÇIŞ", "CYBER ESCAPE"),
    "oyun.neon.aciklama": ("Neon uzayda dalga dalga düşmanı yok et, güçlen ve boss'u devir.",
                           "Destroy enemies wave after wave in neon space, power up and take down the boss."),
    "oyun.siber.aciklama": ("Geleceğin şehrinde robotlarla savaş, görevleri tamamla ve sistemi kurtar.",
                            "Fight robots in the city of the future, complete missions and save the system."),
    "oyun.flappy.baslik": ("FLAPPY BIRD", "FLAPPY BIRD"),
    "oyun.flappy.aciklama": (
        "Kuşu boruların arasından geçir ve en yüksek skoru yap.",
        "Guide the bird through the pipes and get the highest score.",
    ),
    
    "oyun.acik": ("{oyun} AÇIK", "{oyun} IS RUNNING"),
    "oyun.donus": ("Oyunu kapattığında buraya geri döneceksin.", "You will return here when you close the game."),
    "hata.dosya": ("{dosya} bulunamadı! Bu dosyayla aynı klasörde olmalı.", "{dosya} not found! It must be in the same folder as this file."),
    "hata.baslatilamadi": ("Oyun başlatılamadı: {hata}", "Could not start the game: {hata}"),
    "hata.kapandi": ("Oyun beklenmedik şekilde kapandı. pygame kurulu mu?", "The game closed unexpectedly. Is pygame installed?"),
    # ayarlar ekranı
    "ayar.baslik": ("AYARLAR", "SETTINGS"), "ayar.geri": ("GERİ", "BACK"),
    "sekme.genel": ("GENEL", "GENERAL"), "sekme.gorunum": ("GÖRÜNÜM", "APPEARANCE"), "sekme.dil": ("DİL", "LANGUAGE"),
    "sekme.profil": ("PROFİL", "PROFILE"), "sekme.kontroller": ("KONTROLLER", "CONTROLS"),
    "genel.ses": ("Ses efektleri", "Sound effects"), "genel.animasyon": ("Arka plan animasyonu", "Background animation"),
    "genel.fps": ("FPS göstergesi", "FPS counter"), "genel.tam": ("Tam ekran (F11)", "Fullscreen (F11)"),
    "genel.tam_btn": ("AÇ / KAPAT", "TOGGLE"),
    "genel.ipucu": ("Pencereyi kenarından sürükleyerek de boyutlandırabilirsin.", "You can also resize the window by dragging its edge."),
    "gor.uygula": ("TEMAYI UYGULA", "APPLY THEME"), "gor.uygulandi": ("UYGULANDI", "APPLIED"),
    "gor.aktif": ("Aktif tema: {tema}", "Active theme: {tema}"),
    "tema.varsayilan": ("Varsayılan", "Default"), "tema.uzay": ("Uzay", "Space"), "tema.neon_sehir": ("Neon Şehir", "Neon City"),
    "tema.siberpunk": ("Siberpunk", "Cyberpunk"), "tema.galaksi": ("Galaksi ve Yıldızlar", "Galaxy & Stars"),
    "tema.doga": ("Doğa", "Nature"), "tema.karanlik": ("Karanlık", "Dark"),
    "dil.baslik": ("Dil seçin", "Select language"), "dil.not": ("Tüm yazılar anında değişir.", "All text changes instantly."),
    "profil.ad": ("KULLANICI ADI", "USERNAME"), "profil.avatar": ("AVATAR SEÇ", "CHOOSE AVATAR"),
    "profil.kaydet": ("PROFİLİ KAYDET", "SAVE PROFILE"), "ok.profil": ("Profil kaydedildi!", "Profile saved!"),
    "kon.sifirla": ("VARSAYILANA DÖN", "RESET TO DEFAULT"), "kon.birinci": ("Birincil tuş", "Primary key"),
    "kon.ikinci": ("İkincil tuş", "Secondary key"), "kon.bekle": ("Bir tuşa bas...", "Press a key..."),
    "kon.ipucu": ("Bir tuş kutusuna tıkla, sonra yeni tuşa bas.  ESC: iptal   DEL: temizle",
                  "Click a key box, then press the new key.  ESC: cancel   DEL: clear"),
    "kon.not": ("Tuşlar oyun başlatılırken uygulanır; açık oyunu kapatıp yeniden aç.",
                "Keys are applied when a game starts; restart a running game."),
    "kon.cakisma": ("'{tus}' tuşu zaten '{eylem}' için kullanılıyor!", "Key '{tus}' is already used for '{eylem}'!"),
    "kon.atandi": ("{eylem}: {tus} olarak atandı.", "{eylem} set to {tus}."),
    "kon.sifirlandi": ("Bu oyunun tuşları varsayılana döndü.", "This game's keys were reset to default."),
    "kon.en_az": ("Her eylemde en az bir tuş kalmalı.", "Each action needs at least one key."),
    "kon.gecersiz": ("Bu tuş atanamaz.", "This key cannot be assigned."),
    "kon.temizlendi": ("Tuş temizlendi.", "Key cleared."),
    "eylem.yukari": ("Yukarı hareket", "Move up"), "eylem.asagi": ("Aşağı hareket", "Move down"),
    "eylem.sol": ("Sola hareket", "Move left"), "eylem.sag": ("Sağa hareket", "Move right"),
    "eylem.ates": ("Ateş etme", "Fire"),
}
DILLER = [("tr", "Türkçe"), ("en", "English")]
_dil = "tr"


def dil_ayarla(kod):
    global _dil
    _dil = kod if kod in ("tr", "en") else "tr"


def t(anahtar, **kw):
    """Seçili dile göre metni döndürür (anahtar yoksa anahtarın kendisini döndürür)."""
    v = _M.get(anahtar)
    s = anahtar if v is None else v[0 if _dil == "tr" else 1]
    return s.format(**kw) if kw else s


# ----------------------------------------------------------------- tuş tanımları
KONTROL_VARSAYILAN = {"yukari": ["w", "up"], "asagi": ["s", "down"], "sol": ["a", "left"],
                      "sag": ["d", "right"], "ates": ["space", ""]}        # her eylem: [birincil, ikincil]
OYUN_KONTROLLERI = {"neon": copy.deepcopy(KONTROL_VARSAYILAN),               # oyun kimliği -> eylemler
                    "siber": copy.deepcopy(KONTROL_VARSAYILAN)}              # (oyuna özel eylem/varsayılan eklenebilir)


def _kodlar(isimler):
    sonuc = []
    for isim in isimler:
        if isim:
            try:
                sonuc.append(pygame.key.key_code(isim))
            except ValueError:
                pass
    return sonuc


def tus_donusumu(kullanici, oyun):
    """oyun_baslatici.py için: diskteki ayarları okur.
    Döner: (esle, engel)  esle: {kullanıcının tuşu: [oyunun beklediği orijinal tuşlar]},  engel: kapatılacak orijinal tuşlar.
    Varsayılandan farklı atanmamış eylemlere dokunulmaz (eski tuşlar aynen çalışır)."""
    kayit = _json_yukle().get((kullanici or "").lower(), {})
    kayitli = kayit.get("tuslar", {}).get(oyun, {}) if isinstance(kayit, dict) else {}
    esle, engel = {}, set()
    for eylem, varsayilan in OYUN_KONTROLLERI.get(oyun, KONTROL_VARSAYILAN).items():
        secilen = (list(kayitli.get(eylem, varsayilan)) + ["", ""])[:2]
        if {k for k in secilen if k} == {k for k in varsayilan if k}:
            continue
        orijinal = _kodlar(varsayilan)
        engel.update(orijinal)
        for kod in _kodlar(secilen):
            esle[kod] = orijinal
    return esle, engel


# ----------------------------------------------------------------- ayar deposu (JSON)
VARSAYILAN = dict(dil="tr", tema="varsayilan", ses=True, animasyon=True, fps=False, avatar=0, tuslar={})
AVATAR_SAYISI = 8


def _json_yukle():
    try:
        with open(AYAR_DOSYASI, encoding="utf-8") as dosya:
            veri = json.load(dosya)
            return veri if isinstance(veri, dict) else {}
    except Exception:
        return {}


def _json_kaydet(veri):
    gecici = AYAR_DOSYASI + ".tmp"
    try:
        with open(gecici, "w", encoding="utf-8") as dosya:
            json.dump(veri, dosya, ensure_ascii=False, indent=2)
        os.replace(gecici, AYAR_DOSYASI)           # yazma yarıda kesilse bile eski dosya bozulmaz
    except OSError:
        pass


class AyarDeposu:
    """Her kullanıcının ayarı kendi adı altında saklanır. Giriş yapılmamışken sadece dil/tema ('_genel') hatırlanır."""

    def __init__(self):
        self.veri = _json_yukle()
        self.kullanici = None
        self.d = self._taze()
        self.kullanici_sec(None)

    def _taze(self):
        d, genel = copy.deepcopy(VARSAYILAN), self.veri.get("_genel", {})
        for k in ("dil", "tema"):
            if k in genel:
                d[k] = genel[k]
        return d

    def kullanici_sec(self, ad):
        """Giriş/çıkışta çağrılır; o kullanıcının ayarlarını yükler ve dili uygular."""
        self.kullanici = ad.lower() if ad else None
        if self.kullanici:
            kayit = self.veri.get(self.kullanici)
            if not isinstance(kayit, dict):
                kayit = self.veri[self.kullanici] = self._taze()
            for k, v in VARSAYILAN.items():
                kayit.setdefault(k, copy.deepcopy(v))
            self.d = kayit
            self.kaydet()
        else:
            self.d = self._taze()
        dil_ayarla(self.d["dil"])

    def al(self, anahtar):
        return self.d.get(anahtar, VARSAYILAN[anahtar])

    def ata(self, anahtar, deger):
        self.d[anahtar] = deger
        if anahtar in ("dil", "tema"):
            self.veri.setdefault("_genel", {})[anahtar] = deger      # giriş ekranı da son tercihi hatırlasın
        self.kaydet()

    def kaydet(self):
        _json_kaydet(self.veri)

    def hesap_tasi(self, eski_ad, yeni_ad):
        """Kullanıcı adı değişince ayarları yeni ada taşır."""
        eski, yeni = eski_ad.lower(), yeni_ad.lower()
        if eski != yeni and eski in self.veri:
            self.veri[yeni] = self.veri.pop(eski)
        self.kullanici = yeni
        self.d = self.veri.setdefault(yeni, self._taze())
        self.kaydet()

    # --- tuşlar
    def tuslar(self, oyun):
        """{eylem: [birincil, ikincil]} (kayıtlı değer yoksa varsayılan)."""
        kayitli = self.d.get("tuslar", {}).get(oyun, {})
        return {e: (list(kayitli.get(e, v)) + ["", ""])[:2]
                for e, v in OYUN_KONTROLLERI.get(oyun, KONTROL_VARSAYILAN).items()}

    def tus_ata(self, oyun, eylem, slot, isim):
        tum = self.tuslar(oyun)
        tum[eylem][slot] = isim
        self.d.setdefault("tuslar", {})[oyun] = tum
        self.kaydet()

    def cakisma(self, oyun, eylem, slot, isim):
        """Aynı tuş başka bir yerde kullanılıyorsa o eylemi döndürür."""
        for e, ks in self.tuslar(oyun).items():
            for i, k in enumerate(ks):
                if k == isim and (e, i) != (eylem, slot):
                    return e
        return None

    def tus_sifirla(self, oyun):
        self.d.get("tuslar", {}).pop(oyun, None)
        self.kaydet()


# ----------------------------------------------------------------- avatarlar
AVATAR_RENKLER = [TURKUAZ, PEMBE, SARI, YESIL, TURUNCU, MOR, KIRMIZI, (120, 170, 255)]


def avatar_ciz(yuzey, indeks, merkez, r):
    """8 avatardan birini merkez/yarıçapa göre çizer (resim dosyası gerekmez)."""
    cx, cy = merkez
    u = r / 10
    renk = AVATAR_RENKLER[indeks % AVATAR_SAYISI]
    kal = max(2, int(u * 0.6))
    pygame.draw.circle(yuzey, (11, 9, 26), merkez, r)
    pygame.draw.circle(yuzey, renk, merkez, r, max(2, int(u * 0.7)))
    koyu = (11, 9, 26)
    if indeks % AVATAR_SAYISI == 0:                    # robot
        pygame.draw.rect(yuzey, renk, (cx - 5 * u, cy - 4 * u, 10 * u, 8 * u), kal)
        for dx in (-2.5, 1.0):
            yuzey.fill(renk, (cx + dx * u, cy - 1.5 * u, 1.6 * u, 1.6 * u))
        pygame.draw.line(yuzey, renk, (cx, cy - 4 * u), (cx, cy - 7 * u), kal)
        pygame.draw.circle(yuzey, renk, (cx, cy - 7 * u), max(2, int(u * 0.9)))
        pygame.draw.line(yuzey, renk, (cx - 2.5 * u, cy + 2 * u), (cx + 2.5 * u, cy + 2 * u), kal)
    elif indeks % AVATAR_SAYISI == 1:                  # uzaylı
        pygame.draw.ellipse(yuzey, renk, (cx - 5 * u, cy - 6 * u, 10 * u, 12 * u), kal)
        for dx in (-4.2, 0.8):
            pygame.draw.ellipse(yuzey, renk, (cx + dx * u, cy - 1.5 * u, 3.4 * u, 2.2 * u))
        pygame.draw.line(yuzey, renk, (cx - 1.5 * u, cy + 3 * u), (cx + 1.5 * u, cy + 3 * u), kal)
    elif indeks % AVATAR_SAYISI == 2:                  # ninja
        pygame.draw.circle(yuzey, renk, (cx, cy), int(6 * u), kal)
        pygame.draw.rect(yuzey, renk, (cx - 6 * u, cy - 2 * u, 12 * u, 3.6 * u))
        for dx in (-2.5, 2.5):
            pygame.draw.circle(yuzey, BEYAZ, (cx + dx * u, cy - 0.2 * u), max(1, int(0.8 * u)))
    elif indeks % AVATAR_SAYISI == 3:                  # kedi
        pygame.draw.circle(yuzey, renk, (cx, cy + u), int(5.5 * u), kal)
        for s in (-1, 1):
            pygame.draw.polygon(yuzey, renk, [(cx + s * 5 * u, cy - 1.5 * u), (cx + s * 4.6 * u, cy - 6.5 * u),
                                              (cx + s * 1.2 * u, cy - 4 * u)], kal)
            yuzey.fill(renk, (cx + s * 2.4 * u - u * 0.6, cy - 0.5 * u, 1.2 * u, 1.6 * u))
            pygame.draw.line(yuzey, renk, (cx + s * 3 * u, cy + 2.5 * u), (cx + s * 7 * u, cy + 2 * u), 1)
        pygame.draw.polygon(yuzey, renk, [(cx - u, cy + 1.8 * u), (cx + u, cy + 1.8 * u), (cx, cy + 3 * u)])
    elif indeks % AVATAR_SAYISI == 4:                  # astronot
        pygame.draw.circle(yuzey, renk, (cx, cy), int(6.5 * u), kal)
        pygame.draw.ellipse(yuzey, renk, (cx - 4.5 * u, cy - 3 * u, 9 * u, 6 * u), kal)
        pygame.draw.line(yuzey, renk, (cx - 3 * u, cy - 1.5 * u), (cx - 1 * u, cy - 2.2 * u), kal)
    elif indeks % AVATAR_SAYISI == 5:                  # kuru kafa
        pygame.draw.circle(yuzey, renk, (cx, cy - u), int(5.5 * u), kal)
        for dx in (-2.2, 2.2):
            pygame.draw.circle(yuzey, renk, (cx + dx * u, cy - 1.5 * u), max(2, int(1.4 * u)))
        pygame.draw.polygon(yuzey, renk, [(cx - 0.7 * u, cy + 0.5 * u), (cx + 0.7 * u, cy + 0.5 * u), (cx, cy + 1.6 * u)])
        for dx in (-2, 0, 2):
            pygame.draw.line(yuzey, renk, (cx + dx * u, cy + 3.5 * u), (cx + dx * u, cy + 5.5 * u), 1)
    elif indeks % AVATAR_SAYISI == 6:                  # tek gözlü altıgen
        pygame.draw.polygon(yuzey, renk, [(cx + 6.5 * u * math.cos(k * math.pi / 3), cy + 6.5 * u * math.sin(k * math.pi / 3))
                                          for k in range(6)], kal)
        pygame.draw.circle(yuzey, renk, (cx, cy), int(2.8 * u), kal)
        pygame.draw.circle(yuzey, renk, (cx, cy), max(2, int(1.1 * u)))
    else:                                              # gülen yüz
        pygame.draw.circle(yuzey, renk, (cx, cy), int(6 * u), kal)
        for dx in (-2.2, 2.2):
            pygame.draw.circle(yuzey, renk, (cx + dx * u, cy - 1.8 * u), max(2, int(0.9 * u)))
        pygame.draw.arc(yuzey, renk, (cx - 3.6 * u, cy - 2.4 * u, 7.2 * u, 6.4 * u), math.pi * 1.15, math.pi * 1.85, kal)
    return koyu


# ----------------------------------------------------------------- arayüz
class AyarlarEkrani:
    """Sekmeli ayarlar ekranı. 'c' (cizim) oyun_merkezi.py'nin verdiği çizim/olay yardımcılarıdır."""
    P = pygame.Rect(90, 50, 920, 620)        # ana panel
    A = pygame.Rect(120, 190, 860, 460)      # sekme içeriği
    GERI = pygame.Rect(110, 66, 130, 36)
    SEKMELER = ("genel", "gorunum", "dil", "profil", "kontroller")

    def __init__(self, depo, c, temalar):
        self.depo, self.c, self.temalar = depo, c, temalar
        self.sekme, self.mesaj, self.bekleyen = "genel", None, None
        self.tema_secili, self.avatar_secili, self.ad_giris, self.odak_ad = "varsayilan", 0, "", False
        self.oyun_secili = list(OYUN_KONTROLLERI)[0]
        self.onizleme, self.kucuk, self.son_onizleme, self.kare = pygame.Surface((1100, 720)), None, None, 0

    # --- giriş / yardımcılar
    def ac(self, sekme="genel"):
        self.sekme, self.mesaj, self.bekleyen, self.odak_ad = sekme, None, None, False
        self.tema_secili = self.depo.al("tema")
        self.avatar_secili = self.depo.al("avatar") % AVATAR_SAYISI
        self.ad_giris = self.c.kullanici() or ""

    def sekme_rect(self, i):
        return pygame.Rect(110 + i * 178, 128, 168, 38)

    def satir(self, i):
        return pygame.Rect(self.A.x, self.A.y + i * 70, 860, 56)

    def tema_rect(self, i):
        return pygame.Rect(self.A.x, self.A.y + i * 52, 330, 44)

    def tus_rect(self, i, slot):
        return pygame.Rect(self.A.x + 380 + slot * 220, self.A.y + 72 + i * 52, 200, 44)

    def oyun_rect(self, i):
        return pygame.Rect(self.A.x + i * 190, self.A.y, 180, 36)

    def avatar_rect(self, i):
        return pygame.Rect(self.A.x + (i % 4) * 116, self.A.y + 215 + (i // 4) * 112, 100, 100)

    def dil_rect(self, i):
        return pygame.Rect(self.A.x + 200, self.A.y + 90 + i * 110, 460, 84)

    def ad_rect(self):
        return pygame.Rect(self.A.x + 190, self.A.y + 40, 420, 42)

    def kaydet_rect(self):
        return pygame.Rect(self.A.x + 190, self.A.y + 100, 420, 46)

    def uygula_rect(self):
        return pygame.Rect(self.A.x + 370, self.A.y + 345, 490, 46)

    def sifirla_rect(self):
        return pygame.Rect(self.A.x + 560, self.A.y + 345, 240, 44)

    def _mesaj(self, anahtar, renk, **kw):
        self.mesaj = (anahtar, kw, renk)

    def _sekme_ac(self, s):
        self.c.ses("tik")
        self.ac(s)

    # --- olaylar
    def olay(self, o):
        c = self.c
        if o.type == pygame.KEYDOWN and self.bekleyen:
            self._tus_yakala(o)
            return
        if o.type == pygame.KEYDOWN and o.key == pygame.K_ESCAPE:
            if self.odak_ad:
                self.odak_ad = False
            else:
                c.geri()
            return
        if self.sekme == "profil" and self.odak_ad:
            if o.type == pygame.TEXTINPUT:
                izinli = "".join(ch for ch in o.text if ch.isalnum() or ch in "_-.")
                self.ad_giris = (self.ad_giris + izinli)[:16]
                self.mesaj = None
            elif o.type == pygame.KEYDOWN and o.key == pygame.K_BACKSPACE:
                self.ad_giris = self.ad_giris[:-1]
            elif o.type == pygame.KEYDOWN and o.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._profil_kaydet()
        if o.type == pygame.MOUSEBUTTONDOWN and o.button == 1:
            self._tikla(c.mantiksal(o.pos))

    def _tikla(self, p):
        c = self.c
        self.bekleyen = None
        if self.GERI.collidepoint(p):
            c.ses("tik")
            c.geri()
            return
        for i, s in enumerate(self.SEKMELER):
            if self.sekme_rect(i).collidepoint(p):
                if s != self.sekme:
                    self._sekme_ac(s)
                return
        getattr(self, "_tikla_" + self.sekme)(p)

    def _tikla_genel(self, p):
        for i, anahtar in enumerate(("ses", "animasyon", "fps")):
            if self.satir(i).collidepoint(p):
                self.depo.ata(anahtar, not self.depo.al(anahtar))
                if self.depo.al("ses"):
                    self.c.ses("tik")
                return
        if pygame.Rect(self.satir(3).right - 220, self.satir(3).y + 6, 220, 44).collidepoint(p):
            self.c.ses("tik")
            self.c.tam_ekran()

    def _tikla_gorunum(self, p):
        for i, kimlik in enumerate(self.temalar.TEMA_SIRASI):
            if self.tema_rect(i).collidepoint(p):
                self.tema_secili = kimlik
                self.c.ses("tik")
                return
        if self.uygula_rect().collidepoint(p) and self.tema_secili != self.depo.al("tema"):
            self.depo.ata("tema", self.tema_secili)
            self.c.ses("basari")

    def _tikla_dil(self, p):
        for i, (kod, _) in enumerate(DILLER):
            if self.dil_rect(i).collidepoint(p):
                if kod != self.depo.al("dil"):
                    self.depo.ata("dil", kod)
                    dil_ayarla(kod)
                    self.mesaj = None
                    self.c.dil_degisti()
                    self.c.ses("tik")
                return

    def _tikla_profil(self, p):
        self.odak_ad = self.ad_rect().collidepoint(p)
        if self.odak_ad:
            self.c.ses("tik")
        elif self.kaydet_rect().collidepoint(p):
            self._profil_kaydet()
        else:
            for i in range(AVATAR_SAYISI):
                if self.avatar_rect(i).collidepoint(p):
                    self.avatar_secili = i
                    self.c.ses("tik")

    def _profil_kaydet(self):
        c, yeni, eski = self.c, self.ad_giris.strip(), self.c.kullanici()
        if yeni != eski:
            ok, anahtar, ad = c.adi_degistir(eski, yeni)
            if not ok:
                self._mesaj(anahtar, KIRMIZI)
                c.ses("hata")
                return
            self.depo.hesap_tasi(eski, ad)
            c.kullanici_ata(ad)
            self.ad_giris = ad
        self.depo.ata("avatar", self.avatar_secili)
        self._mesaj("ok.profil", YESIL)
        c.ses("basari")

    def _tikla_kontroller(self, p):
        for i, oyun in enumerate(OYUN_KONTROLLERI):
            if self.oyun_rect(i).collidepoint(p):
                self.oyun_secili, self.mesaj = oyun, None
                self.c.ses("tik")
                return
        if self.sifirla_rect().collidepoint(p):
            self.depo.tus_sifirla(self.oyun_secili)
            self._mesaj("kon.sifirlandi", YESIL)
            self.c.ses("basari")
            return
        for i, eylem in enumerate(OYUN_KONTROLLERI[self.oyun_secili]):
            for slot in (0, 1):
                if self.tus_rect(i, slot).collidepoint(p):
                    self.bekleyen, self.mesaj = (eylem, slot), None
                    self.c.ses("tik")
                    return

    def _tus_yakala(self, o):
        """Bir tuş kutusuna tıklandıktan sonra basılan tuşu atar."""
        oyun, (eylem, slot) = self.oyun_secili, self.bekleyen
        if o.key == pygame.K_ESCAPE:
            self.bekleyen = None
            return
        if o.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            if not self.depo.tuslar(oyun)[eylem][1 - slot]:
                self._mesaj("kon.en_az", KIRMIZI)
                self.c.ses("hata")
            else:
                self.depo.tus_ata(oyun, eylem, slot, "")
                self._mesaj("kon.temizlendi", YESIL)
                self.c.ses("tik")
            self.bekleyen = None
            return
        isim = pygame.key.name(o.key)
        if not isim or o.key == pygame.K_F11:
            self._mesaj("kon.gecersiz", KIRMIZI)
            self.c.ses("hata")
            return
        diger = self.depo.cakisma(oyun, eylem, slot, isim)
        if diger:                                              # aynı tuş iki işleve atanamaz
            self._mesaj("kon.cakisma", KIRMIZI, tus=isim.upper(), eylem="eylem." + diger)
            self.c.ses("hata")
        else:
            self.depo.tus_ata(oyun, eylem, slot, isim)
            self._mesaj("kon.atandi", YESIL, eylem="eylem." + eylem, tus=isim.upper())
            self.c.ses("basari")
        self.bekleyen = None

    # --- çizim yardımcıları
    def _metin(self, font, metin, renk, konum, ortala=False):
        return self.c.yazi(font, metin, renk, konum, ortala=ortala)

    def _dugme(self, rect, metin, renk, aktif=True):
        self.c.dugme(rect, metin, renk if aktif else (90, 95, 120), aktif and rect.collidepoint(self.c.fare()))

    def _kutu(self, rect, secili=False, renk=TURKUAZ):
        tuval = self.c.tuval()
        pygame.draw.rect(tuval, (10, 10, 28), rect)
        if secili:
            self.c.parlama(tuval, renk, rect.center, 4)
        pygame.draw.rect(tuval, renk if secili else (70, 80, 120), rect, 2)

    def _toggle(self, rect, acik):
        tuval = self.c.tuval()
        pygame.draw.rect(tuval, (10, 10, 28), rect, border_radius=14)
        pygame.draw.rect(tuval, YESIL if acik else (70, 80, 120), rect, 2, border_radius=14)
        pygame.draw.circle(tuval, YESIL if acik else (110, 120, 160), (rect.right - 14 if acik else rect.x + 14, rect.centery), 9)

    def _mesaj_ciz(self, konum):
        if self.mesaj:
            anahtar, kw, renk = self.mesaj
            kw = {k: (t(v) if isinstance(v, str) and v.startswith("eylem.") else v) for k, v in kw.items()}
            self._metin(self.c.fk, t(anahtar, **kw), renk, konum)

    # --- çizim
    def ciz(self, zaman):
        c, tuval = self.c, self.c.tuval()
        self.kare += 1
        c.panel(self.P, 228)
        pygame.draw.rect(tuval, TURKUAZ, self.P, 2)
        self._metin(c.fb, t("ayar.baslik"), TURKUAZ, (self.P.centerx, self.P.y + 34), True)
        self._dugme(self.GERI, "< " + t("ayar.geri"), PEMBE)
        for i, s in enumerate(self.SEKMELER):
            r, aktif = self.sekme_rect(i), s == self.sekme
            pygame.draw.rect(tuval, TURKUAZ if aktif else (24, 24, 50), r)
            pygame.draw.rect(tuval, TURKUAZ if aktif else (70, 80, 120), r, 2)
            self._metin(c.fk, t("sekme." + s), (5, 10, 25) if aktif else SOLUK, r.center, True)
        getattr(self, "_ciz_" + self.sekme)(zaman)

    def _ciz_genel(self, zaman):
        c, tuval = self.c, self.c.tuval()
        for i, anahtar in enumerate(("ses", "animasyon", "fps")):
            r = self.satir(i)
            self._kutu(r, r.collidepoint(c.fare()))
            self._metin(c.fo, t("genel." + anahtar), BEYAZ, (r.x + 20, r.y + 16))
            self._toggle(pygame.Rect(r.right - 90, r.y + 14, 70, 28), self.depo.al(anahtar))
        r = self.satir(3)
        self._kutu(r)
        self._metin(c.fo, t("genel.tam"), BEYAZ, (r.x + 20, r.y + 16))
        self._dugme(pygame.Rect(r.right - 220, r.y + 6, 220, 44), t("genel.tam_btn"), TURKUAZ)
        self._metin(c.fk, t("genel.ipucu"), SOLUK, (self.A.x, self.A.y + 310))

    def _ciz_gorunum(self, zaman):
        c, tuval = self.c, self.c.tuval()
        for i, kimlik in enumerate(self.temalar.TEMA_SIRASI):
            r = self.tema_rect(i)
            self._kutu(r, kimlik == self.tema_secili)
            k1, k2 = self.temalar.TEMALAR[kimlik]["renkler"]
            pygame.draw.rect(tuval, k1, (r.x + 8, r.y + 7, 15, 30))
            pygame.draw.rect(tuval, k2, (r.x + 23, r.y + 7, 15, 30))
            self._metin(c.fo, t("tema." + kimlik), BEYAZ, (r.x + 52, r.y + 11))
            if kimlik == self.depo.al("tema"):                  # uygulanmış temanın yanına onay işareti
                pygame.draw.lines(tuval, YESIL, False, [(r.right - 34, r.centery), (r.right - 26, r.centery + 8), (r.right - 12, r.centery - 8)], 3)
        pr = pygame.Rect(self.A.x + 370, self.A.y, 490, 321)    # canlı önizleme (2 karede bir yenilenir)
        if self.kucuk is None or self.kare % 2 == 0 or self.son_onizleme != self.tema_secili:
            self.temalar.ciz(self.tema_secili, self.onizleme, 0, 0, zaman)
            self.kucuk = pygame.transform.smoothscale(self.onizleme, pr.size)
            self.son_onizleme = self.tema_secili
        tuval.blit(self.kucuk, pr)
        pygame.draw.rect(tuval, TURKUAZ, pr, 2)
        self._dugme(self.uygula_rect(), t("gor.uygulandi") if self.tema_secili == self.depo.al("tema") else t("gor.uygula"),
                    YESIL, self.tema_secili != self.depo.al("tema"))
        self._metin(c.fk, t("gor.aktif", tema=t("tema." + self.depo.al("tema"))), SOLUK, (self.A.x + 370, self.A.y + 405))

    def _ciz_dil(self, zaman):
        c, tuval = self.c, self.c.tuval()
        self._metin(c.fo, t("dil.baslik"), BEYAZ, (self.A.x + 200, self.A.y + 40))
        for i, (kod, ad) in enumerate(DILLER):
            r, aktif = self.dil_rect(i), kod == self.depo.al("dil")
            self._kutu(r, aktif or r.collidepoint(c.fare()), YESIL if aktif else TURKUAZ)
            self._metin(c.fb, ad, YESIL if aktif else BEYAZ, (r.x + 40, r.centery - 14))
            if aktif:
                pygame.draw.lines(tuval, YESIL, False, [(r.right - 60, r.centery), (r.right - 46, r.centery + 14), (r.right - 20, r.centery - 14)], 4)
        self._metin(c.fk, t("dil.not"), SOLUK, (self.A.x + 200, self.A.y + 330))

    def _ciz_profil(self, zaman):
        c, tuval = self.c, self.c.tuval()
        c.parlama(tuval, AVATAR_RENKLER[self.avatar_secili], (self.A.x + 75, self.A.y + 75), 90)
        avatar_ciz(tuval, self.avatar_secili, (self.A.x + 75, self.A.y + 75), 66)
        self._metin(c.fk, t("profil.ad"), SOLUK, (self.A.x + 190, self.A.y + 18))
        r = self.ad_rect()
        self._kutu(r, self.odak_ad)
        alan = self._metin(c.fo, self.ad_giris, BEYAZ, (r.x + 12, r.y + 9))
        if self.odak_ad and int(pygame.time.get_ticks() / 500) % 2 == 0:
            pygame.draw.rect(tuval, TURKUAZ, (alan.right + 2, r.y + 8, 2, 24))
        self._dugme(self.kaydet_rect(), t("profil.kaydet"), YESIL)
        self._mesaj_ciz((self.A.x + 190, self.A.y + 158))
        self._metin(c.fk, t("profil.avatar"), SOLUK, (self.A.x, self.A.y + 190))
        for i in range(AVATAR_SAYISI):
            r = self.avatar_rect(i)
            self._kutu(r, i == self.avatar_secili, AVATAR_RENKLER[i])
            avatar_ciz(tuval, i, r.center, 38)

    def _ciz_kontroller(self, zaman):
        c, tuval = self.c, self.c.tuval()
        for i, oyun in enumerate(OYUN_KONTROLLERI):
            r, aktif = self.oyun_rect(i), oyun == self.oyun_secili
            pygame.draw.rect(tuval, TURKUAZ if aktif else (24, 24, 50), r)
            pygame.draw.rect(tuval, TURKUAZ if aktif else (70, 80, 120), r, 2)
            self._metin(c.fk, t("oyun." + oyun + ".baslik"), (5, 10, 25) if aktif else SOLUK, r.center, True)
        for slot, anahtar in enumerate(("kon.birinci", "kon.ikinci")):
            self._metin(c.fk, t(anahtar), SOLUK, (self.tus_rect(0, slot).centerx, self.A.y + 54), True)
        tuslar = self.depo.tuslar(self.oyun_secili)
        for i, eylem in enumerate(OYUN_KONTROLLERI[self.oyun_secili]):
            self._metin(c.fo, t("eylem." + eylem), BEYAZ, (self.A.x + 10, self.tus_rect(i, 0).y + 12))
            for slot in (0, 1):
                r, bekliyor = self.tus_rect(i, slot), self.bekleyen == (eylem, slot)
                self._kutu(r, bekliyor or r.collidepoint(c.fare()), SARI if bekliyor else TURKUAZ)
                ad = t("kon.bekle") if bekliyor else (tuslar[eylem][slot].upper() or "-")
                self._metin(c.fo, ad, SARI if bekliyor else BEYAZ, r.center, True)
        self._mesaj_ciz((self.A.x + 10, self.A.y + 352))
        self._dugme(self.sifirla_rect(), t("kon.sifirla"), KIRMIZI)
        self._metin(c.fk, t("kon.ipucu"), SOLUK, (self.A.x + 10, self.A.y + 405))
        self._metin(c.fk, t("kon.not"), (100, 110, 150), (self.A.x + 10, self.A.y + 430))
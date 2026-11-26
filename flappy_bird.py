"""Flappy Bird - Python & Pygame (tek dosya)

Kurulum:   pip install pygame
Çalıştır:  python flappy_bird.py

Kontroller: Space / ↑ / sol tık = zıpla,  P = duraklat,  ESC = ana menü
Tüm görseller ve sesler kodla üretilir; harici dosya gerekmez.
İsteğe bağlı: bu dosyanın yanındaki assets/sounds/ klasörüne flap, score, hit,
start, gameover, music adlı .ogg/.wav/.mp3 dosyaları koyarsanız onlar kullanılır.
En yüksek skor ve ayarlar, dosyanın yanında savegame.json içinde saklanır.
"""
import json
import math
import os
import random
import threading
import time
from array import array
from enum import Enum, auto
from pathlib import Path

import pygame

# ==========================================================================
# CONSTANTS
# ==========================================================================
# --- Ekran -----------------------------------------------------------------
W, H = 1024, 768             # mantıksal çözünürlük (geniş ekran)
FPS = 60                     # sabit kare hızı
GROUND_H = 120               # zemin yüksekliği
GROUND_Y = H - GROUND_H      # zeminin başladığı y
GROUND_TILE = 48             # zemin desen genişliği (kaydırma için)
BAR_COLOR = (20, 40, 70)     # letterbox (siyah bant) rengi

# --- Kuş fiziği (piksel / saniye cinsinden, kare hızından bağımsız) --------
BIRD_X = 230
START_Y = 330
BIRD_RADIUS = 15             # çarpışma dairesinin yarıçapı
GRAVITY = 1750.0
FLAP_VELOCITY = -520.0       # zıplama anında verilen yukarı hız
MAX_FALL_SPEED = 850.0

# --- Borular ---------------------------------------------------------------
PIPE_W = 78
CAP_W = 90                   # boru başlığı gövdeden biraz geniştir
CAP_H = 36
PIPE_SPACING = 245           # iki boru arasındaki yatay mesafe
MIN_W, MAX_W = 560, 2800     # pencere oranına göre değişen mantıksal genişlik sınırları
GAP_MARGIN = 55              # boşluk ile tavan/zemin arası asgari mesafe

# --- Zorluk seviyeleri -----------------------------------------------------
#   gap        : borular arası dikey boşluk
#   speed      : başlangıç boru hızı (px/sn)
#   accel      : her puan için hıza eklenen değer
#   max_speed  : hız üst sınırı
#   shift      : iki boru arasında boşluk merkezinin en fazla kayacağı miktar
DIFFICULTIES = {
    "kolay":  dict(label="Kolay",  gap=215, speed=150, accel=4, max_speed=240, shift=150),
    "normal": dict(label="Normal", gap=190, speed=170, accel=5, max_speed=270, shift=140),
    "zor":    dict(label="Zor",    gap=180, speed=185, accel=5, max_speed=275, shift=115),
}
DIFF_ORDER = ["kolay", "normal", "zor"]
DEFAULT_DIFFICULTY = "normal"

# --- Game Over zamanlaması -------------------------------------------------
PANEL_DELAY = 0.7            # çarpmadan sonra panelin çıkmasına kadar süre
PANEL_ANIM = 0.45            # panelin kayarak gelme süresi
SHAKE_TIME = 0.35

# --- Renkler ---------------------------------------------------------------
WHITE = (255, 255, 255)
DARK = (40, 40, 60)

# --- Dosya yolları ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
SOUND_DIR = ASSET_DIR / "sounds"

# ==========================================================================
# LOGIC
# ==========================================================================
def circle_rect_collision(cx, cy, r, rect):
    """Daire ile dikdörtgen (x, y, w, h) çarpışıyor mu?

    Dikdörtgen üzerindeki dairenin merkezine en yakın nokta bulunur; bu
    noktaya olan uzaklık yarıçaptan küçükse çarpışma vardır.
    """
    x, y, w, h = rect
    nearest_x = min(max(cx, x), x + w)
    nearest_y = min(max(cy, y), y + h)
    dx, dy = cx - nearest_x, cy - nearest_y
    return dx * dx + dy * dy < r * r


def pipe_speed(difficulty, score):
    """Skora göre boru hızı: skor arttıkça hız artar, üst sınırı vardır."""
    return min(difficulty["max_speed"], difficulty["speed"] + difficulty["accel"] * score)


class Bird:
    """Kuşun konumu ve fiziği."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = float(BIRD_X)
        self.y = float(START_Y)
        self.vel = 0.0
        self.dead = False
        self.anim = 0.0          # kanat animasyonu için sayaç
        self.hover_t = 0.0

    def flap(self):
        self.vel = FLAP_VELOCITY

    def hover(self, dt):
        """Oyun başlamadan önce kuş olduğu yerde hafifçe sallanır."""
        self.hover_t += dt
        self.anim += dt
        self.y = START_Y + math.sin(self.hover_t * 5.0) * 8.0
        self.vel = 0.0

    def update(self, dt):
        """Yer çekimi + hareket. Tavana değerse kuş aşağı itilir (ölmez)."""
        self.anim += dt
        self.vel = min(self.vel + GRAVITY * dt, MAX_FALL_SPEED)
        self.y += self.vel * dt
        if self.y - BIRD_RADIUS < 0:
            self.y = BIRD_RADIUS
            self.vel = max(self.vel, 0.0)

    def update_dead(self, dt):
        """Çarpmadan sonra kuş yere düşer. Yere indiyse True döner."""
        if self.y + BIRD_RADIUS >= GROUND_Y:
            self.y = GROUND_Y - BIRD_RADIUS
            self.vel = 0.0
            return True
        self.vel = min(self.vel + GRAVITY * dt, MAX_FALL_SPEED)
        self.y += self.vel * dt
        if self.y + BIRD_RADIUS >= GROUND_Y:
            self.y = GROUND_Y - BIRD_RADIUS
            self.vel = 0.0
            return True
        return False

    @property
    def angle(self):
        """Burun yönü: yukarı çıkarken yukarı, düşerken aşağı bakar (derece)."""
        return max(-80.0, min(28.0, -self.vel * 0.09))

    def hits_ground(self):
        return self.y + BIRD_RADIUS >= GROUND_Y


class Pipe:
    """Bir boru çifti (üst + alt). x: borunun sol kenarı, gap_y: boşluk merkezi."""

    def __init__(self, x, gap_y, gap):
        self.x = float(x)
        self.gap_y = float(gap_y)
        self.gap = float(gap)
        self.scored = False

    @property
    def gap_top(self):
        return self.gap_y - self.gap / 2

    @property
    def gap_bottom(self):
        return self.gap_y + self.gap / 2

    def rects(self):
        """Çarpışmaya girecek 4 dikdörtgen: üst gövde, üst başlık, alt başlık, alt gövde."""
        cap_x = self.x - (CAP_W - PIPE_W) / 2
        top, bottom = self.gap_top, self.gap_bottom
        return [
            (self.x, 0, PIPE_W, top - CAP_H),
            (cap_x, top - CAP_H, CAP_W, CAP_H),
            (cap_x, bottom, CAP_W, CAP_H),
            (self.x, bottom + CAP_H, PIPE_W, GROUND_Y - (bottom + CAP_H)),
        ]

    def collides(self, bird):
        return any(
            circle_rect_collision(bird.x, bird.y, BIRD_RADIUS, r)
            for r in self.rects() if r[2] > 0 and r[3] > 0
        )


class PipeField:
    """Boruların üretimi, hareketi ve temizlenmesi."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.pipes = []
        self.last_center = None

    def reset(self):
        self.pipes = []
        self.last_center = None

    def update(self, dx, difficulty):
        """Boruları dx piksel sola kaydır, ekran dışına çıkanları sil, gerekirse yenisini üret."""
        for p in self.pipes:
            p.x -= dx
        self.pipes = [p for p in self.pipes if p.x > -CAP_W]
        if not self.pipes or self.pipes[-1].x <= (W + 40) - PIPE_SPACING:
            self.spawn(difficulty)

    def spawn(self, difficulty):
        """Rastgele ama ulaşılabilir konumda yeni boru oluştur.

        Boşluğun merkezi bir öncekine en fazla 'shift' kadar uzak olabilir;
        böylece oyuncunun her boruya yetişmesi mümkün kalır.
        """
        gap = difficulty["gap"]
        lo = GAP_MARGIN + gap / 2
        hi = GROUND_Y - GAP_MARGIN - gap / 2
        if self.last_center is None:
            lo, hi = max(lo, START_Y - 120), min(hi, START_Y + 120)
        else:
            shift = difficulty["shift"]
            lo = max(lo, self.last_center - shift)
            hi = min(hi, self.last_center + shift)
        center = self.rng.uniform(lo, hi)
        self.last_center = center
        self.pipes.append(Pipe(W + 40, center, gap))      # ekranın hemen sağında doğar

    def next_pipe(self, bird_x):
        """Kuşun henüz geçmediği ilk boru (bot ve test için)."""
        for p in self.pipes:
            if p.x + PIPE_W > bird_x - BIRD_RADIUS:
                return p
        return None

# ==========================================================================
# STORAGE
# ==========================================================================
SAVE_NAME = "savegame.json"


def default_paths():
    """Önce proje klasörü, yazılamazsa kullanıcının ev dizini denenir."""
    return [BASE_DIR / SAVE_NAME, Path.home() / ".flappy_bird" / SAVE_NAME]


class SaveData:
    def __init__(self, path=None):
        self.paths = [Path(path)] if path else default_paths()
        self.high_score = 0
        self.music = True
        self.sfx = True
        self.difficulty = DEFAULT_DIFFICULTY
        self.active_path = None
        self.load()

    # -- yükleme ------------------------------------------------------------
    def load(self):
        for path in self.paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict):
                self._apply(data)
                self.active_path = path
                return

    def _apply(self, data):
        """Değerleri doğrulayarak uygula (bozuk değerler yok sayılır)."""
        hs = data.get("high_score")
        if isinstance(hs, int) and not isinstance(hs, bool) and hs >= 0:
            self.high_score = hs
        for key in ("music", "sfx"):
            if isinstance(data.get(key), bool):
                setattr(self, key, data[key])
        if data.get("difficulty") in DIFFICULTIES:
            self.difficulty = data["difficulty"]

    # -- kaydetme -----------------------------------------------------------
    def save(self):
        """Başarılıysa True döner. Önce son çalışan yol, sonra diğerleri denenir."""
        payload = {
            "high_score": self.high_score,
            "music": self.music,
            "sfx": self.sfx,
            "difficulty": self.difficulty,
        }
        candidates = ([self.active_path] if self.active_path else []) + \
                     [p for p in self.paths if p != self.active_path]
        for path in candidates:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                os.replace(tmp, path)          # yarım yazılmış dosya kalmasın
                self.active_path = path
                return True
            except OSError:
                continue
        return False

# ==========================================================================
# SYNTH
# ==========================================================================
def midi_to_freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _osc(kind, phase):
    """Tek bir dalga örneği. phase: devir sayısı."""
    phase -= math.floor(phase)
    if kind == "square":
        return 1.0 if phase < 0.5 else -1.0
    if kind == "triangle":
        return 4.0 * abs(phase - 0.5) - 1.0
    if kind == "saw":
        return 2.0 * phase - 1.0
    return math.sin(2 * math.pi * phase)


class Synth:
    def __init__(self, rate):
        self.rate = rate

    def tone(self, f0, f1, dur, kind="sine", vol=0.5, attack=0.004, power=2.0):
        """f0'dan f1'e kayan frekanslı, sönümlenen tek nota."""
        n = max(1, int(dur * self.rate))
        att = max(1, int(attack * self.rate))
        out = [0.0] * n
        phase = 0.0
        for i in range(n):
            t = i / n
            phase += (f0 + (f1 - f0) * t) / self.rate
            env = (1.0 - t) ** power
            if i < att:
                env *= i / att
            out[i] = _osc(kind, phase) * env * vol
        return out

    def noise(self, dur, vol=0.5, power=2.0, smooth=0.5, seed=1):
        """Alçak geçirgen filtreden geçmiş gürültü (çarpma sesi için)."""
        rnd = random.Random(seed)
        n = max(1, int(dur * self.rate))
        out = [0.0] * n
        last = 0.0
        for i in range(n):
            last += (rnd.uniform(-1.0, 1.0) - last) * smooth
            out[i] = last * (1.0 - i / n) ** power * vol
        return out

    def mix(self, parts, length=None, wrap=False):
        """(başlangıç_saniyesi, örnekler) çiftlerini tek bir listede topla.

        wrap=True ise taşan kısımlar başa sarılır (kesintisiz müzik döngüsü).
        """
        if length is None:
            length = max(int(off * self.rate) + len(s) for off, s in parts)
        out = [0.0] * length
        for off, samples in parts:
            start = int(off * self.rate)
            if wrap:
                for i, v in enumerate(samples):
                    out[(start + i) % length] += v
            else:
                for i, v in enumerate(samples):
                    out[start + i] += v
        return out


def to_pcm(samples, channels=1):
    """float örnekleri 16-bit işaretli PCM bayt dizisine çevir (cihazın kanal sayısına göre)."""
    mono = array("h", (max(-32767, min(32767, int(v * 32767))) for v in samples))
    if channels == 1:
        return mono.tobytes()
    out = array("h", [0]) * (len(mono) * channels)
    for c in range(channels):
        out[c::channels] = mono
    return out.tobytes()


def build_effects(rate):
    """Tüm ses efektlerini üretip {isim: örnekler} olarak döndür."""
    s = Synth(rate)
    fx = {}
    fx["flap"] = s.mix([(0, s.tone(380, 760, 0.12, "triangle", 0.6, power=1.4))])
    fx["score"] = s.mix([
        (0.00, s.tone(988, 988, 0.07, "square", 0.22, power=0.8)),
        (0.07, s.tone(1319, 1319, 0.20, "square", 0.22, power=1.6)),
    ])
    fx["hit"] = s.mix([
        (0, s.noise(0.24, 0.8, power=2.5, smooth=0.35)),
        (0, s.tone(220, 50, 0.30, "saw", 0.45, power=1.5)),
    ])
    fx["start"] = s.mix([
        (0.00, s.tone(523, 523, 0.10, "triangle", 0.5, power=1.0)),
        (0.09, s.tone(659, 659, 0.10, "triangle", 0.5, power=1.0)),
        (0.18, s.tone(784, 784, 0.10, "triangle", 0.5, power=1.0)),
        (0.27, s.tone(1047, 1047, 0.30, "triangle", 0.5, power=1.6)),
    ])
    fx["gameover"] = s.mix([
        (0.00, s.tone(392, 392, 0.22, "triangle", 0.55, power=1.0)),
        (0.20, s.tone(330, 330, 0.22, "triangle", 0.55, power=1.0)),
        (0.40, s.tone(262, 262, 0.28, "triangle", 0.55, power=1.0)),
        (0.65, s.tone(196, 196, 0.55, "triangle", 0.55, power=1.8)),
    ])
    return fx


# Müzik: C - Am - F - G akoru dizisi, 8 ölçülük döngü.
_CHORDS = [
    ([60, 64, 67, 72], 48),   # C
    ([57, 60, 64, 69], 45),   # Am
    ([53, 57, 60, 65], 41),   # F
    ([55, 59, 62, 67], 43),   # G
]
_ARP = [0, 1, 2, 3, 2, 1, 2, 3]
# Son 4 ölçüde çalan melodi: (ölçü içi vuruş, midi notası, süre-vuruş)
_MELODY = {
    4: [(0, 76, 1.5), (1.5, 74, 0.5), (2, 72, 1), (3, 76, 1)],
    5: [(0, 72, 1.5), (1.5, 76, 0.5), (2, 79, 1), (3, 76, 1)],
    6: [(0, 77, 1.5), (1.5, 76, 0.5), (2, 72, 1), (3, 69, 1)],
    7: [(0, 74, 1), (1, 79, 1), (2, 74, 1), (3, 71, 1)],
}


def build_music(rate, bpm=108, pause=None):
    """Arpej + bas + melodiden oluşan döngülü bir arka plan müziği üretir.

    pause: her nota üretiminde çağrılan isteğe bağlı fonksiyon (arka plan
    iş parçacığının oyunu kasmaması için kısa uyku vermekte kullanılır).
    """
    s = Synth(rate)
    beat = 60.0 / bpm
    bars = 8
    length = int(bars * 4 * beat * rate)
    cache = {}

    def note(midi, dur, kind, vol, power):
        key = (midi, round(dur, 3), kind, vol, power)
        if key not in cache:
            if pause:
                pause()
            f = midi_to_freq(midi)
            cache[key] = s.tone(f, f, dur, kind, vol, attack=0.012, power=power)
        return cache[key]

    parts = []
    for bar in range(bars):
        chord, bass = _CHORDS[bar % 4]
        t0 = bar * 4 * beat
        for k, idx in enumerate(_ARP):
            parts.append((t0 + k * 0.5 * beat, note(chord[idx], 0.42, "triangle", 0.20, 1.8)))
        for b in (0, 2):
            parts.append((t0 + b * beat, note(bass, 1.8 * beat, "triangle", 0.32, 1.2)))
        for b, midi, dur in _MELODY.get(bar, []):
            parts.append((t0 + b * beat, note(midi, dur * beat * 0.95, "sine", 0.22, 1.1)))

    out = s.mix(parts, length=length, wrap=True)
    peak = max(abs(v) for v in out) or 1.0
    gain = min(1.0, 0.75 / peak)
    return [v * gain for v in out]

# ==========================================================================
# AUDIO
# ==========================================================================
EFFECT_VOLUMES = {"flap": 0.55, "score": 0.50, "hit": 0.70, "start": 0.60, "gameover": 0.65}
MUSIC_VOLUME = 0.30
EXTENSIONS = (".ogg", ".wav", ".mp3")


class AudioManager:
    def __init__(self, sounds_dir, music_on=True, sfx_on=True):
        self.sounds_dir = Path(sounds_dir)
        self.music_on = music_on
        self.sfx_on = sfx_on
        self.available = False
        self.sounds = {}
        self.music = None
        self.music_playing = False
        self._pcm = None                 # arka plan iş parçacığının ürettiği müzik
        self.rate, self.channels, self.synth_ok = 22050, 1, False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            info = pygame.mixer.get_init()
        except Exception:                # ses cihazı yok / sürücü hatası
            info = None
        if not info:
            return                       # sessiz mod
        self.rate, fmt, self.channels = info
        self.synth_ok = (fmt == -16)     # üretilen PCM 16-bit işaretli olduğu için
        self.available = True

        self._load_effects()
        self._load_music()

    # -- yükleme ------------------------------------------------------------
    def _load_external(self, name):
        for ext in EXTENSIONS:
            path = self.sounds_dir / (name + ext)
            if path.is_file():
                try:
                    return pygame.mixer.Sound(str(path))
                except Exception:
                    pass                 # bozuk dosya → koda geri dön
        return None

    def _make_sound(self, samples):
        try:
            return pygame.mixer.Sound(buffer=to_pcm(samples, self.channels))
        except Exception:
            return None

    def _load_effects(self):
        generated = None
        for name, volume in EFFECT_VOLUMES.items():
            snd = self._load_external(name)
            if snd is None and self.synth_ok:
                if generated is None:
                    generated = build_effects(self.rate)
                snd = self._make_sound(generated[name])
            if snd is not None:
                snd.set_volume(volume)
                self.sounds[name] = snd

    def _load_music(self):
        snd = self._load_external("music")
        if snd is not None:
            self.music = snd
            self.music.set_volume(MUSIC_VOLUME)
            return
        if self.synth_ok:
            # Müzik üretimi birkaç yüz ms sürebilir; menü donmasın diye arka planda yapılır.
            threading.Thread(target=self._music_worker, daemon=True).start()

    def _music_worker(self):
        try:
            samples = build_music(self.rate, pause=lambda: time.sleep(0.001))
            self._pcm = to_pcm(samples, self.channels)
        except Exception:
            self._pcm = None

    # -- her karede çağrılır ------------------------------------------------
    def update(self):
        """Arka planda hazırlanan müzik bittiyse Sound nesnesine çevirip başlat."""
        if self._pcm is not None and self.music is None:
            pcm, self._pcm = self._pcm, None
            try:
                self.music = pygame.mixer.Sound(buffer=pcm)
                self.music.set_volume(MUSIC_VOLUME)
            except Exception:
                self.music = None
        if self.music_on and self.music is not None and not self.music_playing:
            self.play_music()

    # -- oynatma ------------------------------------------------------------
    def play(self, name):
        if self.available and self.sfx_on and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

    def play_music(self):
        if self.available and self.music_on and self.music is not None and not self.music_playing:
            try:
                self.music.play(loops=-1)
                self.music_playing = True
            except Exception:
                pass

    def set_music_enabled(self, on):
        self.music_on = on
        if on:
            self.play_music()
        elif self.music is not None:
            try:
                self.music.stop()
            except Exception:
                pass
            self.music_playing = False

    def set_sfx_enabled(self, on):
        self.sfx_on = on

    def shutdown(self):
        if self.available:
            try:
                pygame.mixer.quit()
            except Exception:
                pass

# ==========================================================================
# GRAPHICS
# ==========================================================================
# --- Renk yardımcıları -----------------------------------------------------
def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def gradient_color(stops, t):
    """[(konum, renk), ...] listesinde t (0-1) konumundaki rengi hesapla."""
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            u = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return lerp_color(c0, c1, max(0.0, min(1.0, u)))
    return stops[-1][1]


def lighten(color, amount):
    return tuple(min(255, c + amount) for c in color)


# --- Gökyüzü, tepeler, bulutlar ---------------------------------------------
def make_sky():
    """Üçlü renk geçişli gökyüzü + güneş."""
    surf = pygame.Surface((W, H)).convert()
    stops = [(0.0, (46, 140, 230)), (0.55, (120, 200, 250)), (1.0, (228, 246, 255))]
    for y in range(H):
        pygame.draw.line(surf, gradient_color(stops, y / (H - 1)), (0, y), (W, y))
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    sx, sy = int(W * 0.8), 140
    for radius, alpha in ((120, 14), (90, 22), (66, 34), (46, 70)):
        pygame.draw.circle(glow, (255, 250, 200, alpha), (sx, sy), radius)
    pygame.draw.circle(glow, (255, 248, 210, 255), (sx, sy), 34)
    surf.blit(glow, (0, 0))
    return surf


def make_hills(height, base, amp, wave1, wave2, phase, color):
    """Yatayda kesintisiz tekrarlanan tepe silueti (genişlik = W).

    k1/k2 tam sayı olduğu için sol ve sağ kenar aynı yükseklikte biter;
    yüzey yan yana konunca dikiş görünmez.
    """
    k1, k2 = max(1, round(W / wave1)), max(1, round(W / wave2))   # tam sayı → dikişsiz
    surf = pygame.Surface((W, height), pygame.SRCALPHA)
    pts = [(0, height)]
    for x in range(0, W + 1, 4):
        y = base - amp * (0.65 * math.sin(2 * math.pi * k1 * x / W + phase)
                          + 0.35 * math.sin(2 * math.pi * k2 * x / W + phase * 2.3))
        pts.append((x, y))
    pts.append((W, height))
    pygame.draw.polygon(surf, color, pts)
    return surf.convert_alpha()


def make_cloud(width):
    """Yumuşak, hafif gölgeli bir bulut."""
    height = int(width * 0.55)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    blobs = [(0.22, 0.60, 0.17), (0.40, 0.42, 0.23), (0.64, 0.47, 0.21),
             (0.80, 0.62, 0.16), (0.50, 0.64, 0.19)]
    shade, white = (205, 225, 245, 255), (255, 255, 255, 255)
    for color, dy in ((shade, 0.035), (white, 0.0)):
        for cx, cy, r in blobs:
            pygame.draw.circle(surf, color, (int(cx * width), int((cy + dy) * width)), int(r * width))
        base = pygame.Rect(int(0.10 * width), int((0.55 + dy) * width * 0.9),
                           int(0.80 * width), int(0.17 * width))
        pygame.draw.rect(surf, color, base, border_radius=int(0.08 * width))
    surf = surf.convert_alpha()
    surf.set_alpha(235)                      # hafif saydamlık (convert'ten sonra uygulanır)
    return surf


# --- Kuş -----------------------------------------------------------------
def make_bird_frames():
    """4 karelik kanat çırpma animasyonu (yukarı, orta, aşağı, orta).

    4 kat büyük çizilip küçültülür (anti-aliasing). Gövde merkezi, sprite
    merkeziyle aynı noktadadır; böylece döndürme gövdenin etrafında olur.
    """
    ss = 4
    cw, ch = 52, 40
    outline = (84, 48, 24)
    ow = 2 * ss
    frames = []

    def rect(x, y, w, h):
        return pygame.Rect(int(x * ss), int(y * ss), int(w * ss), int(h * ss))

    def pts(*p):
        return [(int(x * ss), int(y * ss)) for x, y in p]

    for dy, wing_h in ((-7, 12), (0, 10), (6, 9), (0, 10)):
        big = pygame.Surface((cw * ss, ch * ss), pygame.SRCALPHA)

        tail = pts((12, 15), (1, 9), (3, 20), (1, 27), (13, 24))
        pygame.draw.polygon(big, (235, 120, 40), tail)
        pygame.draw.polygon(big, outline, tail, ow)

        tuft = pts((22, 8), (20, 1), (27, 6), (29, 0), (32, 8))
        pygame.draw.polygon(big, (235, 90, 60), tuft)
        pygame.draw.polygon(big, outline, tuft, ow)

        pygame.draw.ellipse(big, (255, 205, 50), rect(9, 7, 34, 26))          # gövde
        pygame.draw.ellipse(big, (255, 238, 180), rect(14, 20, 24, 11))       # karın
        pygame.draw.ellipse(big, outline, rect(9, 7, 34, 26), ow)             # gövde çizgisi

        wing = rect(12, 22 + dy - wing_h / 2, 17, wing_h)                      # kanat
        pygame.draw.ellipse(big, (255, 150, 40), wing)
        pygame.draw.ellipse(big, outline, wing, ow)

        eye = (int(34 * ss), int(14.5 * ss))                                   # göz
        pygame.draw.circle(big, (255, 255, 255), eye, int(6 * ss))
        pygame.draw.circle(big, outline, eye, int(6 * ss), ow)
        pygame.draw.circle(big, (20, 20, 30), (int(36 * ss), int(14.5 * ss)), int(2.8 * ss))
        pygame.draw.circle(big, (255, 255, 255), (int(37 * ss), int(13.3 * ss)), int(1.0 * ss))

        upper = pts((40, 16), (51, 19.5), (40, 21))                            # gaga
        lower = pts((40, 21), (49, 22), (40, 25))
        pygame.draw.polygon(big, (255, 120, 45), upper)
        pygame.draw.polygon(big, (225, 85, 35), lower)
        pygame.draw.polygon(big, outline, upper, ow)
        pygame.draw.polygon(big, outline, lower, ow)

        frames.append(pygame.transform.smoothscale(big, (62, 48)).convert_alpha())
    return frames


# --- Borular -------------------------------------------------------------
_PIPE_STOPS = [(0.0, (70, 150, 40)), (0.18, (120, 200, 60)), (0.35, (170, 235, 95)),
               (0.60, (110, 190, 55)), (1.0, (55, 125, 35))]
_PIPE_OUTLINE = (40, 80, 28)


def _pipe_gradient(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        pygame.draw.line(surf, gradient_color(_PIPE_STOPS, x / (w - 1)), (x, 0), (x, h))
    return surf


def make_pipe_textures():
    """(gövde, başlık) yüzeylerini üret. Gövde uzun tek parçadır; boruya göre kırpılarak çizilir."""
    body = _pipe_gradient(PIPE_W, GROUND_Y)
    pygame.draw.line(body, _PIPE_OUTLINE, (1, 0), (1, GROUND_Y), 3)
    pygame.draw.line(body, _PIPE_OUTLINE, (PIPE_W - 2, 0), (PIPE_W - 2, GROUND_Y), 3)

    cap = _pipe_gradient(CAP_W, CAP_H)
    mask = pygame.Surface((CAP_W, CAP_H), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, CAP_W, CAP_H), border_radius=8)
    cap.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)   # köşeleri yuvarla
    pygame.draw.rect(cap, _PIPE_OUTLINE, (0, 0, CAP_W, CAP_H), 3, border_radius=8)
    return body.convert_alpha(), cap.convert_alpha()


def draw_pipe(surf, pipe, textures):
    """Bir boru çiftini (üst ve alt) başlıklarıyla çiz."""
    body, cap = textures
    x = int(pipe.x)
    cap_x = x - (CAP_W - PIPE_W) // 2
    gap_top, gap_bottom = int(pipe.gap_top), int(pipe.gap_bottom)

    top_h = gap_top - CAP_H
    if top_h > 0:
        surf.blit(body, (x, 0), pygame.Rect(0, 0, PIPE_W, top_h))
    surf.blit(cap, (cap_x, gap_top - CAP_H))

    surf.blit(cap, (cap_x, gap_bottom))
    bottom_h = GROUND_Y - (gap_bottom + CAP_H)
    if bottom_h > 0:
        surf.blit(body, (x, gap_bottom + CAP_H), pygame.Rect(0, 0, PIPE_W, bottom_h))


# --- Zemin -----------------------------------------------------------------
def make_ground():
    """Yatayda GROUND_TILE'ın katları kadar kaydırılınca kesintisiz görünen zemin."""
    tile = pygame.Surface((GROUND_TILE, GROUND_H)).convert()
    band = 28                                                   # çim şeridi yüksekliği
    for y in range(GROUND_H):                                   # kum rengi geçişi
        t = max(0.0, (y - band) / (GROUND_H - band))
        pygame.draw.line(tile, lerp_color((228, 214, 150), (196, 172, 108), t), (0, y), (GROUND_TILE, y))
    rnd = random.Random(7)
    for _ in range(9):                                          # tekrarlanan kum lekeleri
        pygame.draw.circle(tile, (188, 164, 100), (rnd.randrange(GROUND_TILE),
                                                   rnd.randrange(band + 8, GROUND_H - 4)), 2)
    tile.fill((118, 205, 58), (0, 0, GROUND_TILE, band))        # çim
    for off in (-GROUND_TILE, 0, GROUND_TILE):                  # çapraz çim çizgileri
        stripe = [(off + 12, 5), (off + 36, 5), (off + 16, band - 3), (off - 8, band - 3)]
        pygame.draw.polygon(tile, (150, 226, 84), stripe)
    tile.fill((72, 126, 40), (0, 0, GROUND_TILE, 4))            # üst kenar çizgisi
    tile.fill((86, 150, 48), (0, band, GROUND_TILE, 4))         # çim altı çizgi

    ground = pygame.Surface((W + GROUND_TILE, GROUND_H)).convert()
    for x in range(0, W + GROUND_TILE, GROUND_TILE):
        ground.blit(tile, (x, 0))
    return ground

# ==========================================================================
# UI
# ==========================================================================
_FONT_CANDIDATES = ("arialrounded", "arialroundedmtbold", "verdana", "trebuchetms",
                    "dejavusans", "liberationsans", "opensans", "arial", "helvetica")
_font_path = None
_font_searched = False
_fonts = {}
_text_cache = {}

def _supports_turkish(path):
    """Fontta 'ş' ve 'Ş' için gerçek karakter glifi var mı? (Kutu çizilmesini engeller.)"""
    try:
        font = pygame.font.Font(path, 24)
        # 'ş' ve 'Ş' karakterlerinin metrik/görüntü boyutlarının boş/kutu olmadığını kontrol et
        for ch in ("ş", "Ş"):
            surf = font.render(ch, True, WHITE)
            if surf.get_width() <= 2 or surf.get_height() <= 2:
                return False
        # Standart Türkçe fontlardan (Arial / Segoe UI / Tahoma / Verdana / DejaVu Sans) biri değilse
        # ve sadece kutu üretiyorsa atla
        return True
    except Exception:
        return False


def _find_font_path():
    """Sistemde 'ş' ve 'Ş' destekleyen bir font yolu bul (bir kez)."""
    global _font_path, _font_searched
    if not _font_searched:
        _font_searched = True
        adaylar = list(_FONT_CANDIDATES) + list(pygame.font.get_fonts())
        for name in adaylar:
            for bold in (True, False):
                try:
                    path = pygame.font.match_font(name, bold=bold)
                    if path and _supports_turkish(pygame.font.Font(path, 24)):
                        _font_path = path
                        return _font_path
                except Exception:
                    continue
    return _font_path


def get_font(size):
    """Boyuta göre önbellekli font."""
    font = _fonts.get(size)
    if font is None:
        path = _find_font_path()
        try:
            if path:
                font = pygame.font.Font(path, size)
            else:
                font = pygame.font.SysFont("segoeui,arial,tahoma,verdana,dejavusans", size, bold=True)
        except Exception:
            font = pygame.font.SysFont("arial,tahoma,dejavusans", size, bold=True)
        _fonts[size] = font
    return font


def render_text(text, size, color=WHITE, outline=None, ow=0):
    """Kenarlıklı yazı yüzeyi üret (önbellekli)."""
    key = (text, size, color, outline, ow)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 400:
            _text_cache.clear()
        font = get_font(size)
        base = font.render(text, True, color)
        if outline and ow > 0:
            w, h = base.get_size()
            surf = pygame.Surface((w + 2 * ow, h + 2 * ow), pygame.SRCALPHA)
            edge = font.render(text, True, outline)
            for dx in range(-ow, ow + 1):
                for dy in range(-ow, ow + 1):
                    if dx * dx + dy * dy <= ow * ow + 1:
                        surf.blit(edge, (ow + dx, ow + dy))
            surf.blit(base, (ow, ow))
        else:
            surf = base
        _text_cache[key] = surf
    return surf


def draw_text(surf, text, size, color, pos, anchor="center", outline=DARK, ow=3, max_w=None):
    """Yazıyı verilen noktaya (anchor: center, topleft, midtop ...) çizer; Rect döner.

    max_w verilirse yazı bu genişliğe sığana kadar küçültülür (farklı fontlarda taşmayı önler).
    """
    img = render_text(text, size, color, outline, ow)
    while max_w and img.get_width() > max_w and size > 12:
        size -= 1
        img = render_text(text, size, color, outline, ow)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surf.blit(img, rect)
    return rect


def draw_panel(surf, rect, fill=(255, 244, 214), border=(120, 80, 40), radius=24):
    """Gölgeli, yuvarlak köşeli panel."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, (95, 65, 35), rect.move(0, 8), border_radius=radius)
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, 4, border_radius=radius)


class Button:
    """Yuvarlak köşeli, 3 boyutlu görünümlü buton (üzerine gelme ve basma efektli)."""

    THEMES = {
        "green":  ((104, 205, 70), (58, 138, 44)),
        "orange": ((255, 176, 40), (205, 112, 20)),
        "blue":   ((80, 175, 240), (40, 108, 190)),
        "red":    ((240, 95, 85), (176, 48, 48)),
    }
    DEPTH = 6

    def __init__(self, rect, text, callback, theme="green", font_size=34):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.theme = theme
        self.font_size = font_size
        self.offset = 0            # animasyon için dikey kaydırma
        self.hover = False
        self.pressed = False

    def _area(self):
        return self.rect.move(0, self.offset)

    def contains(self, pos):
        return self._area().collidepoint(pos)

    def update(self, pos):
        self.hover = self.contains(pos)

    def handle_event(self, event, pos):
        """Fare bırakıldığında buton üzerindeyse callback çağırır; tıklandıysa True döner."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed = self.contains(pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed, self.pressed = self.pressed, False
            if was_pressed and self.contains(pos):
                self.callback()
                return True
        return False

    def draw(self, surf):
        face_color, base_color = self.THEMES[self.theme]
        area = self._area()
        radius = min(24, area.h // 2)
        down = self.pressed and self.hover
        drop = self.DEPTH - 2 if down else 0

        base = pygame.Rect(area.x, area.y + self.DEPTH, area.w, area.h)
        pygame.draw.rect(surf, base_color, base, border_radius=radius)
        pygame.draw.rect(surf, DARK, base, 3, border_radius=radius)

        face = pygame.Rect(area.x, area.y + drop, area.w, area.h)
        color = lighten(face_color, 22) if self.hover else face_color
        pygame.draw.rect(surf, color, face, border_radius=radius)
        gloss = pygame.Rect(face.x + 8, face.y + 5, face.w - 16, face.h // 2 - 4)
        pygame.draw.rect(surf, lighten(color, 30), gloss, border_radius=max(1, radius - 8))
        pygame.draw.rect(surf, DARK, face, 3, border_radius=radius)

        draw_text(surf, self.text, self.font_size, WHITE, face.center, outline=DARK, ow=3,
                  max_w=face.w - 24)

# ==========================================================================
# GAME
# ==========================================================================
class State(Enum):
    MENU = auto()
    SETTINGS = auto()
    READY = auto()       # "Hazır mısın?" - ilk zıplamayı bekler
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()


class Cloud:
    """Yavaşça süzülen, ekrandan çıkınca yeniden doğan bulut."""

    def __init__(self, img, x, y, speed):
        self.img, self.x, self.y, self.speed = img, x, y, speed

    def update(self, dt, world_speed):
        self.x -= (self.speed + world_speed * 0.04) * dt
        if self.x < -self.img.get_width():
            self.x = W + random.uniform(0, 140)
            self.y = random.uniform(40, 330)

    def draw(self, surf):
        surf.blit(self.img, (int(self.x), int(self.y)))


class Particle:
    """Çarpma ve zıplama sırasında çıkan küçük parçacıklar."""

    def __init__(self, x, y, vx, vy, life, color, size):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size = color, size

    def update(self, dt):
        self.life -= dt
        self.vy += 900 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        radius = max(1, int(self.size * self.life / self.max_life))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), radius)


def ease_out(t):
    return 1.0 - (1.0 - t) ** 3


def star_points(cx, cy, r_out, r_in, n=5):
    pts = []
    for i in range(n * 2):
        ang = -math.pi / 2 + i * math.pi / n
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    return pts


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)     # init() öncesi: kendi ses ayarımız
        pygame.init()
        pygame.display.set_caption("Flappy Bird")
        self.window = pygame.display.set_mode(self._initial_window_size(), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.view = (0, 0, 1.0)                          # (x kayması, y kayması, ölçek)
        self.scroll_far = self.scroll_near = self.scroll_ground = 0.0

        # Görseller (hepsi kodla çizilir). Genişliğe bağlı olanlar build_scenery'de kurulur.
        self.cloud_imgs = [make_cloud(w) for w in (150, 110, 190)]
        self.bird_frames = make_bird_frames()
        self.pipe_tex = make_pipe_textures()
        self.build_scenery()
        pygame.display.set_icon(self.bird_frames[1])

        # Kayıt ve ses
        self.save = SaveData()
        self.audio = AudioManager(SOUND_DIR, self.save.music, self.save.sfx)

        # Oyun durumu
        self.state = State.MENU
        self.running = True
        self.time = 0.0
        self.bird = Bird()
        self.pipes = PipeField()
        self.score = 0
        self.new_record = False
        self.go_timer = 0.0
        self.panel_t = 0.0
        self.jingle_played = False
        self.score_pop = 0.0
        self.flash = 0.0
        self.shake = 0.0
        self.world_speed = 0.0
        self.scroll_far = self.scroll_near = self.scroll_ground = 0.0
        self.particles = []
        self._build_ui()

    # ======================================================================
    # Kurulum
    # ======================================================================
    def build_scenery(self):
        """Mantıksal genişliğe (W) bağlı tüm yüzeyleri yeniden oluştur."""
        self.canvas = pygame.Surface((W, H)).convert()   # mantıksal çizim yüzeyi
        self.sky = make_sky()
        self.hills_far = make_hills(200, 60, 35, 256, 146, 0.7, (166, 212, 232))
        self.hills_near = make_hills(200, 125, 26, 146, 93, 2.1, (104, 192, 118))
        self.ground_img = make_ground()
        self.dim = pygame.Surface((W, H), pygame.SRCALPHA)
        self.flash_surf = pygame.Surface((W, H))
        self.flash_surf.fill(WHITE)
        self.scroll_far %= W
        self.scroll_near %= W
        self.clouds = [Cloud(random.choice(self.cloud_imgs), random.uniform(0, W),
                             random.uniform(40, 330), random.uniform(6, 16))
                       for _ in range(max(5, W // 115))]

    def fit_to_window(self):
        """Pencere oranına uyum: yükseklik sabit (H), genişlik pencerenin oranına göre değişir.

        Büyütünce / tam ekran yapınca oyun alanı yanlara genişler, siyah bant kalmaz.
        """
        global W
        ww, wh = pygame.display.get_surface().get_size()
        new_w = max(MIN_W, min(MAX_W, int(round(H * ww / max(1, wh)))))
        if new_w != W:
            W = new_w
            self.build_scenery()
            self._build_ui()

    def toggle_fullscreen(self):
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            pass

    @staticmethod
    def _initial_window_size():
        """Pencereyi ekrana sığacak boyutta aç (küçük ekranlarda ölçeklenir)."""
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            dw, dh = 1920, 1080
        scale = min(dh * 0.88 / H, dw * 0.90 / W)      # ekranın büyük bölümünü kapla
        return max(512, int(W * scale)), max(384, int(H * scale))

    def _build_ui(self):
        cx = W // 2
        self.menu_buttons = [
            Button((cx - 135, 405, 270, 70), "Oyuna Başla", self.start_game, "green", 38),
            Button((cx - 135, 495, 270, 62), "Ayarlar", self.open_settings, "orange", 32),
            Button((cx - 135, 575, 270, 62), "Çıkış", self.quit_game, "red", 32),
        ]
        self.btn_music = Button((cx - 150, 235, 300, 60), "", self.toggle_music, "blue", 28)
        self.btn_sfx = Button((cx - 150, 315, 300, 60), "", self.toggle_sfx, "blue", 28)
        self.btn_diff = Button((cx - 150, 395, 300, 60), "", self.cycle_difficulty, "orange", 28)
        self.btn_back = Button((cx - 120, 492, 240, 62), "Geri", self.go_menu, "green", 32)
        self.settings_buttons = [self.btn_music, self.btn_sfx, self.btn_diff, self.btn_back]
        self.over_buttons = [
            Button((cx - 135, 505, 270, 64), "Yeniden Oyna", self.start_game, "green", 34),
            Button((cx - 135, 585, 270, 56), "Ana Menü", self.go_menu, "blue", 30),
        ]
        self._refresh_settings_labels()

    def _refresh_settings_labels(self):
        self.btn_music.text = "Müzik: " + ("Açık" if self.save.music else "Kapalı")
        self.btn_sfx.text = "Ses Efektleri: " + ("Açık" if self.save.sfx else "Kapalı")
        self.btn_diff.text = "Zorluk: " + self.difficulty["label"]

    @property
    def difficulty(self):
        return DIFFICULTIES[self.save.difficulty]

    # ======================================================================
    # Durum geçişleri
    # ======================================================================
    def reset_round(self):
        self.bird.reset()
        self.pipes.reset()
        self.score = 0
        self.new_record = False
        self.particles.clear()
        self.flash = self.shake = self.score_pop = 0.0
        self.panel_t = self.go_timer = 0.0
        self.jingle_played = False

    def start_game(self):
        """Menüden veya Game Over'dan yeni tur: kuş sallanır, ilk zıplamayı bekler."""
        self.reset_round()
        self.pipes.spawn(self.difficulty)               # ilk boru ekranda hazır bekler
        self.pipes.pipes[-1].x = BIRD_X + 480
        self.state = State.READY
        self.audio.play("start")

    def go_menu(self):
        self.commit_score()
        self.reset_round()
        self.state = State.MENU

    def open_settings(self):
        self._refresh_settings_labels()
        self.state = State.SETTINGS

    def quit_game(self):
        self.running = False

    def commit_score(self):
        """Skor rekoru geçtiyse kaydet. Yeni rekor ise True döner."""
        if self.score > self.save.high_score:
            self.save.high_score = self.score
            self.save.save()
            return True
        return False

    def flap(self):
        """Zıplama; READY durumundaysa oyunu başlatır."""
        if self.state is State.READY:
            self.state = State.PLAYING
        if self.state is State.PLAYING:
            self.bird.flap()
            self.audio.play("flap")
            for _ in range(3):
                self.particles.append(Particle(
                    self.bird.x - 14, self.bird.y + 6, random.uniform(-90, -30),
                    random.uniform(-30, 60), 0.35, (255, 255, 255), 5))

    def die(self, hit_ground):
        """Çarpma: efektler, skor kaydı ve Game Over durumuna geçiş."""
        self.state = State.GAME_OVER
        self.bird.dead = True
        if hit_ground:
            self.bird.y = GROUND_Y - BIRD_RADIUS
            self.bird.vel = 0.0
        else:
            self.bird.vel = max(self.bird.vel, 0.0)
        self.audio.play("hit")
        self.flash, self.shake = 1.0, SHAKE_TIME
        for _ in range(16):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80, 320)
            self.particles.append(Particle(
                self.bird.x, self.bird.y, math.cos(ang) * spd, math.sin(ang) * spd - 120,
                random.uniform(0.4, 0.9), random.choice([(255, 205, 50), (255, 150, 40), (255, 255, 255)]),
                random.randint(4, 8)))
        self.new_record = self.commit_score()
        self.go_timer = self.panel_t = 0.0
        self.jingle_played = False

    def toggle_pause(self):
        if self.state is State.PLAYING:
            self.state = State.PAUSED
        elif self.state is State.PAUSED:
            self.state = State.PLAYING

    # -- ayarlar -----------------------------------------------------------
    def toggle_music(self):
        self.save.music = not self.save.music
        self.audio.set_music_enabled(self.save.music)
        self.save.save()
        self._refresh_settings_labels()

    def toggle_sfx(self):
        self.save.sfx = not self.save.sfx
        self.audio.set_sfx_enabled(self.save.sfx)
        self.audio.play("flap")                       # açıldıysa örnek ses
        self.save.save()
        self._refresh_settings_labels()

    def cycle_difficulty(self):
        idx = DIFF_ORDER.index(self.save.difficulty)
        self.save.difficulty = DIFF_ORDER[(idx + 1) % len(DIFF_ORDER)]
        self.save.save()
        self._refresh_settings_labels()

    # ======================================================================
    # Ana döngü
    # ======================================================================
    def run(self):
        while self.running:
            # tick(FPS): kare hızını sabit tutar. dt: geçen süre (saniye), hareketler buna göre
            # hesaplanır; pencere sürüklenirken oluşan uzun karelerde ışınlanma olmasın diye sınırlanır.
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 30)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
            self.present()

    def shutdown(self):
        self.commit_score()
        self.save.save()
        self.audio.shutdown()
        pygame.quit()

    # ======================================================================
    # Girdi
    # ======================================================================
    def to_logical(self, pos):
        """Pencere (piksel) koordinatını mantıksal oyun koordinatına çevir."""
        ox, oy, scale = self.view
        return ((pos[0] - ox) / scale, (pos[1] - oy) / scale)

    def active_buttons(self):
        if self.state is State.MENU:
            return self.menu_buttons
        if self.state is State.SETTINGS:
            return self.settings_buttons
        if self.state is State.GAME_OVER and self.panel_t >= 0.9:
            return self.over_buttons
        return []

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            self.on_key(event.key)
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pos = self.to_logical(event.pos)
            for button in list(self.active_buttons()):
                if button.handle_event(event, pos):
                    return                           # tıklama butona ait, başka işlem yapma
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.on_click()

    def on_click(self):
        if self.state in (State.READY, State.PLAYING):
            self.flap()
        elif self.state is State.PAUSED:
            self.toggle_pause()

    def on_key(self, key):
        if key == pygame.K_F11:
            self.toggle_fullscreen()
        elif key == pygame.K_ESCAPE:
            if self.state is not State.MENU:
                self.go_menu()
        elif key == pygame.K_p:
            self.toggle_pause()
        elif key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN):
            if self.state in (State.READY, State.PLAYING) and key != pygame.K_RETURN:
                self.flap()
            elif self.state is State.MENU:
                self.start_game()
            elif self.state is State.PAUSED:
                self.toggle_pause()
            elif self.state is State.GAME_OVER and self.panel_t >= 0.9:
                self.start_game()

    # ======================================================================
    # Güncelleme
    # ======================================================================
    def current_speed(self):
        return pipe_speed(self.difficulty, self.score)

    def update(self, dt):
        self.fit_to_window()
        self.audio.update()
        if self.state is State.PAUSED:
            return
        self.time += dt

        # Arka plan ve zemin hızı duruma göre belirlenir.
        if self.state is State.PLAYING:
            self.world_speed = self.current_speed()
        elif self.state is State.READY:
            self.world_speed = 0.0                   # ilk zıplamaya kadar dünya durur
        elif self.state is State.GAME_OVER:
            self.world_speed = 0.0                   # çarpınca her şey durur
        else:
            self.world_speed = 60.0                  # menüde yavaş akış
        ws = self.world_speed
        self.scroll_far = (self.scroll_far + ws * 0.08 * dt) % W
        self.scroll_near = (self.scroll_near + ws * 0.30 * dt) % W
        self.scroll_ground = (self.scroll_ground + ws * dt) % GROUND_TILE
        for cloud in self.clouds:
            cloud.update(dt, ws)

        if self.state is State.READY:
            self.bird.hover(dt)
        elif self.state is State.PLAYING:
            self.update_playing(dt)
        elif self.state is State.GAME_OVER:
            self.update_game_over(dt)
        elif self.state is State.MENU:
            self.bird.anim += dt

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        self.flash = max(0.0, self.flash - dt * 4.0)
        self.shake = max(0.0, self.shake - dt)
        self.score_pop = max(0.0, self.score_pop - dt * 5.0)

        pos = self.to_logical(pygame.mouse.get_pos())
        for button in self.active_buttons():
            button.update(pos)

    def update_playing(self, dt):
        bird = self.bird
        bird.update(dt)
        self.pipes.update(self.current_speed() * dt, self.difficulty)

        if bird.hits_ground():
            self.die(hit_ground=True)
            return
        if any(p.collides(bird) for p in self.pipes.pipes):
            self.die(hit_ground=False)
            return

        # Kuş borunun ortasını geçince puan ver.
        for p in self.pipes.pipes:
            if not p.scored and p.x + PIPE_W / 2 < bird.x:
                p.scored = True
                self.score += 1
                self.score_pop = 1.0
                self.audio.play("score")

    def update_game_over(self, dt):
        self.bird.update_dead(dt)
        self.go_timer += dt
        if self.go_timer >= PANEL_DELAY and not self.jingle_played:
            self.jingle_played = True
            self.audio.play("gameover")
        self.panel_t = max(0.0, min(1.0, (self.go_timer - PANEL_DELAY) / PANEL_ANIM))
        for button in self.over_buttons:             # butonlar panelle birlikte aşağıdan kayar
            button.offset = int((1.0 - ease_out(self.panel_t)) * 520)

    # ======================================================================
    # Çizim
    # ======================================================================
    def draw(self):
        c = self.canvas
        c.blit(self.sky, (0, 0))
        for cloud in self.clouds:
            cloud.draw(c)
        self._draw_scrolling(c, self.hills_far, self.scroll_far)
        self._draw_scrolling(c, self.hills_near, self.scroll_near)

        in_round = self.state in (State.READY, State.PLAYING, State.PAUSED, State.GAME_OVER)
        if in_round:
            for pipe in self.pipes.pipes:
                draw_pipe(c, pipe, self.pipe_tex)
        c.blit(self.ground_img, (-int(self.scroll_ground), GROUND_Y))

        if in_round:
            self.draw_bird(c, self.bird.x, self.bird.y, self.bird.angle, self.bird.anim)
        for p in self.particles:
            p.draw(c)

        if self.state is State.MENU:
            self.draw_menu(c)
        elif self.state is State.SETTINGS:
            self.draw_settings(c)
        elif self.state is State.READY:
            self.draw_hud(c)
            self.draw_ready(c)
        elif self.state is State.PLAYING:
            self.draw_hud(c)
        elif self.state is State.PAUSED:
            self.draw_hud(c)
            self.draw_pause(c)
        elif self.state is State.GAME_OVER:
            if self.panel_t <= 0.0:
                self.draw_hud(c)
            self.draw_game_over(c)

        if self.flash > 0:
            self.flash_surf.set_alpha(int(255 * min(1.0, self.flash) * 0.7))
            c.blit(self.flash_surf, (0, 0))

    @staticmethod
    def _draw_scrolling(surf, layer, offset):
        """Katmanı sola kaydır; iki kopya yan yana çizilerek kesintisiz döngü sağlanır."""
        x = -int(offset)
        y = GROUND_Y - layer.get_height()
        surf.blit(layer, (x, y))
        surf.blit(layer, (x + W, y))

    def draw_bird(self, surf, x, y, angle, anim, scale=1.0):
        frame = self.bird_frames[int(anim * 14) % len(self.bird_frames)]
        img = pygame.transform.rotozoom(frame, angle, scale)
        surf.blit(img, img.get_rect(center=(int(x), int(y))))

    def draw_hud(self, surf):
        size = 84 + int(10 * self.score_pop)
        draw_text(surf, str(self.score), size, WHITE, (W // 2, 95), outline=DARK, ow=5)

    def draw_ready(self, surf):
        draw_text(surf, "Hazır mısın?", 46, (255, 236, 120), (W // 2, 210), outline=(110, 60, 15), ow=4,
                     max_w=W - 40)
        if int(self.time * 2) % 2 == 0:
            draw_text(surf, "Zıplamak için Space veya Sol Tık", 26, WHITE, (W // 2, 520), ow=3,
                         max_w=W - 30)

    def draw_pause(self, surf):
        self.dim.fill((0, 0, 0, 110))
        surf.blit(self.dim, (0, 0))
        draw_text(surf, "DURAKLATILDI", 56, WHITE, (W // 2, 340), outline=DARK, ow=5, max_w=W - 40)
        draw_text(surf, "Devam için P, Space veya Tık", 26, WHITE, (W // 2, 410), ow=3, max_w=W - 30)

    def draw_menu(self, surf):
        bob = math.sin(self.time * 3.0) * 6
        draw_text(surf, "FLAPPY", 88, (255, 214, 60), (W // 2, 115 + bob),
                     outline=(115, 60, 15), ow=6, max_w=W - 30)
        draw_text(surf, "BIRD", 88, (255, 140, 80), (W // 2, 195 + bob),
                     outline=(110, 40, 10), ow=6, max_w=W - 30)
        self.draw_bird(surf, W // 2, 305 + math.sin(self.time * 4.0) * 10, 8 * math.sin(self.time * 4.0),
                       self.bird.anim, 1.5)
        for b in self.menu_buttons:
            b.draw(surf)
        draw_panel(surf, (W // 2 - 140, 672, 280, 50), radius=18)
        draw_text(surf, f"En Yüksek Skor: {self.save.high_score}", 26, (120, 70, 20),
                     (W // 2, 697), outline=None, ow=0, max_w=250)

    def draw_settings(self, surf):
        draw_panel(surf, (W // 2 - 180, 150, 360, 440))
        draw_text(surf, "AYARLAR", 54, WHITE, (W // 2, 192), outline=(110, 60, 15), ow=5, max_w=320)
        for b in self.settings_buttons:
            b.draw(surf)
        draw_text(surf, "Zorluk bir sonraki oyunda geçerli olur", 20, (120, 70, 20),
                     (W // 2, 575), outline=None, ow=0, max_w=330)

    def draw_game_over(self, surf):
        e = ease_out(self.panel_t)
        if e <= 0:
            return
        self.dim.fill((0, 0, 0, int(110 * e)))
        surf.blit(self.dim, (0, 0))

        off = int((1.0 - e) * 520)
        draw_text(surf, "GAME OVER", 66, (255, 98, 78), (W // 2, 140 - int((1.0 - e) * 300)),
                     outline=(100, 25, 20), ow=6, max_w=W - 30)

        panel = pygame.Rect(W // 2 - 170, 200 + off, 340, 260)
        draw_panel(surf, panel)
        self.draw_medal(surf, (panel.x + 82, panel.y + 132), self.score)

        col_x = panel.right - 100
        draw_text(surf, "SKOR", 22, (150, 100, 50), (col_x, panel.y + 40), outline=None, ow=0)
        draw_text(surf, str(self.score), 64, WHITE, (col_x, panel.y + 88), outline=DARK, ow=4, max_w=140)
        draw_text(surf, "EN YÜKSEK", 22, (150, 100, 50), (col_x, panel.y + 150), outline=None, ow=0,
                     max_w=140)
        draw_text(surf, str(self.save.high_score), 52, WHITE, (col_x, panel.y + 198), outline=DARK, ow=4,
                     max_w=140)
        if self.new_record:
            badge = pygame.Rect(0, 0, 150, 34)
            badge.center = (panel.centerx, panel.y - 2)
            pygame.draw.rect(surf, (240, 70, 60), badge, border_radius=17)
            pygame.draw.rect(surf, DARK, badge, 3, border_radius=17)
            draw_text(surf, "YENİ REKOR!", 22, WHITE, badge.center, outline=None, ow=0, max_w=134)

        for b in self.over_buttons:
            b.draw(surf)

    @staticmethod
    def draw_medal(surf, center, score):
        """Skora göre madalya: 10 bronz, 20 gümüş, 30 altın, 40 platin."""
        tiers = [(40, (120, 230, 230)), (30, (255, 205, 50)), (20, (205, 210, 220)), (10, (205, 127, 50))]
        color = next((col for need, col in tiers if score >= need), None)
        cx, cy = center
        if color is None:
            pygame.draw.circle(surf, (225, 205, 165), center, 38)
            pygame.draw.circle(surf, (190, 165, 120), center, 38, 4)
            return
        pygame.draw.circle(surf, DARK, center, 40)
        pygame.draw.circle(surf, color, center, 37)
        pygame.draw.circle(surf, lighten(color, 40), center, 28, 3)
        pygame.draw.polygon(surf, lighten(color, 50), star_points(cx, cy, 20, 8))
        pygame.draw.polygon(surf, DARK, star_points(cx, cy, 20, 8), 2)

    # ======================================================================
    # Pencereye aktarım (yeniden boyutlandırma + letterbox)
    # ======================================================================
    def present(self):
        win = pygame.display.get_surface()
        ww, wh = win.get_size()
        scale = min(ww / W, wh / H)
        dw, dh = max(1, int(W * scale)), max(1, int(H * scale))
        ox, oy = (ww - dw) // 2, (wh - dh) // 2
        self.view = (ox, oy, scale)

        win.fill(BAR_COLOR)
        frame = self.canvas if (dw, dh) == (W, H) else pygame.transform.smoothscale(self.canvas, (dw, dh))
        sx = sy = 0
        if self.shake > 0:                           # çarpma sarsıntısı
            amp = max(1, int(9 * self.shake / SHAKE_TIME * scale))
            sx, sy = random.randint(-amp, amp), random.randint(-amp, amp)
        win.blit(frame, (ox + sx, oy + sy))
        pygame.display.flip()


# ============================================================================
# GİRİŞ NOKTASI
# ============================================================================
def main():
    game = Game()
    try:
        game.run()
    except KeyboardInterrupt:
        pass
    finally:
        game.shutdown()


if __name__ == "__main__":
    main()
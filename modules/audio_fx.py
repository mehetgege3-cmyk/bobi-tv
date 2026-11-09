"""
BOBİ TV — Profesyonel Ses Efektleri (SFX), Telifsiz BGM ve Sidechain Miksaj Motoru v6.0
- Sıfır telif riski: NumPy tabanlı stüdyo kalitesinde SFX sentezi (whoosh, pop, vine_boom, riser, ding)
- Telefon hoparlöründe duyulabilir harmonikli 808 Vine Boom & Bubble Pop
- Konuşma sırasında otomatik kısılan (Sidechain Ducking, -20 dB) ritmik Lo-Fi Komedi BGM
- FFmpeg EBU R128 / YouTube Shorts standardı (-14 LUFS) ses dengelemesi
"""
import os
import wave
import subprocess
from pathlib import Path
import numpy as np

SR = 44100
SFX_KLASORU = Path("bobi_tv/assets/sfx")


def _wav_kaydet(yol: Path, veri: np.ndarray, sr: int = SR) -> str:
    yol.parent.mkdir(parents=True, exist_ok=True)
    veri = np.clip(veri, -0.98, 0.98)
    pcm = (veri * 32767.0).astype(np.int16)
    with wave.open(str(yol), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return str(yol)


def _wav_oku(yol: str) -> np.ndarray:
    """Herhangi bir ses dosyasını 44.1kHz mono float32 dizi olarak okur."""
    tmp_wav = str(yol) + "_norm44k.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(yol), "-ar", str(SR), "-ac", "1", "-f", "wav", tmp_wav],
            capture_output=True, check=True, timeout=30
        )
        with wave.open(tmp_wav, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return arr
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)


def sfx_varliklarini_hazirla() -> dict:
    """Tüm temel SFX dosyalarını bobi_tv/assets/sfx/ altında üretir (varsa önbellekten döner)."""
    SFX_KLASORU.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    yollar = {}

    # 1. WHOOSH (0.30sn — sinematik geçiş rüzgarı)
    whoosh_yol = SFX_KLASORU / "whoosh.wav"
    if not whoosh_yol.exists():
        sure = 0.30
        t = np.linspace(0, sure, int(SR * sure), endpoint=False)
        noise = rng.standard_normal(len(t)).astype(np.float32)
        # Hareketli ortalama ile dinamik alçak geçiren süpürme + frekans modülasyonlu ton
        sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(160, 920, len(t)) / SR))
        kernel = np.hanning(35)
        kernel /= kernel.sum()
        filtered = np.convolve(noise, kernel, mode="same")
        env = np.sin(np.pi * (t / sure)) ** 1.6
        sig = (0.72 * filtered + 0.28 * sweep) * env * 0.75
        _wav_kaydet(whoosh_yol, sig)
    yollar["whoosh"] = str(whoosh_yol)

    # 2. POP (0.10sn — konuşma balonu açılış sesi)
    pop_yol = SFX_KLASORU / "pop.wav"
    if not pop_yol.exists():
        sure = 0.10
        t = np.linspace(0, sure, int(SR * sure), endpoint=False)
        freqs = 240.0 + 540.0 * ((t / sure) ** 1.4)
        phase = 2 * np.pi * np.cumsum(freqs / SR)
        env = np.exp(-t * 28.0) * np.minimum(1.0, t / 0.006)
        sig = (np.sin(phase) + 0.25 * np.sin(2 * phase)) * env * 0.65
        _wav_kaydet(pop_yol, sig)
    yollar["pop"] = str(pop_yol)

    # 3. VINE BOOM (0.85sn — telefon hoparlöründe de duyulan harmonikli 808 şok bası)
    boom_yol = SFX_KLASORU / "vine_boom.wav"
    if not boom_yol.exists():
        sure = 0.85
        t = np.linspace(0, sure, int(SR * sure), endpoint=False)
        # Hızlı transient (135Hz -> 44Hz)
        freqs = 44.0 + 95.0 * np.exp(-t * 16.0)
        phase = 2 * np.pi * np.cumsum(freqs / SR)
        sub = np.sin(phase) + 0.48 * np.sin(2 * phase) + 0.22 * np.sin(3 * phase)
        punch = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 45.0) * 0.5
        env = np.exp(-t * 3.6) * np.minimum(1.0, t / 0.005)
        sig = np.tanh((sub + punch) * env * 1.9) * 0.88
        _wav_kaydet(boom_yol, sig)
    yollar["vine_boom"] = str(boom_yol)

    # 4. RISER (0.68sn — twist öncesi gerilim yükselişi)
    riser_yol = SFX_KLASORU / "riser.wav"
    if not riser_yol.exists():
        sure = 0.68
        t = np.linspace(0, sure, int(SR * sure), endpoint=False)
        freqs = np.linspace(180, 1250, len(t))
        phase = 2 * np.pi * np.cumsum(freqs / SR)
        shimmer = rng.standard_normal(len(t)).astype(np.float32) * 0.18
        env = (t / sure) ** 2.1 * np.minimum(1.0, (sure - t) / 0.02)
        sig = (0.65 * np.sin(phase) + 0.25 * np.sin(1.5 * phase) + shimmer) * env * 0.55
        _wav_kaydet(riser_yol, sig)
    yollar["riser"] = str(riser_yol)

    # 5. DING (0.42sn — parlak komedi vurgu çanı)
    ding_yol = SFX_KLASORU / "ding.wav"
    if not ding_yol.exists():
        sure = 0.42
        t = np.linspace(0, sure, int(SR * sure), endpoint=False)
        env = np.exp(-t * 9.5) * np.minimum(1.0, t / 0.003)
        sig = (
            0.60 * np.sin(2 * np.pi * 1046.5 * t)
            + 0.28 * np.sin(2 * np.pi * 2093.0 * t)
            + 0.12 * np.sin(2 * np.pi * 3136.0 * t)
        ) * env * 0.65
        _wav_kaydet(ding_yol, sig)
    yollar["ding"] = str(ding_yol)

    return yollar


def telifsiz_bgm_sentezle(toplam_sure: float, ruh_hali: str = "komedi") -> np.ndarray:
    """
    Konuşma frekanslarını (1kHz-4kHz) maskelemeyen, 116 BPM sıcak ritmik komedi/lo-fi arka plan müziği üretir.
    %100 telifsizdir ve başa sardığında ritim kesintisiz devam eder.
    """
    ornek_sayisi = max(1, int(SR * toplam_sure))
    bgm = np.zeros(ornek_sayisi, dtype=np.float32)
    rng = np.random.default_rng(101)

    bpm = 118.0 if ruh_hali != "dramatik" else 102.0
    vurus_sn = 60.0 / bpm
    yarim_vurus = vurus_sn / 2.0

    # Minör pentatonik komedi pizzicato yürüyüşü (Hz): A2, C3, D3, E3, G3, E3, D3, C3
    notalar = [110.0, 130.81, 146.83, 164.81, 196.00, 164.81, 146.83, 130.81]
    if ruh_hali == "gerilim":
        notalar = [110.0, 116.54, 146.83, 155.56, 146.83, 116.54, 110.0, 98.0]

    adim_idx = 0
    zaman = 0.0
    while zaman < toplam_sure:
        bas = int(zaman * SR)
        # Yumuşak Kick (her tam vuruşta: çift adımlarda)
        if adim_idx % 2 == 0:
            k_len = min(int(0.16 * SR), ornek_sayisi - bas)
            if k_len > 10:
                kt = np.linspace(0, k_len / SR, k_len, endpoint=False)
                kf = 52.0 + 75.0 * np.exp(-kt * 28.0)
                k_sig = np.sin(2 * np.pi * np.cumsum(kf / SR)) * np.exp(-kt * 16.0) * 0.48
                bgm[bas:bas + k_len] += k_sig.astype(np.float32)

        # İnce Shaker / Hi-hat (her yarım vuruşta, özellikle off-beat'te)
        h_len = min(int(0.045 * SR), ornek_sayisi - bas)
        if h_len > 10:
            ht = np.linspace(0, h_len / SR, h_len, endpoint=False)
            seviye = 0.14 if adim_idx % 2 == 1 else 0.07
            shaker = rng.standard_normal(h_len).astype(np.float32) * np.exp(-ht * 65.0) * seviye
            bgm[bas:bas + h_len] += shaker

        # Pizzicato sıcak bas notası
        p_len = min(int(yarim_vurus * 0.88 * SR), ornek_sayisi - bas)
        if p_len > 10:
            pt = np.linspace(0, p_len / SR, p_len, endpoint=False)
            f0 = notalar[adim_idx % len(notalar)]
            env = np.exp(-pt * 7.5) * np.minimum(1.0, pt / 0.008)
            pluck = (0.72 * np.sin(2 * np.pi * f0 * pt) + 0.28 * np.sin(2 * np.pi * (f0 * 2) * pt)) * env * 0.36
            bgm[bas:bas + p_len] += pluck.astype(np.float32)

        zaman += yarim_vurus
        adim_idx += 1

    # Son 80ms'de mikroskobik loop yumuşatma
    fade_n = min(int(0.06 * SR), ornek_sayisi // 4)
    if fade_n > 0:
        bgm[:fade_n] *= np.linspace(0.35, 1.0, fade_n, dtype=np.float32)
        bgm[-fade_n:] *= np.linspace(1.0, 0.35, fade_n, dtype=np.float32)

    return bgm


def profesyonel_ses_miksla(
    diyalog_wav: str,
    sfx_olaylari: list,
    toplam_sure: float,
    cikis_wav: str,
    ruh_hali: str = "komedi",
) -> str:
    """
    Diyalog + Sidechain BGM (-19dB konuşmada / -14dB boşlukta) + Milisaniyelik SFX + -14 LUFS Loudnorm.
    """
    sfx_haritasi = sfx_varliklarini_hazirla()
    hedef_ornek = max(int(toplam_sure * SR), 1)

    diyalog = _wav_oku(diyalog_wav) if os.path.exists(diyalog_wav) else np.zeros(hedef_ornek, dtype=np.float32)
    if len(diyalog) < hedef_ornek:
        diyalog = np.pad(diyalog, (0, hedef_ornek - len(diyalog)))
    else:
        hedef_ornek = len(diyalog)
        toplam_sure = hedef_ornek / SR

    # BGM üret ve konuşma zarfına göre otomatik kıs (Sidechain Ducking)
    bgm = telifsiz_bgm_sentezle(toplam_sure, ruh_hali=ruh_hali)
    if len(bgm) < hedef_ornek:
        bgm = np.pad(bgm, (0, hedef_ornek - len(bgm)))
    bgm = bgm[:hedef_ornek]

    # Konuşma enerji zarfı (120ms pencere)
    pencere = int(0.12 * SR)
    kare_enerji = np.convolve(np.abs(diyalog), np.ones(pencere, dtype=np.float32) / pencere, mode="same")
    konusma_aktif = np.clip(kare_enerji * 8.0, 0.0, 1.0)
    # Konuşma yokken ~0.18 (-15dB), konuşma varken ~0.10 (-20dB)
    bgm_kazanc = 0.18 - (0.085 * konusma_aktif)
    mikslenen = diyalog * 1.02 + bgm * bgm_kazanc

    # SFX olaylarını tam milisaniyesine yerleştir
    sfx_cache = {}
    for olay in sfx_olaylari:
        tip = olay.get("tip", "")
        yol = sfx_haritasi.get(tip)
        if not yol or not os.path.exists(yol):
            continue
        if tip not in sfx_cache:
            sfx_cache[tip] = _wav_oku(yol)
        efekt = sfx_cache[tip]
        seviye = float(olay.get("seviye", 0.42))
        bas_idx = max(0, int(float(olay.get("zaman", 0.0)) * SR))
        if bas_idx >= hedef_ornek:
            continue
        ek_uzunluk = min(len(efekt), hedef_ornek - bas_idx)
        mikslenen[bas_idx:bas_idx + ek_uzunluk] += efekt[:ek_uzunluk] * seviye

    # Geçici ham miksajı yaz ve FFmpeg loudnorm (-14 LUFS) ile YouTube Shorts standardına getir
    ham_wav = str(cikis_wav) + "_raw.wav"
    _wav_kaydet(Path(ham_wav), mikslenen, SR)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", ham_wav,
                "-af", "highpass=f=45,loudnorm=I=-14:TP=-1.5:LRA=11",
                "-ar", str(SR), "-ac", "1",
                str(cikis_wav),
            ],
            capture_output=True, check=True, timeout=60
        )
    except Exception:
        os.replace(ham_wav, cikis_wav)
    finally:
        if os.path.exists(ham_wav):
            os.remove(ham_wav)

    return str(cikis_wav)

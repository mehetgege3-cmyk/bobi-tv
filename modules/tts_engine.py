"""
BOBİ TV — Çift Sesli (Ahmet + Emel), Sıfır Ölü Boşluklu TTS Motoru v6.0
Yenilikler:
- Gerçek 2 karakterli diyalog: tr-TR-AhmetNeural (Erkek) + tr-TR-EmelNeural (Kadın) otomatik zıt atama
- Kritik Hata Çözümü: edge-tts MP3 çıktısı gerçek 44.1kHz PCM WAV'a dönüştürülür (eski wave.open 3.0sn hatası giderildi)
- Sıfır Ölü Boşluk: FFmpeg silenceremove ile cümle başı/sonu nefes boşlukları kesilir (+45ms doğal geçiş payı)
- Milimetrik Altyazı Senkronu: WordBoundary kelime zaman damgaları kırpılmış gerçek süreye kalibre edilir
- 3 Katmanlı Sağlam Fallback: edge-tts → gTTS (cinsiyet/ton ayrımlı) → espeak-ng
"""
import os
import re
import wave
import asyncio
import importlib.util
import subprocess
from pathlib import Path

from modules.senaryo_v7.ayarlar import Ayarlar

TTS_YOLU = Path("bobi_tv/production/tts")

ERKEK_SES = "tr-TR-AhmetNeural"
KADIN_SES = "tr-TR-EmelNeural"

KADIN_KARAKTER_IPUCLARI = {
    "KADIN", "AYŞE", "AYSE", "ELİF", "ELIF", "ZEYNEP", "ANNE", "ANNESİ", "ANNESI",
    "KARI", "EŞ", "HEMŞİRE", "HEMSIRE", "İK", "IK", "DİYETİSYEN", "DIYETSYEN",
    "ASİSTAN", "ASISTAN", "SEKRETER", "YAPAYZEKA", "YAPAY ZEKA", "SİRİ", "KEDİ", "KEDI",
    "KAHVE MAKİNESİ", "KAHVE", "MÜŞTERİ", "MİSAFİR",
}

# Duygu / ton profilleri (cinsiyet çalışma anında karaktere göre seçilir)
TON_PROFILLERI = {
    "normal":          {"rate": "+10%", "volume": "+0%",  "pitch": "+0Hz"},
    "enerjik":         {"rate": "+18%", "volume": "+8%",  "pitch": "+8Hz"},
    "sinirli":         {"rate": "+22%", "volume": "+12%", "pitch": "+12Hz"},
    "panik":           {"rate": "+24%", "volume": "+10%", "pitch": "+18Hz"},
    "sasirmis":        {"rate": "+16%", "volume": "+8%",  "pitch": "+20Hz"},
    "suprized":        {"rate": "+16%", "volume": "+8%",  "pitch": "+20Hz"},
    "şaşkın":          {"rate": "+16%", "volume": "+8%",  "pitch": "+20Hz"},
    "surprised":       {"rate": "+16%", "volume": "+8%",  "pitch": "+20Hz"},
    "kesin":           {"rate": "+12%", "volume": "+6%",  "pitch": "-4Hz"},
    "ciddi":           {"rate": "+6%",  "volume": "+4%",  "pitch": "-6Hz"},
    "soguk":           {"rate": "+4%",  "volume": "+0%",  "pitch": "-10Hz"},
    "soğuk":           {"rate": "+4%",  "volume": "+0%",  "pitch": "-10Hz"},
    "bikkin":          {"rate": "+2%",  "volume": "+0%",  "pitch": "-8Hz"},
    "bikeyn":          {"rate": "+2%",  "volume": "+0%",  "pitch": "-8Hz"},
    "yavas_bikkin":    {"rate": "+0%",  "volume": "+0%",  "pitch": "-8Hz"},
    "bikkin_dramatik": {"rate": "-2%",  "volume": "+4%",  "pitch": "-12Hz"},
    "bikeyn_dramatik": {"rate": "-2%",  "volume": "+4%",  "pitch": "-12Hz"},
    "yavas_dramatik":  {"rate": "-4%",  "volume": "+5%",  "pitch": "-10Hz"},
    "uykulu":          {"rate": "-6%",  "volume": "-4%",  "pitch": "-12Hz"},
    "dusunceli":       {"rate": "+2%",  "volume": "+0%",  "pitch": "-6Hz"},
    "gururlu":         {"rate": "+10%", "volume": "+6%",  "pitch": "+6Hz"},
    "endiseli":        {"rate": "+15%", "volume": "+2%",  "pitch": "+12Hz"},
    "umutlu":          {"rate": "+12%", "volume": "+4%",  "pitch": "+8Hz"},
    "robotik":         {"rate": "+22%", "volume": "+6%",  "pitch": "+28Hz"},
    "robotik_koro":    {"rate": "+22%", "volume": "+8%",  "pitch": "+28Hz"},
    "derin":           {"rate": "+0%",  "volume": "+8%",  "pitch": "-22Hz"},
    "derin_dramatik":  {"rate": "-5%",  "volume": "+10%", "pitch": "-25Hz"},
    "alarm":           {"rate": "+28%", "volume": "+12%", "pitch": "+35Hz"},
    "twist":           {"rate": "+8%",  "volume": "+12%", "pitch": "-6Hz"},
}


def edge_tts_kurulu_mu() -> bool:
    return importlib.util.find_spec("edge_tts") is not None


def ses_tonu_al(
    ses_tipi: str,
    cinsiyet: str = "erkek",
    *,
    sesid: str | None = None,
    hiz: float = 1.0,
) -> dict:
    """Duygu profilini sabit karakter sesi ve 0.85–1.25 TTS hız çarpanıyla birleştirir."""
    baz = dict(TON_PROFILLERI.get(ses_tipi, TON_PROFILLERI["normal"]))
    default_voice = KADIN_SES if str(cinsiyet).lower().startswith("kad") else ERKEK_SES
    baz["voice"] = sesid if sesid in {ERKEK_SES, KADIN_SES} else default_voice
    multiplier = max(0.85, min(1.25, float(hiz)))
    try:
        rate_percent = int(baz.get("rate", "+0%").replace("%", "").replace("+", ""))
    except ValueError:
        rate_percent = 0
    adjusted_rate = round((1.0 + rate_percent / 100) * multiplier * 100 - 100)
    baz["rate"] = f"{adjusted_rate:+d}%"
    return baz


def _sanitize_for_tts(metin: str) -> str:
    """Türkçe diksiyon düzeltme ve ekrana özel emojileri TTS metninden temizleme."""
    metin = re.sub(r"\bM\.Ö\.\s*", "milattan önce ", metin)
    metin = re.sub(r"\bMÖ\b", "milattan önce", metin)
    metin = re.sub(r"\bİK\b", "insan kaynakları", metin)
    metin = re.sub(r"\bTL\b", "lira", metin)
    metin = re.sub(r"%(\d+)", r"yüzde \1", metin)
    metin = re.sub(r"(\d)\.(\d{3})\b", r"\1\2", metin)
    metin = re.sub(r"(\d)\.(\d)", r"\1,\2", metin)
    metin = re.sub(r"[#*_`~<>]", "", metin)
    # Emoji karakterlerini TTS'in "gülen yüz" diye okumaması için temizle
    metin = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\uFE0F\u200D]+",
        "",
        metin,
    )
    metin = re.sub(r"\s+", " ", metin).strip()
    return metin or "Evet."


def _wav_sessizlik_kirp(giris_ses: str, cikis_wav: Path, ek_filtre: str = "") -> float:
    """
    Giriş sesini (MP3/WAV) 44.1kHz PCM WAV'a çevirir, baştaki ve sondaki ölü sessizliği keser,
    sonuna 45ms yumuşak geçiş payı ekler ve gerçek süreyi (saniye) döndürür.
    """
    zincir = []
    if ek_filtre:
        zincir.append(ek_filtre)
    zincir.append(
        "silenceremove="
        "start_periods=1:start_duration=0.01:start_threshold=-43dB:"
        "stop_periods=-1:stop_duration=0.045:stop_threshold=-43dB"
    )
    zincir.append("afade=t=in:st=0:d=0.012")
    zincir.append("apad=pad_dur=0.045")
    af = ",".join(zincir)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(giris_ses),
            "-af", af,
            "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
            str(cikis_wav),
        ],
        capture_output=True, check=True, timeout=30,
    )
    sure = _ses_suresi_hesapla(cikis_wav)
    # Güvenlik: aşırı kırpma olduysa filtresiz dönüştür
    if sure < 0.22:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(giris_ses),
                "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
                str(cikis_wav),
            ],
            capture_output=True, check=True, timeout=30,
        )
        sure = _ses_suresi_hesapla(cikis_wav)
    return sure


def _ses_suresi_hesapla(ses_dosyasi: Path) -> float:
    try:
        with wave.open(str(ses_dosyasi), "rb") as wf:
            frames = wf.getnframes()
            rate = float(wf.getframerate())
            if rate > 0 and frames > 0:
                return round(frames / rate, 3)
    except Exception:
        pass
    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(ses_dosyasi),
            ],
            capture_output=True, text=True, timeout=10,
        )
        return round(max(0.35, float(res.stdout.strip())), 3)
    except Exception:
        return 1.8


def _zamanlamalari_kalibre_et(ham_zamanlar: list, temiz_metin: str, gercek_sure: float) -> list:
    """
    Başlangıç/bitiş sessizliği kırpıldıktan sonra WordBoundary zaman damgalarını
    [0.00, gercek_sure - 0.04] aralığına sıfır kaymayla oturtur.
    """
    kullanilabilir = max(0.25, gercek_sure - 0.04)
    if not ham_zamanlar:
        return _oransal_zamanlama(temiz_metin, kullanilabilir)

    ilk_bas = ham_zamanlar[0]["baslangic"]
    son_bit = max(ham_zamanlar[-1]["bitis"], ilk_bas + 0.15)
    ham_aralik = max(0.15, son_bit - ilk_bas)
    olcek = kullanilabilir / ham_aralik

    kalibre = []
    for k in ham_zamanlar:
        yeni_bas = max(0.0, round((k["baslangic"] - ilk_bas) * olcek, 3))
        yeni_bit = min(gercek_sure, max(yeni_bas + 0.06, round((k["bitis"] - ilk_bas) * olcek, 3)))
        kalibre.append({
            "kelime": k["kelime"],
            "baslangic": yeni_bas,
            "bitis": yeni_bit,
        })
    return kalibre


def _oransal_zamanlama(metin: str, toplam_sure: float) -> list:
    """Kelime harf uzunluğu ağırlıklı doğal zaman damgası üretir (fallback için)."""
    kelimeler = [k for k in metin.split() if k.strip()]
    if not kelimeler:
        return []
    agirliklar = [max(2, len(k)) for k in kelimeler]
    toplam_agirlik = float(sum(agirliklar))
    sonuc = []
    imlec = 0.0
    for k, ag in zip(kelimeler, agirliklar):
        pay = toplam_sure * (ag / toplam_agirlik)
        sonuc.append({
            "kelime": k,
            "baslangic": round(imlec, 3),
            "bitis": round(imlec + pay, 3),
        })
        imlec += pay
    return sonuc


async def _edge_tts_uret(
    metin: str,
    cikis_mp3: str,
    ses_tipi: str,
    cinsiyet: str,
    sesid: str | None = None,
    hiz: float = 1.0,
) -> list:
    import edge_tts

    ton = ses_tonu_al(ses_tipi, cinsiyet, sesid=sesid, hiz=hiz)
    communicate = edge_tts.Communicate(
        metin,
        ton["voice"],
        rate=ton.get("rate", "+10%"),
        volume=ton.get("volume", "+0%"),
        pitch=ton.get("pitch", "+0Hz"),
    )

    word_timestamps = []
    with open(cikis_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_s = chunk["offset"] / 10_000_000.0
                dur_s = chunk["duration"] / 10_000_000.0
                word_timestamps.append({
                    "kelime": chunk["text"],
                    "baslangic": round(start_s, 3),
                    "bitis": round(start_s + max(0.05, dur_s), 3),
                })
    return word_timestamps


def _gtts_uret(metin: str, cikis_wav: Path, ses_tipi: str, cinsiyet: str, hiz: float = 1.0) -> float:
    """gTTS fallback — kadın ve erkek karakterler için ayrı hız/perde profili uygular."""
    from gtts import gTTS

    tmp_mp3 = str(cikis_wav) + "_gtts.mp3"
    try:
        gTTS(text=metin, lang="tr", slow=False).save(tmp_mp3)
        ton = ses_tonu_al(ses_tipi, cinsiyet, hiz=hiz)
        try:
            pct = int(ton.get("rate", "+10%").replace("%", "").replace("+", ""))
        except Exception:
            pct = 10

        # Erkek karakterde daha tok perde, kadın karakterde daha canlı perde
        if str(cinsiyet).lower().startswith("erk"):
            asetrate = int(44100 * 0.91)
            atempo = max(0.85, min(1.45, (1.0 + pct / 100.0) / 0.91))
        else:
            asetrate = int(44100 * 1.05)
            atempo = max(0.85, min(1.45, (1.0 + pct / 100.0) / 1.05))

        ek_filtre = f"asetrate={asetrate},aresample=44100,atempo={atempo:.3f}"
        return _wav_sessizlik_kirp(tmp_mp3, cikis_wav, ek_filtre=ek_filtre)
    finally:
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)


def _espeak_fallback(metin: str, cikis_wav: Path, cinsiyet: str, hiz: float = 1.0) -> float:
    raw_wav = str(cikis_wav) + "_esp.wav"
    pitch = "68" if str(cinsiyet).lower().startswith("kad") else "42"
    speech_rate = str(round(max(130, min(260, 185 * max(0.85, min(1.25, hiz))))))
    try:
        subprocess.run(
            ["espeak-ng", "-v", "tr", "-p", pitch, "-s", speech_rate, "-w", raw_wav, metin],
            capture_output=True, check=True, timeout=20,
        )
        return _wav_sessizlik_kirp(raw_wav, cikis_wav)
    except Exception:
        with wave.open(str(cikis_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b"\x00\x00" * int(44100 * 1.4))
        return 1.4
    finally:
        if os.path.exists(raw_wav):
            os.remove(raw_wav)


def _calistir_async(coro):
    """Hem senkron hem de çalışan bir asyncio döngüsü içinden güvenle çağrılır."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as havuz:
            return havuz.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


def metin_sese_cevir(
    metin: str,
    dosya_adi: str,
    ses_tipi: str = "normal",
    cinsiyet: str = "erkek",
    *,
    sesid: str | None = None,
    hiz: float = 1.0,
) -> dict:
    """
    Tek bir diyalog satırını seslendirir, nefes boşluklarını kırpar ve kalibre zaman damgalarını döndürür.
    """
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    cikis_wav = TTS_YOLU / f"{dosya_adi}.wav"
    tmp_mp3 = TTS_YOLU / f"{dosya_adi}_raw.mp3"

    gorunen_metin = re.sub(r"\s+", " ", metin).strip()
    temiz_metin = _sanitize_for_tts(gorunen_metin)
    ham_zamanlar = []
    sure = 0.0

    if edge_tts_kurulu_mu():
        try:
            ham_zamanlar = _calistir_async(
                _edge_tts_uret(temiz_metin, str(tmp_mp3), ses_tipi, cinsiyet, sesid, hiz)
            )
            if tmp_mp3.exists() and tmp_mp3.stat().st_size > 800:
                sure = _wav_sessizlik_kirp(str(tmp_mp3), cikis_wav)
            else:
                raise RuntimeError("edge-tts boş ses döndürdü")
        except Exception as e:
            print(f"[TTS] edge-tts uyarı ({e}), gTTS devreye giriyor...")
            try:
                sure = _gtts_uret(temiz_metin, cikis_wav, ses_tipi, cinsiyet, hiz)
            except Exception:
                sure = _espeak_fallback(temiz_metin, cikis_wav, cinsiyet, hiz)
        finally:
            if tmp_mp3.exists():
                tmp_mp3.unlink(missing_ok=True)
    else:
        try:
            sure = _gtts_uret(temiz_metin, cikis_wav, ses_tipi, cinsiyet, hiz)
        except Exception:
            sure = _espeak_fallback(temiz_metin, cikis_wav, cinsiyet, hiz)

    # Ekranda gösterilecek kelimelerle (emoji temizlenmiş kelimeler) zaman damgalarını eşle
    ekran_kelimeleri = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\uFE0F\u200D]+",
        "",
        gorunen_metin,
    ).strip()
    zamanlamalar = _zamanlamalari_kalibre_et(ham_zamanlar, ekran_kelimeleri or temiz_metin, sure)

    return {
        "ses_dosyasi": str(cikis_wav),
        "zamanlamalar": zamanlamalar,
        "sure": sure,
        "metin": ekran_kelimeleri or temiz_metin,
        "ham_metin": gorunen_metin,
        "ses_tipi": ses_tipi,
        "cinsiyet": cinsiyet,
        "sesid": sesid or (KADIN_SES if str(cinsiyet).lower().startswith("kad") else ERKEK_SES),
        "hiz": max(0.85, min(1.25, hiz)),
    }


def _karakter_cinsiyetleri_ata(diyaloglar: list) -> dict:
    """
    Diyalogdaki farklı karakterlere otomatik zıt ses (Erkek Ahmet ↔ Kadın Emel) atar.
    Böylece her 2 kişilik diyalogda sesler %100 birbirinden ayrışır.
    """
    harita = {}
    siradaki_varsayilan = ["erkek", "kadin"]
    sayac = 0

    for d in diyaloglar:
        karakter = str(d.get("karakter", "KARAKTER")).strip().upper()
        acik_cinsiyet = str(d.get("cinsiyet", "")).strip().lower()
        if acik_cinsiyet in ("erkek", "kadin", "kadın"):
            harita[karakter] = "kadin" if acik_cinsiyet.startswith("kad") else "erkek"
            continue
        if karakter in harita:
            continue

        if karakter in KADIN_KARAKTER_IPUCLARI:
            secim = "kadin"
        elif sayac == 0:
            secim = "erkek"
        else:
            # İlk karakter neyse ikinci karakter mutlaka tersi olsun!
            ilk_deger = next(iter(harita.values()))
            secim = "kadin" if ilk_deger == "erkek" else siradaki_varsayilan[sayac % 2]

        harita[karakter] = secim
        sayac += 1

    return harita


def senaryo_seslendir(senaryo_paketi: dict) -> dict:
    """
    Senaryodaki tüm replikleri çift sesli (Ahmet + Emel), nefes boşluksuz ve
    kelime zaman damgalı olarak seslendirir.
    """
    ayarlar = Ayarlar.ortamdan()
    minimum_sure = ayarlar.minimum_yayin_suresi
    hedef_sure = minimum_sure + ayarlar.tts_guvenlik_payi
    senaryo = senaryo_paketi["senaryo"]
    dosya_adi_taslak = senaryo_paketi["dosya_adi"]
    diyaloglar = senaryo.get("diyaloglar", [])
    cinsiyet_haritasi = _karakter_cinsiyetleri_ata(diyaloglar)

    ses_dosyalari = []
    toplam_idx = len(diyaloglar)
    twist_idx = next(
        (index for index, line in enumerate(diyaloglar) if line.get("twist") or line.get("rol") == "twist"),
        int(senaryo.get("twist_indeksi", max(0, toplam_idx - 2))),
    )

    for sira, diyalog in enumerate(diyaloglar):
        metin = diyalog["metin"]
        karakter = str(diyalog.get("karakter", "BOBİ")).strip()
        ses_tipi = diyalog.get("ses", "twist" if sira == twist_idx else "normal")
        cinsiyet = cinsiyet_haritasi.get(karakter.upper(), "erkek")
        dosya_adi = f"{dosya_adi_taslak}_{sira:02d}"

        sonuc = metin_sese_cevir(
            metin,
            dosya_adi,
            ses_tipi=ses_tipi,
            cinsiyet=cinsiyet,
            sesid=str(diyalog.get("sesid") or (KADIN_SES if cinsiyet == "kadin" else ERKEK_SES)),
            hiz=float(diyalog.get("hiz", 1.0)),
        )
        sonuc["karakter"] = karakter
        sonuc["sira"] = sira
        sonuc["taraf"] = "sol" if list(cinsiyet_haritasi.keys()).index(karakter.upper()) % 2 == 0 else "sag"
        twist_mi = bool(diyalog.get("twist", diyalog.get("rol") == "twist" or sira == twist_idx))
        sonuc["twist_mi"] = twist_mi
        sonuc["rol"] = diyalog.get("rol", "twist" if twist_mi else "escalation")
        sonuc["vurgu_kelimeler"] = diyalog.get("vurgukelimeler", diyalog.get("vurgu_kelimeler", []))
        sonuc["hiz"] = float(diyalog.get("hiz", 1.0))
        sonuc["duraklamams"] = int(diyalog.get("duraklamams", 120))
        sonuc["altyazistili"] = diyalog.get("altyazistili", "normal")
        sonuc["kamera"] = diyalog.get("kamera", "cut")
        sonuc["emojioverlay"] = diyalog.get("emojioverlay")
        sonuc["sfx"] = diyalog.get("sfx", "vine_boom" if twist_mi else "pop")
        ses_dosyalari.append(sonuc)

        ses_etiket = "Emel(K)" if cinsiyet == "kadin" else "Ahmet(E)"
        print(
            f"[TTS] #{sira+1} [{karakter} | {ses_etiket}] "
            f"'{sonuc['metin'][:45]}' -> {sonuc['sure']:.2f}sn ({len(sonuc['zamanlamalar'])} kelime)"
        )

    # TTS'nin gerçek süresini ölç. Tahmini metin hesabı değil, gerçek WAV süreleri
    # minimumu belirler; kısa kalırsa twist'ten önce doğal diyalog çiftleri ekle.
    toplam_gercek_sure = sum(
        float(s.get("sure", 0.0))
        + (float(s.get("duraklamams", 0)) / 1000 if index < len(ses_dosyalari) - 1 else 0.0)
        for index, s in enumerate(ses_dosyalari)
    )
    ek_replik_ciftleri = [
        ("Dur, asıl mesele şimdi başlıyor; bu hikâyenin en tuhaf yerini duymadın!", "Söyle artık, meraktan sonunu bekleyemiyorum gerçekten!"),
        ("Peki bu karışıklığı şimdi kim çözecek, herkes bize bakıyor!", "Bir dakika daha sabret, cevap sandığından da komik çıkacak!"),
        ("Bundan daha garip ne olabilir, bütün planımız zaten değişti!", "Finali görünce fikrin değişecek, hazır ol ve dikkatle dinle!"),
        ("Tamam, son bir soru: bu işin sorumlusu kim sence?", "Cevabı birazdan duyacaksın, ama önce küçük bir itirafım var!"),
        ("Herkes sakin olsun, bu olayın arkasında çok basit bir sebep var!", "Basitse anlat, çünkü şu an hiçbir şey anlamadım gerçekten!"),
        ("Şimdi geriye dönüp bakınca bütün işaretler aslında ortadaymış!", "Evet ama finali bilseydim en başta başka kapıdan girerdim!")
    ]
    if toplam_gercek_sure < hedef_sure:
        print(f"[TTS] ⏱️ Gerçek diyalog {toplam_gercek_sure:.2f}sn; saniyelik güvenlik hedefi için doğal replik ekleniyor.")
        twist_idx = min(max(0, int(senaryo.get("twist_indeksi", max(0, len(diyaloglar) - 2)))), len(diyaloglar))
        ilk_karakter = str(diyaloglar[0].get("karakter", "MERT")).upper() if diyaloglar else "MERT"
        ikinci_satir = next((d for d in diyaloglar if str(d.get("karakter", "")).upper() != ilk_karakter), {})
        ikinci_karakter = str(ikinci_satir.get("karakter", "AYŞE")).upper()
        ilk_satir = diyaloglar[0] if diyaloglar else {}
        ilk_cinsiyet = cinsiyet_haritasi.get(ilk_karakter, "erkek")
        ikinci_cinsiyet = cinsiyet_haritasi.get(ikinci_karakter, "kadin")
        for pair_no, (replik_a, replik_b) in enumerate(ek_replik_ciftleri[:ayarlar.tts_uzatma_cift_azami]):
            if toplam_gercek_sure >= hedef_sure:
                break
            yeni_diyaloglar = []
            yeni_sesler = []
            for offset, (karakter, cinsiyet, metin, ses_tipi, character_line) in enumerate((
                (ikinci_karakter, ikinci_cinsiyet, replik_a, "sasirmis", ikinci_satir),
                (ilk_karakter, ilk_cinsiyet, replik_b, "enerjik", ilk_satir),
            )):
                sıra = toplam_idx + pair_no * 2 + offset
                sesid = str(character_line.get("sesid") or (KADIN_SES if cinsiyet == "kadin" else ERKEK_SES))
                sonuc = metin_sese_cevir(
                    metin,
                    f"{dosya_adi_taslak}_min_{sıra:02d}",
                    ses_tipi=ses_tipi,
                    cinsiyet=cinsiyet,
                    sesid=sesid,
                )
                ref = str(character_line.get("karakter_ref") or f"karakter_{karakter.lower()}")
                words = [word.strip(".,!?;:") for word in metin.split()[-3:] if word.strip(".,!?;:")]
                new_line = {
                    "karakter": karakter,
                    "karakter_ref": ref,
                    "cinsiyet": cinsiyet,
                    "sesid": sesid,
                    "metin": metin,
                    "ses": ses_tipi,
                    "hiz": 1.0,
                    "duraklamams": 120,
                    "vurgukelimeler": words or [metin.split()[-1]],
                    "vurgu_kelimeler": words or [metin.split()[-1]],
                    "altyazistili": "normal",
                    "kamera": "cut",
                    "emojioverlay": None,
                    "tahminisuresn": round(len(metin.split()) * 0.36, 2),
                    "rol": "escalation",
                    "twist": False,
                    "sfx": "pop",
                }
                sonuc["karakter"] = karakter
                sonuc["sira"] = twist_idx + offset
                sonuc["taraf"] = "sag" if karakter == ikinci_karakter else "sol"
                sonuc["twist_mi"] = False
                sonuc["vurgu_kelimeler"] = new_line["vurgukelimeler"]
                sonuc["duraklamams"] = 120
                sonuc["rol"] = "escalation"
                sonuc["hiz"] = 1.0
                sonuc["altyazistili"] = "normal"
                sonuc["kamera"] = "cut"
                sonuc["emojioverlay"] = None
                sonuc["sfx"] = "pop"
                yeni_diyaloglar.append(new_line)
                yeni_sesler.append(sonuc)
                toplam_gercek_sure += float(sonuc.get("sure", 0.0)) + 0.12
            diyaloglar[twist_idx:twist_idx] = yeni_diyaloglar
            ses_dosyalari[twist_idx:twist_idx] = yeni_sesler
            twist_idx = next(
                (idx for idx, line in enumerate(diyaloglar) if line.get("twist") or line.get("rol") == "twist"),
                min(twist_idx + len(yeni_diyaloglar), max(0, len(diyaloglar) - 1)),
            )
            senaryo["twist_indeksi"] = twist_idx
            for idx, ses in enumerate(ses_dosyalari):
                line = diyaloglar[idx]
                ses["sira"] = idx
                ses["twist_mi"] = bool(line.get("twist", line.get("rol") == "twist"))
                ses["rol"] = line.get("rol", "escalation")
            print(f"[TTS] ➕ Uzatma {pair_no + 1}: toplam gerçek süre {toplam_gercek_sure:.2f}sn")

        if toplam_gercek_sure < minimum_sure:
            raise RuntimeError(f"Minimum {minimum_sure:.1f} saniye kuralı: TTS {toplam_gercek_sure:.2f}sn oldu; yayın iptal edildi.")
        senaryo["diyaloglar"] = diyaloglar
        senaryo["tts_metinleri"] = [d.get("metin", "") for d in diyaloglar]
        senaryo["toplam_sure"] = round(toplam_gercek_sure, 2)
        print(f"[TTS] ✅ Gerçek süre eşiği geçti: {toplam_gercek_sure:.2f}sn")

    senaryo_paketi["ses_dosyalari"] = ses_dosyalari
    return senaryo_paketi


if __name__ == "__main__":
    ornek = {
        "dosya_adi": "tts_v6_test",
        "senaryo": {
            "twist_indeksi": 2,
            "diyaloglar": [
                {"karakter": "PATRON", "metin": "İşte tam bu yüzden kahve makinesini kovdum!", "ses": "sinirli"},
                {"karakter": "İK", "metin": "Müdür bey, makinenin kıdem tazminatı ne olacak?", "ses": "endiseli"},
                {"karakter": "PATRON", "metin": "Avukat tutmuş, sabah beni mahkemeye verdi!", "ses": "twist"},
            ],
        },
    }
    paket = senaryo_seslendir(ornek)
    print("Toplam süre:", round(sum(x["sure"] for x in paket["ses_dosyalari"]), 2), "sn")

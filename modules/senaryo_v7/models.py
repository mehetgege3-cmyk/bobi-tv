"""Tipli v7 senaryo modelleri ve eski JSON adlarıyla uyumluluk dönüştürücüleri."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from difflib import get_close_matches
from enum import Enum, StrEnum
from typing import Any, TypeVar

_LOG = logging.getLogger("bobi_tv.senaryo_v7.models")


class Duygu(StrEnum):
    """Diyalog TTS duygu etiketlerinin kanonik, ASCII uyumlu kümesi."""

    NORMAL = "normal"
    ENERJIK = "enerjik"
    SINIRLI = "sinirli"
    PANIK = "panik"
    SASIRMIS = "sasirmis"
    KESIN = "kesin"
    CIDDI = "ciddi"
    SOGUK = "soguk"
    BIKKIN = "bikkin"
    BIKKIN_DRAMATIK = "bikkin_dramatik"
    YAVAS_DRAMATIK = "yavas_dramatik"
    UYKULU = "uykulu"
    DUSUNCELI = "dusunceli"
    GURURLU = "gururlu"
    ENDISELI = "endiseli"
    UMUTLU = "umutlu"
    ROBOTIK = "robotik"
    ROBOTIK_KORO = "robotik_koro"
    DERIN = "derin"
    DERIN_DRAMATIK = "derin_dramatik"
    ALARM = "alarm"
    TWIST = "twist"


class AltyaziStili(StrEnum):
    """Desteklenen altyazı vurgu stilleri."""

    NORMAL = "normal"
    BUYUK = "büyük"
    TITRESIMLI = "titreşimli"
    RENKLI = "renkli"


class KameraHareketi(StrEnum):
    """Replik başına izin verilen kamera hareketleri."""

    CUT = "cut"
    ZOOMIN = "zoomin"
    ZOOMOUT = "zoomout"
    SHAKE = "shake"
    WHIPPAN = "whippan"


class DiyalogRolu(StrEnum):
    """Hikâye akışındaki replik işlevleri."""

    HOOK = "hook"
    SETUP = "setup"
    ESCALATION = "escalation"
    TWIST = "twist"
    LOOPKAPANIS = "loopkapanis"


_DUYGU_ALIASES = {
    "suprized": "sasirmis",
    "surprised": "sasirmis",
    "şaşkın": "sasirmis",
    "bikeyn": "bikkin",
    "bikeyn_dramatik": "bikkin_dramatik",
    "yavas_bikkin": "bikkin",
    "soğuk": "soguk",
    "ciddi": "ciddi",
}


def duyguyu_normalize_et(raw: object) -> Duygu:
    """Yazım varyantını kanonik enum'a çevirir; bilinmeyen etikette güvenli fallback kullanır."""
    value = str(raw or Duygu.NORMAL.value).strip().lower().replace(" ", "_")
    canonical = _DUYGU_ALIASES.get(value, value)
    try:
        return Duygu(canonical)
    except ValueError:
        # Yalnızca yüksek benzerlik eşiğini geçen eşleşmeleri kabul et; yoksa NORMAL fallback
        match = get_close_matches(canonical, [item.value for item in Duygu], n=1, cutoff=0.6)
        if match:
            nearest = Duygu(match[0])
            _LOG.warning("Bilinmeyen duygu etiketi %r; en yakın değer %r seçildi.", raw, nearest.value)
            return nearest
        else:
            _LOG.warning("Bilinmeyen duygu etiketi %r; NORMAL fallback'i kullanıldı.", raw)
            return Duygu.NORMAL


_EnumValue = TypeVar("_EnumValue", bound=Enum)


def _enum_value(enum_type: type[_EnumValue], raw: object, default: _EnumValue) -> _EnumValue:
    """Bir metin/enum değerini enum'a çevirir; geçersiz değer için uyarı verir."""
    if isinstance(raw, enum_type):
        return raw
    text = str(raw or default.value).strip().lower()
    for value in enum_type:
        if str(value.value).lower() == text:
            return value
    _LOG.warning("Geçersiz %s değeri %r; varsayılan %r kullanıldı.", enum_type.__name__, raw, default.value)
    return default


@dataclass(slots=True)
class Karakter:
    """Şablonlar ve bölümler arasında sabit kimlik/ses taşıyan karakter."""

    ref: str = field(
        default="karakter_bobi", metadata={"description": "Karakter havuzundaki kalıcı referans anahtarı."}
    )
    ad: str = field(default="BOBİ", metadata={"description": "Karakterin gösterilecek adı."})
    cinsiyet: str = field(
        default="erkek", metadata={"description": "Karakterin sabit ses seçimi için cinsiyeti."}
    )
    sesid: str = field(
        default="tr-TR-AhmetNeural", metadata={"description": "Edge TTS voice ID; Ahmet/Emel sabittir."}
    )
    yasaraligi: str = field(
        default="yetişkin", metadata={"description": "Kurgu karakterinin yaklaşık yaş aralığı."}
    )
    kisiliknotu: str = field(
        default="", metadata={"description": "Yazım ve oyunculuk için kısa kişilik rehberi."}
    )
    varsayilanduygu: Duygu = field(
        default=Duygu.NORMAL, metadata={"description": "Karakterin repliklerdeki varsayılan TTS duygusu."}
    )

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> Karakter:
        """Karakter JSON nesnesini okuyup Ahmet/Emel ses kimliğini sabitler."""
        gender_raw = str(raw.get("cinsiyet") or "erkek").strip().lower()
        gender = "kadin" if gender_raw in {"kadın", "kadin", "female", "f"} else "erkek"
        fixed_voice = "tr-TR-EmelNeural" if gender == "kadin" else "tr-TR-AhmetNeural"
        requested_voice = str(raw.get("sesid") or fixed_voice)
        if requested_voice != fixed_voice:
            _LOG.warning(
                "%s için sesid %r sabit %r ile değiştirildi.", raw.get("ad"), requested_voice, fixed_voice
            )
        return cls(
            ref=str(raw.get("ref") or raw.get("id") or raw.get("ad") or "karakter_bobi"),
            ad=str(raw.get("ad") or "BOBİ"),
            cinsiyet=gender,
            sesid=fixed_voice,
            yasaraligi=str(raw.get("yasaraligi") or "yetişkin"),
            kisiliknotu=str(raw.get("kisiliknotu") or ""),
            varsayilanduygu=duyguyu_normalize_et(raw.get("varsayilanduygu", "normal")),
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON uyumlu karakter verisi verir."""
        return asdict(self)


@dataclass(slots=True)
class Diyalog:
    """Bir konuşmacının tek repliği ve satır başına prodüksiyon metadata'sı."""

    karakter: str = field(default="BOBİ", metadata={"description": "Geriye uyumluluk için gösterim adı."})
    metin: str = field(default="", metadata={"description": "Türkçe seslendirilecek replik."})
    cinsiyet: str = field(
        default="erkek", metadata={"description": "Legacy TTS alanı; karakter kaydından çözülür."}
    )
    ses: Duygu = field(
        default=Duygu.NORMAL, metadata={"description": "Enum ile doğrulanan TTS duygu profili."}
    )
    sfx: str = field(default="pop", metadata={"description": "Replik başında kullanılacak ses efekti."})
    karakter_ref: str = field(
        default="", metadata={"description": "Şablon karakter havuzundaki sabit karakter kimliği."}
    )
    hiz: float = field(default=1.0, metadata={"description": "TTS hız çarpanı; 0.85 ile 1.25 arasında."})
    duraklamams: int = field(
        default=120, metadata={"description": "Satır sonrasında eklenecek boşluk, milisaniye."}
    )
    vurgukelimeler: list[str] = field(
        default_factory=list, metadata={"description": "Otomatik çıkarılmış altyazı vurgu sözcükleri."}
    )
    altyazistili: AltyaziStili = field(
        default=AltyaziStili.NORMAL, metadata={"description": "normal/büyük/titreşimli/renkli altyazı stili."}
    )
    kamera: KameraHareketi = field(
        default=KameraHareketi.CUT, metadata={"description": "İzin verilen kamera hareketlerinden biri."}
    )
    emojioverlay: str | None = field(
        default=None, metadata={"description": "İsteğe bağlı tek emoji overlay."}
    )
    tahminisuresn: float = field(default=0.0, metadata={"description": "Satırın tahmini TTS süresi, saniye."})
    rol: DiyalogRolu = field(
        default=DiyalogRolu.SETUP,
        metadata={"description": "Hook/setup/escalation/twist/loopkapanis hikâye rolü."},
    )
    twist: bool = field(default=False, metadata={"description": "Bu replik hikâyenin ters köşesidir."})
    # Legacy schema name retained for current subtitle pipeline.
    vurgu_kelimeler: list[str] = field(
        default_factory=list, metadata={"description": "Legacy alias of vurgukelimeler."}
    )
    sesid: str = field(default="tr-TR-AhmetNeural", metadata={"description": "Sabit karakter TTS voice ID."})

    @classmethod
    def from_dict(
        cls,
        raw: Mapping[str, object],
        karakterler: Mapping[str, Karakter] | None = None,
        index: int = 0,
        count: int = 1,
    ) -> Diyalog:
        """Legacy veya v7 JSON satırından typed Diyalog üretir; eksik prodüksiyon alanlarını doldurur."""
        characters = karakterler or {}
        ref = str(raw.get("karakter_ref") or raw.get("karakter") or "").strip()
        character = characters.get(ref) or characters.get(ref.upper())
        name = character.ad if character else str(raw.get("karakter") or ref or "BOBİ")
        gender = character.cinsiyet if character else _normalize_gender(raw.get("cinsiyet"))
        voice_id = (
            character.sesid
            if character
            else ("tr-TR-EmelNeural" if gender == "kadin" else "tr-TR-AhmetNeural")
        )
        emotion = duyguyu_normalize_et(
            raw.get("ses", character.varsayilanduygu.value if character else "normal")
        )
        text = str(raw.get("metin") or "").strip()
        old_words = raw.get("vurgukelimeler", raw.get("vurgu_kelimeler", []))
        words = _words(old_words)
        if not words:
            words = _extract_keywords(text)
        role_default = (
            DiyalogRolu.HOOK
            if index == 0
            else (
                DiyalogRolu.TWIST
                if index == count - 2
                else DiyalogRolu.LOOPKAPANIS
                if index == count - 1
                else DiyalogRolu.ESCALATION
            )
        )
        twist_flag = bool(raw.get("twist", str(raw.get("rol", "")).lower() == "twist"))
        role_value: object = raw.get("rol", role_default.value)
        if twist_flag:
            role_value = DiyalogRolu.TWIST.value
        role = _enum_value(DiyalogRolu, role_value, role_default)
        pause = _int_value(raw.get("duraklamams"), 120)
        speed = _float_value(raw.get("hiz"), 1.0)
        if not 0.85 <= speed <= 1.25:
            clamped_speed = min(1.25, max(0.85, speed))
            _LOG.warning("Diyalog hiz=%s sınır dışında; %s aralığına alındı.", speed, clamped_speed)
            speed = clamped_speed
        pause = min(max(pause, 0), 3000)
        emoji = str(raw.get("emojioverlay") or "").strip() or None
        if emoji and not _is_single_emoji(emoji):
            _LOG.warning("emojioverlay tek emoji değil; kaldırıldı: %r", emoji)
            emoji = None
        style = _enum_value(AltyaziStili, raw.get("altyazistili"), AltyaziStili.NORMAL)
        camera = _enum_value(KameraHareketi, raw.get("kamera"), KameraHareketi.CUT)
        estimated = _float_value(raw.get("tahminisuresn"), len(text.split()) * 0.36 / speed)
        if text and estimated <= 0:
            estimated = len(text.split()) * 0.36 / speed
        requested_voice = raw.get("sesid")
        if requested_voice and str(requested_voice) != voice_id:
            _LOG.warning("Satır %r için sesid karakter kartındaki sabit sesle değiştirildi.", ref)
        legacy_words = list(words)
        return cls(
            karakter=name,
            metin=text,
            cinsiyet=gender,
            ses=emotion,
            sfx=str(raw.get("sfx") or "pop"),
            karakter_ref=str(raw.get("karakter_ref") or ref or name),
            hiz=speed,
            duraklamams=pause,
            vurgukelimeler=words,
            altyazistili=style,
            kamera=camera,
            emojioverlay=emoji,
            tahminisuresn=max(0.0, estimated),
            rol=role,
            twist=twist_flag or role is DiyalogRolu.TWIST,
            vurgu_kelimeler=legacy_words,
            sesid=voice_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Diyalog modelini canonical ve legacy TTS alanlarıyla döndürür."""
        payload = asdict(self)
        payload["ses"] = self.ses.value
        payload["rol"] = self.rol.value
        payload["altyazistili"] = self.altyazistili.value
        payload["kamera"] = self.kamera.value
        payload["vurgu_kelimeler"] = list(self.vurgukelimeler)
        payload["vurgukelimeler"] = list(self.vurgukelimeler)
        return payload


@dataclass(slots=True)
class Senaryo:
    """Doğrulanmış, zenginleştirilmiş ve v7 şema sürümü taşıyan hikâye."""

    semaversiyonu: str = field(default="7.0", metadata={"description": "Kalıcı JSON şema sürümü."})
    kategori: str = field(default="absurt_komedi", metadata={"description": "Senaryo içerik kategorisi."})
    ortam_etiketi: str = field(
        default="gündelik hayat", metadata={"description": "Görsel üretim ve sahne ortamı."}
    )
    ruh_hali: str = field(default="komedi", metadata={"description": "Ses ve görsel ton profili."})
    hook_metni: str = field(default="", metadata={"description": "İlk saniyedeki dikkat kancası."})
    hook_ust_bant: str = field(default="", metadata={"description": "Dikey videodaki üst başlık bandı."})
    hook_suresi: float = field(
        default=0.0, metadata={"description": "Hook öncesi boşluk; sıfır ölü hava için 0."}
    )
    diyaloglar: list[Diyalog] = field(
        default_factory=list, metadata={"description": "Sıralı çift karakter replikleri."}
    )
    karakterler: list[Karakter] = field(
        default_factory=list, metadata={"description": "Bölümde kullanılan karakter/ses kayıtları."}
    )
    tts_metinleri: list[str] = field(
        default_factory=list, metadata={"description": "TTS motoruna gidecek temiz konuşma metinleri."}
    )
    punchline_efekt: str = field(
        default="zoom_in", metadata={"description": "Finalde kullanılacak görsel vurgu."}
    )
    etkilesim: str = field(
        default="Bunu bir arkadaşına gönder!", metadata={"description": "İçeriğe özgü paylaşım çağrısı."}
    )
    sabit_yorum: str = field(
        default="Siz olsanız ne yapardınız? Yorumlara yazın 👇",
        metadata={"description": "Yayın sonrası ilk/sabit yorum."},
    )
    toplam_sure: float = field(
        default=0.0, metadata={"description": "Tahmini toplam konuşma süresi (saniye)."}
    )
    baslik: str = field(default="", metadata={"description": "Shorts başlığı."})
    acilis: str = field(
        default="", metadata={"description": "Tekrar kontrolü ve arşiv için kısa açılış özeti."}
    )
    hash: str = field(
        default="", metadata={"description": "Senaryo metninden hesaplanan MD5 tekrar anahtarı."}
    )
    etiketler: list[str] = field(default_factory=list, metadata={"description": "Hashtag etiketi listesi."})
    hedefkitle: str = field(
        default="Genel, 13+ Türkçe Shorts izleyicisi", metadata={"description": "Hedef izleyici grubu."}
    )
    mevsimsellik: list[str] = field(
        default_factory=list, metadata={"description": "Pazartesi, bayram, yılbaşı gibi yayın bağlamları."}
    )
    tekrarkullanimgunsayisi: int = field(
        default=30, metadata={"description": "Aynı şablonun yeniden kullanılabileceği minimum gün aralığı."}
    )
    performanspuani: float = field(
        default=0.0, metadata={"description": "Analytics ile güncellenecek performans puanı."}
    )
    yasakkelimekontrolugecti: bool = field(
        default=False, metadata={"description": "Yasaklı kelime kontrolünün başarılı sonucu."}
    )

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> Senaryo:
        """Migrate edilmiş mapping'den karakter referanslarını çözüp tipli Senaryo kurar."""
        raw_dialogues = raw.get("diyaloglar", [])
        characters = _character_map(raw.get("karakterler")) or _infer_characters(raw_dialogues)
        twist_index = _int_value(
            raw.get("twist_indeksi"), max(0, len(raw_dialogues) - 2) if isinstance(raw_dialogues, list) else 0
        )
        dialogues = _dialogues_from_raw(raw_dialogues, characters, twist_index)
        raw_texts = raw.get("tts_metinleri", [])
        texts = [str(item) for item in raw_texts] if isinstance(raw_texts, list) else []
        hook_duration = _float_value(raw.get("hook_suresi"), 0.0)
        total_duration = _float_value(raw.get("toplam_sure"), 0.0)
        return cls(
            semaversiyonu=str(raw.get("semaversiyonu") or "7.0"),
            kategori=str(raw.get("kategori") or "absurt_komedi"),
            ortam_etiketi=str(raw.get("ortam_etiketi") or "gündelik hayat"),
            ruh_hali=str(raw.get("ruh_hali") or "komedi"),
            hook_metni=str(raw.get("hook_metni") or raw.get("hook_ust_bant") or ""),
            hook_ust_bant=str(raw.get("hook_ust_bant") or raw.get("hook_metni") or ""),
            hook_suresi=hook_duration,
            diyaloglar=dialogues,
            karakterler=_unique_characters(characters),
            tts_metinleri=texts,
            punchline_efekt=str(raw.get("punchline_efekt") or "zoom_in"),
            etkilesim=str(raw.get("etkilesim") or "Bunu bir arkadaşına gönder!"),
            sabit_yorum=str(raw.get("sabit_yorum") or raw.get("aciklama") or "Siz olsanız ne yapardınız? 👇"),
            toplam_sure=total_duration,
            baslik=str(raw.get("baslik") or ""),
            acilis=str(raw.get("acilis") or ""),
            hash=str(raw.get("hash") or ""),
            etiketler=_words(raw.get("etiketler", [])),
            hedefkitle=str(raw.get("hedefkitle") or "Genel, 13+ Türkçe Shorts izleyicisi"),
            mevsimsellik=_words(raw.get("mevsimsellik", [])),
            tekrarkullanimgunsayisi=max(0, _int_value(raw.get("tekrarkullanimgunsayisi"), 30)),
            performanspuani=_float_value(raw.get("performanspuani"), 0.0),
            yasakkelimekontrolugecti=bool(raw.get("yasakkelimekontrolugecti", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Senaryoyu legacy render/TTS modülleriyle uyumlu dict'e çevirir."""
        payload = asdict(self)
        payload["diyaloglar"] = [item.to_dict() for item in self.diyaloglar]
        payload["karakterler"] = [item.to_dict() for item in self.karakterler]
        # Compatibility field only: canonical model stores twist on the dialogue role.
        payload["twist_indeksi"] = next(
            (
                index
                for index, line in enumerate(self.diyaloglar)
                if line.twist or line.rol is DiyalogRolu.TWIST
            ),
            max(0, len(self.diyaloglar) - 2),
        )
        return payload


@dataclass(slots=True)
class SenaryoPaketi:
    """Ana pipeline'ın beklediği üretim paketi."""

    video_no: int = field(default=1, metadata={"description": "Üretim serisindeki video sıra numarası."})
    dosya_adi: str = field(default="", metadata={"description": "Dosya sistemi için güvenli paket adı."})
    baslik: str = field(default="", metadata={"description": "Yayın başlığı."})
    aciklama: str = field(default="", metadata={"description": "Shorts açıklaması veya sabit yorum."})
    senaryo: Senaryo = field(default_factory=Senaryo, metadata={"description": "Tipli senaryo alanı."})
    kaynak: str = field(
        default="sablon", metadata={"description": "arena_kuyruk, arena_canli veya yerlesik_v7."}
    )
    olusturuldu: str = field(default="", metadata={"description": "ISO 8601 UTC oluşturulma zamanı."})
    hash: str = field(default="", metadata={"description": "Senaryo tekrar denetimi hash'i."})
    semaversiyonu: str = field(default="7.0", metadata={"description": "Paket JSON şema sürümü."})

    def to_dict(self) -> dict[str, Any]:
        """Paketi legacy ana pipeline'ın kullanacağı dict biçimine çevirir."""
        payload = asdict(self)
        payload["senaryo"] = self.senaryo.to_dict()
        return payload

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> SenaryoPaketi:
        """Eski veya v7 paket JSON'unu tipli SenaryoPaketi olarak yükler."""
        nested = raw.get("senaryo", {})
        scenario_data = nested if isinstance(nested, Mapping) else raw
        video_no = _int_value(raw.get("video_no"), 1)
        return cls(
            video_no=video_no,
            dosya_adi=str(raw.get("dosya_adi") or ""),
            baslik=str(raw.get("baslik") or scenario_data.get("baslik") or ""),
            aciklama=str(raw.get("aciklama") or scenario_data.get("sabit_yorum") or ""),
            senaryo=Senaryo.from_dict(scenario_data),
            kaynak=str(raw.get("kaynak") or "migrate_v6"),
            olusturuldu=str(raw.get("olusturuldu") or ""),
            hash=str(raw.get("hash") or scenario_data.get("hash") or ""),
            semaversiyonu=str(raw.get("semaversiyonu") or "7.0"),
        )


@dataclass(slots=True)
class Sablon:
    """Tekrarlanabilir yerleşik içerik üretim şablonu ve yayınlama metadata'sı."""

    kategori: str = field(default="absurt_komedi", metadata={"description": "Şablon kategorisi."})
    ortam_etiketi: str = field(default="gündelik hayat", metadata={"description": "Sahne ortamı."})
    ruh_hali: str = field(default="komedi", metadata={"description": "Ses/görüntü tonu."})
    hook_ust_bant: str = field(default="", metadata={"description": "Kapak ve ilk saniye hook metni."})
    baslik: str = field(default="", metadata={"description": "Örnek yayın başlığı."})
    diyaloglar: list[Diyalog] = field(default_factory=list, metadata={"description": "Şablon diyalogları."})
    karakterler: list[Karakter] = field(
        default_factory=list, metadata={"description": "Şablon karakter havuzu."}
    )
    sabit_yorum: str = field(default="", metadata={"description": "Şablon CTA/sabit yorumu."})
    etkilesim: str = field(default="", metadata={"description": "Şablon etkileşim metni."})
    etiketler: list[str] = field(default_factory=list, metadata={"description": "Hashtag etiketi listesi."})
    hedefkitle: str = field(
        default="Genel, 13+ Türkçe Shorts izleyicisi", metadata={"description": "Hedef izleyici grubu."}
    )
    mevsimsellik: list[str] = field(
        default_factory=list, metadata={"description": "Pazartesi, bayram, yılbaşı gibi bağlam etiketleri."}
    )
    tekrarkullanimgunsayisi: int = field(
        default=30, metadata={"description": "Şablon tekrar kullanımı için bekleme gün sayısı."}
    )
    performanspuani: float = field(
        default=0.0, metadata={"description": "Analytics ile güncellenecek performans puanı."}
    )
    yasakkelimekontrolugecti: bool = field(
        default=False, metadata={"description": "Yasaklı kelime kontrolü başarılı mı."}
    )

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> Sablon:
        """JSON şablonunu karakter havuzuna ve alan tiplerine bağlar."""
        dialog_data = raw.get("diyaloglar", [])
        character_map = _character_map(raw.get("karakterler")) or _infer_characters(dialog_data)
        twist_index = _int_value(
            raw.get("twist_indeksi"), max(0, len(dialog_data) - 2) if isinstance(dialog_data, list) else 0
        )
        dialogues = _dialogues_from_raw(dialog_data, character_map, twist_index)
        return cls(
            kategori=str(raw.get("kategori") or ""),
            ortam_etiketi=str(raw.get("ortam_etiketi") or ""),
            ruh_hali=str(raw.get("ruh_hali") or "komedi"),
            hook_ust_bant=str(raw.get("hook_ust_bant") or ""),
            baslik=str(raw.get("baslik") or ""),
            diyaloglar=dialogues,
            karakterler=_unique_characters(character_map),
            sabit_yorum=str(raw.get("sabit_yorum") or ""),
            etkilesim=str(raw.get("etkilesim") or ""),
            etiketler=_words(raw.get("etiketler", [])),
            hedefkitle=str(raw.get("hedefkitle") or "Genel, 13+ Türkçe Shorts izleyicisi"),
            mevsimsellik=_words(raw.get("mevsimsellik", [])),
            tekrarkullanimgunsayisi=max(0, _int_value(raw.get("tekrarkullanimgunsayisi"), 30)),
            performanspuani=_float_value(raw.get("performanspuani"), 0.0),
            yasakkelimekontrolugecti=bool(raw.get("yasakkelimekontrolugecti", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Şablonu canonical referanslar ve eski renderer için gerekli display alanlarıyla verir."""
        payload = asdict(self)
        payload["diyaloglar"] = [item.to_dict() for item in self.diyaloglar]
        payload["karakterler"] = [item.to_dict() for item in self.karakterler]
        # Compatibility only; line-level role/twist is canonical.
        payload["twist_indeksi"] = _derived_twist_index(self.diyaloglar)
        return payload


def _derived_twist_index(dialogues: list[Diyalog]) -> int:
    """Return the compatibility index from canonical line roles."""
    return next(
        (index for index, line in enumerate(dialogues) if line.twist or line.rol is DiyalogRolu.TWIST),
        max(0, len(dialogues) - 2),
    )


def _dialogues_from_raw(raw: object, characters: Mapping[str, Karakter], twist_index: int) -> list[Diyalog]:
    """Apply legacy twist index once, then return typed rows whose roles are canonical."""
    if not isinstance(raw, list):
        return []
    result: list[Diyalog] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            continue
        prepared = dict(item)
        if "rol" not in prepared and "twist" not in prepared and index == twist_index:
            prepared["rol"] = DiyalogRolu.TWIST.value
            prepared["twist"] = True
        result.append(Diyalog.from_dict(prepared, characters, index, len(raw)))
    return result


def _character_map(raw: object) -> dict[str, Karakter]:
    """Character list/dict girdisini anahtar ve görünen ad üzerinden indeksler."""
    result: dict[str, Karakter] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping):
                character = Karakter.from_dict(item)
                ref = str(item.get("ref") or item.get("id") or character.ref)
                result[ref] = character
                result[ref.upper()] = character
                result[character.ad] = character
                result[character.ad.upper()] = character
    elif isinstance(raw, Mapping):
        for ref, item in raw.items():
            if isinstance(ref, str) and isinstance(item, Mapping):
                enriched = dict(item)
                enriched.setdefault("ad", ref)
                character = Karakter.from_dict(enriched)
                result[ref] = character
                result[ref.upper()] = character
                result[character.ad] = character
                result[character.ad.upper()] = character
    return result


def _unique_characters(characters: Mapping[str, Karakter]) -> list[Karakter]:
    """Alias anahtarlarından tekil karakter kayıtlarını sıralı çıkarır."""
    unique: dict[str, Karakter] = {}
    for character in characters.values():
        unique.setdefault(character.ref, character)
    return list(unique.values())


def _infer_characters(raw_dialogues: object) -> dict[str, Karakter]:
    """Legacy satırlardaki ad/cinsiyetten sabit Ahmet/Emel karakter kartları kurar."""
    inferred: dict[str, Karakter] = {}
    if not isinstance(raw_dialogues, list):
        return inferred
    for raw in raw_dialogues:
        if not isinstance(raw, Mapping):
            continue
        name = str(raw.get("karakter") or raw.get("karakter_ref") or "BOBİ").strip()
        ref = str(
            raw.get("karakter_ref") or f"karakter_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}"
        )
        if ref not in inferred:
            inferred[ref] = Karakter.from_dict(
                {
                    "ref": ref,
                    "ad": name,
                    "cinsiyet": raw.get("cinsiyet", "erkek"),
                    "sesid": raw.get("sesid"),
                    "kisiliknotu": "Legacy senaryodan türetilmiş karakter; kimlik boyunca sabit ses.",
                    "varsayilanduygu": raw.get("ses", "normal"),
                }
            )
    return inferred


def _normalize_gender(raw: object) -> str:
    """Legacy cinsiyet değerini `erkek`/`kadin` biçimine indirger."""
    return "kadin" if str(raw or "").strip().lower() in {"kadın", "kadin", "female", "f"} else "erkek"


def _is_single_emoji(value: str) -> bool:
    """Accept one Unicode emoji grapheme (including flags, keycaps and ZWJ sequences)."""
    if re.fullmatch(r"[0-9#*]\ufe0f?\u20e3", value):
        return True
    codepoints = [ord(character) for character in value]
    regional = [point for point in codepoints if 0x1F1E6 <= point <= 0x1F1FF]
    if len(codepoints) == 2 and len(regional) == 2:
        return True
    allowed = all(
        0x1F300 <= point <= 0x1FAFF
        or 0x2600 <= point <= 0x27BF
        or point in {0xFE0E, 0xFE0F, 0x200D, 0x20E3}
        or 0x1F3FB <= point <= 0x1F3FF
        or 0xE0020 <= point <= 0xE007F
        for point in codepoints
    )
    modifiers = {0xFE0E, 0xFE0F, 0x200D, 0x20E3}
    bases = [point for point in codepoints if point not in modifiers and not 0x1F3FB <= point <= 0x1F3FF]
    return allowed and bool(bases) and (len(bases) == 1 or 0x200D in codepoints)


def _words(raw: object) -> list[str]:
    """Metin listesini normalize eder."""
    return (
        [str(item).strip() for item in raw if isinstance(item, str) and item.strip()]
        if isinstance(raw, list)
        else []
    )


def _extract_keywords(text: str, limit: int = 3) -> list[str]:
    """Cümledeki anlamlı, görece uzun sözcüklerden vurgu listesi üretir."""
    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9'-]+", text)
    stop_words = {
        "bunun",
        "şunun",
        "olarak",
        "şimdi",
        "benim",
        "senin",
        "bana",
        "sana",
        "ama",
        "fakat",
        "çünkü",
        "yani",
        "bile",
        "daha",
        "sonra",
        "gibi",
        "için",
        "kadar",
        "mi",
        "mı",
        "mu",
        "mü",
    }
    meaningful = [token for token in tokens if len(token) >= 4 and token.casefold() not in stop_words]
    chosen = meaningful[-limit:]
    return chosen or tokens[-limit:] or ["..."]


def _int_value(value: object, default: int) -> int:
    """JSON scalar'ını integer'a dönüştürür; bilinmeyen tipte varsayılanı kullanır."""
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _float_value(value: object, default: float) -> float:
    """JSON scalar'ını float'a dönüştürür; bilinmeyen tipte varsayılanı kullanır."""
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return default
    return default


# Loop validator import (public API)
from .loop_validator import (
    LoopDogrulamaSonuc,
    loop_dogrula,
    loop_kalite_skoru,
    loop_icin_yedek_sablon,
)

__all__ = [
    "Duygu",
    "AltyaziStili",
    "Sahne",
    "Senaryo",
    "duyguyu_normalize_et",
    "loop_dogrula",
    "loop_kalite_skoru",
    "loop_icin_yedek_sablon",
    "LoopDogrulamaSonuc",
]


@dataclass
class Sahne:
    """Geriye donuk uyumluluk icin v6 sahne temsilcisi (v7'de Senaryo/Diyalog kullanilir)."""
    konu: str = ""
    baslik: str = ""
    replik: str = ""
    duygu_etiketi: str = "normal"
    ses_turu: str = "erkek"
    tts_url: str = ""

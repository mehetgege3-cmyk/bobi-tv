"""Arena erişilemediğinde kullanılan DOĞRULANMIŞ bilgi bankası.

NEDEN VAR: tam otonomi kuralı. Arena çökerse/yavaşlarsa üretim DURMAMALI.
Ama "uydurma bilgi yok" kuralı da duruyor — bu yüzden banka, kaynağı
adlandırılabilir, iyi bilinen bilgilerden oluşur ve **uzun vadeli çözüm
değil, sigortadır**: her biri bankada en fazla 1 kez kullanılır, sonra
`kullanildi` işaretlenir; banka biterse üretim o tur durur (uydurmaktansa
durmak doğru).

Her kayıt: soru · cevap (200-300 kelime) · sonuc · kaynak · kategori.
"""

from __future__ import annotations

from modules.ilginc_bilgi.kurallar import BASLIK_CEVAP, BASLIK_SONUC, BASLIK_SORU

YEDEK_BILGILER: list[dict] = [
    {
        "anahtar": "ahtapot_uc_kalp",
        "kapak_baslik": "ÜÇ KALBİ VAR, BİRİ DURUYOR",
        "kategori": "hayvanlar",
        "baslik": "Ahtapotların Üç Kalbi Var — Biri Yüzerken Duruyor! 🐙",
        "soru": "Ahtapotların kaç kalbi var ve neden biri yüzerken duruyor?",
        "cevap": (
            "Çoğumuz hayvanların tek kalbi olduğunu düşünürüz, oysa ahtapotlarda işler bambaşka. "
            "Ahtapotların tam üç kalbi vardır ve bu kalplerin her biri farklı bir iş yapar. İki kalp "
            "solungaçlara kan pompalar, üçüncüsü ise vücudun geri kalanına temiz kanı taşır. İşin "
            "ilginç yanı, bu kalplerden biri yüzerken durur. Yani ahtapot yüzdüğü sürece üçüncü "
            "kalbi çalışmaz ve hayvan bu yüzden deniz tabanında sürünmeyi tercih eder. Sürünmek yavaş "
            "ama daha az yorucu bir seçenektir.\n\n"
            "Bilim insanları bu davranışı uzun süre anlamlandıramadı, ta ki kalp ritimleri ölçülene "
            "kadar. Bir düşün: sabah kahveni içerken, denizin altında senden tamamen farklı bir "
            "dolaşım sistemiyle yaşayan bir canlı olduğunu hayal et. Ahtapotun kanı da sıra dışıdır: "
            "oksijen taşıyan pigment demir değil bakır kullanır, bu yüzden kanının rengi farklıdır. Bakır "
            "temelli kan oksijeni soğuk sularda daha verimli taşır; bu da ahtapotun neden derin ve "
            "soğuk denizlerde rahat yaşadığını açıklar.\n\n"
            "Ahtapotlar ayrıca kollarını bağımsız hareket ettirebilir; kollarında sinir hücresi "
            "kümeleri vardır. Yani kolları neredeyse kendi başına karar verebilir. Bir ahtapotun "
            "kolu koptuğunda bir süre hareket etmeye devam eder; çünkü komutların bir kısmı kolda "
            "üretilir. Dokunaçlarındaki vantuzlar tat alır, bu yüzden hayvan adeta dokunarak tadar. "
            "Kendi türünü tanır, hatta bazı bireylerin yüzlerini ayırt edebildiği gözlemlenmiştir. "
            "Laboratuvarda kavanoz kapağını açmayı öğrenen, sonra bu bilgiyi başka bir kavanoza "
            "uyarlayan bireyler kaydedilmiştir. Kısacası ahtapot, omurgasızlar arasında beklenmedik "
            "bir problem çözme yeteneği gösterir. Bu yüzden bilim insanları ahtapotu dünyanın en sıra "
            "dışı zekâlarından biri sayar; sinir sisteminin üçte ikisi kollarında dağılmış durumdadır."
        ),
        "sonuc": (
            "Üç kalbi olan bir canlı, yüzerken kalplerinden birini kapatıyor. Doğa, verimliliği "
            "bizim hayal ettiğimizden çok daha tuhaf yollarla çözüyor. 🐙"
        ),
        "kaynak": "National Geographic — Octopus (hayvan profili) ve Britannica 'octopus' maddesi",
        "sayilar": ["3"],
    },
    {
        "anahtar": "kopekbaligi_agac",
        "kapak_baslik": "AĞAÇTAN 60 MİLYON YIL ESKİ",
        "kategori": "doga_evren",
        "baslik": "Köpekbalıkları Ağaçlardan Daha Yaşlı! 🦈",
        "soru": "Köpekbalıkları mı daha yaşlı, yoksa ağaçlar mı?",
        "cevap": (
            "Ağaçların dünyanın en eski canlıları olduğunu düşünmek kolaydır; ormanda yürürken "
            "yüzyıllık gövdeler bize zamanın kendisini hatırlatır. Ama gerçek daha tuhaf: köpekbalıkları "
            "ağaçlardan çok daha önce ortaya çıktı.\n\n"
            "Köpekbalıklarının ataları yaklaşık 450 milyon yıl önce okyanuslarda yaşıyordu. Bugün "
            "bildiğimiz anlamda ağaçlar ise yaklaşık 385 milyon yıl önce ortaya çıktı. Yani aradaki "
            "fark 60 milyon yıldan fazla. Bir düşün: evinin bahçesindeki o ağacın ataları, köpekbalığı "
            "atalarının yanında neredeyse yeni doğmuş sayılır. Bu süre içinde köpekbalıkları beş büyük "
            "yok oluşu gördü; dinozorlar gelip geçti, memeliler ortaya çıktı, okyanusların haritası "
            "birkaç kez değişti. Köpekbalıkları hâlâ orada.\n\n"
            "Bunun nedeni kısmen sade tasarımları: kıkırdaktan yapılmış iskeletleri kemikten çok daha "
            "hafiftir ve esnektir, bu da onları çevik kılar. Ayrıca bazı türler kendi elektriksel "
            "sinyallerini algılayarak avlarını karanlıkta bile bulur. Deniz ekosistemlerinde avcı "
            "zincirinin tepesinde durdukları için, sağlıklı bir okyanusun göstergesi olarak kabul "
            "edilirler. Yani eski olmaları sadece bir tuhaflık değil, aynı zamanda işe yarayan bir "
            "tasarımın kanıtı.\n\n"
            "Bir de şu var: köpekbalıklarının çoğu sürekli yüzmek zorunda değildir; bazı türler "
            "deniz tabanında hareketsiz durup suyu solungaçlarından pompalayarak dinlenir. Dişleri "
            "ise ömür boyu yenilenir; bir köpekbalığı hayatı boyunca binlerce diş çıkarabilir. "
            "Yani evrimin ona verdiği hediye tek bir büyük yenilik değil, sürekli yenilenen küçük "
            "parçalar. Bugün okyanuslarda yaşayan türlerin bir kısmı ciddi tehdit altında; çünkü "
            "yavaş üredikleri için popülasyonları kolay toparlanmıyor. Bu da onları hem eski hem "
            "kırılgan yapıyor."
        ),
        "sonuc": (
            "Bahçendeki ağaçtan 60 milyon yıl daha eski bir canlı okyanuslarda dolaşıyor. Yaşlılık "
            "her zaman yavaşlık değil; bazen sadece iyi tasarlanmış olmak demek. 🦈"
        ),
        "kaynak": "Britannica — 'shark' maddesi ve Smithsonian Ocean (köpekbalığı evrimi)",
        "sayilar": ["450", "385", "60"],
    },
    {
        "anahtar": "kleopatra_piramit",
        "kapak_baslik": "PİRAMİTLER ONUN İÇİN ESKİYDİ",
        "kategori": "tarih_medeniyet",
        "baslik": "Kleopatra, Piramitlerin Yapılışından Çok Ay'a Daha Yakındı! 🏛️",
        "soru": "Kleopatra, Büyük Giza Piramidi'ne mi daha yakın, yoksa Apollo 11'in Ay'a inişine mi?",
        "cevap": (
            "Bu soruyu ilk duyduğunda muhtemelen hemen 'piramitlere' diyeceksin; piramitlerle "
            "Kleopatra aynı ders kitabı sayfasında durur. Ama tarih, hissettiğimizden farklı çalışıyor.\n\n"
            "Büyük Giza Piramidi yaklaşık 2.560 yılda, MÖ 2.560 civarında tamamlandı. Kleopatra ise "
            "MÖ 69'da doğdu ve MÖ 30'da öldü. Arada yaklaşık 2.500 yıl var. Apollo 11'in Ay'a inişi ise "
            "1969 yılında gerçekleşti; Kleopatra'nın ölümünden bu yana geçen süre yaklaşık 2.000 yıl. "
            "Yani Kleopatra, piramit inşa edileli 2.500 yıl geçtikten sonra yaşadı; biz ise ondan 2.000 "
            "yıl sonra Ay'a gittik.\n\n"
            "Bir düşün: elindeki telefonla Roma İmparatorluğu'nun yıkılışından bu yana geçen süreyi "
            "sayfaya sığdırabiliyorsun, ama piramitlerle Kleopatra arasındaki boşluk bundan daha geniş. "
            "Bu yüzden Kleopatra piramitleri harabe olarak gördü; onlar için 'antik' değil, çoktan antik "
            "olmuş yapılardı. Tarihi tek bir düz çizgi gibi düşünmek, bizi bu tür sürprizlere hazırlıksız "
            "bırakıyor.\n\n"
            "Bu yüzden tarihçiler olayları üst üste yığılmış katmanlar gibi düşünmeyi önerir: aynı "
            "manzarada birbirinden binlerce yıl uzak katmanlar yan yana durur. Şaşırtıcı olan, bu "
            "katmanların çoğu zaman aynı şehirde, aynı sokakta yan yana olması.\n\n"
            "İstanbul'da bir sokakta yürürken bir Roma sütununun yanından geçip Osmanlı çeşmesine "
            "rastlayabilirsin; ikisinin arasında bin yıldan fazla zaman var, ama aralarında sadece "
            "birkaç adım. Kahveni alıp o sokakta yürüdüğünde, aynı anda birkaç medeniyetin izini "
            "görüyorsun. Tarih derslerinde her şey birbirinden kopuk görünür: Mısır, Roma, Orta Çağ, "
            "modern zamanlar. Oysa bunlar aynı coğrafyada, bazen aynı taşların üzerinde birikti. "
            "Kleopatra da kendi döneminde 'eski' bir dünyanın ortasında yaşıyordu; tıpkı bizim "
            "bugün 1900'lerin başını eski saymamız gibi."
        ),
        "sonuc": (
            "Kleopatra için piramitler bizim için ne ise, Ay'a iniş de onun için oydu: uzak bir geçmiş. "
            "Zaman algımız, takvimden çok daha kırılgan. ⏳"
        ),
        "kaynak": "Britannica — Great Pyramid of Giza ve Cleopatra maddeleri; NASA Apollo 11 arşivi",
        "sayilar": ["2.560", "69", "30", "1969", "2.500", "2.000"],
    },
]


def kullanilmamis_bilgiler(kullanilan_anahtarlar: list[str] | None = None) -> list[dict]:
    """Daha önce kullanılmamış yedek bilgiler (kategoriye göre filtrelenebilir)."""
    kullanilan = {str(k) for k in (kullanilan_anahtarlar or [])}
    return [b for b in YEDEK_BILGILER if b["anahtar"] not in kullanilan]


def bilgi_sec(kategori: str, kullanilan_anahtarlar: list[str] | None = None) -> dict | None:
    """Kategoriye uygun, kullanılmamış bir yedek bilgi döndürür (yoksa None)."""
    havuz = kullanilmamis_bilgiler(kullanilan_anahtarlar)
    for b in havuz:
        if b["kategori"] == kategori:
            return b
    return havuz[0] if havuz else None


def tam_metin(bilgi: dict) -> str:
    """Zorunlu formata (🧠 / 🔍 / 💡) çevirir."""
    return (
        f"{BASLIK_SORU}\n{bilgi['soru']}\n\n"
        f"{BASLIK_CEVAP}\n{bilgi['cevap']}\n\n"
        f"{BASLIK_SONUC}\n{bilgi['sonuc']}"
    )

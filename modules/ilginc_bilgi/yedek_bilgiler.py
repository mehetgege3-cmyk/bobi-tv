"""Arena erişilemediğinde kullanılan DOĞRULANMIŞ bilgi bankası.

NEDEN VAR: tam otonomi kuralı. Arena çökerse/yavaşlarsa üretim DURMAMALI.
Ama "uydurma bilgi yok" kuralı da duruyor — bu yüzden banka, kaynağı
adlandırılabilir, iyi bilinen bilgilerden oluşur ve **uzun vadeli çözüm
değil, sigortadır**: her biri en fazla 1 kez kullanılır; banka biterse üretim
o tur durur (uydurmaktansa durmak doğru).

8 kategorinin TAMAMI kapsanır (2026-11-11 genişletmesi): Arena uzun süre
erişilemezse bile kanal 8 farklı konuda yayın yapabilir.

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
    },    {
        "anahtar": "gps_izafiyet",
        "kategori": "bilim_teknoloji",
        "kapak_baslik": "UYDU SAATLERI DAHA HIZLI",
        "baslik": "GPS Uydularının Saati Her Gün Kayıyor — Düzeltmesek Yolu Şaşardık! 🛰️",
        "soru": "Navigasyon uygulaman doğru yolu nasıl buluyor, uyduların saati kaymasa ne olurdu?",
        "cevap": (
            "Telefonundaki haritayı açıp 'buradan sağa dön' dediğinde, arkanda 20 bin kilometre "
            "yükseklikte dönen uydularla konuşuyorsun. Ama işin tuhaf yanı şu: o uyduların saatleri, "
            "senin saatinden farklı hızda işliyor.\n\n"
            "Bunun nedeni Einstein'ın görelilik kuramı. Uydular çok hızlı hareket ettiği için saatleri "
            "biraz yavaşlıyor; ama yer çekimi daha zayıf olduğu için saatleri biraz da hızlanıyor. İki "
            "etki birleşince uydu saatleri günde yaklaşık 38 mikrosaniye ileri gidiyor. Kulağa hiçbir "
            "şey gibi gelmiyor, değil mi? Oysa ışık bu sürede yaklaşık 11 kilometre yol alıyor.\n\n"
            "Bir düşün: sabah işe giderken navigasyonun 10 kilometre kaymış olsa, seni bambaşka bir "
            "şehre götürürdü. Bu yüzden GPS uydularının saatleri kasıtlı olarak yavaşlatılıyor ve "
            "sürekli düzeltiliyor. Yani cebindeki harita uygulaması, farkında olmadan her gün görelilik "
            "fiziğini kullanıyor.\n\n"
            "Bu, teorik fiziğin günlük hayata en somut dokunuşlarından biri. Einstein 1905'te denklemi "
            "yazdığında ne uydular ne de cep telefonları vardı; yine de hesap bugün senin yol tarifini "
            "doğru yapıyor."
            "Bir de şu var: GPS uyduları yalnız saat hatasıyla uğraşmıyor. Sinyal, atmosferden "
            "geçerken de bükülüyor; bu yüzden yer istasyonları sürekli ölçüm yapıp düzeltme gönderiyor. "
            "Yani telefonundaki mavi nokta, uzaydan gelen bir sinyalin dört ayrı katmanda "
            "düzeltilmesiyle ortaya çıkıyor. Konumun sokak hassasiyetinde görünmesi, bu zincirin ne "
            "kadar sıkı kurulduğunu gösteriyor."
            "Bir başka ayrıntı: uyduların yörüngesi ve saat düzeltmeleri olmasa, iki farklı "
            "uydudan gelen sinyalin gecikme farkını ölçmek de anlamsız olurdu. Konum bulmak, "
            "aslında üç ayrı uydunun konumunu karşılaştırmak demek."
        ),
        "sonuc": (
            "Cebindeki navigasyon, Einstein'ın 100 yıl önceki denklemi olmadan çalışmazdı. Soyut "
            "görünen fizik, her gün sessizce seni eve götürüyor. 🛰️"
        ),
        "kaynak": "NASA — GPS ve Görelilik (NASA JPL açıklamaları)",
        "sayilar": ["20", "38", "11", "1905"],
    },
    {
        "anahtar": "uykuda_beyin_temizligi",
        "kategori": "insan_vucudu",
        "kapak_baslik": "BEYIN GECELERI COP ATIYOR",
        "baslik": "Beyin Asıl Temizliğini Uyurken Yapıyor! 🧠",
        "soru": "Beynimiz neden uyumadan çalışamıyor, uyku sırasında içeride ne oluyor?",
        "cevap": (
            "Uykuyu genelde 'dinlenme' diye düşünürüz; sanki beyin kapanıp hiçbir şey yapmıyormuş gibi. "
            "Oysa uyku sırasında beynin en yoğun işlerinden biri başlıyor: temizlik.\n\n"
            "Beyin hücrelerinin arasında, gün içinde biriken atık proteinler var. Uyanıkken bu kanallar "
            "daralıyor; uykuya geçtiğinde hücreler arası boşluk genişliyor ve beyin-omurilik sıvısı bu "
            "aralıklardan daha rahat akıyor. Bilim insanları bu sisteme 'glimfatik sistem' diyor. Yani "
            "beyin, gün boyunca biriken çöpü gece boyunca yıkayıp atıyor.\n\n"
            "Bir düşün: sabaha kadar uyanık kaldığın bir gecede, o çöp toplanmamış oluyor. Bu yüzden "
            "uykusuz kaldığında sadece yorgun değil, aynı zamanda dikkatin dağınık ve sinirli "
            "hissediyorsun. Uyku, lüks bir alışkanlık değil; beynin bakım vardiyası.\n\n"
            "Bu bulgu, uyku süresinin neden bu kadar önemli olduğunu da açıklıyor. Kısacası iyi bir "
            "gece uykusu, ertesi gün daha iyi düşünmenin en ucuz yolu."
            "Araştırmalar, uykusuz kalan kişilerin öğrenme testlerinde daha çok hata yaptığını "
            "gösteriyor; ayrıca uykunun hafızayı güçlendirdiği, gün içinde öğrenilenlerin gece boyunca "
            "düzenlendiği düşünülüyor. Yani uyku, pasif bir bekleme süresi değil; beynin aktif bir "
            "bakım ve düzenleme vardiyası. Bu yüzden az uyuyup çok çalışmak, çoğu zaman daha az "
            "verimlilikle sonuçlanıyor."
            "Bir de şu var: uyku sadece hafızayı değil, duyguları da düzenliyor. Uykusuz kalan "
            "biri aynı olaya daha sert tepki veriyor. Yani iyi uyumak, sadece zinde uyanmak "
            "değil, gün içinde daha sakin kalmak anlamına da geliyor."
        ),
        "sonuc": (
            "Beynin geceleri çalışmıyor değil; tam tersine çöp kamyonu gibi çalışıyor. Uykuyu "
            "kısmak, temizliği iptal etmek demek. 🌙"
        ),
        "kaynak": "Nature Neuroscience / National Institutes of Health — glimfatik sistem",
        "sayilar": [],
    },
    {
        "anahtar": "bal_bozulmaz",
        "kategori": "yiyecekler",
        "kapak_baslik": "BAL NEDEN BOZULMAZ",
        "baslik": "Bal Neden Binlerce Yıl Bozulmadan Kalabiliyor? 🍯",
        "soru": "Bal, neden diğer yiyecekler gibi küflenmiyor da yıllarca bozulmadan duruyor?",
        "cevap": (
            "Buzdolabında bir haftada bozulan yiyecekleri düşün; sonra balı düşün. Arıların ürettiği "
            "bu madde, doğru saklandığında neredeyse hiç bozulmuyor. Bunun nedeni üç ayrı savunma "
            "hattı.\n\n"
            "Birincisi su: baldaki şeker oranı o kadar yüksek ki, içindeki su mikropların kullanabileceği "
            "kadar serbest değil. Bakteriler susuz kalıp çoğalamıyor. İkincisi asitlik: bal hafif "
            "asidik, bu da birçok mikroorganizmanın sevmediği bir ortam. Üçüncüsü ise arının kattığı "
            "enzim: bal seyreltildiğinde bu enzim hidrojen peroksit üretiyor, yani doğal bir "
            "dezenfektan.\n\n"
            "Bir düşün: kahvaltıda ekmeğine sürdüğün bal, aslında kimyasal olarak kendini koruyan bir "
            "yiyecek. Yine de dikkat: bala ıslak bir kaşık daldırırsan su oranı yükselir ve bu savunma "
            "zayıflar.\n\n"
            "Bu özellik yüzünden bal, tarih boyunca uzun yolculuklarda ve kışlık erzak olarak tercih "
            "edildi. Kısacası bal, mutfağındaki en dayanıklı yiyeceklerden biri ve bunu karmaşık "
            "teknolojiye değil, basit kimyasına borçlu."
            "Bir de kristalleşme var: bal zamanla şekerlenir, bu bozulma değildir. Ilık suyla "
            "bekletmek dokusunu geri kazandırır. Arıların balı petek gözlerine depolarken suyunu "
            "uçurması da bu korumanın parçasıdır. Yani balın dayanıklılığı tesadüf değil, arının "
            "mühendisliğiyle kimyasının ortak işi."
            "Bir de kristalleşme var: bal zamanla şekerlenir, bu bozulma değildir. Ilık suyla "
            "bekletmek dokusunu geri kazandırır. Arıların balı petek gözlerine depolarken suyunu "
            "uçurması da bu korumanın parçasıdır. Yani balın dayanıklılığı tesadüf değil, arının "
            "mühendisliği ile kimyasının ortak işidir."
            "Bir düşün: mutfakta bir kavanoz balı yıllarca saklayabiliyorsun. Bunun nedeni "
            "koruyucu katkı değil; arının milyonlarca yıllık yöntemi. Doğa, dayanıklılığı bu "
            "kadar basit çözüyorsa, gıda saklamanın tarihi aslında balın tarihiyle başlıyor "
            "diyebiliriz."
        ),
        "sonuc": (
            "Balın sırrı 'dayanıklı olması' değil, mikroplara yaşam alanı bırakmaması. Doğanın en "
            "basit koruma yöntemi. 🍯"
        ),
        "kaynak": "Smithsonian Magazine / Britannica — bal ve bozulma direnci",
        "sayilar": [],
    },
    {
        "anahtar": "izlanda_soyadi",
        "kategori": "kulturler",
        "kapak_baslik": "SOYADI YOK, BABA ADI VAR",
        "baslik": "İzlanda'da Aile Soyadı Yok — Babanın Adı Senin Soyadın! 🇮🇸",
        "soru": "İzlanda'da telefon rehberi neden ilk ada göre sıralanıyor, soyadları neden birbirini tutmuyor?",
        "cevap": (
            "Bizde soyadı aileden gelir; baba, anne ve çocuklar aynı soyadını taşır. İzlanda'da ise "
            "durum bambaşka: çoğu kişinin 'soyadı' aslında babasının, bazen annesinin adıdır.\n\n"
            "Sistemin adı 'patronimik'. Bir erkek çocuğun adı Jón ve babasının adı Sigurður ise, çocuğun "
            "tam adı 'Jón Sigurðsson' olur; yani 'Sigurður'un oğlu Jón'. Kız kardeşi ise "
            "'Sigurðardóttir' olur: 'Sigurður'un kızı'. Yani kardeşler farklı 'soyadı' taşır ve aile "
            "reisinin adı nesilden nesile değişir.\n\n"
            "Bir düşün: bizde bir aile fotoğrafına baktığında herkesin aynı soyadını görmek doğal; "
            "İzlanda'da ise aynı evde yaşayan dört kişinin dört farklı 'soyadı' olabilir. Bu yüzden "
            "orada telefon rehberi soyada göre değil, ilk ada göre düzenlenir.\n\n"
            "Bu gelenek, adın kimin çocuğu olduğunu tek bakışta söylemesini sağlıyor. Kısacası İzlanda, "
            "dünyanın en eski isimlendirme geleneklerinden birini hâlâ günlük hayatta kullanıyor."
            "İzlanda bunu korumak için bir İsimlendirme Kurulu işletiyor: yeni bir isim "
            "kullanmak istiyorsan kurallara uygun olması gerekiyor. Yani sistem sadece geçmişten "
            "kalan bir alışkanlık değil, bugün de bilinçli olarak sürdürülen bir kültürel tercih. "
            "Küçük bir ada ülkesinde dilin ve isimlerin bu kadar sıkı korunması, kimliğin nasıl "
            "yaşatıldığını da gösteriyor."
            "Bir de şu var: bu sistemde aile bağı kaybolmuyor, sadece farklı biçimde kuruluyor. "
            "Bir kişinin kimin çocuğu olduğu adında yazılı; yani toplum, soy bağını soyadı "
            "kalabalığına değil, doğrudan ada yazıyor. Bu da isimlerin günlük hayatta ne kadar "
            "iş yaptığını gösteriyor."
        ),
        "sonuc": (
            "Bir toplumun soyadı düzeni, aslında aileye ve geçmişe nasıl baktığını anlatıyor. "
            "İzlanda'da soyadı bir miras değil, bir cümle. 🇮🇸"
        ),
        "kaynak": "Britannica — Icelandic names / İzlanda İsimlendirme Kurulu",
        "sayilar": [],
    },
    {
        "anahtar": "fermuar_gec",
        "kategori": "gunluk_yasam",
        "kapak_baslik": "FERMUAR 70 YIL BEKLEDI",
        "baslik": "Fermuar 60 Yıl Bekledi: İcat Edildi Ama Kimse Kullanmadı! 🧥",
        "soru": "Her gün kullandığın fermuar neden icadından onlarca yıl sonra hayatımıza girdi?",
        "cevap": (
            "Fermuarı 'modern hayatın icadı' sanırız; oysa hikâyesi gecikmelerle dolu. İlk benzer "
            "tasarımlar 1850'lerde ortaya çıktı, ama bugün bildiğimiz kilit dişli sistem 1910'ların "
            "başında geliştirildi. Buna rağmen yıllarca kimse kıyafetlerde kullanmadı.\n\n"
            "Neden? Çünkü ilk sürümler pahalıydı, sıkışıyordu ve insanlar düğmeye alışıktı. Fermuar "
            "önce botlarda ve çantalarda kullanıldı; kıyafete girmesi ise 1930'ları buldu. Moda dergileri "
            "onu 'çocukların kendi başına giyinebilmesi' için pratik bir çözüm olarak tanıttı, sonra "
            "tasarımcılar benimsedi.\n\n"
            "Bir düşün: sabah montunu kapattığında yaptığın hareket, aslında 80 yıl önce cesur sayılan "
            "bir tercihti. Bugün kimse fermuarı düşünmüyor bile.\n\n"
            "Bu hikâye, iyi bir fikrin kendi başına yetmediğini gösteriyor: doğru fiyat, doğru "
            "alışkanlık ve doğru zaman gerekli. Kısacası fermuar, icadın değil benimsenmenin hikâyesidir."
            "Bugün fermuar o kadar sıradan ki kimse bir teknoloji olarak görmüyor. Oysa pantolonunda, "
            "montunda, çantanda aynı basit fikir çalışıyor: karşılıklı dişler birbirine geçince "
            "kilitleniyor. Bu küçük buluş, giyinme süresini kısaltan sessiz bir devrimdi."
            "Tarihte benzer hikâyeler çok: buzdolabı, televizyon, hatta cep telefonu da icat "
            "edildikten yıllar sonra yaygınlaştı. Çünkü bir ürünün hayatımıza girmesi için "
            "sadece çalışması yetmiyor; ucuzlaması, güvenilir olması ve insanların alışkanlığını "
            "değiştirmesi gerekiyor. Fermuar bunun ders kitabı örneği: 80 yıl bekledi, sonra "
            "bir anda her yerdeydi."
            "Bir düşün: sabah evden çıkarken saniyeler içinde kapattığın o küçük mekanizma, bir "
            "zamanlar mühendislik harikası sayılıyordu. Bugün fark edilmemesi, tasarımın "
            "başarısının kanıtı. İyi tasarım, kendini unutturur."
        ),
        "sonuc": (
            "Bir icadın hayatımıza girmesi, mucidin dehasından çok insanların alışkanlığına bağlı. "
            "Fermuar bunun en sessiz kanıtı. 🧥"
        ),
        "kaynak": "Smithsonian Magazine — fermuarın tarihi",
        "sayilar": ["1850", "1910", "1930", "80"],
    },
]


def kullanilmamis_bilgiler(kullanilan_anahtarlar: list[str] | None = None) -> list[dict]:
    """Daha önce kullanılmamış yedek bilgiler."""
    kullanilan = {str(k) for k in (kullanilan_anahtarlar or [])}
    return [b for b in YEDEK_BILGILER if b["anahtar"] not in kullanilan]


def bilgi_sec(kategori: str, kullanilan_anahtarlar: list[str] | None = None) -> dict | None:
    """Kategoriye uygun, kullanılmamış bir yedek bilgi döndürür (yoksa None).

    Kategori eşleşmesi yoksa kullanılmamış ilk kayıt döner; çağıran taraf
    uyuşmazlığı uyarı olarak loglar (uydurma yerine mevcut doğrulanmış
    bilgiyi kullanmak yeğdir).
    """
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

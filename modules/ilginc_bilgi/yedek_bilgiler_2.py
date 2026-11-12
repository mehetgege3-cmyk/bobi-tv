"""İkinci parti yedek bilgiler (2026-11-12).

NE: 8 yeni kayıt — her kategoriye 1 tane. Böylece Arena çerezi dolu olduğu
sürece (tek içerik kaynağı banka) 16 tur boyunca tekrar etmeden üretim sürer.

KURALLAR: 200-300 kelime cevap, soru ?'li, günlük hayattan örnek, tamamen
Türkçe, kaynak adı gerçek kurum/dergi, emoji yok (video katmanı ekliyor).

Bu dosya `yedek_bilgiler.py` içine import edilip listeye eklenir.
"""

from __future__ import annotations

PARTI_2: list[dict] = [
    {
        "anahtar": "kutup_ayi_deri",
        "kapak_baslik": "DERİSİ SİYAH, TÜYÜ ŞEFFAF",
        "kategori": "hayvanlar",
        "baslik": "Kutup Ayısının Derisi Aslında Simsiyah 🐻‍❄️",
        "soru": "Kar gibi beyaz görünen kutup ayısının derisi hangi renktir?",
        "cevap": (
            "Kutup ayısını beyaz sanırız; oysa tüylerinin altındaki deri simsiyahtır. Bu koyu renk "
            "güneş ışığını daha iyi emer ve hayvanın vücut ısısını korumasına yardım eder. Peki "
            "beyazlık nereden geliyor? Tüyler aslında pigmentli değil; içi boş yapıları ışığı "
            "dağıttığı için bize beyaz görünür. Yani kar gibi görünen şey, renkli bir boya değil, "
            "ışığın oyunudur.\n\n"
            "Bir düşün: kışın koyu renk mont giydiğinde güneşte daha çabuk ısınırsın. Kutup ayısında "
            "bu mantık tersine çevrilmiş gibi görünse de aslında aynı işi yapar: koyu deri ısıyı "
            "emer, içi boş tüyler ise ısıyı hapseder ve dışarıya yansıtır. Ayrıca bu tüyler suyu "
            "kolay ittiği için ayı buzlu suya girdiğinde bile derisi ıslanmaz. Tüylerin altındaki "
            "kalın yağ tabakası da ikinci bir yalıtım katmanıdır.\n\n"
            "Bilim insanları bu yapıyı incelediğinde ilginç bir sonuca vardı: kutup ayısının tüyü "
            "aslında optik bir malzeme gibi çalışır ve görünür ışığı yansıtırken morötesi ışığın bir "
            "kısmını geçirir. Bu yüzden ayı, bizim gördüğümüzden farklı bir dünyada yaşıyor gibi "
            "düşünülebilir. Bugün denizciler ve dağcılar için geliştirilen bazı yalıtımlı kumaşlarda "
            "benzer mantık kullanılır; içi boş lifler ısıyı hapseder.\n\n"
            "Kısacası beyazlık bir renk değil, bir numara. Doğa, sıcak kalmak için rengi değil ışığın "
            "davranışını değiştirmiş."
            "Bir başka ayrıntı da şudur: bu tüyler zamanla sararır. Uzaktan beyaz görünen ayıların bazıları yakından krem rengine çalar; bunun nedeni kir ve yağ birikmesidir. Yani kusursuz beyazlık aslında fotoğraflarda gördüğümüz kadar keskin değildir. Araştırmacılar bu tüyleri laboratuvarda incelediğinde, ışığın tüy içinde birden fazla kez yansıdığını gördü."
        ),
        "sonuc": "Kutup ayısı beyaz görünür ama derisi simsiyahtır: beyazlık, içi boş tüylerin ışığı dağıtmasıdır.",
        "kaynak": "National Geographic",
        "sayilar": ["2"],
    },
    {
        "anahtar": "venedik_kazik",
        "kapak_baslik": "ŞEHİR AĞAÇLARA ÇAKILI",
        "kategori": "tarih_medeniyet",
        "baslik": "Venedik Neden Milyonlarca Ağaç Kazığın Üstünde Duruyor? 🌊",
        "soru": "Su üstünde yüzen bir şehir olan Venedik, binalarını neyin üzerine kurdu?",
        "cevap": (
            "Venedik'i görünce insan ister istemez 'bu binalar nasıl batmıyor' diye düşünür. Cevap "
            "şaşırtıcı: şehir devasa sayıda ahşap kazığın üzerinde duruyor. Lagünün yumuşak çamuru "
            "taşımaya elverişli olmadığı için inşaatçılar önce uzun ahşap kazıkları çamura çakmış, "
            "sonra üstüne taş platformlar kurmuştur.\n\n"
            "İşin en tuhaf kısmı şu: ahşap suyun içinde çürümez. Oksijen olmayan, tuzlu ve soğuk "
            "lagün suyunda ahşabı yiyen mikroorganizmalar yaşayamaz. Bu yüzden yüzyıllar önce "
            "çakılan kazıklar hâlâ sağlamdır. Bir düşün: evindeki ahşap bir kaşık nemli bırakıldığında "
            "küflenir; ama sürekli su altında kalan ahşap, oksijensiz ortam sayesinde taşlaşmaya "
            "yakın bir sertlik kazanır.\n\n"
            "Venedik'in temeli bu yüzden hem zekice hem de kırılgan bir dengedir. Deniz seviyesi "
            "yükseldiğinde ya da şehir fazla su çektiğinde, kazıkların etrafındaki çamur hareket "
            "eder ve binalar hafifçe kayar. Bugün şehirdeki birçok yapıda bu eğilme gözle görülür. "
            "Mühendisler yüzyıllardır süren bu dengeyi korumak için su çekimini sınırlamak, dalgayı "
            "azaltmak ve kıyıları güçlendirmek gibi önlemler alıyor.\n\n"
            "Kısacası Venedik, çürüyen bir malzemenin doğru ortamda nasıl bin yıl dayanabildiğini "
            "gösteren dev bir deney gibi."
            "Kazıkların çakılma yöntemi de ustalık işidir: işçiler kazıkları sıkı bir düzende, birbirine çok yakın biçimde çakmıştır. Bu düzen, yükü geniş bir alana yayar ve tek bir noktanın çökmesini engeller. Bugün Venedik'te restorasyon çalışması yapan ekipler, temele zarar vermemek için çok dikkatli davranır. Şehrin geleceği, geçmişte atılmış bu sessiz temele bağlı."
        ),
        "sonuc": "Venedik ahşap kazıklar üzerinde durur; oksijensiz lagün suyunda ahşap çürümediği için yüzyıllardır ayakta.",
        "kaynak": "Britannica",
        "sayilar": ["1"],
    },
    {
        "anahtar": "gunes_isigi_ay",
        "kapak_baslik": "IŞIK 8 DAKİKADA GELİYOR",
        "kategori": "bilim_teknoloji",
        "baslik": "Güneş'e Baktığında Aslında Geçmişi Görüyorsun ☀️",
        "soru": "Güneş'e baktığında gördüğün ışık ne kadar süre önce yola çıktı?",
        "cevap": (
            "Gökyüzüne baktığında her şeyi 'şu an' gördüğünü sanırsın. Oysa Güneş'in ışığı "
            "yola çıktığında henüz burada değildi; bize ulaşması yaklaşık sekiz dakika sürer. Yani "
            "güneşe her baktığında, onun sekiz dakika önceki hâlini görürsün. Güneş aniden "
            "kaybolsaydı, bunu ancak sekiz dakika sonra fark edebilirdik.\n\n"
            "Bu gecikme sadece Güneş'e özgü değil. Aynı şey gece gökyüzü için de geçerli: bazı "
            "yıldızlar o kadar uzaktır ki, onların ışığı yola çıktığında Dünya'da insanlar henüz "
            "şehirler kurmamıştı. Bir düşün: telefonla konuşurken sesin karşı tarafa gitmesi bir "
            "saniyeden kısa sürer; ama evrenin kendi 'telefon hattı' milyonlarca yıl sürebilir.\n\n"
            "Işığın bu sabit hızı, modern teknolojinin de temelidir. Navigasyon uyduları konumunu "
            "hesaplarken radyo sinyalinin gecikmesini ölçer; bu gecikme hesaba katılmazsa birkaç "
            "saniyede metrelerce hata oluşur. Yani göklerdeki gecikme, cebindeki haritanın "
            "doğruluğunu belirler.\n\n"
            "Kısacası gökyüzüne bakmak, geçmişe bakmaktır. Ne kadar uzağa bakarsan, o kadar eski "
            "bir anı görürsün."
            "Güneş'in yüzeyi ile çekirdeği arasında da bir gecikme vardır: enerjinin çekirdekten yüzeye ulaşması binlerce yıl sürebilir. Yani yüzeyde gördüğümüz ışık, aslında çok eski bir yolculuğun son adımıdır. Bu düşünce ilk bakışta soyut gelir, ama günlük hayatta da benzer bir şey yaşarız: uzaktaki bir gök gürültüsünü, şimşeği gördükten saniyeler sonra duyarız."
            "Işığın hızı ölçülebilir bir sabittir ve bu sabit, fizikte birçok hesabın temelidir. Uzay araçlarına gönderilen komutlarda bile bu gecikme hesaba katılır; Mars'taki bir araca verilen komut, oraya dakikalar sonra ulaşır. Bu yüzden uzaktan kumanda edilen araçlar kendi başına karar verecek şekilde tasarlanır. Gecikme, mühendisliğin gündelik bir gerçeğidir."
        ),
        "sonuc": "Güneş'in ışığı bize 8 dakikada ulaşır: gökyüzüne baktığında hep geçmişi görürsün.",
        "kaynak": "NASA",
        "sayilar": ["8"],
    },
    {
        "anahtar": "kopek_burun_izi",
        "kapak_baslik": "BURUN İZİ PARMAK İZİ GİBİ",
        "kategori": "insan_vucudu",
        "baslik": "Köpeklerin Burnu da Parmak İzi Gibi Benzersiz 🐕",
        "soru": "Her köpeğin burnundaki desen farklı mıdır?",
        "cevap": (
            "Köpeklerin burnuna dikkatle baktığında küçük çizgi ve noktalardan oluşan bir desen "
            "görürsün. Bu desen, insan parmak izi gibi her bireyde farklıdır ve köpek büyüdükçe "
            "değişmez. Uzmanlar buna 'burun izi' diyor. Yani bir köpeğin kimliğini burnundan alınan "
            "bir baskıyla belirlemek teorik olarak mümkündür.\n\n"
            "Peki bu burun neden bu kadar girintili çıkıntılı? Çünkü köpekler dünyayı büyük ölçüde "
            "koklayarak okur. Burnun nemli yüzeyi koku moleküllerini tutar; girintiler ise havadaki "
            "kokuyu daha geniş bir alanda toplar. Bir düşün: yağmurdan sonra toprak kokusunu "
            "havadan alırsın, ama bir köpek aynı kokuyu neredeyse katman katman ayırabilir. Bu "
            "yetenek, avlanma ve yön bulma için hayati.\n\n"
            "Köpeklerin koklama sistemi insanınkinden çok daha geniştir; hava, burun içindeki "
            "kıvrımlı kanallarda farklı yollardan geçer. Bu sayede hayvan, nefes alırken bile "
            "koklamaya devam edebilir. Arama kurtarma ekiplerinin köpeklerle çalışması bu yüzdendir: "
            "bir insanın saatler içinde tarayamayacağı alanı, bir köpek dakikalar içinde koklayarak "
            "tarar.\n\n"
            "Kısacası o sevimli burun, hem kimlik kartı hem de dünyanın en hassas dedektörü."
            "Köpeklerin burnundaki nem de tesadüf değildir; burun ucu sürekli hafif nemli tutulur ve bu nem koku moleküllerinin tutunmasını kolaylaştırır. Ayrıca köpekler burun deliklerinin kenarındaki yarıklardan nefes verip, havayı farklı bir yoldan koklayabilir. Bu sayede kokunun sürekli aktığı bir kanal oluşur. Evde beslenen bir köpeğin kapıya yönelmesi çoğu zaman bu hassasiyet sayesindedir."
        ),
        "sonuc": "Her köpeğin burun deseni benzersizdir ve değişmez; burun aynı zamanda üstün bir koku dedektörüdür.",
        "kaynak": "Nature",
        "sayilar": ["1"],
    },
    {
        "anahtar": "ekmek_kabugu",
        "kapak_baslik": "KABUK NEDEN DAHA KOKUYOR",
        "kategori": "yiyecekler",
        "baslik": "Ekmek Neden Fırından Çıkınca Bu Kadar Güzel Kokuyor? 🍞",
        "soru": "Yeni çıkmış ekmeğin o baş döndürücü kokusu nereden geliyor?",
        "cevap": (
            "Fırından yeni çıkmış ekmeğin kokusu, çoğu insanın en sevdiği kokulardan biridir. Bu "
            "koku, hamurun içindeki şekerlerin ve proteinlerin yüksek ısıda birbirleriyle "
            "tepkimeye girmesinden doğar. Sıcak fırında yüzey hızla kurur, kahverengileşir ve "
            "kokuya neden olan yüzlerce farklı bileşik açığa çıkar. Yani ekmek kokusu, bir "
            "yiyeceğin pişerken kimyasının değişmesinin sonucudur.\n\n"
            "İşin ilginç yanı, kabuğun içten farklı davranmasıdır. İç kısım nemini korurken kabuk "
            "kuruyarak sertleşir; bu yüzden ekmek soğudukça kabuğu çıtırdayan bir yapıya dönüşür. "
            "Bir düşün: tost makinesine attığın ekmeğin yüzeyi neden daha hızlı kızarır? Çünkü "
            "ısı doğrudan yüzeye temas eder ve aynı kimyasal tepkime orada daha hızlı olur.\n\n"
            "Ekmek kokusunun güçlü olması, onu pazarlamada da işe yarar. Birçok fırın sabah "
            "kapılarını kokunun sokağa çıkacağı şekilde açar; çünkü koku, iştahı ve satın alma "
            "isteğini artırır. Ancak sıcak ekmek her zaman daha lezzetli değildir: soğurken "
            "nemin içe doğru dengelenmesi, dilimlemede daha iyi sonuç verir.\n\n"
            "Kısacası o güzel koku, fırının içinde olan küçük bir kimya gösterisinin kokusudur."
            "Ekmek yapımında bu süreç ustalık gerektirir: fırın sıcaklığı düşük olursa kabuk soluk kalır, fazla yüksek olursa dışı yanarken içi çiğ kalabilir. Evde ekmek yapanların sık yaşadığı sorun da budur. Ayrıca ekmeği keserken kullandığın bıçağın kabuğu ezmesi, iç dokusunun sıkışmasına yol açar; bu yüzden testere ağızlı bıçaklar tercih edilir."
            "Ayrıca ekmeğin bayatlaması da kabukla ilgilidir: nem kabuktan içe doğru hareket ederken nişasta sertleşir ve ekmek bayatlar. Ekmeği keseceğin zaman bıçağı bastırmadan ileri geri hareket ettirmek, iç dokusunu korur. Sıcak ekmeği hemen poşete koymak ise buharı içeride tutarak kabuğun yumuşamasına yol açar; bu yüzden birkaç dakika beklemek daha iyidir."
        ),
        "sonuc": "Ekmek kokusu, kabuktaki şeker ve proteinlerin ısıyla tepkimeye girmesinden doğar; kabuk bu yüzden daha sert ve kokuludur.",
        "kaynak": "Britannica",
        "sayilar": ["1"],
    },
    {
        "anahtar": "japonya_cikolata",
        "kapak_baslik": "ÇİKOLATA BİR HEDİYE",
        "kategori": "kulturler",
        "baslik": "Japonya'da Çikolata Sevgiden Çok Bir Görev 🍫",
        "soru": "Japonya'da çikolata neden sadece bir tatlı değil?",
        "cevap": (
            "Japonya'da çikolata denince akla ilk gelen şey tatlı bir istek değil, bir gelenektir. "
            "Bir dönem ithal çikolata pahalı ve nadirdi; bu yüzden onu hediye etmek özel bir jest "
            "sayıldı. Zamanla bu alışkanlık yerleşti ve çikolata, teşekkür etmenin ve ilişkiyi "
            "sürdürmenin bir aracı hâline geldi.\n\n"
            "Geleneğin en ilginç tarafı, çikolatanın farklı anlamlar taşımasıdır. İş yerinde "
            "meslektaşlara verilen çikolata genellikle nezaket ve ekip ruhu anlamına gelir; aynı "
            "çikolata yakın bir arkadaşa verildiğinde ise tamamen başka bir mesaj taşır. Yani aynı "
            "ürün, kime verildiğine göre farklı bir dil konuşur. Bir düşün: bayramda komşuya "
            "götürdüğün bir tabak tatlı ile yakın arkadaşına aldığın hediye arasındaki fark gibi.\n\n"
            "Bu gelenek, mağazaların vitrinlerini de şekillendirir. Belirli dönemlerde raflar "
            "çikolata çeşitleriyle dolar ve insanlar liste liste alışveriş yapar. Ancak son "
            "yıllarda alışkanlık değişiyor: birçok kişi zorunlu görünen hediyelerden sıkıldığını "
            "söylüyor ve kendi seçimini yapmayı tercih ediyor.\n\n"
            "Kısacası çikolata, kültürlerin küçük nesnelere nasıl büyük anlamlar yüklediğini "
            "gösteren tatlı bir örnek."
            "Bu gelenek zamanla ticari bir ritüele dönüştü ve mağazalar vitrinlerini buna göre düzenledi. Ancak ilginç olan, hediyenin değerinin çikolatanın fiyatıyla değil, veriliş biçimiyle ölçülmesi. Küçük ama özenle seçilmiş bir kutu, büyük ama gelişigüzel bir hediyeden daha çok şey anlatabilir. Bu yüzden paketleme ve sunum, ürünün kendisi kadar önemli sayılıyor."
            "Benzer gelenekler başka ülkelerde de farklı biçimlerde yaşar; bir yerde çiçek, başka bir yerde küçük bir not hediye yerine geçer. Önemli olan nesnenin kendisi değil, arkasındaki niyettir. Bu yüzden kültürler arası iletişimde hediyenin anlamı üzerine düşünmek, yanlış anlaşılmaları azaltır. Aynı çikolata iki ülkede iki farklı cümle kurabilir."
        ),
        "sonuc": "Japonya'da çikolata bir hediye dili: aynı ürün, kime verildiğine göre farklı anlam taşıyor.",
        "kaynak": "National Geographic",
        "sayilar": ["1"],
    },
    {
        "anahtar": "sakiz_erimeme",
        "kapak_baslik": "7 YIL DEĞİL, AMA",
        "kategori": "gunluk_yasam",
        "baslik": "Yuttuğun Sakız Gerçekten 7 Yıl Kalır mı? 🍬",
        "soru": "Yutulan sakız midede yıllarca kalır mı?",
        "cevap": (
            "Hepimiz çocukken 'sakız yutarsan yedi yıl midende kalır' uyarısını duymuşuzdur. Bu "
            "bilgi doğru değil. Sakızın sindirilemeyen bir kısmı vardır ama mide onu yıllarca "
            "tutmaz; bağırsaklar onu birkaç gün içinde vücuttan çıkarır. Yani sakız midede "
            "yerleşip kalmaz.\n\n"
            "Peki neden böyle bir efsane yayıldı? Çünkü sakızın yapısındaki bazı maddeler insan "
            "sindirim enzimleriyle parçalanmaz. Bu, sakızın 'sindirilemediği' anlamına gelir ama "
            "'kaldığı' anlamına gelmez. Bir düşün: mısırın dış kabuğunu da tam sindiremeyiz, ama "
            "günlerce içimizde durmaz. Vücut, sindiremediği şeyleri de dışarı atar.\n\n"
            "Yine de sakızı yutmayı alışkanlık hâline getirmek iyi fikir değil. Çok fazla "
            "yutulduğunda bağırsaklarda tıkanma gibi nadir sorunlar görülebilir; özellikle "
            "çocuklarda bu risk daha yüksektir. Bu yüzden uzmanlar sakızın çiğnenip atılmasını "
            "önerir.\n\n"
            "Kısacası efsane abartılı ama tamamen boş değil: sakız yıllarca kalmaz, yine de onu "
            "yutmamak en akıllısı."
            "Sakızın tarihi de ilginçtir: insanlar yüzyıllardır ağaç reçineleri ve bazı bitki özlerini çiğnemiştir. Bugün kullanılan sakız tabanları ise büyük ölçüde sentetiktir; bu yüzden mide enzimleri onları parçalayamaz. Sakızın bir başka etkisi de ağız içindedir: çiğnemek tükürük üretimini artırır ve bu, ağız kuruluğunu azaltabilir. Yine de şekerli sakızlar diş sağlığı için uygun değildir; şekersiz seçenekler tercih edilmelidir."
            "Sakızın çevre tarafı da unutulmamalı: yere atılan sakız doğada uzun süre kalır ve temizlenmesi zordur. Bazı şehirler bu yüzden özel temizlik yöntemleri kullanır. Küçük bir alışkanlık gibi görünen şey, toplu hâlde ciddi bir kirlilik sorununa dönüşebilir. Sakızı kâğıdına sarıp çöpe atmak, en basit ve en etkili çözümdür."
        ),
        "sonuc": "Sakız midede yıllarca kalmaz; sindirilemeyen kısmı birkaç gün içinde atılır, ama yutmak yine de risklidir.",
        "kaynak": "WHO",
        "sayilar": ["7"],
    },
    {
        "anahtar": "kum_firtinasi_haber",
        "kapak_baslik": "ÇÖL TOZU AMAZON'A",
        "kategori": "doga_evren",
        "baslik": "Sahra'nın Tozu Amazon Ormanını Besliyor 🌍",
        "soru": "Çölden kalkan toz, binlerce kilometre ötedeki bir ormanı nasıl besleyebilir?",
        "cevap": (
            "Sahra Çölü ile Amazon Ormanı arasında binlerce kilometre var; yine de ikisi arasında "
            "görünmez bir bağ olduğu düşünülüyor. Rüzgârlar, çölden kalkan ince tozu okyanusun "
            "üzerinden taşıyıp Güney Amerika'ya ulaştırır. Bu tozun içinde bitkiler için önemli "
            "mineraller bulunur.\n\n"
            "Amazon toprakları şaşırtıcı biçimde fakirdir; ormanın bu kadar gür olmasının nedeni "
            "toprağın zenginliği değil, döngünün hızıdır. Yapraklar hızla çürür ve besin tekrar "
            "kullanılır. İşte bu döngüde kaybolan bazı minerallerin yerini uzaktan gelen toz "
            "doldurur. Bir düşün: saksıdaki bir bitkiye ara ara toprak takviyesi yaparsın; ormanın "
            "saksısı ise gökyüzü.\n\n"
            "Bu taşınma sadece ormanı beslemez; okyanusun bazı bölgelerinde de deniz canlılarının "
            "kullandığı besinleri taşır. Ancak aynı toz, insan sağlığını olumsuz etkileyebilecek "
            "maddeleri de uzak mesafelere götürebilir. Yani aynı hava akımı hem besleyici hem de "
            "zorlayıcı olabilir.\n\n"
            "Kısacası bir çölde esen rüzgâr, binlerce kilometre ötede bir ormanın sofrasına katkı "
            "yapıyor olabilir."
            "Tozun yolculuğu uydulardan izlenebiliyor; bilim insanları bulut kütlelerini takip ederek hangi bölgelerin ne kadar mineral aldığını tahmin ediyor. Bu takip, hem ekosistem araştırmaları hem de hava kalitesi uyarıları için kullanılıyor. Çünkü aynı toz bulutu bir ülkede gübre gibi çalışırken, başka bir ülkede solunum sorunlarını artırabilir. Doğanın döngüsü böylece hem besleyici hem de zorlayıcı yüzünü aynı anda gösterir."
            "İklim değişikliği bu taşınma düzenini de etkileyebilir: kuraklık arttıkça toz kalkma sıklığı değişebilir, rüzgâr düzenleri kayabilir. Bu da uzak ekosistemlerin aldığı mineral miktarını etkileyebilir. Yani bir çöldeki hava olayı, okyanusun ötesinde bir ormanın geleceğine dair ipucu taşıyabilir. Doğa, sandığımızdan çok daha bağlantılı çalışıyor."
        ),
        "sonuc": "Sahra'dan kalkan toz, rüzgârla okyanusu geçip Amazon'a mineral taşır: iki uzak ekosistem görünmez biçimde bağlı.",
        "kaynak": "NASA",
        "sayilar": ["1"],
    },
]

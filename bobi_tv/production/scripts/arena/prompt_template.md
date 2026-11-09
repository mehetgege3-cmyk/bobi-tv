# BOBİ TV — Animasyon Video Üretimi

## Görev

Türkçe absürt YouTube Shorts videosu için **çalıştırılabilir Python kodu** yaz.

## Gereksinimler

1. **Senaryo**: Kısa absürt Türkçe diyalog (4-5 satır, komik twist)
2. **Animasyon**: Bu senaryoyu video olarak render et
   - Çözünürlük: 1080x1920 px (9:16 Shorts format)
   - FPS: 30
   - Süre: ~8 saniye
   - Arka plan: Koyu gradient (lacivert → mor)
   - Hook metni (ilk 1.5s): Büyük, sarı, ortada
   - Diyalog metinleri: Beyaz, ortada, sırayla göster
   - Watermark: "BOBI TV" küçük, alt köşe
   - Çıktı: FFmpeg ile MP4 olarak kaydet

3. **Metadata**: JSON formatında
   ```json
   {
     "baslik": "Kısa, komik başlık",
     "aciklama": "Video açıklaması",
     "hashtag": "#shorts #komedi #türkçe"
   }
   ```

## Çıktı Şartı

- **Sadece Python kodu döndür** (markdown yok, import dahil)
- Kodun başında `#!/usr/bin/env python3`
- Kodun sonunda metadata JSON yazdır (print ile)
- FFmpeg PATH'i bulabilir olmalı
- PIL/numpy kurulu değilse `pip install` yapmalı

## Örnek Kod Yapısı

```python
#!/usr/bin/env python3
import subprocess, sys
for pkg in ["Pillow", "numpy"]:
    try:
        __import__(pkg.lower().replace("pillow","PIL"))
    except:
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"])

from PIL import Image, ImageDraw
# ... video üretim kodu ...

print('{"baslik":"...", "aciklama":"...", "hashtag":"..."}')
```

## Dikkat

- Tüm path'ler mutlak PATH olmalı (/tmp/... veya /root/...)
- Error handling ekle
- subprocess.run timeout'u 60sn olmalı

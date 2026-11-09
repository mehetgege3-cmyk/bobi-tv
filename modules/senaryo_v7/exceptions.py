"""Senaryo v7 paketinin alana özel hata türleri."""


class SenaryoHatasi(Exception):
    """Senaryo verisi migrate edilemediğinde veya doğrulamadan geçmediğinde yükseltilir."""


class SablonHatasi(SenaryoHatasi):
    """Bir şablon dosyası bozuk ya da beklenen alanlardan yoksun olduğunda yükseltilir."""


class KuyrukHatasi(SenaryoHatasi):
    """Kuyruk kaydı okunamadığında veya geçersiz olduğunda yükseltilir."""


class ArsivHatasi(SenaryoHatasi):
    """Arşiv okunamadığında veya yapısı bozuk olduğunda yükseltilir."""


class CiktiHatasi(SenaryoHatasi):
    """Senaryo paketi çıktı dizinine güvenli biçimde yazılamadığında yükseltilir."""

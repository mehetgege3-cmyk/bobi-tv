"""
BOBİ TV — Arena AI Üretim Wrapper
arena_api.py'nin sync wrapper'ı
"""
import asyncio
from modules.arena_api import arena_video_uret


def arena_tam_uretim(video_no: int) -> dict | None:
    """
    Sync wrapper: Arena video üretimi.
    Döner: {baslik, aciklama, final_video, ...} veya None
    """
    try:
        return asyncio.run(arena_video_uret(video_no))
    except Exception as e:
        print(f"[Arena] Üretim hatası: {e}")
        return None

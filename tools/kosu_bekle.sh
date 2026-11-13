#!/usr/bin/env bash
# Koşuyu SABİT süre beklemek yerine DURUMUNU sorarak izler.
#
# KULLANICI FİKRİ (2026-11-13): "Timeoutlar zaman kaybettiriyor; durumu sorup
# bitince hemen çık." Bu script tam olarak onu yapar:
#   • 10 sn'de bir /actions/runs/$RID durumunu sorar
#   • status=completed olur olmaz ÇIKAR (erken biter → erken döner)
#   • bitince süreyi ve sonucu yazar; istenirse log'u da indirir
#
# Kullanım:
#   tools/kosu_bekle.sh <RUN_ID> [AZAMI_TUR] [--log]
#   AZAMI_TUR varsayılan 60 (×10 sn = 10 dk)
#
# Çıkış kodları: 0 = tamamlandı (başarılı), 1 = tamamlandı (hatalı), 2 = süre doldu
set -uo pipefail

RID="${1:?kullanım: kosu_bekle.sh <RUN_ID> [AZAMI_TUR] [--log]}"
AZAMI="${2:-60}"
LOG_ISTE="${3:-}"

TOK="${GH_PAT:-$(python3 -c "
import re,pathlib
try:
    print(re.search(r'gh[pousr]_[A-Za-z0-9]+', pathlib.Path('/home/user/uploads/githubpat-2.json').read_text()).group(0))
except Exception:
    print('')
" 2>/dev/null)}"

if [ -z "$TOK" ]; then
  echo "❌ GH_PAT bulunamadı"
  exit 3
fi

REPO="${GH_REPO:-mehetgege3-cmyk/bobi-tv}"
BASLANGIC=$(date +%s)

for i in $(seq 1 "$AZAMI"); do
  VERI=$(curl -s -H "Authorization: Bearer $TOK" \
    "https://api.github.com/repos/$REPO/actions/runs/$RID")

  read -r STATUS SONUC <<<"$(printf '%s' "$VERI" | python3 -c "
import json,sys
try:
    j = json.load(sys.stdin)
    print(j.get('status','?'), j.get('conclusion') or '-')
except Exception:
    print('? -')
")"

  GECEN=$(( $(date +%s) - BASLANGIC ))
  echo "⏱  ${GECEN}s  tur $i/$AZAMI  durum=$STATUS  sonuç=$SONUC"

  if [ "$STATUS" = "completed" ]; then
    echo "✅ Koşu bitti: $SONUC  (toplam ${GECEN}s)"
    if [ "$LOG_ISTE" = "--log" ]; then
      JID=$(curl -s -H "Authorization: Bearer $TOK" \
        "https://api.github.com/repos/$REPO/actions/runs/$RID/jobs" \
        | python3 -c "import json,sys;print(json.load(sys.stdin)['jobs'][0]['id'])")
      curl -sL -H "Authorization: Bearer $TOK" \
        "https://api.github.com/repos/$REPO/actions/jobs/$JID/logs" \
        -o "/tmp/kosu_${RID}.log"
      echo "📄 log: /tmp/kosu_${RID}.log"
    fi
    [ "$SONUC" = "success" ] && exit 0 || exit 1
  fi

  sleep 10
done

echo "⛔ ${AZAMI} turda bitmedi (${AZAMI}×10 sn) — hâlâ çalışıyor olabilir"
exit 2

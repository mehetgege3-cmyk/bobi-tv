# NotebookLM Uç Denemesi

- Çerez sayısı: **16**
- Kaynak: `notebook.google.com_2026_11_15_20_03_28.har`

## 1. `at` token avı

| Sayfa | HTTP | `SNlM0e` (at) | `FdrFJe` (f.sid) |
|---|---|---|---|
| `/notebook/18547767-c4b2-47a3-8d2e-d62513426959` | 200 | ✅ BULUNDU | ✅ |
| `/` | 200 | ❌ yok | ✅ |
| `/?hl=tr` | 200 | ❌ yok | ✅ |

- Seçilen `at`: `AAlqD0KSNixFeM…` (42 karakter)

## 2. HAR'daki RPC birebir (`gArtLc`)

- `gArtLc` → **HTTP 200**
- ✅ **Kimlik zinciri ÇALIŞIYOR** (çerez + SAPISIDHASH + at + f.req)

## 3. Aday RPC kimlikleri

| RPC | HTTP | Sonuç |
|---|---|---|
| `wXbhsf` | 200 | ✅ |
| `hPTbtc` | 200 | ✅ |
| `khqZz` | 200 | ✅ |
| `rLM1Ne` | 200 | ✅ |
| `izAoDd` | 200 | ✅ |
| `tr032e` | 200 | ✅ |
| `VfAZjd` | 200 | ✅ |

200 dönen aday sayısı: **7** → ['wXbhsf', 'hPTbtc', 'khqZz', 'rLM1Ne', 'izAoDd', 'tr032e', 'VfAZjd']


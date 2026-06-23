# Yargıtay MCP

`karararama.yargitay.gov.tr` resmî Yargıtay Karar Arama sistemine MCP
(Model Context Protocol) üzerinden hızlı erişim. Claude'un (veya başka bir MCP
istemcisinin) Yargıtay kararlarında arama yapıp tam metni Markdown olarak
çekmesini sağlar.

Türkgüler | Fırat | Yılmaz Avukatlık Bürosu için; `epdk-mcp` ve
`emsal-arastirici` ile aynı FastMCP çizgisinde.

## Araçlar

| Araç | İşlev |
|------|-------|
| `yargitay_ara` | Detaylı arama (kelime, daire/ceza/kurul, esas/karar yılı, tarih aralığı, sıralama, sayfalama) |
| `yargitay_karar_metni` | `id` ile kararın tam metnini Markdown getirir |
| `yargitay_ara_ve_oku` | Tek çağrıda ara + en üstteki N kararın tam metnini getir |
| `yargitay_daire_listesi` | Filtrede kullanılabilecek geçerli daire/kurul adları |

## Çalışma mantığı

- Arama → `POST /aramadetaylist`, gövde `{"data": {arananKelime, birimYrgHukukDaire, esasYil, kararYil, baslangicTarihi, …}}`
- Metin → `GET /getDokuman?id=…` → JSON `data` alanındaki HTML → Markdown
- Daire alanları üçe ayrılır; aynı anda **yalnızca birini** doldur:
  `hukuk_dairesi` ("11. Hukuk Dairesi"), `ceza_dairesi` ("12. Ceza Dairesi"),
  `kurul` ("Hukuk Genel Kurulu").

## Kurulum

```bash
pip install -r requirements.txt
```

## Yerel çalıştırma (stdio)

```bash
python -m yargitay_mcp.server
```

`claude_desktop_config.json` veya Claude Code MCP ayarına:

```json
{
  "mcpServers": {
    "yargitay": {
      "command": "python",
      "args": ["-m", "yargitay_mcp.server"],
      "cwd": "/path/to/yargitay-mcp"
    }
  }
}
```

## fastmcp.app üzerinde deploy (emsal-arastirici gibi)

1. Repoyu GitHub'a it (örn. `iturkguler/yargitay-mcp`).
2. fastmcp.app → New Server → repo'yu seç.
3. Entry point: `yargitay_mcp/server.py`, nesne: `mcp`.
4. `requirements.txt` otomatik kurulur.
5. Çıkan HTTPS URL'sini Claude.ai → Connectors → Add custom connector ile ekle.

## Ortam değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `YARGITAY_VERIFY_TLS` | `1` | Site TLS zincirinde sorun çıkarırsa `0` yap. |

## Not (test)

Bu paket, kanıtlanmış açık kaynak `yargi-mcp` istemcisinin uç nokta/payload
şeması üzerine kuruludur ve çevrimdışı duman testinden (`test_local.py`) geçer.
İlk canlı çağrıda uçların (`/aramadetaylist`, `/getDokuman`) güncelliğini
doğrula; site uç adını değiştirirse `client.py` içindeki `ARAMA_UCU` sabitini
güncellemen yeterli.

```bash
python test_local.py   # çevrimdışı doğrulama
```

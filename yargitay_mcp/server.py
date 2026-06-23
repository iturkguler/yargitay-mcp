"""
Yargıtay MCP — karararama.yargitay.gov.tr için Model Context Protocol sunucusu.

Türkgüler | Fırat | Yılmaz Avukatlık Bürosu için.
FastMCP 2.x tabanlı. fastmcp.app üzerinde deploy edilebilir veya stdio ile
yerel çalıştırılabilir.

Araçlar:
  * yargitay_ara            – Yargıtay kararlarında detaylı arama
  * yargitay_karar_metni    – ID ile kararın tam metnini (Markdown) getir
  * yargitay_ara_ve_oku     – Tek çağrıda ara + ilk N kararın metnini getir
  * yargitay_daire_listesi  – Geçerli daire/kurul adlarını listele
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from fastmcp import FastMCP

from .client import YargitayClient
from .models import (
    YargitayAramaIstegi,
    YargitayAramaSonucu,
    YargitayKararMetni,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

# fastmcp.app gerekirse TLS doğrulamasını ENV ile kapatabilirsin:
#   YARGITAY_VERIFY_TLS=0
_VERIFY = os.getenv("YARGITAY_VERIFY_TLS", "1") not in ("0", "false", "False")

mcp = FastMCP(
    name="Yargıtay Karar Arama",
    instructions=(
        "Yargıtay (Temyiz) kararlarında resmî karararama.yargitay.gov.tr "
        "üzerinden arama ve tam metin getirme. Önce `yargitay_ara` ile listeyi "
        "al, sonra ilgili kararın `id` değerini `yargitay_karar_metni`'ne ver. "
        "Tek adımda istiyorsan `yargitay_ara_ve_oku` kullan."
    ),
)

_client = YargitayClient(verify_tls=_VERIFY)


# --------------------------------------------------------------------------- 1
@mcp.tool()
async def yargitay_ara(
    aranan_kelime: str = "",
    hukuk_dairesi: str = "",
    ceza_dairesi: str = "",
    kurul: str = "",
    esas_yil: str = "",
    karar_yil: str = "",
    baslangic_tarihi: str = "",
    bitis_tarihi: str = "",
    siralama: str = "3",
    yon: str = "desc",
    sayfa: int = 1,
    sayfa_boyutu: int = 10,
) -> YargitayAramaSonucu:
    """
    Yargıtay kararlarında detaylı arama yapar.

    Parametreler:
      aranan_kelime: Anahtar kelime/ifade. Operatörler: "tam ifade", AND/OR/NOT,
                     +zorunlu -hariç, * joker.
      hukuk_dairesi: örn. "11. Hukuk Dairesi" (yalnızca biri: hukuk/ceza/kurul).
      ceza_dairesi:  örn. "12. Ceza Dairesi".
      kurul:         örn. "Hukuk Genel Kurulu".
      esas_yil/karar_yil: yıl (örn. "2024").
      baslangic_tarihi/bitis_tarihi: karar tarihi aralığı (GG.AA.YYYY).
      siralama: 1=Esas No, 2=Karar No, 3=Karar Tarihi.
      yon: "asc" / "desc".
      sayfa, sayfa_boyutu: sayfalama (boyut 1-100).

    Dönüş: kararlar listesi (id, daire, esasNo, kararNo, kararTarihi, belge_url)
    ve toplam kayıt sayısı. Tam metin için `id` -> `yargitay_karar_metni`.
    """
    istek = YargitayAramaIstegi(
        arananKelime=aranan_kelime,
        birimYrgHukukDaire=hukuk_dairesi,
        birimYrgCezaDaire=ceza_dairesi,
        birimYrgKurulDaire=kurul,
        esasYil=esas_yil,
        kararYil=karar_yil,
        baslangicTarihi=baslangic_tarihi,
        bitisTarihi=bitis_tarihi,
        siralama=siralama,
        siralamaDirection=yon,
        pageNumber=sayfa,
        pageSize=sayfa_boyutu,
    )
    yanit = await _client.ara(istek)
    return YargitayAramaSonucu(
        kararlar=yanit.data.data,
        toplam_kayit=yanit.data.recordsTotal,
        sayfa=sayfa,
        sayfa_boyutu=sayfa_boyutu,
    )


# --------------------------------------------------------------------------- 2
@mcp.tool()
async def yargitay_karar_metni(belge_id: str) -> YargitayKararMetni:
    """
    Verilen ID'ye sahip Yargıtay kararının tam metnini Markdown olarak getirir.
    `belge_id` değeri `yargitay_ara` sonuçlarındaki `id` alanından gelir.
    """
    return await _client.belge_getir(belge_id)


# --------------------------------------------------------------------------- 3
@mcp.tool()
async def yargitay_ara_ve_oku(
    aranan_kelime: str = "",
    hukuk_dairesi: str = "",
    ceza_dairesi: str = "",
    kurul: str = "",
    esas_yil: str = "",
    karar_yil: str = "",
    baslangic_tarihi: str = "",
    bitis_tarihi: str = "",
    kac_karar: int = 3,
) -> dict:
    """
    Tek çağrıda arama yapar ve en üstteki `kac_karar` kararın TAM METNİNİ getirir.
    Dilekçeye emsal toplarken pratiktir. `kac_karar` 1-10 arası tutulması önerilir
    (her metin ayrı bir HTTP isteğidir).
    """
    kac = max(1, min(kac_karar, 10))
    sonuc = await yargitay_ara(
        aranan_kelime=aranan_kelime,
        hukuk_dairesi=hukuk_dairesi,
        ceza_dairesi=ceza_dairesi,
        kurul=kurul,
        esas_yil=esas_yil,
        karar_yil=karar_yil,
        baslangic_tarihi=baslangic_tarihi,
        bitis_tarihi=bitis_tarihi,
        sayfa_boyutu=kac,
    )

    metinler: List[dict] = []
    for k in sonuc.kararlar[:kac]:
        try:
            m = await _client.belge_getir(k.id)
            metinler.append(
                {
                    "id": k.id,
                    "daire": k.daire,
                    "esasNo": k.esasNo,
                    "kararNo": k.kararNo,
                    "kararTarihi": k.kararTarihi,
                    "kaynak_url": m.kaynak_url,
                    "metin": m.markdown,
                }
            )
        except Exception as e:  # bir belge düşse de diğerleri gelsin
            metinler.append({"id": k.id, "hata": str(e)})

    return {"toplam_kayit": sonuc.toplam_kayit, "getirilen": len(metinler), "kararlar": metinler}


# --------------------------------------------------------------------------- 4
@mcp.tool()
def yargitay_daire_listesi() -> dict:
    """
    Arama filtrelerinde kullanılabilecek geçerli daire/kurul adlarını döndürür.
    (Site dropdown'ındaki değerlerle birebir kullanılmalıdır.)
    """
    hukuk = [f"{i}. Hukuk Dairesi" for i in range(1, 24)]
    ceza = [f"{i}. Ceza Dairesi" for i in range(1, 24)]
    kurullar = [
        "Hukuk Genel Kurulu",
        "Ceza Genel Kurulu",
        "Büyük Genel Kurulu",
        "Hukuk Daireleri Başkanlar Kurulu",
        "Ceza Daireleri Başkanlar Kurulu",
    ]
    return {"kurullar": kurullar, "hukuk_daireleri": hukuk, "ceza_daireleri": ceza}


if __name__ == "__main__":
    # Yerel test: stdio. fastmcp.app otomatik olarak `mcp` nesnesini bulur.
    mcp.run()

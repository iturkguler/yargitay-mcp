"""
Yargıtay Karar Arama API – Pydantic veri modelleri.

karararama.yargitay.gov.tr resmî sisteminin /aramadetaylist (POST) ve
/getDokuman (GET) uçlarının istek/yanıt şemalarını modeller.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# İSTEK (arama parametreleri)
# ---------------------------------------------------------------------------
class YargitayAramaIstegi(BaseModel):
    """
    /aramadetaylist gövdesindeki `data` nesnesi.

    Daire alanları üçe ayrılır; aynı anda yalnızca birini doldurun:
      * birimYrgKurulDaire  -> Kurullar  (örn. "Hukuk Genel Kurulu",
                                          "Ceza Genel Kurulu", "Büyük Genel Kurulu")
      * birimYrgHukukDaire  -> Hukuk Dairesi (örn. "1. Hukuk Dairesi",
                                              "11. Hukuk Dairesi")
      * birimYrgCezaDaire   -> Ceza Dairesi  (örn. "12. Ceza Dairesi")

    Boş bırakılan tüm alanlar tüm daireleri kapsar.
    """

    arananKelime: str = Field(
        "",
        description=(
            "Aranacak kelime/ifade. Gelişmiş operatörler desteklenir: "
            '"tam ifade" çift tırnak; AND/OR/NOT; +zorunlu -hariç; * joker.'
        ),
    )

    birimYrgKurulDaire: str = Field("", description="Yargıtay Kurulu (örn. 'Hukuk Genel Kurulu').")
    birimYrgHukukDaire: str = Field("", description="Hukuk Dairesi (örn. '11. Hukuk Dairesi').")
    birimYrgCezaDaire: str = Field("", description="Ceza Dairesi (örn. '12. Ceza Dairesi').")

    esasYil: str = Field("", description="Esas yılı (örn. '2024').")
    esasIlkSiraNo: str = Field("", description="Esas no başlangıç sıra.")
    esasSonSiraNo: str = Field("", description="Esas no bitiş sıra.")

    kararYil: str = Field("", description="Karar yılı (örn. '2025').")
    kararIlkSiraNo: str = Field("", description="Karar no başlangıç sıra.")
    kararSonSiraNo: str = Field("", description="Karar no bitiş sıra.")

    baslangicTarihi: str = Field("", description="Karar tarihi başlangıcı (GG.AA.YYYY).")
    bitisTarihi: str = Field("", description="Karar tarihi bitişi (GG.AA.YYYY).")

    # 1: Esas No, 2: Karar No, 3: Karar Tarihi
    siralama: str = Field("3", description="Sıralama ölçütü (1 Esas, 2 Karar, 3 Tarih).")
    siralamaDirection: str = Field("desc", description="Sıralama yönü ('asc'/'desc').")

    pageSize: int = Field(10, ge=1, le=100, description="Sayfa başına kayıt (1-100).")
    pageNumber: int = Field(1, ge=1, description="Sayfa numarası.")


# ---------------------------------------------------------------------------
# YANIT (arama listesi)
# ---------------------------------------------------------------------------
class YargitayKararOzeti(BaseModel):
    """Arama listesindeki tek bir karar satırı."""
    id: str
    daire: Optional[str] = None
    esasNo: Optional[str] = None
    kararNo: Optional[str] = None
    kararTarihi: Optional[str] = None
    arananKelime: Optional[str] = None
    belge_url: Optional[str] = Field(None, description="Karar metnine doğrudan bağlantı.")

    class Config:
        populate_by_name = True


class _IcVeri(BaseModel):
    data: List[YargitayKararOzeti] = []
    recordsTotal: int = 0
    recordsFiltered: int = 0


class YargitayAramaYaniti(BaseModel):
    data: _IcVeri


class YargitayAramaSonucu(BaseModel):
    """MCP aracının döndürdüğü derli toplu sonuç."""
    kararlar: List[YargitayKararOzeti]
    toplam_kayit: int
    sayfa: int
    sayfa_boyutu: int


# ---------------------------------------------------------------------------
# KARAR METNİ
# ---------------------------------------------------------------------------
class YargitayKararMetni(BaseModel):
    belge_id: str = Field(..., description="Kararın sistemdeki ID'si.")
    markdown: Optional[str] = Field(None, description="Markdown'a çevrilmiş karar metni.")
    kaynak_url: str = Field(..., description="Orijinal belge URL'si.")

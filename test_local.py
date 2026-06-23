"""
Çevrimdışı duman testi: gerçek API yerine sahte HTTP yanıtı kullanır.
Arama -> ayrıştırma -> belge HTML -> Markdown akışını doğrular.
"""
import asyncio
import json
import httpx

from yargitay_mcp.client import YargitayClient
from yargitay_mcp.models import YargitayAramaIstegi

# karararama.yargitay.gov.tr'nin gerçekte döndürdüğü şekle yakın sahte yanıtlar
SAHTE_ARAMA = {
    "data": {
        "data": [
            {
                "id": "abc123",
                "daire": "11. Hukuk Dairesi",
                "esasNo": "2023/4567",
                "kararNo": "2024/8910",
                "kararTarihi": "12.03.2024",
                "arananKelime": "haksız rekabet",
            }
        ],
        "recordsTotal": 1,
        "recordsFiltered": 1,
    }
}
SAHTE_BELGE = {
    "data": "<html><body><h1>11. HUKUK DAİRESİ</h1>"
            "<p>Esas No: 2023\\/4567</p><p>Karar metni \\r\\n burada.</p></body></html>"
}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/aramadetaylist":
        govde = json.loads(request.content)
        assert "data" in govde and "arananKelime" in govde["data"], "payload şekli yanlış"
        return httpx.Response(200, json=SAHTE_ARAMA)
    if request.url.path == "/getDokuman":
        return httpx.Response(200, json=SAHTE_BELGE)
    return httpx.Response(404)


async def main():
    c = YargitayClient()
    c._http = httpx.AsyncClient(
        base_url=c.BASE_URL,
        transport=httpx.MockTransport(handler),
    )

    # 1) arama
    yanit = await c.ara(YargitayAramaIstegi(arananKelime="haksız rekabet", birimYrgHukukDaire="11. Hukuk Dairesi"))
    k = yanit.data.data[0]
    assert yanit.data.recordsTotal == 1
    assert k.belge_url.endswith("/getDokuman?id=abc123"), k.belge_url
    print("[1] arama OK ->", k.daire, k.esasNo, k.kararNo, "| url:", k.belge_url)

    # 2) belge metni (HTML -> Markdown/metin)
    metin = await c.belge_getir("abc123")
    assert metin.markdown and "11. HUKUK" in metin.markdown.upper()
    assert "\\r\\n" not in metin.markdown, "\\r\\n kaçışı çözülmemiş"
    print("[2] belge OK -> metin uzunluğu:", len(metin.markdown))
    print("    önizleme:", repr(metin.markdown[:80]))

    await c.kapat()
    print("\nTÜM TESTLER GEÇTİ ✓")


asyncio.run(main())

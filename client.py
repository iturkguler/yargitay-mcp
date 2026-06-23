"""
Yargıtay Karar Arama – asenkron API istemcisi.

karararama.yargitay.gov.tr ile konuşur:
  * arama:        POST /aramadetaylist   (gövde: {"data": {...}})
  * belge metni:  GET  /getDokuman?id=…  (JSON; HTML "data" alanında)

Notlar:
- Site, tarayıcı dışı isteklerde bazen TLS zinciri/Referer kontrolü yapar;
  bu yüzden tarayıcı benzeri başlıklar gönderilir.
- HTML -> Markdown çevirisi `markitdown` varsa onunla, yoksa BeautifulSoup
  ile yapılır (sert bağımlılık değil).
"""
from __future__ import annotations

import html
import logging
import re
import os
from typing import Optional

import httpx

from .models import (
    YargitayAramaIstegi,
    YargitayAramaYaniti,
    YargitayKararMetni,
)

logger = logging.getLogger("yargitay_mcp.client")


class YargitayClient:
    BASE_URL = "https://karararama.yargitay.gov.tr"
    ARAMA_UCU = "/aramadetaylist"
    BELGE_UCU = "/getDokuman"

    def __init__(self, timeout: float = 60.0, verify_tls: bool = True,
                 proxy: Optional[str] = None):
        # Türkiye çıkışlı proxy. Ayarlanırsa tüm istekler buradan geçer.
        # Horizon'da YARGITAY_PROXY env değişkeni ile verilir:
        #   http://kullanici:parola@host:port   veya   http://host:port
        proxy = proxy or os.getenv("YARGITAY_PROXY") or None
        if proxy:
            logger.info("Proxy üzerinden bağlanılacak: %s", proxy.split("@")[-1])

        self._http = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.BASE_URL}/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
            },
            timeout=timeout,
            verify=verify_tls,
            proxy=proxy,
        )

    # ------------------------------------------------------------------ arama
    async def ara(self, istek: YargitayAramaIstegi) -> YargitayAramaYaniti:
        govde = {"data": istek.model_dump(by_alias=True)}
        logger.info("Yargıtay araması: %s", govde["data"].get("arananKelime") or "(filtre)")

        resp = await self._http.post(self.ARAMA_UCU, json=govde)
        resp.raise_for_status()
        yanit = YargitayAramaYaniti(**resp.json())

        for k in yanit.data.data:
            k.belge_url = f"{self.BASE_URL}{self.BELGE_UCU}?id={k.id}"
        return yanit

    # ------------------------------------------------------------ belge metni
    async def belge_getir(self, belge_id: str) -> YargitayKararMetni:
        kaynak = f"{self.BASE_URL}{self.BELGE_UCU}?id={belge_id}"
        resp = await self._http.get(f"{self.BELGE_UCU}?id={belge_id}")
        resp.raise_for_status()

        ham = resp.json().get("data")
        if not isinstance(ham, str):
            raise ValueError("Belge yanıtında HTML 'data' alanı bulunamadı.")

        return YargitayKararMetni(
            belge_id=belge_id,
            markdown=self._html_to_markdown(ham),
            kaynak_url=kaynak,
        )

    # --------------------------------------------------------------- yardımcı
    @staticmethod
    def _html_to_markdown(raw: str) -> Optional[str]:
        if not raw:
            return None
        # API kaçışlı HTML döndürür; normalize et.
        s = html.unescape(raw)
        s = s.replace('\\"', '"').replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")

        # 1) markitdown (en temiz çıktı) varsa
        try:
            import tempfile, os
            from markitdown import MarkItDown

            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(s)
                path = f.name
            try:
                return MarkItDown(enable_plugins=False).convert(path).text_content
            finally:
                os.remove(path)
        except Exception as e:  # markitdown yoksa/başarısızsa düş
            logger.debug("markitdown yok/başarısız, BeautifulSoup'a düşülüyor: %s", e)

        # 2) BeautifulSoup ile sade metin
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(s, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text("\n")
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()
        except Exception as e:
            logger.warning("HTML çevrimi başarısız: %s", e)
            return s  # son çare: ham normalize HTML

    async def kapat(self):
        await self._http.aclose()

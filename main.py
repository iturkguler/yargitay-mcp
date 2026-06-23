"""
fastmcp.app / FastMCP Cloud giriş noktası.

Deploy sırasında "entrypoint" olarak şunu ver:   main.py:mcp

Bu dosya yalnızca paket içindeki sunucuyu dışarı açar; tüm mantık
yargitay_mcp/ klasöründedir.
"""
from yargitay_mcp.server import mcp

__all__ = ["mcp"]

if __name__ == "__main__":
    mcp.run()

"""
Verifica la version de protocolo MCP que fastmcp.Client negocia
con tu servidor, usando mode="auto" (el default de FastMCP 4),
que intenta primero la era moderna (2026-07-28) y cae a la era
legacy (handshake) si el servidor o transporte no la soporta.

Uso:
    python check_protocol_final.py ruta_a_tu_servidor.py
"""
import asyncio
import sys
from pathlib import Path
from fastmcp import Client

async def main():
    if len(sys.argv) < 2:
        print("Uso: python check_protocol_final.py <servidor.py>")
        return

    target = Path(sys.argv[1])

    print("--- Conectando en mode='auto' (default FastMCP 4) ---")
    async with Client(target, mode="auto") as client:
        print("Version de protocolo negociada:", client.protocol_version)
        print("Info del servidor:", client.server_info)
        print("Capacidades del servidor:", client.server_capabilities)

    print()
    print("--- Conectando en mode='legacy' (forzado) ---")
    async with Client(target, mode="legacy") as client:
        print("Version de protocolo negociada:", client.protocol_version)
        print("Info del servidor:", client.server_info)

if __name__ == "__main__":
    asyncio.run(main())
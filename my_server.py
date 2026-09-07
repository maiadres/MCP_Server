import json
import os
from PyPDF2 import PdfReader
from fastmcp import FastMCP


mcp = FastMCP("My MCP Server")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"
# Basic dynamic resource returning a string
@mcp.resource("resource://greeting")
def get_greeting() -> str:
    """Provides a simple greeting message."""
    return "Hello from FastMCP Resources!"

# Resource returning JSON data
@mcp.resource("data://config")
def get_config() -> str:
    """Provides application configuration as JSON."""
    return json.dumps({
        "theme": "dark",
        "version": "1.2.0",
        "features": ["tools", "resources"],
    })
@mcp.resource("estudios://fasta/maestria/plan")
def obtener_plan_estudios() -> str:
    """Recurso estático: Plan de estudios de la Maestría en Ciberseguridad e Informática Forense."""
    ruta_pdf = "C:/Users/famil/Downloads/Maia/MCP-1/Plan_de_estudios_2023-_Ingenieria-Online (1).pdf" 
    
    if not os.path.exists(ruta_pdf):
        return "Error: El archivo PDF del plan de estudios no se encontró en el servidor."
        
    try:
        lector_pdf = PdfReader(ruta_pdf)
        texto_extraido = "Plan de Estudios - Maestria\n\n"
        
        # Iteramos sobre todas las páginas para extraer el texto
        for pagina in lector_pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_extraido += texto + "\n"
                
        return texto_extraido
        
    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}"
    
@mcp.resource("estudios://fcad-uner/sistemas/plan")
def obtener_plan_estudios() -> str:
    """Recurso estático: Plan de estudios de la Licenciatura en Sistemas."""
    ruta_pdf = "C:/Users/famil/Downloads/Maia/MCP-1/Sistemas.pdf" 
    if not os.path.exists(ruta_pdf):
        return "Error: El archivo PDF del plan de estudios no se encontró en el servidor."
        
    try:
        lector_pdf = PdfReader(ruta_pdf)
        texto_extraido = "Plan de Estudios - Sistemas\n\n"
        
        # Iteramos sobre todas las páginas para extraer el texto
        for pagina in lector_pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_extraido += texto + "\n"
        texto_limpio = texto_extraido.replace(".smcp", "").replace("/", "")       
        return texto_limpio
        
    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}"

@mcp.resource("estudios://fcad-uner/sistemas/digesto")
def obtener_plan_estudios() -> str:
    """Recurso estático: Plan de estudios de la Licenciatura en Sistemas."""
    ruta_pdf = "C:/Users/famil/Downloads/Maia/MCP-1/_CS_Nº_195_11_Anexo_II.pdf" 
   
    if not os.path.exists(ruta_pdf):
        return "Error: El archivo PDF del plan de estudios no se encontró en el servidor."
        
    try:
        lector_pdf = PdfReader(ruta_pdf)
        texto_extraido = "Plan de Estudios - Sistemas\n\n"
        
        # Iteramos sobre todas las páginas para extraer el texto
        for pagina in lector_pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_extraido += texto + "\n"
                
        return texto_extraido
        
    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}"





if __name__ == "__main__":
    mcp.run()

from pathlib import Path


def buscar_carpeta(nombre: str) -> Path:
    """Sube desde este archivo hasta encontrar una carpeta con ese nombre."""
    aqui = Path(__file__).resolve()
    for carpeta in aqui.parents:
        candidata = carpeta / nombre
        if candidata.is_dir():
            return candidata
    return aqui.parent / nombre


ASSETS = buscar_carpeta("assets")
LOGS = buscar_carpeta("logs")
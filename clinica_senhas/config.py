from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "clinic.db"
TEMPO_MEDIO_PADRAO_MINUTOS = 30
ALTERNANCIA_PREFERENCIAIS = 3
INTERVALO_RECHAMADA_SEGUNDOS = 30
SEQUENCIA_INICIAL = 1

ESPECIALIDADES_PADRAO = {
    "CG": "Clínico Geral",
    "PSI": "Psicologia",
    "PED": "Pediatria",
    "GIN": "Ginecologia",
    "CAR": "Cardiologia",
    "PQT": "Psiquiatria",
}

PRIORIDADES_PESO = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6}

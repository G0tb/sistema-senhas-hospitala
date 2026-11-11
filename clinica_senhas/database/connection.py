from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "clinic.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS especialidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    codigo TEXT NOT NULL COLLATE NOCASE UNIQUE,
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    tempo_medio INTEGER NOT NULL DEFAULT 30 CHECK (tempo_medio > 0)
);

CREATE TABLE IF NOT EXISTS consultorios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS profissionais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    registro TEXT NOT NULL UNIQUE,
    especialidade_id INTEGER NOT NULL,
    consultorio_id INTEGER NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    FOREIGN KEY (especialidade_id) REFERENCES especialidades(id),
    FOREIGN KEY (consultorio_id) REFERENCES consultorios(id)
);

CREATE TABLE IF NOT EXISTS senhas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL,
    especialidade_id INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('N', 'P')),
    prioridade TEXT CHECK (prioridade IS NULL OR prioridade IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')),
    criada_em TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Aguardando'
        CHECK (status IN ('Aguardando', 'Chamando', 'Em atendimento', 'Finalizada', 'Ausente', 'Cancelada')),
    FOREIGN KEY (especialidade_id) REFERENCES especialidades(id),
    CHECK ((tipo = 'N' AND prioridade IS NULL) OR (tipo = 'P' AND prioridade IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_senhas_fila
    ON senhas(especialidade_id, status, prioridade, criada_em);

CREATE TABLE IF NOT EXISTS atendimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    senha_id INTEGER NOT NULL,
    profissional_id INTEGER NOT NULL,
    inicio TEXT NOT NULL,
    fim TEXT,
    resultado TEXT,
    FOREIGN KEY (senha_id) REFERENCES senhas(id),
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    UNIQUE (senha_id)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL CHECK (perfil IN ('Administrador', 'Recepção', 'Profissional', 'Coordenação')),
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Mantém a regra de negócio mesmo se alguém gravar diretamente via SQL.
CREATE TRIGGER IF NOT EXISTS trg_limite_profissionais_insert
BEFORE INSERT ON profissionais
WHEN NEW.ativo = 1 AND (
    SELECT COUNT(*) FROM profissionais
    WHERE especialidade_id = NEW.especialidade_id AND ativo = 1
) >= 3
BEGIN
    SELECT RAISE(ABORT, 'Uma especialidade pode ter no máximo 3 profissionais ativos');
END;

CREATE TRIGGER IF NOT EXISTS trg_limite_profissionais_update
BEFORE UPDATE OF especialidade_id, ativo ON profissionais
WHEN NEW.ativo = 1 AND (
    SELECT COUNT(*) FROM profissionais
    WHERE especialidade_id = NEW.especialidade_id AND ativo = 1 AND id <> OLD.id
) >= 3
BEGIN
    SELECT RAISE(ABORT, 'Uma especialidade pode ter no máximo 3 profissionais ativos');
END;
"""

SPECIALTIES = (
    ("Clínico geral", "CG"),
    ("Psicologia", "PSI"),
    ("Pediatria", "PED"),
    ("Ginecologia", "GIN"),
    ("Cardiologia", "CAR"),
    ("Psiquiatria", "PQT"),
)

DEFAULT_SETTINGS = {
    "tempo_medio_padrao": "30",
    "alternancia_normal_preferencial": "3",
    "intervalo_rechamada_segundos": "30",
    "sequencia_diaria": "1",
}


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


class Database:

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.connection = connect(db_path)

    def initialize(self, seed: bool = True) -> None:
        self.connection.executescript(SCHEMA_SQL)
        if seed:
            self.seed()
        self.connection.commit()

    def seed(self) -> None:
        for nome, codigo in SPECIALTIES:
            self.connection.execute(
                "INSERT OR IGNORE INTO especialidades (nome, codigo) VALUES (?, ?)",
                (nome, codigo),
            )

        for index in range(1, 19):
            self.connection.execute(
                "INSERT OR IGNORE INTO consultorios (numero, descricao) VALUES (?, ?)",
                (f"{index:02d}", f"Consultório {index:02d}"),
            )
        for chave, valor in DEFAULT_SETTINGS.items():
            self.connection.execute(
                "INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)",
                (chave, valor),
            )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            self.connection.rollback()
        self.close()


@contextmanager
def transaction(db_path: str | Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    db = Database(db_path)
    try:
        db.initialize()
        yield db.connection
        db.connection.commit()
    except Exception:
        db.connection.rollback()
        raise
    finally:
        db.close()


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH, seed: bool = True) -> None:
    db = Database(db_path)
    try:
        db.initialize(seed=seed)
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Banco inicializado em: {DEFAULT_DB_PATH}")

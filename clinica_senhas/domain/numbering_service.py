from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import Prioridade, Senha, TipoSenha
from database.repositories import SenhaRepository
try:
    from .priority_service import PriorityService
except ImportError:
    from domain.priority_service import PriorityService


class NumberingService:

    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
        self.senhas = SenhaRepository(connection)

    def proximo_numero(self, codigo_especialidade: str, quando: Optional[date] = None) -> int:
        codigo = codigo_especialidade.strip().upper()
        dia = (quando or date.today()).isoformat()
        row = self.db.execute(
            """SELECT COALESCE(MAX(CAST(SUBSTR(codigo, INSTR(codigo, '-') + 3) AS INTEGER)), 0) AS ultimo
               FROM senhas WHERE codigo LIKE ? AND criada_em LIKE ?""",
            (f"{codigo}-%", f"{dia}%"),
        ).fetchone()
        return int(row["ultimo"]) + 1

    def emitir(self, especialidade_id: int, codigo_especialidade: str,
               tipo: TipoSenha | str, prioridade: Prioridade | str | None = None,
               agora: Optional[datetime] = None) -> Senha:

        prioridade_obj = PriorityService.normalizar_prioridade(prioridade) if prioridade is not None else None
        PriorityService.validar(tipo_obj, prioridade_obj)
        instante = agora or datetime.now()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            numero = self.proximo_numero(codigo_especialidade, instante.date())
            senha = Senha(
                codigo=f"{codigo_especialidade.strip().upper()}-{tipo_obj.value}-{numero:03d}",
                especialidade_id=especialidade_id,
                tipo=tipo_obj,
                prioridade=prioridade_obj,
                criada_em=instante.isoformat(timespec="seconds"),
            )
            self.senhas.create(senha)
            self.db.commit()
            return senha
        except Exception:
            self.db.rollback()
            raise


if __name__ == "__main__":
    from database.connection import Database
    with Database(":memory:") as database:
        especialidade_id = database.connection.execute("SELECT id FROM especialidades WHERE codigo='CG'").fetchone()[0]
        service = NumberingService(database.connection)
        print(service.emitir(especialidade_id, "CG", "P", "P1").codigo)
        print(service.emitir(especialidade_id, "CG", "N").codigo)

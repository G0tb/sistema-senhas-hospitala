from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass
class MetricsResult:
    atendimentos_finalizados: int = 0
    media_geral_minutos: Optional[float] = None
    media_por_especialidade: dict[str, float] = field(default_factory=dict)


class MetricsService:

    def __init__(self, connection: sqlite3.Connection):
        self.db = connection

    @staticmethod
    def _minutes(inicio: str, fim: str) -> float:
        return (datetime.fromisoformat(fim) - datetime.fromisoformat(inicio)).total_seconds() / 60

    def calcular(self, especialidade_id: Optional[int] = None) -> MetricsResult:
        sql = """SELECT a.inicio, a.fim, e.codigo
                 FROM atendimentos a
                 JOIN senhas s ON s.id = a.senha_id
                 JOIN especialidades e ON e.id = s.especialidade_id
                 WHERE s.status = 'Finalizada' AND a.fim IS NOT NULL"""
        params: list[object] = []
        if especialidade_id is not None:
            sql += " AND s.especialidade_id = ?"
            params.append(especialidade_id)
        duracoes: list[tuple[str, float]] = []
        for row in self.db.execute(sql, params):
            try:
                duracao = self._minutes(row["inicio"], row["fim"])
                if duracao >= 0:
                    duracoes.append((row["codigo"], duracao))
            except (TypeError, ValueError):
                continue
        result = MetricsResult(atendimentos_finalizados=len(duracoes))
        if duracoes:
            result.media_geral_minutos = round(sum(d for _, d in duracoes) / len(duracoes), 2)
            grupos: dict[str, list[float]] = {}
            for codigo, duracao in duracoes:
                grupos.setdefault(codigo, []).append(duracao)
            result.media_por_especialidade = {codigo: round(sum(vals) / len(vals), 2) for codigo, vals in grupos.items()}
        return result


if __name__ == "__main__":
    from database.connection import Database
    with Database(":memory:") as database:
        result = MetricsService(database.connection).calcular()
        print(f"Atendimentos finalizados: {result.atendimentos_finalizados}")
        print(f"Média geral: {result.media_geral_minutos or 0:.2f} min")

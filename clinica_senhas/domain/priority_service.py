from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import PRIORIDADES_PESO
from database.models import Prioridade, TipoSenha


@dataclass(frozen=True)
class CategoriaPrioridade:
    codigo: Prioridade
    descricao: str
    peso: int


class PriorityService:

    CATEGORIAS = {
        Prioridade.P1: "Idoso com 80 anos ou mais",
        Prioridade.P2: "Idoso abaixo de 80 anos",
        Prioridade.P3: "Pessoa com deficiência (PCD)",
        Prioridade.P4: "Gestante",
        Prioridade.P5: "Pessoa obesa",
        Prioridade.P6: "Criança de colo",
    }

    @classmethod
    def validar(cls, tipo: TipoSenha | str, prioridade: Optional[Prioridade | str] = None) -> None:
        tipo = cls.validar_tipo(tipo)
        prioridade_obj = cls.normalizar_prioridade(prioridade) if prioridade is not None else None
        if tipo == TipoSenha.NORMAL and prioridade_obj is not None:
            raise ValueError("Senha normal não pode possuir prioridade")
        if tipo == TipoSenha.PREFERENCIAL and prioridade_obj is None:
            raise ValueError("Senha preferencial exige uma prioridade P1 a P6")

    @staticmethod
    def validar_tipo(tipo: TipoSenha | str) -> TipoSenha:
        try:
            return tipo if isinstance(tipo, TipoSenha) else TipoSenha(str(tipo).upper())
        except ValueError as exc:
            raise ValueError("Tipo inválido: use N (normal) ou P (preferencial)") from exc

    @staticmethod
    def normalizar_prioridade(prioridade: Prioridade | str) -> Prioridade:
        try:
            return prioridade if isinstance(prioridade, Prioridade) else Prioridade(str(prioridade).upper())
        except ValueError as exc:
            raise ValueError("Prioridade inválida: use P1, P2, P3, P4, P5 ou P6") from exc

    @classmethod
    def peso(cls, prioridade: Prioridade | str | None) -> int:
        return 99 if prioridade is None else PRIORIDADES_PESO[cls.normalizar_prioridade(prioridade).value]

    @classmethod
    def categorias(cls) -> list[CategoriaPrioridade]:
        return [CategoriaPrioridade(codigo, descricao, cls.peso(codigo)) for codigo, descricao in cls.CATEGORIAS.items()]


if __name__ == "__main__":
    print("Categorias de prioridade:")
    for categoria in PriorityService.categorias():
        print(f"{categoria.codigo.value}: {categoria.descricao} (peso {categoria.peso})")
    PriorityService.validar("P", "P1")
    print("Validação rápida: OK")

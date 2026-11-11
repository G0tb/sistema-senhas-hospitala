from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TipoSenha(str, Enum):
    NORMAL = "N"
    PREFERENCIAL = "P"


class Prioridade(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"
    P6 = "P6"


class StatusSenha(str, Enum):
    AGUARDANDO = "Aguardando"
    CHAMANDO = "Chamando"
    EM_ATENDIMENTO = "Em atendimento"
    FINALIZADA = "Finalizada"
    AUSENTE = "Ausente"
    CANCELADA = "Cancelada"


class PerfilUsuario(str, Enum):
    ADMINISTRADOR = "Administrador"
    RECEPCAO = "Recepção"
    PROFISSIONAL = "Profissional"
    COORDENACAO = "Coordenação"


@dataclass
class Especialidade:
    id: Optional[int] = None
    nome: str = ""
    codigo: str = ""
    ativo: bool = True
    tempo_medio: int = 30


@dataclass
class Consultorio:
    id: Optional[int] = None
    numero: str = ""
    descricao: Optional[str] = None
    ativo: bool = True


@dataclass
class Profissional:
    id: Optional[int] = None
    nome: str = ""
    registro: str = ""
    especialidade_id: int = 0
    consultorio_id: int = 0
    ativo: bool = True


@dataclass
class Senha:
    id: Optional[int] = None
    codigo: str = ""
    especialidade_id: int = 0
    tipo: TipoSenha = TipoSenha.NORMAL
    prioridade: Optional[Prioridade] = None
    criada_em: str = ""
    status: StatusSenha = StatusSenha.AGUARDANDO

    @classmethod
    def nova(cls, codigo: str, especialidade_id: int, tipo: TipoSenha,
             prioridade: Optional[Prioridade] = None) -> "Senha":
        if tipo == TipoSenha.NORMAL and prioridade is not None:
            raise ValueError("Senha normal não pode ter prioridade")
        if tipo == TipoSenha.PREFERENCIAL and prioridade is None:
            raise ValueError("Senha preferencial exige uma prioridade")
        return cls(codigo=codigo, especialidade_id=especialidade_id, tipo=tipo,
                   prioridade=prioridade, criada_em=datetime.now().isoformat(timespec="seconds"))


@dataclass
class Atendimento:
    id: Optional[int] = None
    senha_id: int = 0
    profissional_id: int = 0
    inicio: str = ""
    fim: Optional[str] = None
    resultado: Optional[str] = None


@dataclass
class Usuario:
    id: Optional[int] = None
    login: str = ""
    senha_hash: str = ""
    perfil: PerfilUsuario = PerfilUsuario.RECEPCAO
    ativo: bool = True


@dataclass
class Configuracao:
    chave: str = ""
    valor: str = ""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ALTERNANCIA_PREFERENCIAIS
from database.models import Atendimento, Senha, StatusSenha
from database.repositories import AtendimentoRepository, ConfiguracaoRepository, ProfissionalRepository, SenhaRepository
try:
    from .priority_service import PriorityService
except ImportError:
    from domain.priority_service import PriorityService


class QueueService:

    TRANSITIONS = {
        StatusSenha.AGUARDANDO: {StatusSenha.CHAMANDO, StatusSenha.CANCELADA},
        StatusSenha.CHAMANDO: {StatusSenha.EM_ATENDIMENTO, StatusSenha.AUSENTE, StatusSenha.CANCELADA, StatusSenha.CHAMANDO},
        StatusSenha.EM_ATENDIMENTO: {StatusSenha.FINALIZADA, StatusSenha.CANCELADA},
        StatusSenha.AUSENTE: {StatusSenha.CHAMANDO, StatusSenha.CANCELADA},
        StatusSenha.FINALIZADA: set(),
        StatusSenha.CANCELADA: set(),
    }

    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
        self.senhas = SenhaRepository(connection)
        self.atendimentos = AtendimentoRepository(connection)
        self.profissionais = ProfissionalRepository(connection)
        self.config = ConfiguracaoRepository(connection)

    def proxima(self, especialidade_id: int) -> Optional[Senha]:
        aguardando = self.senhas.list_waiting(especialidade_id)
        if not aguardando:
            return None
        preferenciais = [s for s in aguardando if s.prioridade is not None]
        normais = [s for s in aguardando if s.prioridade is None]
        preferenciais.sort(key=lambda s: (PriorityService.peso(s.prioridade), s.criada_em, s.id or 0))
        normais.sort(key=lambda s: (s.criada_em, s.id or 0))
        limite = int(self.config.get("alternancia_normal_preferencial", str(ALTERNANCIA_PREFERENCIAIS)) or ALTERNANCIA_PREFERENCIAIS)
        chave_alternancia = f"preferenciais_desde_normal:{especialidade_id}"
        preferenciais_desde_normal = int(self.config.get(chave_alternancia, "0") or 0)
        if normais and (not preferenciais or preferenciais_desde_normal >= limite):
            return normais[0]
        return preferenciais[0] if preferenciais else normais[0]

    def chamar_proxima(self, especialidade_id: int) -> Optional[Senha]:
        senha = self.proxima(especialidade_id)
        if senha is None:
            return None
        chave_alternancia = f"preferenciais_desde_normal:{especialidade_id}"
        if senha.prioridade is None:
            self.config.set(chave_alternancia, "0")
        else:
            atual = int(self.config.get(chave_alternancia, "0") or 0)
            self.config.set(chave_alternancia, str(atual + 1))
        self.transicionar(senha.id, StatusSenha.CHAMANDO)
        return self.senhas.get(senha.id)

    def transicionar(self, senha_id: int, novo_status: StatusSenha) -> Senha:
        senha = self.senhas.get(senha_id)
        if senha is None:
            raise ValueError("Senha não encontrada")
        if novo_status not in self.TRANSITIONS[senha.status]:
            raise ValueError(f"Transição inválida: {senha.status.value} -> {novo_status.value}")
        self.senhas.update_status(senha_id, novo_status)
        result = self.senhas.get(senha_id)
        if result is None:
            raise RuntimeError("Senha desapareceu durante a transição")
        return result

    def iniciar_atendimento(self, senha_id: int, profissional_id: int) -> Atendimento:
        senha = self.senhas.get(senha_id)
        if senha is None or senha.status != StatusSenha.CHAMANDO:
            raise ValueError("Somente uma senha Chamando pode iniciar atendimento")
        profissional = self.profissionais.get(profissional_id)
        if profissional is None or not profissional.ativo or profissional.especialidade_id != senha.especialidade_id:
            raise ValueError("Profissional inválido, inativo ou de outra especialidade")
        self.transicionar(senha_id, StatusSenha.EM_ATENDIMENTO)
        return self.atendimentos.create(Atendimento(senha_id=senha_id, profissional_id=profissional_id, inicio=datetime.now().isoformat(timespec="seconds")))

    def finalizar_atendimento(self, atendimento_id: int, resultado: Optional[str] = None) -> None:
        atendimento = self.atendimentos.get(atendimento_id)
        if atendimento is None:
            raise ValueError("Atendimento não encontrado")
        senha = self.senhas.get(atendimento.senha_id)
        if senha is None or senha.status != StatusSenha.EM_ATENDIMENTO:
            raise ValueError("A senha não está em atendimento")
        self.atendimentos.finish(atendimento_id, resultado)
        self.transicionar(senha.id, StatusSenha.FINALIZADA)

    def marcar_ausente(self, senha_id: int) -> Senha:
        return self.transicionar(senha_id, StatusSenha.AUSENTE)

    def cancelar(self, senha_id: int) -> Senha:
        senha = self.senhas.get(senha_id)
        if senha is None or senha.status not in {StatusSenha.AGUARDANDO, StatusSenha.CHAMANDO, StatusSenha.EM_ATENDIMENTO, StatusSenha.AUSENTE}:
            raise ValueError("Senha não pode ser cancelada neste estado")
        return self.transicionar(senha_id, StatusSenha.CANCELADA)


if __name__ == "__main__":
    from database.connection import Database
    with Database(":memory:") as database:
        row = database.connection.execute("SELECT id FROM especialidades WHERE codigo='CG'").fetchone()
        print(f"Fila pronta para a especialidade id={row['id']}")

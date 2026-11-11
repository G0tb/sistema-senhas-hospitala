from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime
from typing import Any, Iterable, Optional, TypeVar

from .models import (
    Atendimento, Configuracao, Consultorio, Especialidade, PerfilUsuario,
    Prioridade, Profissional, Senha, StatusSenha, TipoSenha, Usuario,
)

T = TypeVar("T")


def _bool(value: Any) -> bool:
    return bool(value)


def _require(value: Any, label: str) -> None:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{label} é obrigatório")


class BaseRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection

    def _commit(self) -> None:
        self.db.commit()


class EspecialidadeRepository(BaseRepository):
    def create(self, item: Especialidade) -> Especialidade:
        _require(item.nome, "Nome")
        _require(item.codigo, "Código")
        cur = self.db.execute(
            "INSERT INTO especialidades (nome, codigo, ativo, tempo_medio) VALUES (?, ?, ?, ?)",
            (item.nome.strip(), item.codigo.strip().upper(), int(item.ativo), item.tempo_medio),
        )
        self._commit(); item.id = cur.lastrowid; return item

    def get(self, item_id: int) -> Optional[Especialidade]:
        row = self.db.execute("SELECT * FROM especialidades WHERE id = ?", (item_id,)).fetchone()
        return self._from_row(row) if row else None

    def list(self, only_active: bool = False) -> list[Especialidade]:
        sql = "SELECT * FROM especialidades" + (" WHERE ativo = 1" if only_active else "") + " ORDER BY nome"
        return [self._from_row(r) for r in self.db.execute(sql)]

    def update(self, item: Especialidade) -> Especialidade:
        if item.id is None: raise ValueError("Especialidade sem id")
        _require(item.nome, "Nome"); _require(item.codigo, "Código")
        self.db.execute("UPDATE especialidades SET nome=?, codigo=?, ativo=?, tempo_medio=? WHERE id=?",
                        (item.nome.strip(), item.codigo.strip().upper(), int(item.ativo), item.tempo_medio, item.id))
        self._commit(); return item

    def _from_row(self, r: sqlite3.Row) -> Especialidade:
        return Especialidade(r["id"], r["nome"], r["codigo"], _bool(r["ativo"]), r["tempo_medio"])


class ConsultorioRepository(BaseRepository):
    def create(self, item: Consultorio) -> Consultorio:
        _require(item.numero, "Número")
        cur = self.db.execute("INSERT INTO consultorios (numero, descricao, ativo) VALUES (?, ?, ?)",
                              (item.numero.strip(), item.descricao, int(item.ativo)))
        self._commit(); item.id = cur.lastrowid; return item

    def get(self, item_id: int) -> Optional[Consultorio]:
        r = self.db.execute("SELECT * FROM consultorios WHERE id=?", (item_id,)).fetchone()
        return self._from_row(r) if r else None

    def list(self, only_active: bool = False) -> list[Consultorio]:
        sql = "SELECT * FROM consultorios" + (" WHERE ativo=1" if only_active else "") + " ORDER BY numero"
        return [self._from_row(r) for r in self.db.execute(sql)]

    def update(self, item: Consultorio) -> Consultorio:
        if item.id is None: raise ValueError("Consultório sem id")
        _require(item.numero, "Número")
        self.db.execute("UPDATE consultorios SET numero=?, descricao=?, ativo=? WHERE id=?",
                        (item.numero.strip(), item.descricao, int(item.ativo), item.id))
        self._commit(); return item

    @staticmethod
    def _from_row(r: sqlite3.Row) -> Consultorio:
        return Consultorio(r["id"], r["numero"], r["descricao"], _bool(r["ativo"]))


class ProfissionalRepository(BaseRepository):
    def create(self, item: Profissional) -> Profissional:
        _require(item.nome, "Nome"); _require(item.registro, "Registro")
        try:
            cur = self.db.execute("INSERT INTO profissionais (nome, registro, especialidade_id, consultorio_id, ativo) VALUES (?, ?, ?, ?, ?)",
                                  (item.nome.strip(), item.registro.strip(), item.especialidade_id, item.consultorio_id, int(item.ativo)))
            self._commit(); item.id = cur.lastrowid; return item
        except sqlite3.IntegrityError as exc:
            if "máximo de 3" in str(exc): raise ValueError(str(exc)) from exc
            raise ValueError(f"Não foi possível cadastrar profissional: {exc}") from exc

    def get(self, item_id: int) -> Optional[Profissional]:
        r = self.db.execute("SELECT * FROM profissionais WHERE id=?", (item_id,)).fetchone()
        return self._from_row(r) if r else None

    def list(self, especialidade_id: Optional[int] = None, only_active: bool = False) -> list[Profissional]:
        clauses, params = [], []
        if especialidade_id is not None: clauses.append("especialidade_id=?"); params.append(especialidade_id)
        if only_active: clauses.append("ativo=1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        return [self._from_row(r) for r in self.db.execute("SELECT * FROM profissionais" + where + " ORDER BY nome", params)]

    def update(self, item: Profissional) -> Profissional:
        if item.id is None: raise ValueError("Profissional sem id")
        _require(item.nome, "Nome"); _require(item.registro, "Registro")
        try:
            self.db.execute("UPDATE profissionais SET nome=?, registro=?, especialidade_id=?, consultorio_id=?, ativo=? WHERE id=?",
                            (item.nome.strip(), item.registro.strip(), item.especialidade_id, item.consultorio_id, int(item.ativo), item.id))
            self._commit(); return item
        except sqlite3.IntegrityError as exc:
            raise ValueError(str(exc)) from exc

    @staticmethod
    def _from_row(r: sqlite3.Row) -> Profissional:
        return Profissional(r["id"], r["nome"], r["registro"], r["especialidade_id"], r["consultorio_id"], _bool(r["ativo"]))


class SenhaRepository(BaseRepository):
    def create(self, item: Senha) -> Senha:
        _require(item.codigo, "Código"); _require(item.criada_em, "Data de criação")
        if item.tipo == TipoSenha.NORMAL and item.prioridade is not None: raise ValueError("Senha normal não pode ter prioridade")
        if item.tipo == TipoSenha.PREFERENCIAL and item.prioridade is None: raise ValueError("Senha preferencial exige prioridade")
        cur = self.db.execute("INSERT INTO senhas (codigo, especialidade_id, tipo, prioridade, criada_em, status) VALUES (?, ?, ?, ?, ?, ?)",
                              (item.codigo, item.especialidade_id, item.tipo.value, item.prioridade.value if item.prioridade else None, item.criada_em, item.status.value))
        self._commit(); item.id = cur.lastrowid; return item

    def get(self, item_id: int) -> Optional[Senha]:
        r = self.db.execute("SELECT * FROM senhas WHERE id=?", (item_id,)).fetchone()
        return self._from_row(r) if r else None

    def list_waiting(self, especialidade_id: int) -> list[Senha]:
        rows = self.db.execute("""SELECT * FROM senhas WHERE especialidade_id=? AND status='Aguardando'
            ORDER BY CASE WHEN prioridade IS NULL THEN 99 ELSE CAST(SUBSTR(prioridade, 2) AS INTEGER) END, criada_em, id""", (especialidade_id,))
        return [self._from_row(r) for r in rows]

    def update_status(self, item_id: int, status: StatusSenha) -> None:
        self.db.execute("UPDATE senhas SET status=? WHERE id=?", (status.value, item_id)); self._commit()

    @staticmethod
    def _from_row(r: sqlite3.Row) -> Senha:
        return Senha(r["id"], r["codigo"], r["especialidade_id"], TipoSenha(r["tipo"]), Prioridade(r["prioridade"]) if r["prioridade"] else None, r["criada_em"], StatusSenha(r["status"]))


class AtendimentoRepository(BaseRepository):
    def create(self, item: Atendimento) -> Atendimento:
        _require(item.inicio, "Início")
        cur = self.db.execute("INSERT INTO atendimentos (senha_id, profissional_id, inicio, fim, resultado) VALUES (?, ?, ?, ?, ?)",
                              (item.senha_id, item.profissional_id, item.inicio, item.fim, item.resultado))
        self._commit(); item.id = cur.lastrowid; return item

    def get(self, item_id: int) -> Optional[Atendimento]:
        r = self.db.execute("SELECT * FROM atendimentos WHERE id=?", (item_id,)).fetchone()
        return Atendimento(r["id"], r["senha_id"], r["profissional_id"], r["inicio"], r["fim"], r["resultado"]) if r else None

    def finish(self, item_id: int, resultado: Optional[str] = None, fim: Optional[str] = None) -> None:
        self.db.execute("UPDATE atendimentos SET fim=?, resultado=? WHERE id=?", (fim or datetime.now().isoformat(timespec="seconds"), resultado, item_id)); self._commit()


class UsuarioRepository(BaseRepository):
    def create(self, item: Usuario) -> Usuario:
        _require(item.login, "Login"); _require(item.senha_hash, "Senha")
        cur = self.db.execute("INSERT INTO usuarios (login, senha_hash, perfil, ativo) VALUES (?, ?, ?, ?)",
                              (item.login.strip(), item.senha_hash, item.perfil.value, int(item.ativo)))
        self._commit(); item.id = cur.lastrowid; return item

    def get_by_login(self, login: str) -> Optional[Usuario]:
        r = self.db.execute("SELECT * FROM usuarios WHERE login=?", (login,)).fetchone()
        return Usuario(r["id"], r["login"], r["senha_hash"], PerfilUsuario(r["perfil"]), _bool(r["ativo"])) if r else None

    def set_active(self, item_id: int, active: bool) -> None:
        self.db.execute("UPDATE usuarios SET ativo=? WHERE id=?", (int(active), item_id)); self._commit()


class ConfiguracaoRepository(BaseRepository):
    def get(self, chave: str, default: Optional[str] = None) -> Optional[str]:
        r = self.db.execute("SELECT valor FROM configuracoes WHERE chave=?", (chave,)).fetchone()
        return r["valor"] if r else default

    def set(self, chave: str, valor: str) -> None:
        _require(chave, "Chave")
        self.db.execute("INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor", (chave, str(valor))); self._commit()

    def list(self) -> list[Configuracao]:
        return [Configuracao(r["chave"], r["valor"]) for r in self.db.execute("SELECT * FROM configuracoes ORDER BY chave")]

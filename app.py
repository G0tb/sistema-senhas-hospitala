from __future__ import annotations

from config import DATABASE_PATH
from database.connection import Database
from database.repositories import ConsultorioRepository, EspecialidadeRepository


def main() -> None:
    with Database(DATABASE_PATH) as database:
        especialidades = EspecialidadeRepository(database.connection).list(only_active=True)
        consultorios = ConsultorioRepository(database.connection).list(only_active=True)
        print("Sistema de Senhas — backend inicializado")
        print(f"Banco: {DATABASE_PATH}")
        print(f"Especialidades ativas: {len(especialidades)}")
        print(f"Consultórios ativos: {len(consultorios)}")
        print("Status: pronto para os serviços de fila e atendimento")


if __name__ == "__main__":
    main()


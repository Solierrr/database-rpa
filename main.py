import logging

from config import LOG_FILE, LOG_LEVEL
from extract import (
    extrair_usuarios,
    marcar_processado,
    criar_coluna_controle_se_nao_existir,
)
from transform import transformar
from load import carregar, criar_tabela_mapeamento_se_nao_existir
from extended_migration import executar_migracao_complementar


logging.basicConfig(
    filename=LOG_FILE,
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.getLogger().addHandler(logging.StreamHandler())

logger = logging.getLogger(__name__)


def executar():
    logger.info("=== Início da execução do RPA ===")

    try:
        criar_coluna_controle_se_nao_existir()
        criar_tabela_mapeamento_se_nao_existir()

        # ==========================================================
        # 1. MIGRAÇÃO PRINCIPAL DOS USUÁRIOS
        # ==========================================================

        df_origem = extrair_usuarios()

        if not df_origem.empty:
            ids_origem = df_origem["id"].tolist()

            df_transformado = transformar(df_origem)

            carregar(df_transformado)

            marcar_processado(ids_origem)

            logger.info(
                "%s usuários migrados.",
                len(df_transformado),
            )

        else:
            logger.info("Nenhum usuário novo encontrado.")

        # ==========================================================
        # 2. MIGRAÇÃO DAS DEMAIS TABELAS
        # ==========================================================

        executar_migracao_complementar()

        logger.info("Execução concluída com sucesso.")

    except Exception:
        logger.exception("Falha na execução do RPA")

    finally:
        logger.info("=== Fim da execução ===\n")


if __name__ == "__main__":
    executar()
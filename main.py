import logging

from config import LOG_FILE, LOG_LEVEL
from extended_migration import executar_migracao_complementar
from extract import extrair_usuarios
from load import carregar, criar_tabela_mapeamento_se_nao_existir
from transform import transformar


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
        # O mapping é o único controle de processamento. A origem é somente leitura.
        criar_tabela_mapeamento_se_nao_existir()

        df_origem = extrair_usuarios()

        if df_origem.empty:
            logger.info("Nenhum usuário novo encontrado.")
        else:
            df_transformado = transformar(df_origem)
            carregar(df_transformado)
            logger.info("%s usuários migrados.", len(df_transformado))

        # Pais são migrados antes dos filhos dentro da rotina complementar.
        executar_migracao_complementar()
        logger.info("Execução concluída com sucesso.")

    except Exception:
        logger.exception("Falha na execução do RPA")

    finally:
        logger.info("=== Fim da execução ===\n")


if __name__ == "__main__":
    executar()

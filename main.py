import asyncio
import os
import time
from pathlib import Path
from loguru import logger
from download_repository import download_repo
from performance.performance_test import PerformanceTest
from scanner import scan_repo
from analyzers.complexity import calculate_complexity
from analyzers.coupling import calculate_cbo
from analyzers.confiability import ConfiabilityAnalyzer
from analyzers.dryness import calculate_dryness
from core.project_classes import get_project_classes
from core import GlobalConfig
from performance import ApplicationBootstrap
from enums import ApplicationType, BuildToolType
from reports.reportgenerator import gerar_relatorio

def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")

def wait_next():
    input("\nPressione ENTER para continuar...")
    clear_terminal()

def get_repository(repo_link: str):
    repo_path = download_repo(repo_link)
    return repo_path

def load_java_files(repo_path):
    result = scan_repo(repo_path, ".java")
    return result["files"], result["build_tool"]

def load_project_classes(java_files):
    return get_project_classes(java_files)

def show_complexity_analysis(java_files, build_tool):

    print("==============================")
    print("ANÁLISE DE COMPLEXIDADE CICLOMÁTICA - McCabe")
    print("==============================\n")

    print(f"Build tool detectado: {build_tool}\n")

    total_complexidade = 0
    arquivos_analisados = 0

    for file in java_files:

        complexity = calculate_complexity(file)

        if complexity is None:
            print(f"{file}")
            print("Complexidade não encontrada.\n")
            continue

        print(f"{file}")
        print(f"Complexidade McCabe: {complexity}\n")

        total_complexidade += complexity
        arquivos_analisados += 1

    if arquivos_analisados == 0:
        media = 0
    else:
        media = (
            total_complexidade / arquivos_analisados
        )

    print(f"Complexidade média do projeto: {media:.2f}")

    return media


def show_project_classes(project_classes):

    print("==============================")
    print("CLASSES DO PROJETO")
    print("==============================\n")

    for classe in project_classes:
        print(classe)

def show_cbo_analysis(java_files, project_classes):

    print("==============================")
    print("ANÁLISE CBO")
    print("==============================")

    total_cbo = 0

    for file in java_files:

        result = calculate_cbo(file, project_classes)

        if result is None:
            continue

        print(f"\nArquivo: {result['file']}")
        print(f"CBO: {result['cbo']}")

        total_cbo += result['cbo']

        if result['cbo'] > 0:

            print("Classes usadas:")

            for classe in result['classes_used']:
                print(f"- {classe}")

    return total_cbo

def show_dryness_analysis(java_files):

    print("==============================")
    print("ANÁLISE DE DUPLICAÇÃO (DRYNESS)")
    print("==============================")

    total_duplicacoes = 0

    for file in java_files:

        result = calculate_dryness(file)

        if result is None:
            continue

        print(f"\nArquivo: {result['file']}")
        print(f"Blocos duplicados: {result['duplicated_blocks']}")

        total_duplicacoes += result['duplicated_blocks']

    print(f"\nTotal de duplicações encontradas: {total_duplicacoes}")

    return total_duplicacoes

async def show_performance_results(
    global_config: GlobalConfig,
    repo_path: str,
    build_tool: BuildToolType,
):
    if global_config.config["feature-flags"]["performance"] == False:
        return
    
    logger.info("STARTING PERFORMANCE TEST")

    application: ApplicationType

    if (
        global_config.config["performance"]["application-type"]
        == ApplicationType.QUARKUS.value
    ):
        application = ApplicationType.QUARKUS

    else:
        application = ApplicationType.SPRING_BOOT

    logger.info(f"repo_path={Path(repo_path).resolve()}")
    logger.info(
        f"api_url={global_config.config['performance']['api-url']}"
    )
    logger.info(
        f"api_endpoints={global_config.config['performance']['api-endpoints']}"
    )
    logger.info(f"build_tool={build_tool.value}")
    logger.info(f"application_type={application.value}")

    performance_test = PerformanceTest(global_config=global_config)

    try:

        bootstrap = ApplicationBootstrap(
            repo_absolute_path=Path(__file__.replace("/main.py", ""), repo_path),
            api_endpoints=global_config.config["performance"]["api-endpoints"],
            api_url=global_config.config["performance"]["api-url"],
            build_tool=build_tool,
            application_type=application
        )

        bootstrap.run()
        perf_results = await performance_test.start_tests()
    finally:

        logger.info("Terminating Java process.")

        bootstrap.process.terminate()
        bootstrap.process.wait()

        logger.info("Process terminated.")
    
    for r in perf_results:
        logger.info(f"--- Step Finished ({r.step} users) ---")
        logger.info(f"Total requests sent: {len(r.requests_time)}")
        logger.info(f"Successes: {r.success_count} | Failures: {r.failure_count}")
        
        if r.average_latency:
            log_message = f"Average Latency: {r.average_latency:.2f} ms"
            if r.difference_latency:
                log_message += f" ({r.difference_latency:.2f}%)"
            logger.info(log_message)
        if r.rps:
            logger.info(f"Estimated RPS: {r.rps:.2f} req/s")

def show_confiability_analysis(
    java_files,
    project_classes,
    repo_path,
    build_tool
):

    confiability_analyzer = ConfiabilityAnalyzer(
        java_files,
        project_classes,
        repo_path,
        True
    )

    result = confiability_analyzer.analyze(
        build_tool
    )

    overall_coverage = result.overall_coverage
    score = result.score

    print()
    print("-" * 60)
    print("  RESUMO DE CONFIABILIDADE")
    print("-" * 60)

    print(f"  Cobertura geral de linhas : {overall_coverage:.2f}%")

    print(
        f"  Score de confiabilidade   : "
        f"{score:.4f}  ({score * 100:.2f}%)"
    )

    print("-" * 60)

    return {
    "coverage": overall_coverage,
    "score": score,
}


def main():
    global_config = GlobalConfig("config/config.toml")
    clear_terminal()
    repo_path = get_repository(global_config.config["repo"]["url"])

    if repo_path is None:
        return
    java_files, build_tool = load_java_files(repo_path)
    project_classes = load_project_classes(java_files)
    clear_terminal()
    complexidade_media = show_complexity_analysis(
        java_files,
        build_tool
    )
    wait_next()
    show_project_classes(project_classes)
    wait_next()
    cbo_total = show_cbo_analysis(
        java_files,
        project_classes
    )
    wait_next()
    duplicacoes = show_dryness_analysis(java_files)
    wait_next()
    confiabilidade = show_confiability_analysis(
        java_files,
        project_classes,
        repo_path,
        build_tool
    )
    wait_next()
    asyncio.run(show_performance_results(
        global_config=global_config,
        repo_path=repo_path,
        build_tool=build_tool
    ))

    resultado_analise = {
    "projeto": os.path.basename(repo_path),
    "build_tool": build_tool.value,
    "total_arquivos_java": len(java_files),
    "total_classes": len(project_classes),
    "total_dependencias": cbo_total,
    "code_smells": round(
        complexidade_media,
        2
    ),
    "duplicacoes": duplicacoes,
    "cobertura": (
        f"{confiabilidade['coverage']:.2f}%"
    ),
    "cbo": cbo_total,
    "score_confiabilidade": round(
        confiabilidade["score"] * 100,
        2
    ),
}

    gerar_relatorio(resultado_analise)

    print("\n==============================")
    print("FIM DA ANÁLISE")
    print("==============================")

if __name__ == "__main__":
    main()
import asyncio
import os
import time
from loguru import logger
from download_repository import download_repo
from performance.performance_test import PerformanceTest
from scanner import scan_repo
from analyzers.complexity import calculate_complexity
from analyzers.coupling import calculate_cbo
from core.project_classes import get_project_classes
from core import GlobalConfig
from analyzers.dryness import calculate_dryness
from performance import ApplicationBootstrap
from enums import ApplicationType, BuildToolType
from pathlib import Path

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

    for file in java_files:

        complexity = calculate_complexity(file)
        print(f"{file}")
        print(f"Complexidade McCabe: {complexity}\n")

    print(f"Total de arquivos Java encontrados: {len(java_files)}")


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

    for file in java_files:

        result = calculate_cbo(file, project_classes)
        if result is None:
            continue

        print(f"\nArquivo: {result['file']}")
        print(f"CBO: {result['cbo']}")

        if result['cbo'] > 0:

            print("Classes usadas:")

            for classe in result['classes_used']:
                print(f"- {classe}")

def show_dryness_analysis(java_files):

    print("==============================")
    print("ANÁLISE DE DUPLICAÇÃO (DRYNESS)")
    print("==============================")

    for file in java_files:

        result = calculate_dryness(file)

        if result is None:
            continue

        print(f"\nArquivo: {result['file']}")
        print(f"Blocos duplicados: {result['duplicated_blocks']}")

async def show_performance_results(
    global_config: GlobalConfig,
    repo_path: str,
    build_tool: BuildToolType,
):
    if global_config.config["feature-flags"]["performance"] == False:
        return
    
    logger.info("STARTING PERFORMANCE TEST")
    application: ApplicationType 
    if global_config.config["performance"]["application-type"] == ApplicationType.QUARKUS.value: 
        application = ApplicationType.QUARKUS
    else: application = ApplicationType.SPRING_BOOT

    logger.info(f"repo_path={Path(__file__, repo_path).resolve()}")
    logger.info(f"api_url={global_config.config["performance"]["api-url"]}")
    logger.info(f"api_endpoints={global_config.config["performance"]["api-endpoints"]}")
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

def main():
    global_config = GlobalConfig("config/config.toml")
    clear_terminal()
    repo_path = get_repository(global_config.config["repo"]["url"])

    if repo_path is None:
        return

    java_files, build_tool = load_java_files(repo_path)
    project_classes = load_project_classes(java_files)

    clear_terminal()
    show_complexity_analysis(java_files, build_tool)
    wait_next()
    show_project_classes(project_classes)
    wait_next()
    show_cbo_analysis(java_files, project_classes)
    wait_next()
    show_dryness_analysis(java_files)
    wait_next()
    asyncio.run(show_performance_results(
        global_config=global_config,
        repo_path=repo_path,
        build_tool=build_tool
    ))

    print("==============================")
    print("FIM DA ANÁLISE")
    print("==============================")


if __name__ == "__main__":
    main()
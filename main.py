import os
import shutil
from download_repository import download_repo
from scanner import scan_repo
from analyzers.complexity import calculate_complexity
from analyzers.coupling import calculate_cbo
from core.project_classes import get_project_classes


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")

def wait_next():
    input("\nPressione ENTER para continuar...")
    clear_terminal()

def get_repository():
    repo_link = input("Insira o link do repositório: ")
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


def main():

    clear_terminal()
    repo_path = get_repository()

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

    print("==============================")
    print("FIM DA ANÁLISE")
    print("==============================")


if __name__ == "__main__":
    main()
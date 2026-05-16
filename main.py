from repository import download_repo
from scanner import find_java_files
from analyzers.complexity import calculate_complexity

def main():

    repo_link = input("Insira o link do repositório: ")

    repo_path = download_repo(repo_link)

    if repo_path is None:
        return

    java_files = find_java_files(repo_path)

    print("\nANÁLISE DE COMPLEXIDADE\n")
    print("\nArquivos Java encontrados:\n")

    for file in java_files:

        complexity = calculate_complexity(file)

        print(f"{file} -> Complexidade McCabe: {complexity}")

    print(f"\nTotal: {len(java_files)} arquivos")


if __name__ == "__main__":
    main()

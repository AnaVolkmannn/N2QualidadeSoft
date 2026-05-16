import git
import os

REPOSITORIES_FOLDER = ".repositories"

def download_repo(repo_link):

    if not repo_link.endswith(".git"):
        print("O link do repositório deve terminar com '.git'.")
        return None

    # cria a pasta .repositories caso não exista
    os.makedirs(REPOSITORIES_FOLDER, exist_ok=True)

    repo_name = repo_link.split("/")[-1].split(".")[0]
    repo_path = os.path.join(REPOSITORIES_FOLDER, repo_name)

    if os.path.exists(repo_path):
        print("O repositório já existe localmente.")
        return repo_path

    print("Baixando repositório...")
    repo = git.Repo.clone_from(repo_link, repo_path)
    print("Download concluído.")
    repo.close()

    return repo_path
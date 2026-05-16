import git
import os

def download_repo(repo_link):

    if not repo_link.endswith(".git"):
        print("O link do repositório deve terminar com '.git'.")
        return None
    
    repo_name = repo_link.split("/")[-1].split(".")[0]

    if os.path.exists(repo_name):
        print("O repositório já existe localmente.")
        return repo_name
        
    print("Baixando repositório...")

    repo = git.Repo.clone_from(repo_link, repo_name)

    print("Download concluído.")
    repo.close()

    return repo_name
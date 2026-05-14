def InsertRepo():
    repoLink = input("Insira o link do seu repositório: ")
    print("O link do seu repositório é: " + repoLink)
    DownloadRepo(repoLink)

def DownloadRepo(repoLink):
    import git
    import os

    repoName = repoLink.split("/")[-1].split(".")[0]
    if os.path.exists(repoName):
        print("O repositório já existe localmente.")
    else:
        if not repoLink.endswith(".git"):
            print("O link do repositório deve terminar com '.git'.")
            print("Repositório não baixado.")
            return
        print("Baixando o repositório...")
        git.Repo.clone_from(repoLink, repoName)
        print("Repositório baixado com sucesso.")

if __name__ == "__main__":
    InsertRepo()

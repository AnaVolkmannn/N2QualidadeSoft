import shutil
import os
import stat
import time

def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def delete_repository(repo_path):
    try:
        if os.path.exists(repo_path):
            time.sleep(1)
            shutil.rmtree(
                repo_path,
                onerror=remove_readonly
            )
            print(f"\nRepositório '{repo_path}' removido com sucesso.")
        else:
            print("\nRepositório não encontrado.")

    except Exception as error:
        print("\nErro ao remover o repositório.")
        print(error)
import javalang

# Escaneia o projeto e retorna um conjunto com os nomes das classes encontradas
def get_project_classes(java_files):

    project_classes = set()
    for file_path in java_files:

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                code = file.read()
            tree = javalang.parse.parse(code)
            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration):
                    project_classes.add(node.name)
        except:
            continue

    return project_classes
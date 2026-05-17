import javalang

#função para calcular o acoplamento entre objetos (CBO) considerando apenas as classes do projeto
def calculate_cbo(file_path, project_classes):

    try:

        with open(file_path, "r", encoding="utf-8") as file:
            code = file.read()
        tree = javalang.parse.parse(code)
        used_classes = set()
        current_class = None
        for path, node in tree:

            # nome da classe atual
            if isinstance(node, javalang.tree.ClassDeclaration):
                current_class = node.name

            # tipos usados
            if isinstance(node, javalang.tree.ReferenceType):
                class_name = node.name

                # usa classes do projeto, descarta bibliotecas externas
                if class_name in project_classes:
                    used_classes.add(class_name)

        # remove auto-acoplamento
        if current_class in used_classes:
            used_classes.remove(current_class)

        return {
            "file": file_path,
            "cbo": len(used_classes),
            "classes_used": list(used_classes)
        }

    except Exception as error:

        print(f"Erro ao analisar {file_path}")
        print(error)

        return None
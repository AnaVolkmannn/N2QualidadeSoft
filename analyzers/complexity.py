import javalang

# Calcula a complexidade ciclomática de um arquivo Java - McCabe
def calculate_complexity(file_path):

    try:

        with open(file_path, "r", encoding="utf-8") as file:
            code = file.read()

        tree = javalang.parse.parse(code)

# A complexidade ciclomática começa em 1 sempre, sendo a menor pontuação possível
        complexity = 1

        for path, node in tree:

# O parser verifica se o nó é um IfStatement, cumprindo os requisitos de analizar apenas os if, if/else, if/else-if/else.
            if isinstance(node, javalang.tree.IfStatement):
                complexity += 1

        return complexity

    except Exception as error:

        print(f"Erro ao analisar {file_path}")
        print(error)

        return None
WINDOW_SIZE = 5

def normalize_line(line: str) -> str:
    return line.strip()

def get_blocks(lines):
    blocks = []
    for i in range(len(lines) - WINDOW_SIZE + 1):
        block = lines[i:i + WINDOW_SIZE]
        blocks.append(block)
    return blocks

def block_to_string(block):
    return "\n".join(block)

def calculate_dryness(file_path):

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        lines = [
            normalize_line(line)
            for line in lines
            if line.strip() != ""
        ]

        blocks = get_blocks(lines)
        seen = []
        duplicates = set()

        for block in blocks:
            block_str = block_to_string(block)
            if block_str in seen:
                duplicates.add(block_str)
            else:
                seen.append(block_str)

        return {
            "file": file_path,
            "duplicated_blocks": len(duplicates)
        }

    except Exception as e:
        print(f"Erro ao analisar duplicação: {file_path}")
        print(e)
        return None
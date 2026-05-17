import os

IGNORED_FOLDERS = [
    ".git",
    "target",
    "build",
    "out",
    ".idea"
]

def scan_repo(repo_path: str, file_extension: str):

    found_files = []
    build_tool = "DESCONHECIDO"

    for root, dirs, files in os.walk(repo_path):

        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
        for file in files:
            if file == "pom.xml":
                build_tool = "MAVEN"
            if file in ["build.gradle", "build.gradle.kts"]:
                build_tool = "GRADLE"
            if file.endswith(file_extension):
                full_path = os.path.join(root, file)
                found_files.append(full_path)

    return {
        "files": found_files,
        "build_tool": build_tool
    }
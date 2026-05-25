from __future__ import annotations
import os
import re
import copy
import random
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from scanner import scan_repo

# ---------------------------------------------------------------------------
# Data classes de resultado
# ---------------------------------------------------------------------------

@dataclass
class FileCoverageResult:
    file_path: str
    total_lines: int
    covered_lines: int
    coverage_percent: float
    has_associated_test: bool


@dataclass
class MutationResult:
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    mutation_score: float          # killed / total  (0–1)
    details: list[dict] = field(default_factory=list)


@dataclass
class ConfiabilityResult:
    has_tests: bool
    test_files: list[str]
    source_files: list[str]
    overall_coverage: float        # 0–100
    file_coverages: list[FileCoverageResult]
    mutation: Optional[MutationResult]
    score: float                   # 0–1  (usado pelo módulo IV)
    build_tool: Optional[str]      # "maven" | "gradle" | None
    jacoco_used: bool
    pitest_used: bool


# ---------------------------------------------------------------------------
# Utilitários de leitura de arquivo
# ---------------------------------------------------------------------------

def _read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _count_non_blank_lines(content: str) -> int:
    return sum(1 for line in content.splitlines() if line.strip())


# ---------------------------------------------------------------------------
# Detecção de build tool
# ---------------------------------------------------------------------------

scan_repo_result = scan_repo(repo_path="", file_extension=".java")
build_tool = scan_repo_result["build_tool"]

# ---------------------------------------------------------------------------
# Execução de JaCoCo
# ---------------------------------------------------------------------------

def _run_jacoco(project_root: str, build_tool: str) -> Optional[str]:

    root = Path(project_root)

    if build_tool == "maven":
        cmd = [
            "mvn", "-q", "-f", str(root / "pom.xml"),
            "test",
            "jacoco:report",
            "-Dmaven.test.failure.ignore=true",
        ]
        report_xml = root / "target" / "site" / "jacoco" / "jacoco.xml"
    else:
        cmd = ["./gradlew", "-q", "test", "jacocoTestReport",
               "--continue", f"-p{root}"]
        report_xml = root / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport.xml"

    try:
        subprocess.run(cmd, timeout=300, capture_output=True, cwd=str(root))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    return str(report_xml) if report_xml.exists() else None


def _parse_jacoco_xml(xml_path: str) -> dict[str, float]:
    coverage_map: dict[str, float] = {}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for package in root.findall(".//package"):
            for sf in package.findall("sourcefile"):
                name = sf.get("name", "")
                counters = {c.get("type"): c for c in sf.findall("counter")}
                if "LINE" in counters:
                    missed = int(counters["LINE"].get("missed", 0))
                    covered = int(counters["LINE"].get("covered", 0))
                    total = missed + covered
                    pct = (covered / total * 100) if total else 0.0
                    coverage_map[name] = pct
    except ET.ParseError:
        pass
    return coverage_map


# ---------------------------------------------------------------------------
# Fallback estático de cobertura
# ---------------------------------------------------------------------------

def _static_coverage_estimate(
    source_file: str,
    test_files: list[str],
) -> float:
    
    #  Busca todos os métodos públicos/privados/protected do arquivo de código-fonte
    source_content = _read_file(source_file)
    method_pattern = re.compile(
        r'\b(?:public|protected|private)\s+\w[\w<>\[\]]*\s+(\w+)\s*\('
    )
    methods = set(method_pattern.findall(source_content))

    # Remove os construtores da classe (métodos com mesmo nome da classe)
    class_name_pattern = re.compile(
        r'\bclass\s+(\w+)'
    )
    class_name_match = class_name_pattern.search(source_content)
    class_name = class_name_match.group(1) if class_name_match else ""
    methods.discard(class_name)

    if not methods:
        return 0.0

    all_test_content = "\n".join(_read_file(test_file) for test_file in test_files)
    
    # Explicação: do `for` filtrado no método `sum`.
    #   - Para cada método, verifica se está no conteúdo dos testes
    #   - Para cada método que estiver dentro do conteúdo dos testes, adiciona 1 ao contador
    referenced = sum(1 for m in methods if m in all_test_content)

    print(methods)

    raw = (referenced / len(methods)) * 100
    return min(raw, 100.0)

class ConfiabilityAnalyzer:

    # Limiar de cobertura para score máximo (%)
    _COVERAGE_FULL_SCORE_THRESHOLD = 80.0

    def __init__(
        self,
        java_files: list[str],
        project_classes: set[str],
        project_root: str,
        run_mutation: bool = True,
    ) -> None:
        self.java_files = java_files
        self.project_classes = project_classes
        self.project_root = project_root
        self.run_mutation = run_mutation

    # ------------------------------------------------------------------
    # Ponto de entrada público
    # ------------------------------------------------------------------

    def analyze(self, build_tool) -> ConfiabilityResult:
        self._print_header()

        test_files, source_files = self._split_test_and_source_files()
        has_tests = bool(test_files)

        if not has_tests:
            print("  Nenhum arquivo de teste encontrado.")
            return self._empty_result(source_files)

        print(f"  Arquivos de teste encontrados : {len(test_files)}")
        print(f"  Arquivos de produção          : {len(source_files)}")

        print(f"  Build tool detectado          : {build_tool or 'não identificado'}")
        
        # --- Coverage ---
        file_coverages, overall_coverage, jacoco_used = self._analyze_coverage(
            source_files, test_files, build_tool
        )

        # --- Score ---
        score = self._calculate_score(overall_coverage)

        # self._print_summary(overall_coverage, mutation_result, score)

        return ConfiabilityResult(
            has_tests=has_tests,
            test_files=test_files,
            source_files=source_files,
            overall_coverage=overall_coverage,
            file_coverages=file_coverages,
            mutation=None,
            score=score,
            build_tool=build_tool,
            jacoco_used=jacoco_used,
            pitest_used=False,
        )

    # ------------------------------------------------------------------
    # Separação de arquivos
    # ------------------------------------------------------------------

    def _split_test_and_source_files(self) -> tuple[list[str], list[str]]:
        test_files: list[str] = []
        source_files: list[str] = []

        for f in self.java_files:
            name = os.path.basename(f)
            path = f.replace("\\", "/")
            is_test = (
                "Test" in name
                or "test" in name
                or "/test/" in path
                or "/tests/" in path
            )
            if is_test:
                test_files.append(f)
            else:
                source_files.append(f)

        return test_files, source_files

    # ------------------------------------------------------------------
    # Cobertura
    # ------------------------------------------------------------------

    def _analyze_coverage(
        self,
        source_files: list[str],
        test_files: list[str],
        build_tool: Optional[str],
    ) -> tuple[list[FileCoverageResult], float, bool]:
        jacoco_xml: Optional[str] = None
        jacoco_used = False

        if build_tool:
            print("\n  [Coverage] Executando JaCoCo…")
            jacoco_xml = _run_jacoco(self.project_root, build_tool)
            if jacoco_xml:
                print(f"  [Coverage] Relatório JaCoCo: {jacoco_xml}")
                jacoco_used = True
            else:
                print("  [Coverage] JaCoCo não disponível — usando estimativa estática.")
        else:
            print("\n  [Coverage] Build tool não encontrado — usando estimativa estática.")

        jacoco_map: dict[str, float] = {}
        if jacoco_xml:
            jacoco_map = _parse_jacoco_xml(jacoco_xml)

        # Variáveis utilzadas para calcular cobertura do projeto:
        file_coverages: list[FileCoverageResult] = []
        total_lines = 0
        covered_lines_sum = 0
        for file in source_files:
            content = _read_file(file)
            lines = _count_non_blank_lines(content)
            name = os.path.basename(file)

            # Verifica se há arquivo de teste associado
            stem = Path(file).stem
            associated_tests = [
                test_file for test_file in test_files
                if stem in os.path.basename(test_file)
                or os.path.basename(test_file).replace("Test", "").replace("Tests", "") == name.replace(".java", ".java")
            ]
            has_associated_test = bool(associated_tests)

            if jacoco_map:
                pct = jacoco_map.get(name, 0.0)
            else:
                pct = _static_coverage_estimate(file, test_files)

            covered = int(lines * pct / 100)
            total_lines += lines
            covered_lines_sum += covered

            file_coverages.append(FileCoverageResult(
                file_path=file,
                total_lines=lines,
                covered_lines=covered,
                coverage_percent=round(pct, 2),
                has_associated_test=has_associated_test,
            ))

        overall = (covered_lines_sum / total_lines * 100) if total_lines else 0.0
        return file_coverages, round(overall, 2), jacoco_used

    # ------------------------------------------------------------------
    # Score
    # ------------------------------------------------------------------

    def _calculate_score(
        self,
        overall_coverage: float,
    ) -> float:
        """
        Score de confiabilidade [0, 1]:
          - 70% do peso vem da cobertura de linhas
          - 30% vem do score de mutação (se disponível)
        """
        coverage_score = min(overall_coverage / self._COVERAGE_FULL_SCORE_THRESHOLD, 1.0)

        return round(coverage_score, 4)

    # ------------------------------------------------------------------
    # Resultado vazio (sem testes)
    # ------------------------------------------------------------------

    def _empty_result(self, source_files: list[str]) -> ConfiabilityResult:
        file_coverages = [
            FileCoverageResult(
                file_path=sf,
                total_lines=_count_non_blank_lines(_read_file(sf)),
                covered_lines=0,
                coverage_percent=0.0,
                has_associated_test=False,
            )
            for sf in source_files
        ]
        return ConfiabilityResult(
            has_tests=False,
            test_files=[],
            source_files=source_files,
            overall_coverage=0.0,
            file_coverages=file_coverages,
            mutation=None,
            score=0.0,
            build_tool=build_tool,
            jacoco_used=False,
            pitest_used=False,
        )

    # ------------------------------------------------------------------
    # Impressão
    # ------------------------------------------------------------------

    def _print_header(self) -> None:
        print()
        print("=" * 60)
        print("  MÓDULO III — CONFIABILIDADE (ISO/IEC 25010)")
        print("=" * 60)

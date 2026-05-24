"""
Módulo III: Confiabilidade (Testabilidade) — ISO/IEC 25010
============================================================
Responsabilidades:
  1. Cobertura de Testes (Coverage)
     - Detecta arquivos de teste JUnit presentes no projeto
     - Executa o projeto com JaCoCo via Maven/Gradle e lê o XML gerado
     - Fallback estático: estima cobertura via análise léxica quando
       o build não está disponível
  2. Análise de Mutação (Bônus)
     - Executa PIT (Pitest) via Maven/Gradle quando possível
     - Fallback estático: simula mutações léxicas nos métodos e verifica
       se os testes referenciam os operadores mutados
"""

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
    """Lê um arquivo ignorando erros de encoding."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _count_non_blank_lines(content: str) -> int:
    return sum(1 for line in content.splitlines() if line.strip())


# ---------------------------------------------------------------------------
# Detecção de build tool
# ---------------------------------------------------------------------------

def _detect_build_tool(project_root: str) -> Optional[str]:
    root = Path(project_root)
    if (root / "pom.xml").exists():
        return "maven"
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return "gradle"
    return None


# ---------------------------------------------------------------------------
# Execução de JaCoCo
# ---------------------------------------------------------------------------

def _run_jacoco(project_root: str, build_tool: str) -> Optional[str]:
    """
    Executa o build com JaCoCo e retorna o caminho do XML de relatório,
    ou None se a execução falhar.
    """
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
    """
    Analisa jacoco.xml e retorna {source_file_name: coverage_percent}.
    """
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

    raw = (referenced / len(methods)) * 100
    return min(raw, 100.0)


# ---------------------------------------------------------------------------
# Execução de PIT (análise de mutação)
# ---------------------------------------------------------------------------

def _run_pitest(project_root: str, build_tool: str) -> Optional[str]:
    """
    Executa o PIT e retorna o caminho do diretório de relatório, ou None.
    """
    root = Path(project_root)
    try:
        if build_tool == "maven":
            subprocess.run(
                ["mvn", "-q", "test-compile",
                 "org.pitest:pitest-maven:mutationCoverage",
                 "-Dmaven.test.failure.ignore=true"],
                timeout=600, capture_output=True, cwd=str(root),
            )
            pit_dir = root / "target" / "pit-reports"
        else:
            subprocess.run(
                ["./gradlew", "-q", "pitest", f"-p{root}"],
                timeout=600, capture_output=True, cwd=str(root),
            )
            pit_dir = root / "build" / "reports" / "pitest"

        if pit_dir.exists():
            return str(pit_dir)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _parse_pitest_report(pit_dir: str) -> MutationResult:
    """Analisa mutations.xml gerado pelo PIT."""
    total = killed = 0
    details: list[dict] = []
    xml_files = list(Path(pit_dir).rglob("mutations.xml"))

    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            for mutation in tree.getroot().findall("mutation"):
                total += 1
                detected = mutation.get("detected", "false").lower() == "true"
                if detected:
                    killed += 1
                details.append({
                    "mutator": mutation.findtext("mutator", ""),
                    "source_file": mutation.findtext("sourceFile", ""),
                    "method": mutation.findtext("methodDescription", ""),
                    "killed": detected,
                })
        except ET.ParseError:
            continue

    survived = total - killed
    score = (killed / total) if total else 0.0
    return MutationResult(total, killed, survived, score, details)


# ---------------------------------------------------------------------------
# Análise de mutação estática (fallback / bônus)
# ---------------------------------------------------------------------------

# Operadores de mutação léxica aplicados ao código-fonte Java
_MUTATION_OPERATORS: list[tuple[str, str, str]] = [
    # (nome, padrão regex, substituição)
    ("AOR_PLUS_TO_MINUS",   r'(?<!=)\+(?!=)',    "-"),
    ("AOR_MINUS_TO_PLUS",   r'(?<!=)-(?!=)',     "+"),
    ("AOR_MUL_TO_DIV",      r'\*',               "/"),
    ("ROR_EQ_TO_NEQ",       r'==',               "!="),
    ("ROR_GT_TO_LT",        r'(?<![=<>!])>(?!=)', "<"),
    ("ROR_LT_TO_GT",        r'(?<![=<>!])<(?!=)', ">"),
    ("NEGATE_CONDITION",    r'\bif\s*\(',         "if (!( "),
    ("TRUE_TO_FALSE",       r'\btrue\b',         "false"),
    ("FALSE_TO_TRUE",       r'\bfalse\b',        "true"),
    ("REMOVE_RETURN_VALUE", r'\breturn\b',       "return null; //"),
]


def _extract_methods(content: str) -> list[dict]:
    """
    Extrai métodos Java (cabeçalho + corpo) de forma simplificada.
    Retorna lista de {name, start, end, body}.
    """
    methods: list[dict] = []
    lines = content.splitlines(keepends=True)

    method_header = re.compile(
        r'^\s*(?:public|protected|private|static|\s)*'
        r'[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
    )

    i = 0
    while i < len(lines):
        m = method_header.match(lines[i])
        if m:
            name = m.group(1)
            depth = lines[i].count("{") - lines[i].count("}")
            start = i
            i += 1
            while i < len(lines) and depth > 0:
                depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            methods.append({
                "name": name,
                "start": start,
                "end": i,
                "body": "".join(lines[start:i]),
            })
        else:
            i += 1
    return methods


def _apply_mutation(body: str, operator: tuple[str, str, str]) -> Optional[str]:
    """Aplica um operador de mutação ao corpo de um método."""
    _, pattern, replacement = operator
    new_body, n = re.subn(pattern, replacement, body, count=1)
    return new_body if n > 0 else None


def _test_kills_mutation(
    mutant_method_name: str,
    mutant_body: str,
    test_files: list[str],
) -> bool:
    """
    Heurística: um teste "mata" a mutação se:
      - Chama o método mutado (nome aparece no teste), E
      - Contém pelo menos uma asserção.
    """
    for tf in test_files:
        tc = _read_file(tf)
        if mutant_method_name in tc and re.search(
            r'\bassert\w*\s*\(', tc, re.IGNORECASE
        ):
            return True
    return False


def _static_mutation_analysis(
    source_files: list[str],
    test_files: list[str],
    max_mutants_per_file: int = 20,
) -> MutationResult:
    """
    Análise de mutação estática (sem build).
    Aplica operadores de mutação léxica e verifica se os testes matariam
    cada mutante usando heurísticas de referência de método + asserção.
    """
    total = killed = 0
    details: list[dict] = []

    for sf in source_files:
        content = _read_file(sf)
        methods = _extract_methods(content)

        # Limita para não explodir o tempo de execução
        sampled = methods if len(methods) <= max_mutants_per_file else \
            random.sample(methods, max_mutants_per_file)

        for method in sampled:
            for op in _MUTATION_OPERATORS:
                mutant_body = _apply_mutation(method["body"], op)
                if mutant_body is None:
                    continue
                is_killed = _test_kills_mutation(
                    method["name"], mutant_body, test_files
                )
                total += 1
                if is_killed:
                    killed += 1
                details.append({
                    "mutator": op[0],
                    "source_file": os.path.basename(sf),
                    "method": method["name"],
                    "killed": is_killed,
                })

    survived = total - killed
    score = (killed / total) if total else 0.0
    return MutationResult(total, killed, survived, score, details)


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

class ConfiabilityAnalyzer:
    """
    Módulo III — Confiabilidade (Testabilidade) — ISO/IEC 25010

    Parâmetros
    ----------
    java_files : list[str]
        Caminhos absolutos de todos os arquivos .java do projeto.
    project_classes : set[str]
        Nomes simples de todas as classes do projeto (usado por outros módulos).
    project_root : str
        Diretório raiz do projeto clonado.
    run_mutation : bool
        Se True, executa (ou simula) análise de mutação.
    """

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

    def analyze(self) -> ConfiabilityResult:
        self._print_header()

        test_files, source_files = self._split_test_and_source_files()
        has_tests = bool(test_files)

        if not has_tests:
            print("  ✗ Nenhum arquivo de teste encontrado.")
            return self._empty_result(source_files)

        print(f"  ✔ Arquivos de teste encontrados : {len(test_files)}")
        print(f"  ✔ Arquivos de produção          : {len(source_files)}")

        build_tool = _detect_build_tool(self.project_root)
        print(f"  ✔ Build tool detectado          : {build_tool or 'não identificado'}")
        
        # --- Coverage ---
        file_coverages, overall_coverage, jacoco_used = self._analyze_coverage(
            source_files, test_files, build_tool
        )

        # TODO: validar como funciona a meneira estática e pensar se fazer sentido manter
        #   Pelo que tinha visto, não parece estar validando muita coisa no modo estático.
        # --- Mutation ---                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
        mutation_result, pitest_used = self._analyze_mutation(
            source_files, test_files, build_tool
        )

        # --- Score ---
        score = self._calculate_score(overall_coverage, mutation_result)

        self._print_summary(overall_coverage, mutation_result, score)

        return ConfiabilityResult(
            has_tests=has_tests,
            test_files=test_files,
            source_files=source_files,
            overall_coverage=overall_coverage,
            file_coverages=file_coverages,
            mutation=mutation_result,
            score=score,
            build_tool=build_tool,
            jacoco_used=jacoco_used,
            pitest_used=pitest_used,
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
        """
        Tenta executar JaCoCo; se não conseguir, usa estimativa estática.
        Retorna (file_coverages, overall_percent, jacoco_was_used).
        """
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
    # Mutação
    # ------------------------------------------------------------------

    def _analyze_mutation(
        self,
        source_files: list[str],
        test_files: list[str],
        build_tool: Optional[str],
    ) -> tuple[Optional[MutationResult], bool]:
        if not self.run_mutation:
            return None, False

        pitest_used = False

        if build_tool:
            print("\n  [Mutação] Executando PIT…")
            pit_dir = _run_pitest(self.project_root, build_tool)
            if pit_dir:
                print(f"  [Mutação] Relatório PIT: {pit_dir}")
                pitest_used = True
                return _parse_pitest_report(pit_dir), True

        print("  [Mutação] PIT não disponível — executando análise estática de mutação…")
        result = _static_mutation_analysis(source_files, test_files)
        return result, pitest_used

    # ------------------------------------------------------------------
    # Score
    # ------------------------------------------------------------------

    def _calculate_score(
        self,
        overall_coverage: float,
        mutation: Optional[MutationResult],
    ) -> float:
        """
        Score de confiabilidade [0, 1]:
          - 70% do peso vem da cobertura de linhas
          - 30% vem do score de mutação (se disponível)
        """
        coverage_score = min(overall_coverage / self._COVERAGE_FULL_SCORE_THRESHOLD, 1.0)

        if mutation and mutation.total_mutants > 0:
            mutation_score = mutation.mutation_score
            return round(coverage_score * 0.7 + mutation_score * 0.3, 4)

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
            build_tool=_detect_build_tool(self.project_root),
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

    def _print_summary(
        self,
        overall_coverage: float,
        mutation: Optional[MutationResult],
        score: float,
    ) -> None:
        print()
        print("-" * 60)
        print("  RESUMO DE CONFIABILIDADE")
        print("-" * 60)
        print(f"  Cobertura geral de linhas : {overall_coverage:.2f}%")

        if mutation:
            print(f"  Mutantes gerados          : {mutation.total_mutants}")
            print(f"  Mutantes eliminados       : {mutation.killed_mutants}")
            print(f"  Mutantes sobreviventes    : {mutation.survived_mutants}")
            print(f"  Score de mutação          : {mutation.mutation_score * 100:.2f}%")

        print(f"  Score de confiabilidade   : {score:.4f}  ({score * 100:.2f}%)")

        rating = self._iso_rating(score)
        print(f"  Avaliação ISO/IEC 25010   : {rating}")
        print("-" * 60)

    @staticmethod
    def _iso_rating(score: float) -> str:
        if score >= 0.80:
            return "APROVADO  ✔  (Confiabilidade adequada)"
        if score >= 0.50:
            return "PARCIAL   ⚠  (Melhorias necessárias)"
        return "REPROVADO ✗  (Confiabilidade insuficiente)"
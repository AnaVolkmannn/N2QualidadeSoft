import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


def gerar_relatorio(resultado):

    # =====================================================
    # CRIA PASTA PDF
    # =====================================================

    pasta_pdf = "PDF"

    if not os.path.exists(pasta_pdf):
        os.makedirs(pasta_pdf)

    # =====================================================
    # NOME DO ARQUIVO
    # =====================================================

    nome_projeto = (
        resultado['projeto']
        .replace(" ", "")
        .replace("/", "")
        .replace("\\", "")
    )

    nome_arquivo = (
        f"Analise{nome_projeto}ISOIEC25010.pdf"
    )

    caminho_pdf = os.path.join(
        pasta_pdf,
        nome_arquivo
    )

    # =====================================================
    # SOBRESCREVE PDF ANTIGO
    # =====================================================

    if os.path.exists(caminho_pdf):
        os.remove(caminho_pdf)

    # =====================================================
    # DOCUMENTO
    # =====================================================

    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=30
    )

    elements = []

    styles = getSampleStyleSheet()

    # =====================================================
    # TÍTULO
    # =====================================================

    titulo = Paragraph(
        """
        Relatório de Análise de Qualidade
        de Repositório Java com Base na
        Norma ISO/IEC 25010
        """,
        styles['Title']
    )

    elements.append(titulo)

    elements.append(Spacer(1, 25))

    # =====================================================
    # RESUMO EXECUTIVO
    # =====================================================

    resumo = Paragraph(
        f"""
        <b>Repositório analisado:</b> {resultado['projeto']}
        <br/>
        <b>Arquivos Java encontrados:</b> {resultado['total_arquivos_java']}
        <br/>
        <b>Classes analisadas:</b> {resultado['total_classes']}
        <br/>
        <b>Build Tool:</b> {resultado['build_tool']}
        <br/>
        """,
        styles['BodyText']
    )

    elements.append(resumo)

    elements.append(Spacer(1, 25))

    # =====================================================
    # PARÂMETROS DAS MÉTRICAS
    # =====================================================

    complexidade_limite = 10
    duplicacao_limite = 5
    cobertura_limite = 70
    cbo_limite = 14
    confiabilidade_limite = 70

    cobertura_numerica = float(
        str(resultado['cobertura']).replace("%", "")
    )

    # =====================================================
    # STATUS
    # =====================================================

    status_complexidade = (
        "APROVADO"
        if resultado['code_smells'] <= complexidade_limite
        else "REPROVADO"
    )

    status_duplicacao = (
        "APROVADO"
        if resultado['duplicacoes'] <= duplicacao_limite
        else "REPROVADO"
    )

    status_cobertura = (
        "APROVADO"
        if cobertura_numerica >= cobertura_limite
        else "REPROVADO"
    )

    status_cbo = (
        "APROVADO"
        if resultado['cbo'] <= cbo_limite
        else "REPROVADO"
    )

    status_confiabilidade = (
        "APROVADO"
        if resultado['score_confiabilidade']
        >= confiabilidade_limite
        else "REPROVADO"
    )

    # =====================================================
    # FUNÇÃO AUXILIAR PARA COLORIR STATUS
    # =====================================================

    def aplicar_estilo_status(tabela_style, dados):

        for i in range(1, len(dados)):

            status = dados[i][-1]

            if status == "APROVADO":

                tabela_style.add(
                    'BACKGROUND',
                    (-1, i),
                    (-1, i),
                    colors.HexColor("#C8E6C9")
                )

                tabela_style.add(
                    'TEXTCOLOR',
                    (-1, i),
                    (-1, i),
                    colors.HexColor("#1B5E20")
                )

            elif status == "REPROVADO":

                tabela_style.add(
                    'BACKGROUND',
                    (-1, i),
                    (-1, i),
                    colors.HexColor("#FFCDD2")
                )

                tabela_style.add(
                    'TEXTCOLOR',
                    (-1, i),
                    (-1, i),
                    colors.HexColor("#B71C1C")
                )

    # =====================================================
    # MÓDULO I
    # =====================================================

    titulo_modulo_1 = Paragraph(
        "<b>MÓDULO I — MANUTENIBILIDADE (ANÁLISE ESTÁTICA)</b>",
        styles['Heading1']
    )

    elements.append(titulo_modulo_1)

    elements.append(Spacer(1, 15))

    descricao_modulo_1 = Paragraph(
    """
    Este módulo avalia características relacionadas à
    manutenibilidade do software conforme a ISO/IEC 25010.

    <br/><br/>

    Foram utilizadas as seguintes métricas:

    <br/><br/>

    <b>• Complexidade Ciclomática (McCabe)</b>
    <br/>
    Mede a quantidade de caminhos lógicos existentes no código.
    O cálculo começa com valor base 1 para cada método analisado,
    somando +1 ponto para cada estrutura condicional encontrada:
    <br/>
    • if
    <br/>
    • else if
    <br/>
    • else

    <br/><br/>

    <b>• Acoplamento entre Objetos (CBO)</b>
    <br/>
    Mede o nível de dependência entre classes.
    O cálculo considera quantas classes diferentes são utilizadas
    por cada classe do projeto.
    <br/>
    Cada classe referenciada soma +1 ponto no CBO total.
    Quanto maior o valor, maior o acoplamento do sistema.

    <br/><br/>

    <b>• Duplicação de Código (Dryness)</b>
    <br/>
    Mede a repetição de blocos de código no projeto.
    Cada bloco com pelo menos 5 linhas consecutivas idênticas
    encontrado em mais de um local soma +1 ponto de duplicação.

    <br/><br/>

    Os resultados encontrados são comparados com parâmetros
    de qualidade utilizados como referência para aprovação
    ou reprovação das métricas analisadas.
    """,
    styles['BodyText']
)

    elements.append(descricao_modulo_1)

    elements.append(Spacer(1, 20))

    dados_modulo_1 = [

        [
            "Métrica",
            "Pontuação",
            "Parâmetro",
            "Status"
        ],

        [
            "Complexidade Ciclomática (McCabe)",
            str(resultado['code_smells']),
            "Média Ideal <= 10",
            status_complexidade
        ],

        [
            "Duplicação de Código",
            str(resultado['duplicacoes']),
            "Média Ideal <= 5",
            status_duplicacao
        ],

        [
            "Acoplamento entre Objetos (CBO)",
            str(resultado['cbo']),
            "Ideal <= 14",
            status_cbo
        ],
    ]

    tabela_modulo_1 = Table(
        dados_modulo_1,
        colWidths=[180, 120, 120, 100]
    )

    estilo_1 = TableStyle([

        ('BACKGROUND', (0, 0), (-1, 0),
         colors.HexColor("#9E9E9E")),

        ('TEXTCOLOR', (0, 0), (-1, 0),
         colors.white),

        ('FONTNAME', (0, 0), (-1, 0),
         'Helvetica-Bold'),

        ('GRID', (0, 0), (-1, -1),
         1, colors.black),

        ('BACKGROUND', (0, 1), (-1, -1),
         colors.white),

        ('ALIGN', (0, 0), (-1, -1),
         'CENTER'),

        ('BOTTOMPADDING', (0, 0), (-1, 0),
         10),
    ])

    aplicar_estilo_status(
        estilo_1,
        dados_modulo_1
    )

    tabela_modulo_1.setStyle(estilo_1)

    elements.append(tabela_modulo_1)

    elements.append(Spacer(1, 30))

    # =====================================================
    # MÓDULO II
    # =====================================================

    titulo_modulo_2 = Paragraph(
        "<b>MÓDULO II — EFICIÊNCIA DE DESEMPENHO (DINÂMICA)</b>",
        styles['Heading1']
    )

    elements.append(titulo_modulo_2)

    elements.append(Spacer(1, 15))

    descricao_modulo_2 = Paragraph(
        """
        Este módulo será implementado futuramente.
        Ele será responsável por executar testes de benchmark,
        latência e análise de desempenho sob carga.
        """,
        styles['BodyText']
    )

    elements.append(descricao_modulo_2)

    elements.append(Spacer(1, 20))

    dados_modulo_2 = [

        [
            "Teste",
            "Status"
        ],

        [
            "Benchmark Automático",
            "PENDENTE"
        ],

        [
            "Análise de Latência",
            "PENDENTE"
        ],
    ]

    tabela_modulo_2 = Table(
        dados_modulo_2,
        colWidths=[300, 220]
    )

    estilo_2 = TableStyle([

        ('BACKGROUND', (0, 0), (-1, 0),
         colors.HexColor("#9E9E9E")),

        ('TEXTCOLOR', (0, 0), (-1, 0),
         colors.white),

        ('FONTNAME', (0, 0), (-1, 0),
         'Helvetica-Bold'),

        ('GRID', (0, 0), (-1, -1),
         1, colors.black),

        ('BACKGROUND', (0, 1), (-1, -1),
         colors.white),

        ('ALIGN', (0, 0), (-1, -1),
         'CENTER'),
    ])

    tabela_modulo_2.setStyle(estilo_2)

    elements.append(tabela_modulo_2)

    elements.append(Spacer(1, 30))

    # =====================================================
    # MÓDULO III
    # =====================================================

    titulo_modulo_3 = Paragraph(
        "<b>MÓDULO III — CONFIABILIDADE (TESTABILIDADE)</b>",
        styles['Heading1']
    )

    elements.append(titulo_modulo_3)

    elements.append(Spacer(1, 15))

    descricao_modulo_3 = Paragraph(
        """
        Este módulo avalia a confiabilidade do sistema através
        da cobertura de testes e análise de mutação, conforme
        os critérios da ISO/IEC 25010.
        """,
        styles['BodyText']
    )

    elements.append(descricao_modulo_3)

    elements.append(Spacer(1, 20))

    dados_modulo_3 = [

        [
            "Métrica",
            "Pontuação",
            "Parâmetro",
            "Status"
        ],

        [
            "Cobertura de Testes",
            str(resultado['cobertura']),
            "Ideal >= 70%",
            status_cobertura
        ],

        [
            "Score de Confiabilidade",
            f"{resultado['score_confiabilidade']}%",
            "Ideal >= 70%",
            status_confiabilidade
        ],
    ]

    tabela_modulo_3 = Table(
        dados_modulo_3,
        colWidths=[180, 120, 120, 100]
    )

    estilo_3 = TableStyle([

        ('BACKGROUND', (0, 0), (-1, 0),
         colors.HexColor("#9E9E9E")),

        ('TEXTCOLOR', (0, 0), (-1, 0),
         colors.white),

        ('FONTNAME', (0, 0), (-1, 0),
         'Helvetica-Bold'),

        ('GRID', (0, 0), (-1, -1),
         1, colors.black),

        ('BACKGROUND', (0, 1), (-1, -1),
         colors.white),

        ('ALIGN', (0, 0), (-1, -1),
         'CENTER'),

        ('BOTTOMPADDING', (0, 0), (-1, 0),
         10),
    ])

    aplicar_estilo_status(
        estilo_3,
        dados_modulo_3
    )

    tabela_modulo_3.setStyle(estilo_3)

    elements.append(tabela_modulo_3)

    elements.append(Spacer(1, 30))

    # =====================================================
    # ESTATÍSTICAS GERAIS
    # =====================================================

    titulo_estatisticas = Paragraph(
        "<b>ESTATÍSTICAS GERAIS DO PROJETO</b>",
        styles['Heading1']
    )

    elements.append(titulo_estatisticas)

    elements.append(Spacer(1, 15))

    estatisticas = [

        ["Indicador", "Valor"],

        ["Arquivos Java encontrados",
         str(resultado['total_arquivos_java'])],

        ["Classes analisadas",
         str(resultado['total_classes'])],

        ["Dependências analisadas",
         str(resultado['total_dependencias'])],

        ["Blocos duplicados",
         str(resultado['duplicacoes'])],
        
    ]

    tabela_estatisticas = Table(
        estatisticas,
        colWidths=[300, 180]
    )

    tabela_estatisticas.setStyle(TableStyle([

        ('BACKGROUND', (0, 0), (-1, 0),
         colors.HexColor("#9E9E9E")),

        ('TEXTCOLOR', (0, 0), (-1, 0),
         colors.white),

        ('FONTNAME', (0, 0), (-1, 0),
         'Helvetica-Bold'),

        ('GRID', (0, 0), (-1, -1),
         1, colors.black),

        ('BACKGROUND', (0, 1), (-1, -1),
         colors.white),

        ('ALIGN', (0, 0), (-1, -1),
         'CENTER'),
    ]))

    elements.append(tabela_estatisticas)

    elements.append(Spacer(1, 30))

    # =====================================================
    # CONCLUSÃO
    # =====================================================

    titulo_conclusao = Paragraph(
        "<b>CONCLUSÃO FINAL</b>",
        styles['Heading1']
    )

    elements.append(titulo_conclusao)

    elements.append(Spacer(1, 15))

    conclusao = Paragraph(
        f"""
        O repositório <b>{resultado['projeto']}</b>
        foi analisado utilizando critérios inspirados
        na norma ISO/IEC 25010.

        <br/><br/>

        A ferramenta executou análises estáticas de
        manutenibilidade e análises de confiabilidade,
        gerando um diagnóstico automatizado do projeto.

        <br/><br/>

        Os módulos avaliados permitem identificar:
        <br/>
        • Complexidade excessiva
        <br/>
        • Alto acoplamento entre classes
        <br/>
        • Duplicação de código
        <br/>
        • Falta de testes automatizados
        <br/>
        • Baixa cobertura de testes
        <br/>
        • Fragilidade nos testes unitários
        """,
        styles['BodyText']
    )

    elements.append(conclusao)

    # =====================================================
    # GERA PDF
    # =====================================================

    doc.build(elements)

    print("==============================")
    print("RELATÓRIO PDF GERADO")
    print("==============================")

    print("\nLocal:")
    print(caminho_pdf)
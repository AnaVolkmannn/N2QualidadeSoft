# N2 - Qualidade de Software - Prof Martim Diettele
## Grupo: Ana Claudia Volkmann, Pedro Henrique Schuch Garcia e João Pedro Sumi Bebber
### Este projeto tem como objetivo fazer uma análise de qualidade de um repositório Java via link do GitHub

#### Analyzers
- complexity.py: Análise de McCabe. O código escaneia o repositório baixado e para cada if, else ou elseif soma 1 ponto para a contagem. A menor pontuação possível é 1 ponto, já que você inicia com 1.

- coupling.py: Acoplamento entre Objetos (CBO). Mede a interdependência entre módulos (quantas classes únicas cada classe usa). Cada classe usada é um ponto. Estamos medindo apenas classes criadas manualmente. Classes que vem de bibliotecas prontas são descartadas, já que o objetivo da métrica é descobrir a interdependência do código pelas classes. Isso serve para detectar se o código teria muitas classes que quebrariam o projeto caso fossem alteradas e/ou removidas.
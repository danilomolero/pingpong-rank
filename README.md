# Ranking de Ping-Pong

Este é um aplicativo web desenvolvido em Python com a biblioteca Streamlit para acompanhar e analisar os resultados de partidas de ping-pong. O aplicativo lê os dados de uma planilha pública do Google Sheets, calcula um ranking dinâmico com um sistema de pontos e bônus, e exibe os resultados de forma interativa.

## ✨ Funcionalidades

O aplicativo é dividido em duas páginas principais:

### 1. Ranking Diário
- **Classificação Dinâmica:** Exibe o ranking dos jogadores, atualizado diariamente.
- **Histórico de Posições:** Mostra a mudança na posição de cada jogador em relação ao dia anterior (⬆️, ⬇️, ➖).
- **Destaques do Dia:**
    - **🏅 Jogador do Dia:** O jogador que mais somou pontos em um único dia.
    - **🦓 Maior Zebra (Upset):** A vitória mais surpreendente do dia, onde um jogador com menos pontos venceu um com mais pontos.
- **Histórico de Partidas:** Tabela com todos os jogos que ocorreram na data selecionada.

### 2. Análise de Jogadores
- **Estatísticas Individuais:** Permite selecionar um jogador e ver suas estatísticas detalhadas (total de jogos, vitórias, derrotas e taxa de vitória).
- **Confrontos Diretos:**
    - **😈 Maior Carrasco:** Mostra o adversário contra quem o jogador selecionado mais perdeu.
    - **😇 Maior Freguês:** Mostra o adversário que o jogador selecionado mais venceu.
- **Histórico Completo:** Exibe todas as partidas jogadas pelo atleta selecionado.

## 🚀 Como Executar o Projeto

Siga os passos abaixo para executar o aplicativo em sua máquina local.

### Pré-requisitos
- Python 3.8 ou superior
- `pip` (gerenciador de pacotes do Python)

### Instalação

1.  **Clone o repositório (ou baixe os arquivos):**
    ```bash
    git clone https://github.com/seu-usuario/seu-repositorio.git
    cd seu-repositorio
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    # Para Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Para macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    Crie um arquivo chamado `requirements.txt` com o seguinte conteúdo:
    ```
    streamlit
    pandas
    requests
    ```
    Em seguida, instale-as:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute o aplicativo Streamlit:**
    Supondo que seu arquivo Python se chame `app.py`:
    ```bash
    streamlit run app.py
    ```
    O aplicativo será aberto automaticamente no seu navegador.

## 📊 Fonte de Dados (Google Sheets)

O aplicativo busca os dados de uma planilha pública do Google Sheets. Para usar sua própria planilha, ela deve ser **pública na web** e seguir a estrutura de colunas abaixo:

| ID_Partida | Data       | Jogador_1 | Resultado_J1 | Resultado_J2 | Jogador_2 |
| :--------- | :--------- | :-------- | :----------- | :----------- | :-------- |
| 1          | 01/10/2023 | Alice     | 2            | 1            | Bob       |
| 2          | 01/10/2023 | Charlie   | 0            | 2            | David     |
| 3          | 02/10/2023 | Alice     | 2            | 0            | Charlie   |

- **ID_Partida:** Um identificador numérico único para cada partida. Essencial para processar os jogos na ordem correta dentro de um mesmo dia.
- **Data:** A data da partida no formato `dd/mm/aaaa`.
- **Jogador_1 / Jogador_2:** Nome dos jogadores.
- **Resultado_J1 / Resultado_J2:** O placar da partida (ex: 2 sets a 1).

Para usar sua planilha, altere a variável `sheet_id` no código:
```python
# Em load_data()
sheet_id = "SEU_ID_DA_PLANILHA_AQUI"
```

## 룰 Lógica de Pontuação

O sistema de ranking é cumulativo e baseado nas seguintes regras:

- **Pontuação Inicial:** Todo jogador começa com **1000** pontos.
- **Pontuação Padrão:**
    - Vitória: **+10** pontos.
    - Derrota: **-10** pontos (a pontuação de um jogador não pode ser negativa).
- **Bônus de Vitória (cumulativos):**
    - **Bônus de Upset (Zebra):** **+5** pontos se vencer um jogador que tinha mais pontos que você no início do dia.
    - **Bônus Top 3:**
        - **+25** pontos se vencer o jogador em 1º lugar no ranking.
        - **+20** pontos se vencer o jogador em 2º lugar no ranking.
        - **+15** pontos se vencer o jogador em 3º lugar no ranking.

**Importante:** Todos os bônus são calculados com base no ranking do **final do dia anterior**.

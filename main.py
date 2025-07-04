# --- IMPORTAÇÃO DE BIBLIOTECAS ---
# Importa as bibliotecas necessárias para o funcionamento do aplicativo.
import streamlit as st  # A biblioteca principal para criar a interface web do aplicativo.
import pandas as pd     # Fundamental para manipulação e análise de dados (planilhas, tabelas).
import datetime         # Para trabalhar com datas (não usado diretamente, mas o pandas o utiliza).
import requests         # Para fazer requisições HTTP e buscar dados da internet (no caso, da planilha).
import io               # Para tratar dados em memória como se fossem arquivos (usado para ler o CSV).


# --- CONFIGURAÇÃO DA PÁGINA ---
# Define as configurações iniciais da página do Streamlit.
# Esta função deve ser a primeira chamada do Streamlit no seu script.
st.set_page_config(
    page_title="Ranking de Ping-Pong",  # Título que aparece na aba do navegador.
    layout="wide",                      # "wide" faz o conteúdo ocupar toda a largura da tela.
    initial_sidebar_state="expanded"    # A barra lateral já começa aberta por padrão.
)

# --- CONSTANTES DE PONTUAÇÃO (ESCOPO GLOBAL) ---
# Definir constantes torna o código mais legível e fácil de manter.
# Se precisarmos alterar uma regra de pontuação, mudamos apenas aqui.
PONTOS_VITORIA = 10     # Pontos que um jogador ganha ao vencer uma partida.
PONTOS_DERROTA = -10    # Pontos que um jogador perde ao ser derrotado.
PONTOS_INICIAIS = 1000  # Pontuação com a qual todo novo jogador começa.
BONUS_TOP_1 = 25        # Bônus de pontos por vencer o jogador que está em 1º lugar no ranking.
BONUS_TOP_2 = 20        # Bônus de pontos por vencer o jogador que está em 2º lugar.
BONUS_TOP_3 = 15        # Bônus de pontos por vencer o jogador que está em 3º lugar.
BONUS_UPSET = 5         # Bônus por "zebra": quando um jogador com menos pontos vence um com mais pontos.


# --- FUNÇÕES DE CARREGAMENTO E CÁLCULO ---

# O decorator @st.cache_data é uma otimização poderosa do Streamlit.
# Ele armazena o resultado da função em cache. Se a função for chamada novamente
# com os mesmos parâmetros, o Streamlit retorna o resultado salvo em vez de
# executar a função de novo. Isso economiza tempo e recursos.
# O `ttl=600` (Time To Live) define que o cache expira após 600 segundos (10 minutos),
# forçando o app a buscar dados atualizados da planilha periodicamente.
@st.cache_data(ttl=600)
def load_data():
    """Carrega os dados da planilha pública do Google Sheets de forma robusta."""
    try:
        # Define os detalhes da planilha do Google Sheets.
        sheet_id = "1cqOvSiRjheDmX6z8p99rJRRL92uDwuWIPk2hu-hiE_c"
        sheet_name = "Página1"
        # Constrói a URL especial que permite baixar a planilha no formato CSV.
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        
        # Faz a requisição para obter os dados da URL.
        response = requests.get(csv_url)
        # Verifica se a requisição foi bem-sucedida (código 200). Se não, levanta um erro.
        response.raise_for_status()
        
        # Decodifica o conteúdo da resposta (que vem em bytes) para uma string de texto.
        content = response.content.decode('utf-8')
        
        # Usa o pandas para ler a string de texto como se fosse um arquivo CSV.
        # io.StringIO trata a string em memória como se fosse um arquivo, evitando criar arquivos temporários.
        df = pd.read_csv(io.StringIO(content))
        
        # --- Limpeza e Tratamento dos Dados ---
        # É uma boa prática limpar os dados logo após o carregamento.
        
        # Remove linhas que estão completamente vazias.
        df.dropna(how='all', inplace=True)
        # Converte a coluna 'Data' para o formato de data do pandas, tratando erros.
        # 'coerce' transforma datas inválidas em NaT (Not a Time).
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        # Converte as colunas de resultado para números inteiros.
        # 'coerce' transforma valores não numéricos em NaN (Not a Number).
        # '.fillna(0)' substitui os NaN por 0.
        df['Resultado_J1'] = pd.to_numeric(df['Resultado_J1'], errors='coerce').fillna(0).astype(int)
        df['Resultado_J2'] = pd.to_numeric(df['Resultado_J2'], errors='coerce').fillna(0).astype(int)
        # Remove quaisquer linhas onde a data não pôde ser convertida, garantindo a integridade.
        df.dropna(subset=['Data'], inplace=True)
        
        return df
    except Exception as e:
        # Se qualquer parte do bloco 'try' falhar, o código aqui é executado.
        # Isso evita que o aplicativo quebre e informa o usuário sobre o problema.
        st.error(f"Erro ao carregar dados: {e}")
        # Retorna um DataFrame vazio para que o resto do app não falhe.
        return pd.DataFrame()

def calculate_rankings(df):
    """Calcula os rankings diários e estatísticas detalhadas a partir do histórico de partidas."""
    # Verificação de segurança: se não houver dados, retorna estruturas vazias.
    if df.empty:
        return {}, {}, {}

    # Pega uma lista de todos os jogadores únicos, buscando nomes das colunas 'Jogador_1' e 'Jogador_2'.
    # '.values.ravel('K')' transforma as duas colunas em uma única lista de nomes.
    jogadores = pd.unique(df[['Jogador_1', 'Jogador_2']].values.ravel('K'))
    # Inicializa um dicionário para armazenar a pontuação de cada jogador.
    # Todos começam com a pontuação inicial definida na constante.
    pontuacoes = {jogador: PONTOS_INICIAIS for jogador in jogadores if pd.notna(jogador)}
    
    # Dicionários que irão armazenar o estado do ranking e as estatísticas ao final de cada dia.
    rankings_diarios = {}
    stats_diarias = {}
    # Obtém uma lista de todas as datas únicas em que ocorreram partidas, em ordem cronológica.
    datas_unicas = sorted(df['Data'].unique())

    # Itera sobre cada dia que teve partidas.
    for data_atual in datas_unicas:
        # Dicionário para rastrear quantos pontos cada jogador ganhou/perdeu *apenas neste dia*.
        pontos_ganhos_dia = {jogador: 0 for jogador in pontuacoes}
        # Obtém o ranking como estava *antes* das partidas do dia atual serem computadas.
        ranking_anterior = sorted(pontuacoes.items(), key=lambda item: item[1], reverse=True)
        # Cria um mapa (dicionário) do jogador para sua posição no ranking anterior. Ex: {'João': 1, 'Maria': 2}
        # Isso é crucial para calcular bônus de "upset" e bônus contra o Top 3.
        mapa_ranking_anterior = {jogador: i + 1 for i, (jogador, _) in enumerate(ranking_anterior)}

        # Filtra apenas as partidas que ocorreram na data atual e as ordena pelo ID.
        partidas_do_dia = df[df['Data'] == data_atual].sort_values(by='ID_Partida')

        # Itera sobre cada partida do dia para calcular os pontos.
        for _, partida in partidas_do_dia.iterrows():
            j1, j2 = partida['Jogador_1'], partida['Jogador_2']
            # Pula a partida se algum dos nomes dos jogadores estiver faltando.
            if pd.isna(j1) or pd.isna(j2): continue
            
            res1, res2 = partida['Resultado_J1'], partida['Resultado_J2']
            # Determina o vencedor e o perdedor da partida usando uma expressão condicional (ternário).
            vencedor, perdedor = (j1, j2) if res1 > res2 else (j2, j1)

            # Obtém a posição do vencedor e do perdedor no ranking do dia anterior.
            rank_vencedor = mapa_ranking_anterior.get(vencedor, len(jogadores) + 1)
            rank_perdedor = mapa_ranking_anterior.get(perdedor, len(jogadores) + 1)

            # Define a pontuação base para vitória e derrota.
            pontos_vencedor = PONTOS_VITORIA
            pontos_perdedor = PONTOS_DERROTA

            # Lógica de bônus:
            # Se o rank do vencedor era maior (pior) que o do perdedor, é um "upset".
            if rank_vencedor > rank_perdedor: pontos_vencedor += BONUS_UPSET
            # Adiciona bônus por vencer um jogador do Top 3.
            if rank_perdedor == 1: pontos_vencedor += BONUS_TOP_1
            elif rank_perdedor == 2: pontos_vencedor += BONUS_TOP_2
            elif rank_perdedor == 3: pontos_vencedor += BONUS_TOP_3
            
            # Atualiza a pontuação geral dos jogadores.
            pontuacoes[vencedor] += pontos_vencedor
            # Garante que a pontuação de um jogador nunca fique abaixo de zero.
            pontuacoes[perdedor] = max(0, pontuacoes.get(perdedor, 0) + pontos_perdedor)
            
            # Registra os pontos ganhos/perdidos *neste dia* para os destaques.
            pontos_ganhos_dia[vencedor] += pontos_vencedor
            pontos_ganhos_dia[perdedor] += pontos_perdedor

        # Ao final do dia, armazena o ranking atualizado (lista ordenada por pontos).
        rankings_diarios[data_atual] = sorted(pontuacoes.items(), key=lambda item: item[1], reverse=True)
        # Armazena também as estatísticas do dia (como os pontos ganhos).
        stats_diarias[data_atual] = {'pontos_ganhos': pontos_ganhos_dia}

    return rankings_diarios, stats_diarias, df

# --- PÁGINA PRINCIPAL: RANKING DIÁRIO ---
# Esta função é responsável por renderizar a primeira página do aplicativo.
def pagina_ranking_diario(rankings_por_dia, stats_diarias, df_partidas):
    # Define o título principal da página.
    st.title("🏆 Ranking Diário de Ping-Pong")
    st.markdown("Acompanhe a classificação e os destaques de cada dia de competição.")

    # Pega as datas disponíveis e as ordena da mais recente para a mais antiga.
    datas_disponiveis = sorted(rankings_por_dia.keys(), reverse=True)
    if not datas_disponiveis:
        st.warning("Não há dados de ranking para exibir.")
        return

    # Cria uma caixa de seleção para o usuário escolher uma data.
    data_selecionada = st.selectbox(
        "Selecione uma data para ver o ranking:",
        options=datas_disponiveis,
        # 'format_func' personaliza como as opções são exibidas para o usuário.
        # Aqui, transforma o objeto de data em uma string legível (dd/mm/aaaa).
        format_func=lambda date: pd.to_datetime(date).strftime('%d/%m/%Y')
    )

    # Se nenhuma data for selecionada, não faz mais nada.
    if not data_selecionada: return

    # --- DESTAQUES DO DIA ---
    st.header(f"Destaques de {pd.to_datetime(data_selecionada).strftime('%d de %B de %Y')}")
    
    # Busca os pontos ganhos no dia selecionado.
    pontos_dia = stats_diarias[data_selecionada]['pontos_ganhos']
    # Encontra o jogador que mais pontuou no dia.
    jogador_do_dia = max(pontos_dia, key=pontos_dia.get)
    pontos_jogador_dia = pontos_dia[jogador_do_dia]

    # Cria duas colunas para organizar os destaques lado a lado.
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏅 Jogador do Dia")
        # 'st.metric' é um componente visual para exibir números importantes.
        st.metric(label=jogador_do_dia, value=f"+{pontos_jogador_dia} pontos")

    # --- Lógica para Upset (Zebra) do Dia ---
    # Filtra as partidas do dia selecionado.
    partidas_dia = df_partidas[df_partidas['Data'] == data_selecionada]
    upsets = []
    
    # Encontra a data anterior à data selecionada para comparar os rankings.
    indice_data_atual = datas_disponiveis.index(data_selecionada)
    data_anterior = datas_disponiveis[indice_data_atual + 1] if indice_data_atual + 1 < len(datas_disponiveis) else None
    
    # Carrega a pontuação do dia anterior.
    if data_anterior:
        ranking_ontem_lista = rankings_por_dia.get(data_anterior, [])
        map_rank_ontem = dict(ranking_ontem_lista) # Converte a lista de tuplas em um dicionário {jogador: pontos}
    else:
        # Caso especial para o primeiro dia de competição, todos têm a pontuação inicial.
        todos_jogadores = pd.unique(df_partidas[['Jogador_1', 'Jogador_2']].values.ravel('K'))
        map_rank_ontem = {j: PONTOS_INICIAIS for j in todos_jogadores if pd.notna(j)}

    # Itera sobre as partidas do dia para identificar os upsets.
    for _, partida in partidas_dia.iterrows():
        j1, j2 = partida['Jogador_1'], partida['Jogador_2']
        res1, res2 = partida['Resultado_J1'], partida['Resultado_J2']
        if pd.isna(j1) or pd.isna(j2): continue
        
        vencedor, perdedor = (j1, j2) if res1 > res2 else (j2, j1)
        # Pega a pontuação do vencedor e do perdedor *antes* da partida (do dia anterior).
        pontos_vencedor = map_rank_ontem.get(vencedor, PONTOS_INICIAIS)
        pontos_perdedor = map_rank_ontem.get(perdedor, PONTOS_INICIAIS)
        
        # Se a pontuação do vencedor era menor que a do perdedor, é um upset.
        if pontos_vencedor < pontos_perdedor:
            diferenca = pontos_perdedor - pontos_vencedor
            upsets.append((diferenca, vencedor, perdedor))
    
    with col2:
        st.subheader("🦓 Maior Zebra (Upset)")
        if upsets:
            # Encontra o maior upset pela diferença de pontos.
            maior_upset = max(upsets, key=lambda item: item[0])
            st.markdown(f"**{maior_upset[1]}** venceu **{maior_upset[2]}**")
            st.markdown(f"Diferença de *{maior_upset[0]}* pontos")
        else:
            st.markdown("Nenhuma zebra neste dia.")

    st.markdown("---") # Linha horizontal para separar seções.

    # --- TABELA DE RANKING ---
    st.header("Classificação Geral")
    ranking_atual = rankings_por_dia[data_selecionada]
    ranking_anterior = {}
    if data_anterior:
        # Prepara o ranking anterior para comparar as posições.
        ranking_anterior_lista = rankings_por_dia.get(data_anterior, [])
        ranking_anterior = {jogador: i + 1 for i, (jogador, _) in enumerate(ranking_anterior_lista)}

    # Cria colunas com larguras personalizadas para alinhar a tabela do ranking.
    cols = st.columns([0.5, 3, 1.5, 1])
    cols[0].markdown("**Pos.**")
    cols[1].markdown("**Jogador**")
    cols[2].markdown("**Pontos**")
    cols[3].markdown("**Mudança**")
    
    # Itera sobre o ranking do dia selecionado para exibir cada jogador.
    for i, (jogador, pontos) in enumerate(ranking_atual):
        posicao_atual = i + 1
        posicao_anterior = ranking_anterior.get(jogador) # Pega a posição do jogador no dia anterior.
        
        # Lógica para determinar o ícone de mudança de posição.
        mudanca_str = "🆕" # 'Novo' se o jogador não estava no ranking anterior.
        if posicao_anterior:
            diff = posicao_anterior - posicao_atual # Posição anterior menor significa que subiu no ranking.
            if diff > 0: mudanca_str = f"⬆️ {diff}"
            elif diff < 0: mudanca_str = f"⬇️ {abs(diff)}"
            else: mudanca_str = "➖"
        
        # Exibe os dados do jogador nas colunas.
        cols = st.columns([0.5, 3, 1.5, 1])
        cols[0].metric(label="", value=f"#{posicao_atual}") # Metric sem label para alinhar melhor.
        cols[1].markdown(f"### {jogador}")
        cols[2].markdown(f"### {pontos}")
        cols[3].markdown(f"### {mudanca_str}")

    # --- HISTÓRICO DE PARTIDAS DO DIA ---
    st.markdown("---")
    st.header("Partidas do Dia")
    # Exibe um DataFrame do Pandas como uma tabela interativa.
    st.dataframe(partidas_dia[['Jogador_1', 'Resultado_J1', 'Resultado_J2', 'Jogador_2']], use_container_width=True)


# --- PÁGINA 2: ANÁLISE DE JOGADOR ---
# Esta função é responsável por renderizar a segunda página do aplicativo.
def pagina_analise_jogador(df_partidas):
    st.title("🔍 Análise de Jogadores")
    
    # Cria uma lista ordenada de todos os jogadores únicos.
    jogadores = sorted(pd.unique(df_partidas[['Jogador_1', 'Jogador_2']].values.ravel('K')))
    # Cria uma caixa de seleção para o usuário escolher um jogador.
    jogador_selecionado = st.selectbox("Selecione um jogador para analisar", jogadores)

    if not jogador_selecionado: return

    # Filtra o DataFrame para obter apenas as partidas do jogador selecionado.
    df_jogador = df_partidas[(df_partidas['Jogador_1'] == jogador_selecionado) | (df_partidas['Jogador_2'] == jogador_selecionado)]
    
    # Contagem de vitórias e derrotas.
    vitorias = 0
    derrotas = 0
    for _, row in df_jogador.iterrows():
        # Verifica se o jogador selecionado é o Jogador 1 e se sua pontuação foi maior.
        if (row['Jogador_1'] == jogador_selecionado and row['Resultado_J1'] > row['Resultado_J2']) or \
           (row['Jogador_2'] == jogador_selecionado and row['Resultado_J2'] > row['Resultado_J1']):
            vitorias += 1
        else:
            derrotas += 1
    
    total_jogos = vitorias + derrotas
    # Calcula a taxa de vitória, com uma verificação para evitar divisão por zero.
    taxa_vitoria = (vitorias / total_jogos * 100) if total_jogos > 0 else 0

    st.header(f"Estatísticas de {jogador_selecionado}")
    
    # Exibe as estatísticas principais em três colunas.
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Partidas", total_jogos)
    col2.metric("Vitórias", vitorias, "V")
    col3.metric("Derrotas", derrotas, "D")
    
    # Mostra a taxa de vitória em uma barra de progresso.
    st.progress(taxa_vitoria / 100)
    st.markdown(f"**Taxa de Vitória: {taxa_vitoria:.2f}%**")
    
    st.markdown("---")
    
    # --- Lógica de Carrasco e Freguês ---
    # Carrasco: adversário contra quem o jogador mais perdeu.
    # Freguês: adversário contra quem o jogador mais venceu.
    adversarios = {}
    for _, row in df_jogador.iterrows():
        # Identifica o adversário na partida.
        adversario = row['Jogador_2'] if row['Jogador_1'] == jogador_selecionado else row['Jogador_1']
        # Identifica o vencedor da partida.
        vencedor = row['Jogador_1'] if row['Resultado_J1'] > row['Resultado_J2'] else row['Jogador_2']
        
        # Se for o primeiro confronto com este adversário, inicializa seu registro.
        if adversario not in adversarios:
            adversarios[adversario] = {'vitorias': 0, 'derrotas': 0}
        
        # Contabiliza o resultado do confronto.
        if vencedor == jogador_selecionado:
            adversarios[adversario]['vitorias'] += 1
        else:
            adversarios[adversario]['derrotas'] += 1

    if adversarios:
        # Encontra o carrasco (maior número de derrotas para o jogador selecionado).
        carrasco = max(adversarios, key=lambda k: adversarios[k]['derrotas'])
        # Encontra o freguês (maior número de vitórias do jogador selecionado).
        fregues = max(adversarios, key=lambda k: adversarios[k]['vitorias'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("😈 Maior Carrasco")
            if adversarios[carrasco]['derrotas'] > 0:
                st.markdown(f"**{carrasco}** ({adversarios[carrasco]['derrotas']} derrotas)")
            else:
                st.markdown("Ninguém!")
        with col2:
            st.subheader("😇 Maior Freguês")
            if adversarios[fregues]['vitorias'] > 0:
                st.markdown(f"**{fregues}** ({adversarios[fregues]['vitorias']} vitórias)")
            else:
                st.markdown("Ninguém!")

    st.markdown("---")
    st.subheader("Histórico de Partidas")
    st.dataframe(df_jogador, use_container_width=True)


# --- NAVEGAÇÃO PRINCIPAL ---
# Função principal que organiza a execução do aplicativo.
def main():
    # 1. Carrega os dados das partidas.
    df_partidas = load_data()
    # Verificação crucial: se os dados não foram carregados, exibe um erro e para a execução.
    if df_partidas.empty:
        st.error("Não foi possível carregar os dados das partidas. Verifique a planilha ou a conexão com a internet.")
        return

    # 2. Processa os dados brutos para calcular todos os rankings e estatísticas.
    rankings_por_dia, stats_diarias, df_partidas = calculate_rankings(df_partidas)

    # 3. Cria o menu de navegação na barra lateral.
    st.sidebar.title("Navegação")
    pagina = st.sidebar.radio("Escolha uma página", ["Ranking Diário", "Análise de Jogadores"])

    # 4. Controla qual página é exibida com base na seleção do usuário no menu.
    if pagina == "Ranking Diário":
        pagina_ranking_diario(rankings_por_dia, stats_diarias, df_partidas)
    elif pagina == "Análise de Jogadores":
        pagina_analise_jogador(df_partidas)

# --- PONTO DE ENTRADA DO SCRIPT ---
# Este bloco de código garante que a função `main()` seja executada apenas quando
# o script é rodado diretamente (ex: `streamlit run seu_script.py`).
# É a porta de entrada padrão para a execução de um programa Python.
if __name__ == "__main__":
    main()

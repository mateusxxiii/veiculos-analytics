import streamlit as st
import pandas as pd
import altair as alt
import datetime

# --- Configuração da Página ---
st.set_page_config(
    layout="wide",
    page_title="Análise de Consultas Veiculares"
)

# --- Título da Aplicação ---
st.title("Análise de Veículos Consultados")
st.markdown("Use este painel para analisar os dados de consultas de veículos exportados.")

# --- Constantes (CORRIGIDAS) ---
# Listas limpas, sem caracteres de espaço inválidos
EXPECTED_COLS = [
    'Placa', 'UfJurisidicao', 'AnoFabricacao', 'COMBUSTIVEL',
    'COR', 'Nome', 'TIPOVEICULO'
]

NORMALIZED_COLS = [
    'placa', 'ufjurisidicao', 'anofabricacao', 'combustivel',
    'cor', 'nome', 'tipoveiculo'
]

# --- Funções Auxiliares ---

@st.cache_data
def convert_df_to_csv(df):
    """Converte um DataFrame para CSV (UTF-8) para download."""
    return df.to_csv(index=False).encode('utf-8')

def load_and_process_data(file):
    """
    Carrega o arquivo (Excel ou CSV), valida as colunas, normaliza
    e cria as colunas 'marca' e 'idade'.
    """
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file, engine='openpyxl')
        else:
            st.error("Formato de arquivo não suportado. Use .csv ou .xlsx")
            return None
            
        # Remove espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Validação de colunas
        missing_cols = [col for col in EXPECTED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"Erro: O arquivo não contém as colunas esperadas. Estão faltando: {', '.join(missing_cols)}")
            st.info(f"Colunas encontradas no arquivo: {', '.join(df.columns)}")
            return None

        # Seleciona e renomeia colunas
        df = df[EXPECTED_COLS].copy()
        df.columns = NORMALIZED_COLS

        # Transformações
        # 1. Criar 'marca' (primeira palavra do campo 'nome')
        df['marca'] = df['nome'].astype(str).str.split().str[0]
        
        # 2. Criar 'idade' (ano atual - ano de fabricação)
        current_year = datetime.datetime.now().year
        # Garante que anofabricacao seja numérico, tratando erros
        df['anofabricacao'] = pd.to_numeric(df['anofabricacao'], errors='coerce')
        df.dropna(subset=['anofabricacao'], inplace=True) # Remove linhas onde o ano não pôde ser lido
        df['anofabricacao'] = df['anofabricacao'].astype(int)
        
        df['idade'] = current_year - df['anofabricacao']
        
        st.success("Arquivo carregado e processado com sucesso!")
        return df

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
        return None

# --- Inicialização do Session State ---
if 'data' not in st.session_state:
    st.session_state.data = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# --- Seção de Upload ---
st.subheader("1. Carregar Arquivo de Dados")
uploaded_file = st.file_uploader(
    "Selecione um arquivo Excel (.xlsx) ou CSV (.csv)",
    type=['xlsx', 'csv']
)

# Botão para carregar dados
load_button = st.button("Carregar dados", type="primary")

if load_button and uploaded_file is not None:
    # Processa os dados quando o botão é clicado
    with st.spinner("Processando arquivo..."):
        df_processed = load_and_process_data(uploaded_file)
        if df_processed is not None:
            st.session_state.data = df_processed
            st.session_state.data_loaded = True
        else:
            st.session_state.data = None
            st.session_state.data_loaded = False
elif load_button and uploaded_file is None:
    st.warning("Por favor, envie um arquivo primeiro.")

# --- Lógica Principal da Aplicação ---
if st.session_state.data_loaded and st.session_state.data is not None:
    df = st.session_state.data
    
    # --- Barra Lateral de Filtros ---
    st.sidebar.header("Filtros da Análise")

    # Filtro de UF
    uf_list = sorted(df['ufjurisidicao'].unique())
    uf_filter = st.sidebar.multiselect(
        "Selecione a UF:", 
        options=uf_list, 
        default=uf_list
    )

    # Filtro de Tipo de Veículo
    tipo_list = sorted(df['tipoveiculo'].unique())
    tipo_filter = st.sidebar.multiselect(
        "Selecione o Tipo de Veículo:",
        options=tipo_list,
        default=tipo_list
    )

    # Filtro de Marca
    marca_list = sorted(df['marca'].unique())
    marca_filter = st.sidebar.multiselect(
        "Selecione a Marca:",
        options=marca_list,
        default=marca_list
    )

    # Filtro de Ano (Slider)
    min_ano, max_ano = int(df['anofabricacao'].min()), int(df['anofabricacao'].max())
    ano_filter = st.sidebar.slider(
        "Selecione a faixa de Ano de Fabricação:",
        min_value=min_ano,
        max_value=max_ano,
        value=(min_ano, max_ano)
    )

    # --- Aplicação dos Filtros ---
    df_filtered = df[
        (df['ufjurisidicao'].isin(uf_filter)) &
        (df['tipoveiculo'].isin(tipo_filter)) &
        (df['marca'].isin(marca_filter)) &
        (df['anofabricacao'] >= ano_filter[0]) &
        (df['anofabricacao'] <= ano_filter[1])
    ]

    # --- Painel Principal ---
    
    st.divider()
    st.subheader("2. Dashboard de Análise")

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
    else:
        # --- KPIs (Indicadores) ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        kpi1.metric(
            label="Total de Consultas Filtradas",
            value=f"{df_filtered.shape[0]:,}".replace(",", ".")
        )
        
        kpi2.metric(
            label="Marcas Distintas",
            value=df_filtered['marca'].nunique()
        )
        
        kpi3.metric(
            label="Tipos de Veículo Distintos",
            value=df_filtered['tipoveiculo'].nunique()
        )
        
        kpi4.metric(
            label="Idade Média dos Veículos (Anos)",
            value=f"{df_filtered['idade'].mean():.1f}"
        )

        st.divider()
        
        # --- Gráficos Interativos ---
        st.subheader("Análises Visuais")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico 1: Consultas por Tipo de Veículo
            st.markdown("##### Consultas por Tipo de Veículo")
            chart_tipo_data = df_filtered['tipoveiculo'].value_counts().reset_index()
            chart_tipo_data.columns = ['Tipo de Veículo', 'Total de Consultas']
            
            chart_tipo = alt.Chart(chart_tipo_data).mark_bar().encode(
                x=alt.X('Total de Consultas:Q', title='Total de Consultas'),
                y=alt.Y('Tipo de Veículo:N', title='Tipo de Veículo', sort='-x'),
                tooltip=['Tipo de Veículo', 'Total de Consultas']
            ).interactive()
            st.altair_chart(chart_tipo, use_container_width=True)

            # Gráfico 2: Top 20 Marcas mais Consultadas
            st.markdown("##### Top 20 Marcas Mais Consultadas")
            chart_marca_data = df_filtered['marca'].value_counts().nlargest(20).reset_index()
            chart_marca_data.columns = ['Marca', 'Total de Consultas']
            
            chart_marca = alt.Chart(chart_marca_data).mark_bar().encode(
                x=alt.X('Total de Consultas:Q', title='Total de Consultas'),
                y=alt.Y('Marca:N', title='Marca', sort='-x'),
                tooltip=['Marca', 'Total de Consultas']
            ).interactive()
            st.altair_chart(chart_marca, use_container_width=True)

        with col2:
            # Gráfico 3: Consultas por UF
            st.markdown("##### Consultas por UF")
            chart_uf_data = df_filtered['ufjurisidicao'].value_counts().reset_index()
            chart_uf_data.columns = ['UF', 'Total de Consultas']
            
            chart_uf = alt.Chart(chart_uf_data).mark_bar().encode(
                x=alt.X('Total de Consultas:Q', title='Total de Consultas'),
                y=alt.Y('UF:N', title='UF', sort='-x'),
                tooltip=['UF', 'Total de Consultas']
            ).interactive()
            st.altair_chart(chart_uf, use_container_width=True)

            # Gráfico 4: Distribuição da Idade dos Veículos
            st.markdown("##### Distribuição por Idade do Veículo")
            chart_idade_data = df_filtered['idade'].value_counts().sort_index().reset_index()
            chart_idade_data.columns = ['Idade', 'Total de Consultas']
            
            chart_idade = alt.Chart(chart_idade_data).mark_line(point=True).encode(
                x=alt.X('Idade:Q', title='Idade do Veículo (anos)'),
                y=alt.Y('Total de Consultas:Q', title='Total de Consultas'),
                tooltip=['Idade', 'Total de Consultas']
            ).interactive()
            st.altair_chart(chart_idade, use_container_width=True)

        # --- Tabela de Dados e Download ---
        st.divider()
        st.subheader("3. Dados Detalhados Filtrados")
        
        st.dataframe(df_filtered)
        
        csv_data = convert_df_to_csv(df_filtered)
        
        st.download_button(
            label="Baixar CSV filtrado",
            data=csv_data,
            file_name=f"dados_filtrados_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv',
        )

elif not st.session_state.data_loaded:
    st.info("Por favor, envie um arquivo .csv ou .xlsx e clique em 'Carregar dados' para iniciar a análise.")


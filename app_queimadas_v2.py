import streamlit as st
from streamlit_folium import folium_static
import streamlit_option_menu
from streamlit_option_menu import option_menu
from st_social_media_links import SocialMediaIcons
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import HeatMap, Fullscreen
from folium.features import FeatureGroup

# Configuração do Layout do APP
def layouts():
    st.set_page_config(
    page_title="Monitoramento de Queimadas em Itajubá-MG",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)
if __name__ == "__main__":
    layouts()

def load_data():
    anos = ['19', '20', '21', '22', '23', '24']
    df_queimadas = pd.read_excel('dataset/QUEIMADAS_2019_2024_TOTAL.xlsx')
    lim_itajuba = gpd.read_file("dataset/itajuba.shp")
    # Converter para datetime
    df_queimadas['Data'] = pd.to_datetime(df_queimadas['Data'], errors='coerce')
    # Usar Data como índice (DatetimeIndex)
    df_queimadas.set_index('Data', inplace=True)
    # Criar coluna de contagem
    df_queimadas['Número de Focos'] = 1
    # Garantir que Latitude e Longitude sejam numéricos e remover linhas inválidas
    df_queimadas['Latitude'] = pd.to_numeric(df_queimadas['Latitude'], errors='coerce')
    df_queimadas['Longitude'] = pd.to_numeric(df_queimadas['Longitude'], errors='coerce')
    df_queimadas = df_queimadas.dropna(subset=['Latitude', 'Longitude'])
    df_queimadas['Bairro'] = df_queimadas['Bairro'].str.strip()
    return anos, df_queimadas, lim_itajuba
anos, df_queimadas, lim_itajuba = load_data()


# Função para calcular focos anuais por bairro
def calcular_focos_anual(df_queimadas):
    df_queimadas["Ano"] = df_queimadas.index.year  # Criar coluna de ano
    df_ano = df_queimadas.groupby(["Ano", "Bairro"])["Número de Focos"].sum().reset_index()
    list_bairros = sorted(df_queimadas["Bairro"].unique()) # Ordenar bairros alfabeticamente
    list_anos = sorted(df_ano["Ano"].unique())  # Ordenar anos
    return df_ano, list_bairros, list_anos
df_ano, list_bairros, list_anos = calcular_focos_anual(df_queimadas)

# Função para calcular o acumulado total de focos de queimadas em Itajubá
def calcular_sazonalidade_focos(df_queimadas):
    df_focos_totais_itajuba = df_queimadas.resample('ME')['Número de Focos'].sum().reset_index()
    df_focos_totais_itajuba['Mês'] = df_focos_totais_itajuba['Data'].dt.month

    map_meses = {1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio', 6: 'junho',
                         7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'}
    
    df_focos_totais_itajuba['Mês'] = df_focos_totais_itajuba['Mês'].map(map_meses)
    df_focos_totais_itajuba['Ano'] = df_focos_totais_itajuba['Data'].dt.year

    df_mensal_anual = df_focos_totais_itajuba.copy()
    df_mensal_anual = df_mensal_anual[['Data', 'Mês', 'Ano', 'Número de Focos']]
    df_mensal_total = df_mensal_anual.groupby("Mês")["Número de Focos"].sum().reset_index()
    
    # Ordenando os meses na sequência correta
    list_meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    df_mensal_total["Mês"] = pd.Categorical(df_mensal_total["Mês"], categories=list_meses, ordered=True)
    df_mensal_total = df_mensal_total.sort_values("Mês")
    return df_mensal_anual, df_mensal_total

df_mensal_anual, df_mensal_total = calcular_sazonalidade_focos(df_queimadas)


# Gráfico acumulado por mês e ano
df_queimadas['Ano'] = df_queimadas.index.year
df_queimadas['Mês'] = df_queimadas.index.month
df_mes_ano = df_queimadas.groupby(['Ano', 'Mês'])['Número de Focos'].sum().reset_index()
df_mes_ano['Mês/Ano'] = df_mes_ano['Ano'].astype(str) + '-' + df_mes_ano['Mês'].astype(str).str.zfill(2)
df_mes_ano = df_mes_ano.sort_values(['Ano', 'Mês'])


fig_mes_ano = px.bar(
    df_mes_ano,
    x='Mês/Ano',
    y='Número de Focos',
    title='Acumulado de Queimadas por Mês/Ano',
    color_discrete_sequence=['red']
)

fig_mes_ano.update_layout(hoverlabel=dict(font_size=12, font_color="white"))


# Gráfico de distribuição anual e total de focos de queimadas em Itajubá
fig_saz = go.Figure()

# Adicionando o gráfico de barras (total de cada mês)
fig_saz.add_trace(go.Bar(
    x=df_mensal_total["Mês"],
    y=df_mensal_total["Número de Focos"],
    name="Total",
    marker_color="#FF0000"
))

lista_cores = ["#FFFF00", "#1ce001", "#1E90FF", "#FFFFFF", "#FF00FF", "#FF8C00"]
for i, ano in enumerate(df_mensal_anual["Ano"].unique()):
    df_total_ano = df_mensal_anual[df_mensal_anual['Ano'] == ano]
    fig_saz.add_trace(go.Scatter(
        x=df_total_ano['Mês'],
        y=df_total_ano['Número de Focos'],
        mode='lines+markers',
        name=str(ano),
        line=dict(color=lista_cores[i], width=2)
        ))
    
# Ajuste de layout
fig_saz.update_layout(
    title='Focos de Queimadas por Mês - Comparativo Anual',
    xaxis=dict(title='Mês', tickmode='linear'),
    yaxis_title='Número de Focos',
    hovermode='x unified',
    legend_title='Legenda',
    barmode='overlay',
    hoverlabel=dict(font_size=12, font_color="white")
    )

#Cálculo do acumulado total de queimadas por bairro
def calcular_focos_total(df_queimadas):
    df_total_bairros = df_queimadas.groupby('Bairro', as_index=False)['Número de Focos'].sum() #Soma dos focos por bairros
    df_total_bairros['Ano'] = 'Total'  # Indica que é o total do período analisado
    return df_total_bairros
df_total_bairros = calcular_focos_total(df_queimadas)

# Novo seletor de número de bairros (substituindo o slider)



# Gráfico acumulado por Natureza
if 'Natureza' in df_queimadas.columns:
    df_natureza = df_queimadas.groupby('Natureza')['Número de Focos'].sum().reset_index()
    df_natureza = df_natureza.sort_values(by='Número de Focos', ascending=True)
    fig_natureza = px.bar(
        df_natureza,
        x='Número de Focos',
        y='Natureza',
        title='Acumulado de Queimadas por Natureza',
        color_discrete_sequence=['red'],
        width=1200,
        height=600
)

# Plotagem do MAPA
def plot_mapa(ano_selecionado="TOTAL"):
    # Filtrar dados conforme o ano selecionado
    if ano_selecionado == "TOTAL":
        df_filtrado = df_queimadas
    else:
        df_filtrado = df_queimadas[df_queimadas.index.year == ano_selecionado]

    # Criando o mapa utilizando o Folium
    map = folium.Map(location=[-22.44, -45.40], zoom_start=11.0)

    # Convertendo o contorno do município para o formato GeoJSON
    lim_itajuba_geojson = lim_itajuba.__geo_interface__
    folium.GeoJson(lim_itajuba_geojson, name="Limites de Itajubá/MG", style_function=lambda x: {'color': 'black', 'weight': 2, 'fillOpacity': 0}).add_to(map)

    # Criando o HeatMap para plotagem com dados filtrados
    heat_data = df_filtrado[['Latitude', 'Longitude']].values.tolist()

    # Adicionando o HeatMap no mapa
    HeatMap(heat_data, radius=10, name="Mapa de Calor", blur=10).add_to(map)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(map)

    # Adicionando marcadores
    marker_group = folium.FeatureGroup(name="Focos de Queimadas")

    for idx, row in df_filtrado.iterrows():
        popup_text = f"""
        <b>Endereço:</b> {row['Rua/Avenida/Rodovia']}<br>
        <b>Data:</b> {idx.strftime('%d/%m/%Y')}<br>
        <b>lat:</b> {row['Latitude']}<br>
        <b>lon:</b> {row['Longitude']}
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="red", icon="fire", icon_color="white")
        ).add_to(marker_group)

    # Adicionando o grupo de marcadores no mapa
    marker_group.add_to(map)

    # Adicionando o Layer Control
    folium.LayerControl(position="topright").add_to(map)
    
    # Adicionando a opção de tela cheia
    Fullscreen().add_to(map)
    return map

# Exibindo o mapa no Streamlit
if __name__ == "__main__":
    plot_mapa()

# CSS customizado para mudar cor e borda do st.metric
st.markdown(
    """
    <style>
    /* Caixa do st.metric */
    div[data-testid="stMetric"] {
        background-color: #5f705e; /* fundo customizado */
        padding: 15px;
        border-radius: 15px;
        border: 2px solid transparent;
        border-image: linear-gradient(45deg, #34322f, #76716b) 1; /* borda em gradiente */
        color: white; /* cor do texto */
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4); /* sombra */
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }

    /* Efeito hover */
    div[data-testid="stMetric"]:hover {
        transform: scale(1.03); /* cresce um pouquinho */
        box-shadow: 0px 6px 18px rgba(0,0,0,0.6);
    }

    /* Valor principal */
    div[data-testid="stMetricValue"] {
        color: #FFFFFF; /* branco */
        font-size: 28px;
        font-weight: bold;
    }

    /* Label */
    div[data-testid="stMetricLabel"] {
        color: #DDDDDD; 
        font-size: 16px;
    }

    /* Delta */
    div[data-testid="stMetricDelta"] {
        color: #00FF00 !important; /* verde claro */
        font-weight: bold; svg {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Criando interface para visualização do APP
horizontal_bar = "<hr style='margin-top: 0; margin-bottom: 0; height: 1px; border: 1px solid #FF9100DA;'><br>"    
# Inicializar session_state para controlar a página ativa
if 'current_page' not in st.session_state:
    st.session_state.current_page = None

# Sidebar com botões
with st.sidebar:
    selected = option_menu(
        menu_title="Navegação",
        options=["Início", "Variação sazonal", "Bairros e Natureza", "Mapa"],
        icons=["house", "bar-chart", "geo-alt", "map"],
        menu_icon="cast",
        default_index=0,
    )

# Mostrar conteúdo dependendo da aba
if selected == "Início":
    # Título principal
    st.subheader("🔥 Monitoramento de Queimadas em Itajubá/MG")

        # Mensagem de introdução com fonte menor (só aparece no Início)
    st.markdown(
        """
        <p style="font-size:15px;">
        Este aplicativo apresenta uma análise interativa sobre os focos de queimadas em <b>Itajubá/MG</b> entre 2019 e 2024.<br>
        Você pode navegar entre as seções usando os botões ao lado esquerdo da tela:
        </p>
        <ul style="font-size:15px;">
        <li>📈 <b>Variação sazonal</b>: mostra como as queimadas variam ao longo dos meses e anos.</li>
        <li>📍 <b>Bairros e natureza</b>: distribuição dos focos por bairros e pela natureza do evento.</li>
        <li>🗺️ <b>Mapa</b>: exibe um mapa interativo com os focos de queimadas, incluindo mapa de calor e marcadores.</li>
        </ul>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    st.markdown(
        """
        <p style="font-size:15px;">
            Maiores ocorrências:
        </p>
        """,
        unsafe_allow_html=True
    )

    # --- Indicadores principais ---
    col1, col2, col3, col4 = st.columns(4)

    # 1. Bairro com mais queimadas
    bairro_top = df_total_bairros.loc[df_total_bairros["Número de Focos"].idxmax()]
    col1.metric(
        label="🏘️ Bairro",
        value=bairro_top["Bairro"],
        delta=f"{bairro_top['Número de Focos']} focos",
        label_visibility="visible",
        border=True
    )

    # 2. Natureza com mais queimadas (se existir a coluna)
    if "Natureza" in df_queimadas.columns:
        natureza_top = df_queimadas.groupby("Natureza")["Número de Focos"].sum().idxmax()
        natureza_val = df_queimadas.groupby("Natureza")["Número de Focos"].sum().max()
        col2.metric(
            label="🏙️ Natureza",
            value=natureza_top,
            delta=f"{natureza_val} focos", 
            label_visibility="visible",
            border=True
        )
    else:
        col2.metric("🏙️ Natureza", "Dados indisponíveis")

    # 3. Mês com mais ocorrências (histórico)
    mes_top = df_mensal_total.loc[df_mensal_total['Número de Focos'].idxmax(), 'Mês']
    total_mes_top = df_mensal_total.loc[df_mensal_total['Número de Focos'].idxmax(), 'Número de Focos']

    col3.metric(
        label="📅 Mês",
        value=mes_top.capitalize(),
        delta=f"{total_mes_top} focos",
        label_visibility="visible",
        border=True
    )

    # 4. Ano com mais queimadas
    ano_top = df_queimadas.groupby("Ano")["Número de Focos"].sum().idxmax()
    ano_val = df_queimadas.groupby("Ano")["Número de Focos"].sum().max()
    col4.metric(
        label="📆 Ano",
        value=str(ano_top),
        delta=f"{ano_val} focos",
        label_visibility="visible",
        border=True
    )

    st.markdown("---")


# Atualizar session_state com base no botão clicado
if selected == "Variação sazonal":
    st.subheader("Distribuição Mensal dos Focos de Queimadas")
    st.plotly_chart(fig_mes_ano, use_container_width=True)
    st.plotly_chart(fig_saz, use_container_width=True)
    st.markdown(horizontal_bar, True)

if selected == "Bairros e Natureza":
    st.subheader("Distribuição Anual dos Focos de Queimadas por Bairro e Natureza")

    # Usando colunas para controlar a largura
    col1, col2, col3 = st.columns([1.2, 2, 1])
    
    with col1:  # Coluna do meio (3x mais larga que as laterais)
    # Seletor de número de bairros
        num_bairros = st.selectbox(
            "Selecione o número de bairros a exibir:",
            options=[10, 20, 30, 40, 50],
            index=0,
            key="num_bairros_selector"
        )
    
    # Criar gráfico de bairros dinamicamente
    if 'Bairro' in df_queimadas.columns:
        df_top_bairros = df_total_bairros.sort_values(by="Número de Focos", ascending=True).tail(num_bairros)
        
        fig_bairro = px.bar(
            df_top_bairros,
            x="Número de Focos",
            y="Bairro", 
            orientation="h",
            title=f"Top {num_bairros} Bairros com Maior Número de Focos ({list_anos[0]}-{list_anos[-1]})",
            color_discrete_sequence=['red'],
            width=1200,
            height=600
        )
        
        fig_bairro.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            hoverlabel=dict(font_size=12, font_color="white")
        )
        
        st.plotly_chart(fig_bairro, use_container_width=True)
    
    st.plotly_chart(fig_natureza, use_container_width=True)
    st.markdown(horizontal_bar, True)


if selected == "Mapa":

    st.subheader("Mapa de Calor dos Focos de Queimadas em Itajubá/MG")
    
    # Caixa de seleção para anos - com layout ajustado
    opcoes_ano = ["TOTAL"] + sorted(df_queimadas.index.year.unique())
    
    # Usando colunas para controlar a largura
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:  # Coluna do meio (3x mais larga que as laterais)
        ano_selecionado = st.selectbox(
            "Selecione o ano para visualizar:",
            options=opcoes_ano,
            index=0,  # "TOTAL" como padrão
            key="ano_selector"
        )
    
    # Exibir título com ano selecionado
    if ano_selecionado == "TOTAL":
        st.markdown(f"**Período completo: 2019-2024**")
    else:
        st.markdown(f"**Ano selecionado: {ano_selecionado}**")
    
    # Plotar mapa com filtro de ano
    mapa = plot_mapa(ano_selecionado)  
    folium_static(mapa, width=800, height=500)
    st.markdown(horizontal_bar, True)

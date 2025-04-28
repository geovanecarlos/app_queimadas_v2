import streamlit as st
from streamlit_folium import folium_static
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

# Carregando os dados
@st.cache_data
def load_data():
    anos = ['19', '20', '21', '22'] # Adicionando a coluna total dos focos
    df_2019_2022 = pd.read_excel('dataset/QUEIMADAS_2019_2022_LOCAL.xlsx')
    lim_itajuba = gpd.read_file("dataset/itajuba.shp")
    df_queimadas = pd.read_excel("dataset/QUEIMADAS_2019_2022.xlsx")
    df_queimadas['Data'] = pd.to_datetime(df_queimadas['Data'], format='%Y') # transformar as datas em datetime
    df_queimadas.set_index('Data', inplace=True) # definir a coluna de tempo como index do DataFrame
    df_queimadas['Número de Focos'] = int(1)
    df_queimadas = df_queimadas[df_queimadas["Bairro - Cidade"].astype(str).str.strip() != "SD"] # dropando os dados "SD: sem definição"
    df_queimadas['cidade'] = df_queimadas['Bairro - Cidade'].str.split(' - ').str[1].str.strip() # Extraindo infos de Itajubá
    df_queimadas = df_queimadas[df_queimadas['cidade'] == 'Itajubá'].drop(columns=['cidade']) 
    df_queimadas['Bairro - Cidade'] = df_queimadas['Bairro - Cidade'].str.split('-').str[0] # Selecionando os nomes dos bairros
    df_queimadas = df_queimadas[["Bairro - Cidade", "Número de Focos"]] # Filtrando as colunas dos Bairros
    df_queimadas = df_queimadas.rename(columns={'Bairro - Cidade': 'Bairro'}) # Renomenando a coluna para Bairro
    return anos, df_queimadas, lim_itajuba, df_2019_2022

anos, df_queimadas, lim_itajuba, df_2019_2022 = load_data()

#Cálculo do acumulado total de queimadas por bairro
def calcular_focos_total(df_queimadas):
    df_total_bairros = df_queimadas.groupby('Bairro', as_index=False)['Número de Focos'].sum() #Soma dos focos por bairros
    df_total_bairros['Ano'] = 'Total'  # Indica que é o total do período analisado
    return df_total_bairros

# Processamento dos dados (inserindo o valor 0 nos meses sem registros de QUEIMADAS)
def calcular_focos_mensal(df_queimadas):
    df_queimadas["Mês/Ano"] = df_queimadas.index.to_period("M")  # Criando coluna Mês/Ano
    df_grouped = df_queimadas.groupby(["Mês/Ano", "Bairro"])["Número de Focos"].sum().reset_index()
    meses = pd.period_range(df_queimadas.index.min(), df_queimadas.index.max(), freq="M")  # Lista dos meses do início ao fim (resolução mensal)
    bairros = sorted(df_queimadas["Bairro"].unique()) # Lista de bairros únicos
    df_completo = pd.MultiIndex.from_product([meses, bairros], names=["Mês/Ano", "Bairro"]).to_frame(index=False) # Agrupando os meses e bairros em um df 
    df_final = df_completo.merge(df_grouped, on=["Mês/Ano", "Bairro"], how="left").fillna(0)  # Preenchendo os meses sem registros com 0
    df_final["Mês/Ano"] = df_final["Mês/Ano"].astype(str)  # Converter para string para facilitar o plot
    df_final["Número de Focos"] = df_final["Número de Focos"].astype(int)  # Garantir tipo inteiro para gráfico
    return df_final

# Função para calcular focos anuais por bairro
def calcular_focos_anual(df_queimadas):
    df_queimadas["Ano"] = df_queimadas.index.year  # Criar coluna de ano
    df_ano = df_queimadas.groupby(["Ano", "Bairro"])["Número de Focos"].sum().reset_index()
    list_bairros = sorted(df_queimadas["Bairro"].unique()) # Ordenar bairros alfabeticamente
    list_anos = sorted(df_ano["Ano"].unique())  # Ordenar anos
    return df_ano, list_bairros, list_anos

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

#Processando os dados
df_total_bairros = calcular_focos_total(df_queimadas)
df_grouped = calcular_focos_mensal(df_queimadas)
df_ano, list_bairros, list_anos = calcular_focos_anual(df_queimadas)
df_mensal_anual, df_mensal_total= calcular_sazonalidade_focos(df_queimadas)

#configurações da sidebar
with st.sidebar:
    st.subheader("Configurações") 

# Função para plotagem do gráficos
tab1, tab2, tab3 = st.tabs(["📃Início", "📊Gráficos", "🗺️Mapa"])

with tab1:
    def introducao():
        st.subheader('Caracterização das Queimadas no Município de Itajubá, MG')
        with st.expander("Informações:", expanded=True):
            horizontal_bar = "<hr style='margin-top: 0; margin-bottom: 0; height: 1px; border: 1px solid #ff9793;'><br>"    
            st.markdown(
                """
                - Os resultados deste dashboard podem ser observados no artigo:  
                [__Caracterização das Queimadas no Município de Itajubá, MG__](https://periodicos.ufpe.br/revistas/index.php/rbgfe/article/view/262758), publicado na *Revista Brasileira de Geografia Física* em 2025.
                
                - Os dados de focos de queimadas em Itajubá-MG são provenientes do **Corpo de Bombeiros de Itajubá**  
                e referem-se ao período entre **2019 e 2022**.
                """
            )

            st.markdown(horizontal_bar, True)
            
            st.markdown(""" 
            Podem ser observados:
            1. Acumulado anual e total de focos de queimadas por bairro.
            2. Distribuição mensal de focos de queimadas por bairro.
            3. Acumulado mensal e total de focos de queimadas em Itajubá.
            4. Distribuição espacial total dos focos de queimadas em Itajubá.
                        """)
            st.markdown(horizontal_bar, True)
                        
    if __name__ == "__main__":
        introducao()

with tab2:
    def plot_graficos():     
        #Gráfico do total de queimadas por bairro durante o período
        num_bairros = st.sidebar.slider("Escolha o número de bairros", min_value=10, max_value=60, value=20)
        df_top_bairros = df_total_bairros.sort_values(by="Número de Focos", ascending=True).reset_index(drop=True)[-num_bairros:] #Escolhendo ps n bairros com maiores focos
        fig_01 = px.bar(df_top_bairros,
                        x="Número de Focos",
                        y="Bairro", 
                        orientation="h",
                        title=f"Acumulado de focos de queimadas por bairro: {list_anos[0]} - {list_anos[-1]}",
                        width=1200,
                        height=600
        )

        fig_01.update_traces(hovertemplate="<br>".join(["Número de Focos: %{x}","Bairro: %{y}"]),
                            textfont_size=14,
                            textangle=0,
                            textposition="outside",
                            cliponaxis=False,
                            marker_color='#FF0000',
                            marker_line_color='#FF0000',
                            marker_line_width=1.5,
                            opacity=0.6
        )

        #Gráfico do total de queimadas por bairro durante o período
        # Criar filtro no sidebar
        ano_selecionado = st.sidebar.selectbox("📆 Selecione o ano", list_anos)
        bairro_selecionado = st.sidebar.selectbox("🏡 Selecione um bairro", list_bairros)

        # Filtrar os dados para o ano selecionado
        df_anual_filtrado = df_ano[df_ano["Ano"] == ano_selecionado]
        df_anual_filtrado = df_anual_filtrado.sort_values(by="Número de Focos", ascending=True).reset_index(drop=True)[-num_bairros:] #Escolhendo ps n bairros com maiores focos

        # Criar gráfico de barras anual
        fig_02= px.bar(df_anual_filtrado,
                    x="Número de Focos",
                    y="Bairro", 
                    orientation="h",
                    title=f"Acumulado de focos de queimadas por bairro em {ano_selecionado}",
                    width=1200,
                    height=600
                    )

        fig_02.update_traces(hovertemplate="<br>".join(["Número de Focos: %{x}","Bairro: %{y}"]),
                            textfont_size=14,
                            textangle=0,
                            textposition="outside",
                            cliponaxis=False,marker_color='#FF0000',
                            marker_line_color='#FF0000',
                            marker_line_width=1.5,
                            opacity=0.6
                            )
        
        # Gráfico do número de queimadas por bairro/mês
        # Filtrar os dados para o bairro selecionado
        df_filtrado = df_grouped[df_grouped["Bairro"] == bairro_selecionado]

        # Gráfico de barras
        fig_03 = px.bar(
            df_filtrado, 
            x="Mês/Ano", 
            y="Número de Focos",
            title=f"Distribuição Mensal dos Focos de Queimadas no Bairro {bairro_selecionado}",
            hover_data={"Mês/Ano": True, "Número de Focos": True},
            width=1200, 
            height=400   
    )
        
        # Personalizando o texto do pop-up
        fig_03.update_traces(hovertemplate="<br>".join(["Mês/Ano: %{x}","Número de Focos: %{y}"]),
                            textfont_size=14,
                            textangle=0,
                            textposition="outside",
                            cliponaxis=False,
                            marker_color='#FF0000',
                            marker_line_color='#FF0000',
                            marker_line_width=1.5,
                            opacity=0.6
        )  

        # Gráfico de distribuição anual e total de focos de queimadas em Itajubá
        fig_04 = go.Figure()

        # Adicionando o gráfico de barras (total de cada mês)
        fig_04.add_trace(go.Bar(
            x=df_mensal_total["Mês"],
            y=df_mensal_total["Número de Focos"],
            name="Total",
            marker_color="rgb(250, 76, 76)"
        ))

        lista_cores = ["#FFFF00", "#1ce001", "#1E90FF", "#FFFFFF"]
        for i, ano in enumerate(df_mensal_anual["Ano"].unique()):
            df_total_ano = df_mensal_anual[df_mensal_anual['Ano'] == ano]
            fig_04.add_trace(go.Scatter(
                x=df_total_ano['Mês'],
                y=df_total_ano['Número de Focos'],
                mode='lines+markers',
                name=str(ano),
                line=dict(color=lista_cores[i], width=2)
                ))
            
        # Ajuste de layout
        fig_04.update_layout(
            title='Focos de Queimadas por Mês - Comparativo Anual',
            xaxis=dict(title='Mês', tickmode='linear'),
            yaxis_title='Número de Focos',
            hovermode='x unified',
            legend_title='Legenda',
            barmode='overlay')

        # Exibindo os gráficos 01 e 02 lado a lado
        st.subheader("Distribuição Anual dos Focos de Queimadas por Bairro")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_01, use_container_width=True)
        with col2:
            st.plotly_chart(fig_02, use_container_width=True)
        #Exibindo o gráfico 03
        st.subheader("Distribuição Mensal dos Focos de Queimadas por Bairro")
        st.plotly_chart(fig_03, use_container_width=True)
        #Exibindo o gráfico 04
        st.subheader("Distribuição Anual dos Focos de Queimadas em Itajubá-MG")
        st.plotly_chart(fig_04, use_container_width=True)

    # Exibindo os gráficos no Streamlit
    if __name__ == "__main__":
        plot_graficos()

with tab3:
    # Plotagem do MAPA
    def plot_mapa():
        # Convertendo o contorno do município para o formato GeoJSON
        lim_itajuba_geojson = lim_itajuba.__geo_interface__
        # Criando o mapa utilizando o Folium
        map = folium.Map(location=[ -22.44, -45.40], zoom_start=11.0)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Esri Satellite',
            overlay=False,
            control=True
        ).add_to(map)

        lim_itajuba_geojson = lim_itajuba.__geo_interface__
        folium.GeoJson(lim_itajuba_geojson, name="Limites de Itajubá/MG", style_function=lambda x: {'color': 'black', 'weight': 2, 'fillOpacity': 0}).add_to(map)

        # Criando o HeatMap para plotagem
        heat_data = df_2019_2022[['latitude', 'longitude']].values.tolist()

        # Adicionando o HeatMap no mapa
        HeatMap(heat_data, radius=10, name="Mapa de Calor", blur=10).add_to(map)

        # Adicionando marcadores
        marker_group = folium.FeatureGroup(name="Focos de Queimadas")

        for idx, row in df_2019_2022.iterrows():
             popup_text = f"""
             Endereço: {row['Endereço']}<br>
             Data: {row.get('Data', 'Sem Data')}<br>  
             lat: {row['latitude']}<br>
             lon: {row['longitude']}        
            """
             
             folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color="red", icon="fire", icon_color="white")
            ).add_to(marker_group)

        # # Adicionando o grupo de marcadores no mapa
        marker_group.add_to(map)

        # Adicionando o Layer Control
        folium.LayerControl(position="topright").add_to(map)
        
        # Adicionando a opção de tela cheia
        Fullscreen().add_to(map)

        # Exibindo o mapa no Streamlit
        st.subheader("Mapa de Calor dos Focos de Queimadas em Itajubá/MG - 2019-2022")

        folium_static(map, width=850, height=400)

    # Exibindo o mapa no Streamlit
    if __name__ == "__main__":
        plot_mapa()

#configurações da sidebar
with st.sidebar:
    st.markdown("---")

    st.markdown(
        """
        <style>
        .custom-text {
            color: #ffffff;
            font-size: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<h6 class="custom-text">Desenvolvido por <a href="https://www.linkedin.com/in/geovanecarlos" target="_blank" style="color: #ffffff;"> Geovane Carlos</a></h6>',
        unsafe_allow_html=True
    )

    social_media_links = ["https://www.linkedin.com/in/geovanecarlos", "https://github.com/geovanecarlos"]
    social_media_icons = SocialMediaIcons(social_media_links)
    social_media_icons.render()
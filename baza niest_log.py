import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# --- KONFIGURACJA ---
st.set_page_config(page_title="Magazyn Pro v3", layout="wide", page_icon="📊")

@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
    except Exception as e:
        st.error("Błąd połączenia z bazą danych.")
        return None

supabase = init_connection()

# --- POBIERANIE DANYCH ---
def get_full_data():
    res = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute()
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    df['Kategoria'] = df['Kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
    df['Wartość'] = df['liczba'] * df['Cena']
    return df

st.title("📦 System Magazynowy z Analityką")

df_main = get_full_data()

tabs = st.tabs(["📋 Lista", "➕ Dodaj", "📊 Analiza", "📂 Kategorie"])

# --- TAB: LISTA ---
with tabs[0]:
    if not df_main.empty:
        st.dataframe(df_main[['id', 'nazwa', 'liczba', 'Cena', 'Kategoria']], use_container_width=True)
    else:
        st.info("Baza jest pusta.")

# --- TAB: DODAWANIE (uproszczone dla czytelności) ---
with tabs[1]:
    with st.form("add_form"):
        st.write("Dodaj nowy produkt")
        # ... (tutaj kod formularza z poprzedniej wersji) ...
        st.form_submit_button("Zapisz")

# --- TAB: ANALIZA (NOWOŚĆ) ---
with tabs[2]:
    if not df_main.empty:
        st.subheader("Wizualizacja Stanów Magazynowych")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Ilość produktów według kategorii**")
            fig_qty = px.bar(
                df_main.groupby("Kategoria")["liczba"].sum().reset_index(),
                x="Kategoria",
                y="liczba",
                color="Kategoria",
                text_auto=True,
                template="plotly_white"
            )
            st.plotly_chart(fig_qty, use_container_width=True)
            
        with col2:
            st.write("**Udział wartościowy kategorii (PLN)**")
            fig_pie = px.pie(
                df_main,
                values="Wartość",
                names="Kategoria",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()
        st.write("**Top 10 najdroższych produktów (Łączna wartość)**")
        top_10 = df_main.nlargest(10, "Wartość")
        fig_top = px.bar(
            top_10,
            x="Wartość",
            y="nazwa",
            orientation='h',
            color="Wartość",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.warning("Dodaj dane, aby zobaczyć wykresy.")

# --- TAB: KATEGORIE ---
with tabs[3]:
    # ... (kod zarządzania kategoriami) ...
    pass

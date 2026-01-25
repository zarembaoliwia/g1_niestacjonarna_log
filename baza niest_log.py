import streamlit as st
import pandas as pd
from supabase import create_client, Client
from postgrest.exceptions import APIError
import datetime

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="ProMagazyn AI-Ready", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLIZACJA CSS (Dla efektu 'wow') ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. POŁĄCZENIE I SESJA ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
    except Exception as e:
        st.error(f"🚨 Błąd krytyczny połączenia: {e}")
        return None

supabase = init_connection()

# --- 4. WARSTWA LOGIKI DANYCH (Backend) ---
class MagazynBaza:
    @staticmethod
    def pobierz_kategorie():
        res = supabase.table("Kategorie").select("*").order("nazwa").execute()
        return res.data

    @staticmethod
    def pobierz_produkty():
        # Pobieramy z relacją do kategorii
        res = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute()
        return res.data

    @staticmethod
    def dodaj_produkt(data):
        return supabase.table("Produkty").insert(data).execute()

    @staticmethod
    def usun_produkt(prod_id):
        return supabase.table("Produkty").delete().eq("id", prod_id).execute()

# --- 5. SIDEBAR - ANALITYKA I FILTRY ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2271/2271062.png", width=100)
    st.title("Panel Sterowania")
    
    st.divider()
    
    szukaj = st.text_input("🔍 Szukaj produktu...", placeholder="Wpisz nazwę...")
    minimalny_stan = st.slider("Alert niskiego stanu", 0, 50, 5)
    
    st.divider()
    st.info("System v3.0 - Kolokwium Advanced Edition")

# --- 6. GŁÓWNY INTERFEJS ---
st.title("📦 System Zarządzania Zasobami")

# Pobranie danych do DataFrame (do analizy)
raw_prods = MagazynBaza.pobierz_produkty()
df = pd.DataFrame(raw_prods)

# Przetwarzanie danych w Pandas (jeśli baza nie jest pusta)
if not df.empty:
    # Rozpakowanie nazwy kategorii z relacji JSON
    df['Kategoria_Nazwa'] = df['Kategorie'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Brak")
    # Filtrowanie wyszukiwarką
    if szukaj:
        df = df[df['nazwa'].str.contains(szukaj, case=False)]

# --- TABS ---
tab_dashboard, tab_produkty, tab_dodaj, tab_ustawienia = st.tabs([
    "📈 Dashboard", "📋 Inwentaryzacja", "➕ Nowy Produkt", "⚙️ Zarządzanie Bazą"
])

# --- TAB: DASHBOARD (Analityka) ---
with tab_dashboard:
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        total_value = (df['liczba'] * df['Cena']).sum()
        
        c1.metric("Wartość Magazynu", f"{total_value:,.2f} zł")
        c2.metric("Liczba SKU", len(df))
        c3.metric("Suma Sztuk", int(df['liczba'].sum()))
        
        niskie_stany = df[df['liczba'] <= minimalny_stan]
        c4.metric("Alerty (Niski stan)", len(niskie_stany), delta=-len(niskie_stany), delta_color="inverse")

        st.divider()
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Podział wartości wg kategorii")
            kat_val = df.groupby('Kategoria_Nazwa')['Cena'].sum()
            st.bar_chart(kat_val)

        with col_right:
            st.subheader("Produkty z niskim stanem")
            if not niskie_stany.empty:
                st.warning(f"Należy uzupełnić {len(niskie_stany)} pozycji!")
                st.table(niskie_stany[['nazwa', 'liczba']])
            else:
                st.success("Wszystkie stany magazynowe w normie.")
    else:
        st.warning("Brak danych do wyświetlenia dashboardu.")

# --- TAB: INWENTARYZACJA (Tabela i Eksport) ---
with tab_produkty:
    st.subheader("Pełna lista produktów")
    
    if not df.empty:
        # Wybieramy kolumny do pokazania
        show_df = df[['id', 'nazwa', 'liczba', 'Cena', 'Kategoria_Nazwa']].rename(columns={
            'nazwa': 'Nazwa', 'liczba': 'Ilość', 'Kategoria_Nazwa': 'Kategoria'
        })
        
        st.dataframe(show_df, use_container_width=True, hide_index=True)
        
        # EKSPORT DO CSV
        csv = show_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Pobierz raport CSV",
            data=csv,
            file_name=f"raport_magazyn_{datetime.date.today()}.csv",
            mime='text/csv',
        )
    else:
        st.info("Brak produktów.")

# --- TAB: NOWY PRODUKT ---
with tab_dodaj:
    st.subheader("Wprowadź nowy towar")
    kategorie = MagazynBaza.pobierz_kategorie()
    
    if kategorie:
        kat_map = {k['nazwa']: k['id'] for k in kategorie}
        
        with st.form("main_add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Nazwa artykułu", placeholder="np. Laptop Dell")
                new_cat = st.selectbox("Kategoria", options=list(kat_map.keys()))
            with col2:
                new_price = st.number_input("Cena netto (PLN)", min_value=0.0, step=0.01)
                new_qty = st.number_input("Ilość na start", min_value=0, step=1)
            
            submit = st.form_submit_button("🔥 Dodaj produkt do systemu", use_container_width=True)
            
            if submit:
                if new_name:
                    MagazynBaza.dodaj_produkt({
                        "nazwa": new_name,
                        "Cena": new_price,
                        "liczba": new_qty,
                        "kategoria_id": kat_map[new_cat]
                    })
                    st.success("Produkt dodany pomyślnie!")
                    st.rerun()
                else:
                    st.error("Błąd: Nazwa nie może być pusta.")
    else:
        st.error("Zanim dodasz produkt, musisz zdefiniować przynajmniej jedną kategorię.")

# --- TAB: USTAWIENIA (Kategorie i Usuwanie) ---
with tab_ustawienia:
    st.subheader("Zarządzanie strukturą bazy")
    
    col_cat, col_del = st.columns(2)
    
    with col_cat:
        st.write("### Dodaj Kategorię")
        k_name = st.text_input("Nazwa kategorii")
        k_desc = st.text_area("Opis (opcjonalnie)")
        if st.button("Zapisz kategorię"):
            if k_name:
                supabase.table("Kategorie").insert({"nazwa": k_name, "opis": k_desc}).execute()
                st.success("Kategoria dodana!")
                st.rerun()

    with col_del:
        st.write("### Usuń Produkt")
        if not df.empty:
            del_id = st.selectbox("Wybierz produkt do usunięcia", options=df['id'].tolist(), 
                                  format_func=lambda x: df[df['id']==x]['nazwa'].values[0])
            if st.button("Potwierdź usunięcie", type="primary"):
                MagazynBaza.usun_produkt(del_id)
                st.toast("Produkt usunięty!")
                st.rerun()
        else:
            st.write("Brak produktów do usunięcia.")

# --- STOPKA ---
st.markdown("---")
st.caption(f"Zalogowano do: {st.secrets['supabase_url']} | Status serwera: Online")

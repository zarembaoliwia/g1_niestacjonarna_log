import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- KONFIGURACJA ---
st.set_page_config(page_title="Magazyn Pro v2", layout="wide", page_icon="📈")

@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
    except Exception as e:
        st.error("Błąd połączenia z bazą danych. Sprawdź Secrets!")
        return None

supabase = init_connection()

# --- FUNKCJE POMOCNICZE ---
def fetch_data(table_name):
    return supabase.table(table_name).select("*").execute().data

# --- SIDEBAR: Statystyki ---
st.sidebar.title("📊 Statystyki")
try:
    prods = fetch_data("Produkty")
    kats = fetch_data("Kategorie")
    
    total_items = sum([p['liczba'] for p in prods])
    # Zakładając, że kolumna nazywa się 'Cena' lub 'cena'
    total_val = sum([p.get('Cena', 0) * p['liczba'] for p in prods])
    
    st.sidebar.metric("Suma produktów", total_items)
    st.sidebar.metric("Wartość magazynu", f"{total_val:,.2f} PLN")
    st.sidebar.divider()
except:
    st.sidebar.warning("Nie udało się pobrać statystyk.")

# --- GŁÓWNY INTERFEJS ---
st.title("🚀 Panel Zarządzania Magazynem")

tabs = st.tabs(["📋 Lista Produktów", "➕ Dodaj Nowy", "📂 Kategorie"])

# TAB 1: LISTA I WYSZUKIWANIE
with tabs[0]:
    col_search, col_filter = st.columns([2, 1])
    search = col_search.text_input("🔍 Szukaj produktu po nazwie...")
    
    # Pobieranie danych z joinem do kategorii
    query = supabase.table("Produkty").select("*, Kategorie(nazwa)")
    if search:
        query = query.ilike("nazwa", f"%{search}%")
    
    data = query.execute().data
    
    if data:
        df = pd.DataFrame(data)
        # Czyszczenie danych do wyświetlenia
        df['Kategoria'] = df['Kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
        display_df = df[['id', 'nazwa', 'liczba', 'Cena', 'Kategoria']]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Sekcja usuwania
        with st.expander("🗑️ Usuwanie produktów"):
            to_delete = st.selectbox("Wybierz produkt do usunięcia", 
                                    options=data, 
                                    format_func=lambda x: f"{x['nazwa']} (ID: {x['id']})")
            if st.button("Potwierdź usunięcie", type="primary"):
                supabase.table("Produkty").delete().eq("id", to_delete['id']).execute()
                st.toast(f"Usunięto: {to_delete['nazwa']}")
                st.rerun()
    else:
        st.info("Brak produktów pasujących do kryteriów.")

# TAB 2: DODAWANIE PRODUKTÓW
with tabs[1]:
    st.subheader("Nowy Produkt")
    if not kats:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię!")
    else:
        with st.form("prod_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nazwa produktu*")
            cat = c2.selectbox("Kategoria", options=kats, format_func=lambda x: x['nazwa'])
            
            c3, c4 = st.columns(2)
            qty = c3.number_input("Ilość", min_value=0, value=0)
            price = c4.number_input("Cena (PLN)", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Dodaj do bazy"):
                if name:
                    payload = {
                        "nazwa": name,
                        "kategoria_id": cat['id'],
                        "liczba": qty,
                        "Cena": price
                    }
                    supabase.table("Produkty").insert(payload).execute()
                    st.success("Produkt dodany!")
                    st.rerun()
                else:
                    st.error("Nazwa jest wymagana!")

# TAB 3: KATEGORIE
with tabs[2]:
    st.subheader("Zarządzaj Kategoriami")
    
    with st.expander("➕ Dodaj nową kategorię"):
        new_cat_name = st.text_input("Nazwa kategorii")
        new_cat_desc = st.text_area("Opis")
        if st.button("Zapisz kategorię"):
            if new_cat_name:
                supabase.table("Kategorie").insert({"nazwa": new_cat_name, "opis": new_cat_desc}).execute()
                st.rerun()

    if kats:
        cat_df = pd.DataFrame(kats)[['id', 'nazwa', 'opis']]
        st.table(cat_df)
        
        del_cat = st.selectbox("Usuń kategorię", options=kats, format_func=lambda x: x['nazwa'])
        if st.button("Usuń kategorię", help="Uwaga: Może to spowodować błędy, jeśli kategoria ma przypisane produkty"):
            try:
                supabase.table("Kategorie").delete().eq("id", del_cat['id']).execute()
                st.rerun()
            except:
                st.error("Nie można usunąć kategorii, która zawiera produkty!")

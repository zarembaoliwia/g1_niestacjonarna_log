import streamlit as st
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="ProMagazyn v2.0", 
    page_icon="📦", 
    layout="wide"
)

# --- POŁĄCZENIE Z BAZĄ ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
        return None

db = init_connection()

# --- LOGIKA BIZNESOWA (Funkcje pomocnicze) ---
def get_categories():
    res = db.table("Kategorie").select("*").execute()
    return res.data

def get_products():
    # Pobieramy produkty wraz z relacją do kategorii (Join)
    res = db.table("Produkty").select("id, nazwa, liczba, Cena, kategoria_id, Kategorie(nazwa)").execute()
    return res.data

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("📦 System Zarządzania Magazynem")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Podgląd i Filtry", "➕ Dodaj Produkt", "📂 Kategorie"])

# --- TAB 1: PODGLĄD PRODUKTÓW ---
with tab1:
    st.subheader("Aktualny stan magazynowy")
    produkty = get_products()
    
    if produkty:
        # Przekształcenie do czytelnej formy dla tabeli
        display_data = []
        for p in produkty:
            display_data.append({
                "ID": p['id'],
                "Nazwa": p['nazwa'],
                "Ilość": p['liczba'],
                "Cena (zł)": f"{p['Cena']:.2f}",
                "Kategoria": p['Kategorie']['nazwa'] if p['Kategorie'] else "Brak"
            })
        
        st.table(display_data) # Elegancka tabela
        
        # Szybkie usuwanie (Selectbox dla bezpieczeństwa)
        with st.expander("🗑️ Usuń produkt"):
            to_delete = st.selectbox("Wybierz produkt do usunięcia", options=produkty, format_func=lambda x: x['nazwa'])
            if st.button("Potwierdź usunięcie", type="primary"):
                db.table("Produkty").delete().eq("id", to_delete['id']).execute()
                st.toast(f"Usunięto: {to_delete['nazwa']}")
                st.rerun()
    else:
        st.info("Magazyn jest pusty.")

# --- TAB 2: DODAWANIE PRODUKTÓW ---
with tab2:
    st.subheader("Nowy produkt")
    kategorie = get_categories()
    
    if not kategorie:
        st.warning("Najpierw dodaj kategorię w zakładce 'Kategorie'!")
    else:
        kat_dict = {k['nazwa']: k['id'] for k in kategorie}
        
        with st.form("product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nazwa produktu")
                cat_name = st.selectbox("Kategoria", options=list(kat_dict.keys()))
            with col2:
                qty = st.number_input("Ilość", min_value=0, step=1)
                price = st.number_input("Cena jednostkowa", min_value=0.0, format="%.2f")
            
            submitted = st.form_submit_button("Dodaj produkt do bazy", use_container_width=True)
            
            if submitted:
                if name:
                    try:
                        new_item = {
                            "nazwa": name,
                            "liczba": qty,
                            "Cena": price,
                            "kategoria_id": kat_dict[cat_name]
                        }
                        db.table("Produkty").insert(new_item).execute()
                        st.success(f"Produkt '{name}' został dodany!")
                    except APIError as e:
                        st.error(f"Błąd bazy danych: {e}")
                else:
                    st.error("Nazwa produktu jest wymagana!")

# --- TAB 3: ZARZĄDZANIE KATEGORIAMI ---
with tab3:
    st.subheader("Twoje Kategorie")
    
    # Dodawanie kategorii
    with st.expander("🆕 Dodaj nową kategorię"):
        new_kat = st.text_input("Nazwa nowej kategorii")
        new_desc = st.text_area("Opis")
        if st.button("Zapisz kategorię"):
            if new_kat:
                db.table("Kategorie").insert({"nazwa": new_kat, "opis": new_desc}).execute()
                st.success("Kategoria dodana!")
                st.rerun()
    
    # Lista kategorii z usuwaniem
    kategorie_list = get_categories()
    for k in kategorie_list:
        c1, c2, c3 = st.columns([2, 3, 1])
        c1.write(f"**{k['nazwa']}**")
        c2.write(f"_{k['opis']}_")
        if c3.button("Usuń", key=f"del_k_{k['id']}"):
            try:
                db.table("Kategorie").delete().eq("id", k["id"]).execute()
                st.rerun()
            except Exception:

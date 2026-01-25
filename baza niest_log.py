import streamlit as st
from supabase import create_client, Client

# Konfiguracja strony
st.set_page_config(page_title="Zarządzanie Magazynem", layout="wide")

# Inicjalizacja połączenia z Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

supabase: Client = init_connection()

st.title("📦 System Zarządzania Produktami")

tab1, tab2 = st.tabs(["Produkty", "Kategorie"])

# --- TAB: KATEGORIE ---
with tab2:
    st.header("Zarządzanie Kategoriami")
    
    # Formularz dodawania
    with st.form("add_category"):
        nazwa_kat = st.text_input("Nazwa kategorii")
        opis_kat = st.text_area("Opis")
        submit_kat = st.form_submit_button("Dodaj kategorię")
        
        if submit_kat and nazwa_kat:
            data = {"nazwa": nazwa_kat, "opis": opis_kat}
            supabase.table("Kategorie").insert(data).execute()
            st.success("Dodano kategorię!")
            st.rerun()

    # Wyświetlanie i usuwanie
    res_kat = supabase.table("Kategorie").select("*").execute()
    kategorie = res_kat.data
    
    if kategorie:
        for kat in kategorie:
            cols = st.columns([3, 1])
            cols[0].write(f"**{kat['nazwa']}** - {kat['opis']}")
            if cols[1].button("Usuń", key=f"del_kat_{kat['id']}"):
                supabase.table("Kategorie").delete().eq("id", kat["id"]).execute()
                st.rerun()
    else:
        st.info("Brak kategorii w bazie.")

# --- TAB: PRODUKTY ---
with tab1:
    st.header("Zarządzanie Produktami")

    # Pobieranie kategorii do dropdowna
    res_kat_prod = supabase.table("Kategorie").select("id, nazwa").execute()
    lista_kat = {item['nazwa']: item['id'] for item in res_kat_prod.data}

    # Formularz dodawania produktu
    with st.form("add_product"):
        nazwa_prod = st.text_input("Nazwa produktu")
        liczba = st.number_input("Liczba (ilość)", min_value=0, step=1)
        cena = st.number_input("Cena", min_value=0.0, format="%.2f")
        wybrana_kat = st.selectbox("Kategoria", options=list(lista_kat.keys()))
        
        submit_prod = st.form_submit_button("Dodaj produkt")
        
        if submit_prod and nazwa_prod:
            new_prod = {
                "nazwa": nazwa_prod,
                "liczba": liczba,
                "Cena": cena, # Wielka litera jak na schemacie "Ce..."
                "kategoria_id": lista_kat[wybrana_kat]
            }
            supabase.table("Produkty").insert(new_prod).execute()
            st.success("Dodano produkt!")
            st.rerun()

    # Wyświetlanie produktów
    res_prod = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute()
    produkty = res_prod.data

    if produkty:
        for p in produkty:
            cols = st.columns([2, 1, 1, 1, 1])
            cols[0].write(f"**{p['nazwa']}**")
            cols[1].write(f"Ilość: {p['liczba']}")
            cols[2].write(f"{p['Cena']} zł")
            cols[3].write(f"📁 {p['Kategorie']['nazwa'] if p['Kategorie'] else 'Brak'}")
            if cols[4].button("Usuń", key=f"del_prod_{p['id']}"):
                supabase.table("Produkty").delete().eq("id", p["id"]).execute()
                st.rerun()

import streamlit as st
from supabase import create_client, Client
from postgrest.exceptions import APIError

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="System Magazynowy Pro", 
    page_icon="📦", 
    layout="wide"
)

# --- 2. POŁĄCZENIE Z BAZĄ (Zabezpieczone) ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Problem z konfiguracją st.secrets: {e}")
        return None

supabase = init_connection()

# --- 3. FUNKCJE DOSTĘPU DO DANYCH (CRUD) ---
def get_categories():
    try:
        res = supabase.table("Kategorie").select("*").execute()
        return res.data
    except Exception:
        return []

def get_products():
    try:
        # Pobieramy produkty wraz z nazwą kategorii (Relacja w Supabase)
        res = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute()
        return res.data
    except Exception as e:
        st.error(f"Błąd pobierania produktów: {e}")
        return []

# --- 4. INTERFEJS UŻYTKOWNIKA ---
st.title("📦 Zarządzanie Produktami i Kategoriami")

tab1, tab2, tab3 = st.tabs(["📊 Lista Produktów", "➕ Dodaj Nowy", "📂 Kategorie"])

# --- TAB 1: LISTA PRODUKTÓW ---
with tab1:
    st.subheader("Stan Magazynowy")
    produkty = get_products()
    
    if produkty:
        # Przygotowanie danych do tabeli (Mapowanie dla ładnego wyglądu)
        clean_data = []
        for p in produkty:
            clean_data.append({
                "ID": p.get('id'),
                "Nazwa Produktu": p.get('nazwa'),
                "Ilość": p.get('liczba', 0),
                "Cena (zł)": f"{p.get('Cena', 0):.2f}",
                "Kategoria": p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
            })
        
        st.dataframe(clean_data, use_container_width=True, hide_index=True)
        
        # Opcja usuwania pod tabelą
        with st.expander("🗑️ Usuń produkt z bazy"):
            prod_to_del = st.selectbox(
                "Wybierz produkt do skasowania", 
                options=produkty, 
                format_func=lambda x: f"{x['nazwa']} (ID: {x['id']})"
            )
            if st.button("Usuń trwale", type="primary"):
                supabase.table("Produkty").delete().eq("id", prod_to_del["id"]).execute()
                st.toast(f"Usunięto produkt: {prod_to_del['nazwa']}")
                st.rerun()
    else:
        st.info("Baza produktów jest obecnie pusta.")

# --- TAB 2: DODAWANIE PRODUKTU ---
with tab2:
    st.subheader("Formularz Nowego Produktu")
    kat_data = get_categories()
    
    if not kat_data:
        st.warning("⚠️ Brak kategorii w bazie. Dodaj kategorię przed dodaniem produktu!")
    else:
        kat_options = {k['nazwa']: k['id'] for k in kat_data}
        
        with st.form("new_product_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("Nazwa produktu")
            p_cat = c1.selectbox("Kategoria", options=list(kat_options.keys()))
            p_qty = c2.number_input("Ilość (szt.)", min_value=0, step=1)
            p_price = c2.number_input("Cena (zł)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Zapisz w bazie", use_container_width=True):
                if p_name:
                    new_item = {
                        "nazwa": p_name,
                        "liczba": p_qty,
                        "Cena": p_price,
                        "kategoria_id": kat_options[p_cat]
                    }
                    supabase.table("Produkty").insert(new_item).execute()
                    st.success(f"Dodano: {p_name}")
                    st.rerun()
                else:
                    st.error("Produkt musi mieć nazwę!")

# --- TAB 3: KATEGORIE ---
with tab3:
    st.subheader("Zarządzanie Kategoriami")
    
    # Formularz dodawania
    with st.expander("➕ Dodaj nową kategorię"):
        c_name = st.text_input("Nazwa kategorii")
        c_desc = st.text_area("Opis kategorii")
        if st.button("Dodaj do bazy"):
            if c_name:
                supabase.table("Kategorie").insert({"nazwa": c_name, "opis": c_desc}).execute()
                st.rerun()
    
    # Wyświetlanie istniejących
    kategorie = get_categories()
    for k in kategorie:
        col_k1, col_k2 = st.columns([4, 1])
        col_k1.write(f"📁 **{k['nazwa']}** — {k['opis'] if k['opis'] else 'Brak opisu'}")
        if col_k2.button("Usuń", key=f"k_{k['id']}"):
            try:
                supabase.table("Kategorie").delete().eq("id", k["id"]).execute()
                st.rerun()
            except Exception:
                st.error("Nie można usunąć kategorii, która ma przypisane produkty!")

# --- 5. SIDEBAR ZE STATYSTYKAMI (Bezpieczna linia 131) ---
with st.sidebar:
    st.header("📊 Statystyki ogólne")
    all_prods = get_products()
    
    if all_prods:
        # Obliczenia z zabezpieczeniem przed None
        total_items = sum((item.get('liczba') or 0) for item in all_prods)
        # UWAGA: p.get('Cena') musi pasować do nazwy kolumny w Supabase (wielkość liter!)
        total_val = sum(((item.get('liczba') or 0) * (item.get('Cena') or 0.0)) for item in all_prods)
        
        st.metric("Różnorodność (SKU)", len(all_prods))
        st.metric("Wszystkich sztuk", total_items)
        st.metric("Łączna wartość", f"{total_val:,.2f} zł")
    else:
        st.write("Brak danych do analizy.")
    
    st.divider()
    st.caption("Aplikacja Magazynowa v2.0 - Kolokwium")

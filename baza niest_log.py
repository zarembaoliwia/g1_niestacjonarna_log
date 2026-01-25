import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. KONFIGURACJA I STYLIZACJA ---
st.set_page_config(page_title="System Nexus ERP v6.0", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .critical-card { background-color: #fff5f5; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; }
    .invoice-box { padding: 25px; border: 2px solid #333; border-radius: 10px; background: #fff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE Z BAZĄ ---
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
    except Exception as e:
        st.error(f"Błąd połączenia z Supabase: {e}")
        return None

db = init_db()

# --- 3. WARSTWA DANYCH (CRUD) ---
class ERPLogic:
    @staticmethod
    def get_all_data():
        res = db.table("Produkty").select("*, Kategorie(nazwa)").execute()
        return res.data

    @staticmethod
    def get_categories():
        return db.table("Kategorie").select("*").execute().data

    @staticmethod
    def update_stock(p_id, new_qty):
        db.table("Produkty").update({"liczba": new_qty}).eq("id", p_id).execute()

# --- 4. PANEL BOCZNY (WYSZUKIWARKA I INFO) ---
with st.sidebar:
    st.title("🔍 Szybki Podgląd")
    raw_prods = ERPLogic.get_all_data()
    if raw_prods:
        p_names = [p['nazwa'] for p in raw_prods]
        search = st.selectbox("Sprawdź dostępność towaru", options=[""] + p_names)
        if search:
            p_found = next(i for i in raw_prods if i['nazwa'] == search)
            st.metric("Stan aktualny", f"{p_found['liczba']} szt.")
            st.progress(min(p_found['liczba'] / 100, 1.0))
            if p_found['liczba'] < 5:
                st.error("❗ Krytycznie niski stan!")
    
    st.divider()
    low_limit = st.slider("Próg ostrzegawczy", 0, 50, 10)
    st.caption("Nexus ERP v6.0 | System Zarządzania")

# --- 5. GŁÓWNY INTERFEJS ---
t_buy, t_inv, t_sale, t_analysis, t_config = st.tabs([
    "🚨 PILNY ZAKUP", "📦 INWENTARYZACJA", "🧾 SPRZEDAŻ", "📊 ANALIZA", "⚙️ KONFIGURACJA"
])

# Budowanie DataFrame do analiz
df = pd.DataFrame(raw_prods) if raw_prods else pd.DataFrame()
if not df.empty:
    df['Kat_Nazwa'] = df['Kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")

# --- TAB 1: PILNY ZAKUP (BRAKI) ---
with t_buy:
    st.header("🛒 Centrum Zaopatrzenia")
    
    # Podgląd braków
    if not df.empty:
        low_stock_df = df[df['liczba'] <= low_limit]
        if not low_stock_df.empty:
            st.error(f"Znaleziono {len(low_stock_df)} produktów wymagających pilnego zakupu!")
            for _, row in low_stock_df.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"⚠️ **{row['nazwa']}** (Obecnie: {row['liczba']} szt.)")
                    add_qty = c2.number_input("Ile dokupić?", min_value=1, key=f"add_{row['id']}")
                    if c3.button("Dostawa", key=f"btn_{row['id']}"):
                        ERPLogic.update_stock(row['id'], row['liczba'] + add_qty)
                        st.success("Zaktualizowano zapas!")
                        st.rerun()
        else:
            st.success("Wszystkie stany magazynowe są na optymalnym poziomie.")
    
    st.divider()
    st.subheader("➕ Wdrożenie nowego towaru (Zaopatrzenie)")
    with st.expander("Kliknij, aby dodać produkt, którego jeszcze nie ma w sklepie"):
        with st.form("new_product_full"):
            col1, col2 = st.columns(2)
            n_name = col1.text_input("Nazwa nowego towaru")
            all_cats = ERPLogic.get_categories()
            cat_options = {c['nazwa']: c['id'] for c in all_cats}
            n_cat = col1.selectbox("Przypisz kategorię", options=list(cat_options.keys()))
            
            n_price = col2.number_input("Cena zakupu/netto", min_value=0.0)
            n_init_qty = col2.number_input("Ilość z dostawy", min_value=1)
            
            if st.form_submit_button("Wdróż produkt do sprzedaży"):
                if n_name:
                    db.table("Produkty").insert({
                        "nazwa": n_name, "Cena": n_price, 
                        "liczba": n_init_qty, "kategoria_id": cat_options[n_cat]
                    }).execute()
                    st.success(f"Produkt {n_name} został pomyślnie wprowadzony na magazyn!")
                    st.rerun()

# --- TAB 2: INWENTARYZACJA ---
with t_inv:
    st.header("Lista Produktów")
    if not df.empty:
        search_inv = st.text_input("Filtruj listę...")
        display_df = df[df['nazwa'].str.contains(search_inv, case=False)] if search_inv else df
        st.dataframe(
            display_df[['id', 'nazwa', 'Kat_Nazwa', 'liczba', 'Cena']],
            column_config={
                "liczba": st.column_config.NumberColumn("Stan", format="%d szt."),
                "Cena": st.column_config.NumberColumn("Cena", format="%.2f zł")
            }, use_container_width=True, hide_index=True
        )
    else:
        st.info("Magazyn jest pusty.")

# --- TAB 3: FAKTURA ---
with t_sale:
    st.header("Nowa Faktura")
    if not df.empty:
        col_s1, col_s2 = st.columns([1, 1])
        with col_s1:
            klient = st.text_input("Nabywca", "Klient Detaliczny")
            wybrany = st.selectbox("Produkt", options=raw_prods, format_func=lambda x: f"{x['nazwa']} ({x['Cena']} zł)")
            ilosc = st.number_input("Ilość", min_value=1, max_value=int(wybrany['liczba']))
            total_netto = ilosc * float(wybrany['Cena'])
            if st.button("Wystaw fakturę"):
                ERPLogic.update_stock(wybrany['id'], wybrany['liczba'] - ilosc)
                st.balloons()
                st.rerun()
        with col_s2:
            st.markdown(f"<div class='invoice-box'><h3>FAKTURA</h3><hr><p>Klient: {klient}</p><p>Towar: {wybrany['nazwa']}</p><h2>Suma: {total_netto * 1.23:.2f} zł</h2></div>", unsafe_allow_html=True)

# --- TAB 4: ANALIZA ---
with t_analysis:
    st.header("Statystyki Biznesowe")
    if not df.empty:
        st.metric("Wartość całkowita towaru", f"{(df['Cena'] * df['liczba']).sum():,.2f} zł")
        st.subheader("Ilość towaru w podziale na kategorie")
        st.bar_chart(df.groupby('Kat_Nazwa')['liczba'].sum())

# --- TAB 5: KONFIGURACJA ---
with t_config:
    st.header("Ustawienia Systemu")
    with st.form("new_cat"):
        c_name = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj kategorię"):
            db.table("Kategorie").insert({"nazwa": c_name}).execute()
            st.rerun()

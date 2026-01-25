import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. KONFIGURACJA I STYLIZACJA ---
st.set_page_config(page_title="System ERP v4.0", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .invoice-card { 
        background-color: white; padding: 40px; border-radius: 5px;
        border: 1px solid #ddd; font-family: 'Courier New', Courier, monospace;
    }
    .metric-box {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE Z BAZĄ ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return None

db = get_db()

# --- 3. KLASA OPERACYJNA (LOGIKA) ---
class WarehouseManager:
    @staticmethod
    def get_all_products():
        # Pobieranie z relacją kategorii
        res = db.table("Produkty").select("*, Kategorie(nazwa)").execute()
        return res.data

    @staticmethod
    def get_all_categories():
        res = db.table("Kategorie").select("*").execute()
        return res.data

    @staticmethod
    def update_stock(prod_id, quantity_change, current_stock):
        new_qty = current_stock - quantity_change
        db.table("Produkty").update({"liczba": new_qty}).eq("id", prod_id).execute()
        return new_qty

    @staticmethod
    def add_product(data):
        return db.table("Produkty").insert(data).execute()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ ERP Admin")
    st.subheader("Ustawienia Systemu")
    low_stock_threshold = st.number_input("Próg niskiego stanu", value=10)
    st.divider()
    st.info("Zalogowano jako: Administrator")

# --- 5. GŁÓWNY INTERFEJS (TABS) ---
t1, t2, t3, t4 = st.tabs(["📈 Analiza", "📦 Inwentaryzacja", "🧾 Faktura Sprzedaży", "⚙️ Konfiguracja"])

# Pobranie danych na starcie
raw_products = WarehouseManager.get_all_products()
df = pd.DataFrame(raw_products) if raw_products else pd.DataFrame()

if not df.empty:
    df['kat_name'] = df['Kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")

# --- TAB 1: DASHBOARD ---
with t1:
    st.header("Analityka Magazynowa")
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        total_val = (df['Cena'] * df['liczba']).sum()
        low_items = df[df['liczba'] <= low_stock_threshold]
        
        m1.metric("Wartość towarów", f"{total_val:,.2f} zł")
        m2.metric("Liczba SKU", len(df))
        m3.metric("Suma jednostek", int(df['liczba'].sum()))
        m4.metric("Alerty zapasów", len(low_items), delta=-len(low_items), delta_color="inverse")
        
        st.subheader("Rozkład zapasów wg kategorii")
        st.bar_chart(df.groupby('kat_name')['liczba'].sum())
    else:
        st.warning("Brak danych do analizy.")

# --- TAB 2: INWENTARYZACJA ---
with t2:
    st.header("Pełna Inwentaryzacja")
    if not df.empty:
        # Filtrowanie
        col_f1, col_f2 = st.columns(2)
        search_query = col_f1.text_input("Szukaj produktu...")
        cat_filter = col_f2.multiselect("Filtruj wg kategorii", options=df['kat_name'].unique())
        
        filtered_df = df.copy()
        if search_query:
            filtered_df = filtered_df[filtered_df['nazwa'].str.contains(search_query, case=False)]
        if cat_filter:
            filtered_df = filtered_df[filtered_df['kat_name'].isin(cat_filter)]
            
        st.dataframe(
            filtered_df[['id', 'nazwa', 'kat_name', 'liczba', 'Cena']],
            column_config={
                "id": "ID", "nazwa": "Nazwa Produktu", 
                "kat_name": "Kategoria", "liczba": "Stan", "Cena": "Cena (PLN)"
            },
            use_container_width=True, hide_index=True
        )
        
        # Szybka edycja stanów
        with st.expander("🛠️ Szybka korekta stanu"):
            with st.form("quick_edit"):
                sel_p = st.selectbox("Wybierz produkt", options=raw_products, format_func=lambda x: x['nazwa'])
                new_val = st.number_input("Nowa ilość", value=sel_p['liczba'])
                if st.form_submit_button("Aktualizuj stan"):
                    db.table("Produkty").update({"liczba": new_val}).eq("id", sel_p['id']).execute()
                    st.success("Zaktualizowano!")
                    st.rerun()
    else:
        st.info("Magazyn jest pusty.")

# --- TAB 3: FAKTURA ---
with t3:
    st.header("Generator Dokumentów")
    if not df.empty:
        c_left, c_right = st.columns([1, 1.5])
        
        with c_left:
            client_name = st.text_input("Nazwa Klienta", "Kontrahent ABC")
            sel_prod = st.selectbox("Produkt na fakturze", options=raw_products, format_func=lambda x: f"{x['nazwa']} (Stan: {x['liczba']})")
            qty_sale = st.number_input("Ilość sprzedaży", min_value=1, max_value=int(sel_prod['liczba']) if sel_prod['liczba'] > 0 else 1)
            tax_rate = st.selectbox("Stawka VAT", [23, 8, 5, 0])
            
            total_netto = qty_sale * float(sel_prod['Cena'])
            total_brutto = total_netto * (1 + tax_rate/100)
            
        with c_right:
            st.markdown(f"""
            <div class="invoice-card">
                <h2 style="text-align:center">FAKTURA VAT</h2>
                <p style="text-align:right">Data: {datetime.date.today()}</p>
                <hr>
                <p><b>Sprzedawca:</b> ERP System Pro sp. z o.o.</p>
                <p><b>Nabywca:</b> {client_name}</p>
                <br>
                <table style="width:100%">
                    <tr style="border-bottom: 1px solid #000">
                        <th>Pozycja</th><th>Ilość</th><th>Cena</th><th>Suma</th>
                    </tr>
                    <tr>
                        <td>{sel_prod['nazwa']}</td>
                        <td>{qty_sale} szt.</td>
                        <td>{sel_prod['Cena']:.2f}</td>
                        <td>{total_netto:.2f}</td>
                    </tr>
                </table>
                <br><br>
                <h3 style="text-align:right">Razem Brutto: {total_brutto:.2f} PLN</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 Zatwierdź i Wydrukuj (Zdejmij ze stanu)", use_container_width=True):
                if sel_prod['liczba'] >= qty_sale:
                    WarehouseManager.update_stock(sel_prod['id'], qty_sale, sel_prod['liczba'])
                    st.success("Transakcja zakończona! Stan magazynowy zaktualizowany.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Błąd: Niewystarczająca ilość towaru!")
    else:
        st.warning("Brak produktów do sprzedaży.")

# --- TAB 4: KONFIGURACJA ---
with t4:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Kategorie")
        new_k = st.text_input("Nazwa nowej kategorii")
        if st.button("Dodaj kategorię"):
            if new_k:
                db.table("Kategorie").insert({"nazwa": new_k}).execute()
                st.rerun()
                
    with col_b:
        st.subheader("Nowy Produkt")
        with st.form("add_p"):
            p_n = st.text_input("Nazwa")
            p_c = st.number_input("Cena", min_value=0.0)
            p_q = st.number_input("Ilość", min_value=0)
            cats = WarehouseManager.get_all_categories()
            p_k = st.selectbox("Kategoria", options=cats, format_func=lambda x: x['nazwa'])
            if st.form_submit_button("Zapisz produkt"):
                WarehouseManager.add_product({"nazwa": p_n, "Cena": p_c, "liczba": p_q, "kategoria_id": p_k['id']})
                st.rerun()

st.divider()
st.caption("ERP Cloud System © 2024 | Projekt na ocenę Bardzo Dobrą")

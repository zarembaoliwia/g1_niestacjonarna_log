import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. KONFIGURACJA I DESIGN ---
st.set_page_config(page_title="ERP Nexus v5.0", page_icon="🏢", layout="wide")

# Custom CSS dla lepszego wyglądu
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .status-ok { color: #2ecc71; font-weight: bold; }
    .status-low { color: #e74c3c; font-weight: bold; }
    .invoice-box { 
        padding: 25px; border: 2px solid #333; border-radius: 10px; background: #fff;
        font-family: 'Helvetica', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])

db = init_db()

# --- 3. FUNKCJE POMOCNICZE (API WRAPPERS) ---
def get_products_full():
    return db.table("Produkty").select("*, Kategorie(nazwa)").execute().data

def get_categories():
    return db.table("Kategorie").select("*").execute().data

# --- 4. PANEL BOCZNY (WYSZUKIWARKA STANÓW) ---
with st.sidebar:
    st.title("🔍 Szybki Stan")
    st.write("Sprawdź dostępność bez wchodzenia w tabele.")
    
    all_data = get_products_full()
    if all_data:
        search_names = [p['nazwa'] for p in all_data]
        selected_search = st.selectbox("Szukaj produktu", options=[""] + search_names)
        
        if selected_search:
            prod_info = next(item for item in all_data if item["nazwa"] == selected_search)
            stan = prod_info['liczba']
            
            st.metric("Aktualnie na stanie", f"{stan} szt.")
            # Wizualny pasek stanu (max założony na 100 dla skali)
            st.progress(min(stan / 100, 1.0))
            
            if stan > 10:
                st.success("✅ Stan optymalny")
            else:
                st.error("⚠️ Wymaga uzupełnienia!")
    st.divider()
    st.caption("ERP System v5.0 | Projekt Kolokwium")

# --- 5. GŁÓWNA TREŚĆ (TABS) ---
t_dash, t_inv, t_invoice, t_config = st.tabs([
    "📊 Analiza Sprzedaży", "📦 Inwentaryzacja", "🧾 Faktura", "⚙️ Konfiguracja"
])

# Przygotowanie DataFrame do analiz
df = pd.DataFrame(all_data)
if not df.empty:
    df['Kategoria'] = df['Kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")

# --- TAB 1: ANALIZA SPRZEDAŻY ---
with t_dash:
    st.header("Raport i Analityka")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        total_value = (df['Cena'] * df['liczba']).sum()
        avg_price = df['Cena'].mean()
        
        c1.metric("Całkowita wartość zapasów", f"{total_value:,.2f} zł")
        c2.metric("Średnia cena produktu", f"{avg_price:,.2f} zł")
        c3.metric("Liczba kategorii", len(df['Kategoria'].unique()))
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("### Wartość towaru wg kategorii")
            df['Wartość'] = df['Cena'] * df['liczba']
            val_chart = df.groupby('Kategoria')['Wartość'].sum()
            st.bar_chart(val_chart)
            
        with col_right:
            st.write("### Top 5 najdroższych produktów")
            top_df = df.nlargest(5, 'Cena')[['nazwa', 'Cena']]
            st.table(top_df)
    else:
        st.info("Brak danych do analizy.")

# --- TAB 2: INWENTARYZACJA ---
with t_inv:
    st.header("Rejestr Magazynowy")
    if not df.empty:
        # Wyszukiwarka wewnątrz inwentaryzacji
        q = st.text_input("Filtruj tabelę (Nazwa produktu)")
        filtered_df = df[df['nazwa'].str.contains(q, case=False)] if q else df
        
        st.dataframe(
            filtered_df[['id', 'nazwa', 'Kategoria', 'liczba', 'Cena']],
            column_config={
                "liczba": st.column_config.NumberColumn("Ilość", format="%d 📦"),
                "Cena": st.column_config.NumberColumn("Cena netto", format="%.2f zł")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.warning("Magazyn jest pusty.")

# --- TAB 3: FAKTURA ---
with t_invoice:
    st.header("Nowa Sprzedaż")
    if not df.empty:
        f_col1, f_col2 = st.columns([1, 1])
        
        with f_col1:
            klient = st.text_input("Dane nabywcy", placeholder="Nazwa firmy / Imię i nazwisko")
            wybrany = st.selectbox("Produkt", options=all_data, format_func=lambda x: f"{x['nazwa']} ({x['Cena']} zł)")
            ilosc = st.number_input("Ilość do sprzedaży", min_value=1, max_value=int(wybrany['liczba']))
            
            suma_netto = ilosc * float(wybrany['Cena'])
            podatek = suma_netto * 0.23
            suma_brutto = suma_netto + podatek
            
            potwierdz = st.button("🔴 WYSTAW I ZDEJMIJ ZE STANU", use_container_width=True)

        with f_col2:
            st.markdown(f"""
            <div class="invoice-box">
                <h3 style="text-align:center">FAKTURA PRO-FORMA</h3>
                <p><b>Data:</b> {datetime.date.today()}</p>
                <p><b>Sprzedawca:</b> System ERP Student v5.0</p>
                <p><b>Nabywca:</b> {klient}</p>
                <hr>
                <p>1. {wybrany['nazwa']} | {ilosc} szt. x {wybrany['Cena']:.2f} zł</p>
                <hr>
                <p style="text-align:right">Suma Netto: {suma_netto:.2f} zł</p>
                <p style="text-align:right">VAT (23%): {podatek:.2f} zł</p>
                <h2 style="text-align:right">TOTAL: {suma_brutto:.2f} zł</h2>
            </div>
            """, unsafe_allow_html=True)
            
        if potwierdz:
            nowy_stan = wybrany['liczba'] - ilosc
            db.table("Produkty").update({"liczba": nowy_stan}).eq("id", wybrany['id']).execute()
            st.success(f"Sprzedano! Nowy stan dla {wybrany['nazwa']}: {nowy_stan}")
            st.rerun()

# --- TAB 4: KONFIGURACJA ---
with t_config:
    st.header("Zarządzanie Systemem")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("Nowy Produkt")
        with st.form("p_form", clear_on_submit=True):
            n_name = st.text_input("Nazwa")
            n_price = st.number_input("Cena", min_value=0.0)
            n_qty = st.number_input("Ilość", min_value=0)
            cats = get_categories()
            n_cat = st.selectbox("Kategoria", options=cats, format_func=lambda x: x['nazwa'])
            if st.form_submit_button("Dodaj Produkt"):
                db.table("Produkty").insert({"nazwa": n_name, "Cena": n_price, "liczba": n_qty, "kategoria_id": n_cat['id']}).execute()
                st.rerun()

    with c_right:
        st.subheader("Nowa Kategoria")
        with st.form("c_form"):
            k_name = st.text_input("Nazwa Kategorii")
            if st.form_submit_button("Dodaj Kategorię"):
                db.table("Kategorie").insert({"nazwa": k_name}).execute()
                st.rerun()

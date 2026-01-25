import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. KONFIGURACJA I STYLIZACJA ---
st.set_page_config(page_title="Nexus ERP Pro v7.0", page_icon="🏢", layout="wide")

# Zaawansowany CSS dla profesjonalnej faktury
st.markdown("""
    <style>
    .invoice-container {
        background-color: white; padding: 40px; border: 1px solid #ccc;
        color: #333; font-family: 'Arial', sans-serif; line-height: 1.5;
    }
    .invoice-header { display: flex; justify-content: space-between; margin-bottom: 30px; }
    .company-logo { font-size: 50px; font-weight: bold; color: #1f77b4; }
    .invoice-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .invoice-table th { background-color: #f2f2f2; border: 1px solid #ddd; padding: 8px; text-align: left; }
    .invoice-table td { border: 1px solid #ddd; padding: 8px; }
    .totals { margin-top: 20px; float: right; width: 300px; }
    .totals table { width: 100%; }
    .totals td { padding: 5px; text-align: right; }
    .grand-total { font-size: 1.2em; font-weight: bold; background: #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE ---
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
    except:
        st.error("Skonfiguruj st.secrets['supabase_url'] i ['supabase_key']!")
        return None

db = init_db()

# --- 3. LOGIKA BAZY ---
class ERPCore:
    @staticmethod
    def get_inventory():
        res = db.table("Produkty").select("*, Kategorie(nazwa)").execute()
        return res.data

    @staticmethod
    def get_cats():
        return db.table("Kategorie").select("*").execute().data

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏢 Nexus ERP v7.0")
    st.write("**Panel Kontrolny**")
    inv_data = ERPCore.get_inventory()
    
    st.divider()
    search_query = st.text_input("🔍 Szybki podgląd indeksu", placeholder="Wpisz nazwę...")
    if search_query and inv_data:
        match = [p for p in inv_data if search_query.lower() in p['nazwa'].lower()]
        for m in match:
            st.info(f"ID: {m['id']} | Stan: {m['liczba']} szt.")

# --- 5. INTERFEJS GŁÓWNY ---
t_urgent, t_inv, t_invoice, t_stats, t_settings = st.tabs([
    "🚨 Pilne Zakupy", "📦 Inwentaryzacja", "🧾 Wystaw Fakturę", "📊 Analiza", "⚙️ Konfiguracja"
])

df = pd.DataFrame(inv_data) if inv_data else pd.DataFrame()

# --- TAB 1: PILNE ZAKUPY & NOWY TOWAR ---
with t_urgent:
    st.subheader("⚠️ Produkty poniżej minimum")
    if not df.empty:
        low_stock = df[df['liczba'] < 5]
        if not low_stock.empty:
            for _, r in low_stock.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.warning(f"Produkt: {r['nazwa']} (Indeks: {r['id']})")
                qty = c2.number_input("Sztuk", min_value=1, key=f"buy_{r['id']}")
                if c3.button("Dodaj zapas", key=f"btn_{r['id']}"):
                    db.table("Produkty").update({"liczba": r['liczba'] + qty}).eq("id", r['id']).execute()
                    st.rerun()
        else: st.success("Stany magazynowe są bezpieczne.")

    st.divider()
    st.subheader("🆕 Wdrożenie Nowego Produktu")
    with st.expander("Dodaj towar, którego nie ma w ofercie"):
        with st.form("new_prod"):
            n_name = st.text_input("Pełna nazwa towaru")
            cats = ERPCore.get_cats()
            n_cat = st.selectbox("Kategoria", options=cats, format_func=lambda x: x['nazwa'])
            n_price = st.number_input("Cena Netto", min_value=0.01)
            n_qty = st.number_input("Ilość początkowa", min_value=1)
            if st.form_submit_button("Zatwierdź wdrożenie"):
                db.table("Produkty").insert({"nazwa": n_name, "Cena": n_price, "liczba": n_qty, "kategoria_id": n_cat['id']}).execute()
                st.rerun()

# --- TAB 2: INWENTARYZACJA ---
with t_inv:
    st.header("Magazyn")
    if not df.empty:
        st.dataframe(df[['id', 'nazwa', 'liczba', 'Cena']], use_container_width=True, hide_index=True)

# --- TAB 3: FAKTURA (ULEPSZONA) ---
with t_invoice:
    st.header("Moduł Sprzedaży")
    if not df.empty:
        col_setup, col_preview = st.columns([1, 1.5])
        
        with col_setup:
            st.write("### Dane Transakcji")
            klient_rand = ["Jan Kowalski - Tech-Bud", "Anna Nowak - Logistyka S.A.", "Piotr Zieliński - Handel-Mix", "Marek Murarski - Usługi Remontowe"]
            nabywca = st.text_input("Nabywca (Dane do faktury)", value=klient_rand[datetime.datetime.now().second % 4])
            wybrany = st.selectbox("Produkt do sprzedaży", options=inv_data, format_func=lambda x: f"{x['nazwa']} (ID: {x['id']})")
            ilosc_s = st.number_input("Ilość", min_value=1, max_value=int(wybrany['liczba']))
            vat_rate = 0.23
            
            # Obliczenia
            netto_jedn = float(wybrany['Cena'])
            total_netto = netto_jedn * ilosc_s
            total_vat = total_netto * vat_rate
            total_brutto = total_netto + total_vat

        with col_preview:
            # HTML FAKTURA
            st.markdown(f"""
            <div class="invoice-container">
                <div class="invoice-header">
                    <div class="company-logo">📦 NEXUS ERP</div>
                    <div style="text-align: right;">
                        <strong>FAKTURA NR: {datetime.datetime.now().strftime('%Y/%m/%d')}/001</strong><br>
                        Data wystawienia: {datetime.date.today()}
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                    <div>
                        <small>SPRZEDAWCA:</small><br>
                        <strong>Nexus ERP Software sp. z o.o.</strong><br>
                        ul. Programistów 102, 00-001 Warszawa<br>
                        NIP: 123-456-78-90
                    </div>
                    <div style="text-align: right;">
                        <small>NABYWCA:</small><br>
                        <strong>{nabywca}</strong><br>
                        Dane losowe pobrane z systemu
                    </div>
                </div>
                <table class="invoice-table">
                    <thead>
                        <tr>
                            <th>Indeks (ID)</th><th>Nazwa Towaru</th><th>Ilość</th><th>Cena Netto</th><th>Wartość Netto</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>#00{wybrany['id']}</td><td>{wybrany['nazwa']}</td><td>{ilosc_s} szt.</td><td>{netto_jedn:.2f} zł</td><td>{total_netto:.2f} zł</td>
                        </tr>
                    </tbody>
                </table>
                <div class="totals">
                    <table>
                        <tr><td>Suma Netto:</td><td>{total_netto:.2f} zł</td></tr>
                        <tr><td>Podatek VAT (23%):</td><td>{total_vat:.2f} zł</td></tr>
                        <tr class="grand-total"><td>RAZEM BRUTTO:</td><td>{total_brutto:.2f} zł</td></tr>
                    </table>
                </div>
                <div style="clear: both; margin-top: 50px; font-size: 10px; color: #999;">
                    Faktura wygenerowana automatycznie w systemie ERP. Dokument bez podpisu.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔥 ZATWIERDŹ SPRZEDAŻ", use_container_width=True):
                db.table("Produkty").update({"liczba": wybrany['liczba'] - ilosc_s}).eq("id", wybrany['id']).execute()
                st.success("Transakcja zaksięgowana!")
                st.rerun()

# --- TAB 4 & 5: ANALIZA I KONFIGURACJA (UPROSZCZONE) ---
with t_stats:
    if not df.empty:
        st.metric("Globalna Wartość Magazynu (Netto)", f"{(df['Cena'] * df['liczba']).sum():,.2f} zł")
        st.bar_chart(df.set_index('nazwa')['liczba'])

with t_settings:
    st.write("Ustawienia Kategorii")
    with st.form("add_cat"):
        new_c = st.text_input("Nazwa kategorii")
        if st.form_submit_button("Dodaj"):
            db.table("Kategorie").insert({"nazwa": new_c}).execute()
            st.rerun()

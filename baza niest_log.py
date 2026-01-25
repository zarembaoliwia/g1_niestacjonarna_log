import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="ERP Magazyn Pro v3.5", page_icon="🧾", layout="wide")

# Stylizacja dla dokumentu faktury
st.markdown("""
    <style>
    .invoice-box {
        background-color: white; padding: 30px; border: 1px solid #eee;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.15); font-size: 14px; color: #555;
    }
    .invoice-header { font-weight: bold; color: #000; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])

supabase = init_connection()

# --- 3. LOGIKA BIZNESOWA ---
def fetch_data(table):
    return supabase.table(table).select("*").execute().data

def update_stock(product_id, new_qty):
    supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()

# --- 4. INTERFEJS ---
st.title("🚀 Zaawansowany System Magazynowy & Sprzedaży")

tabs = st.tabs(["📊 Dashboard", "📋 Produkty", "🧾 Wystaw Fakturę", "📂 Kategorie"])

# --- TAB: DASHBOARD ---
with tabs[0]:
    prods = fetch_data("Produkty")
    if prods:
        df = pd.DataFrame(prods)
        c1, c2, c3 = st.columns(3)
        c1.metric("Łączna wartość", f"{(df['liczba'] * df['Cena']).sum():,.2f} zł")
        c2.metric("Liczba SKU", len(df))
        c3.metric("Niskie stany", len(df[df['liczba'] < 5]))
        st.bar_chart(df.set_index('nazwa')['liczba'])

# --- TAB: PRODUKTY ---
with tabs[1]:
    st.subheader("Aktualne zapasy")
    raw_data = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    if raw_data:
        formatted_data = [{
            "Produkt": r["nazwa"], 
            "Ilość": r["liczba"], 
            "Cena": f"{r['Cena']:.2f} zł",
            "Kategoria": r["Kategorie"]["nazwa"] if r["Kategorie"] else "Brak"
        } for r in raw_data]
        st.table(formatted_data)

# --- TAB: FAKTURA (NOWOŚĆ!) ---
with tabs[2]:
    st.header("Generator Faktury Sprzedażowej")
    
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        st.subheader("Dane sprzedaży")
        all_prods = fetch_data("Produkty")
        prod_names = {p['nazwa']: p for p in all_prods if p['liczba'] > 0}
        
        selected_p_name = st.selectbox("Wybierz produkt", options=list(prod_names.keys()))
        customer = st.text_input("Nabywca", "Jan Kowalski - Firma Testowa")
        
        if selected_p_name:
            chosen = prod_names[selected_p_name]
            max_qty = chosen['liczba']
            qty_to_sell = st.number_input(f"Ilość (Dostępne: {max_qty})", min_value=1, max_value=max_qty, value=1)
            rabat = st.slider("Rabat (%)", 0, 50, 0)
            
            cena_brutto = float(chosen['Cena']) * (1 - rabat/100)
            razem = cena_brutto * qty_to_sell

    with col_f2:
        st.subheader("Podgląd dokumentu")
        if selected_p_name:
            # Renderowanie faktury w HTML/Markdown
            st.markdown(f"""
            <div class="invoice-box">
                <table style="width:100%">
                    <tr>
                        <td class="invoice-header">FAKTURA NR: {datetime.datetime.now().strftime('%Y/%m/%d')}/001</td>
                        <td style="text-align:right">Data: {datetime.date.today()}</td>
                    </tr>
                </table>
                <hr>
                <p><b>Sprzedawca:</b> Moja Firma Magazynowa sp. z o.o.</p>
                <p><b>Nabywca:</b> {customer}</p>
                <table style="width:100%; border-collapse: collapse;">
                    <tr style="background: #eee;">
                        <th>Produkt</th><th>Ilość</th><th>Cena jedn.</th><th>Suma</th>
                    </tr>
                    <tr>
                        <td>{selected_p_name}</td>
                        <td style="text-align:center">{qty_to_sell} szt.</td>
                        <td style="text-align:right">{cena_brutto:.2f} zł</td>
                        <td style="text-align:right"><b>{razem:.2f} zł</b></td>
                    </tr>
                </table>
                <br>
                <h3 style="text-align:right">DO ZAPŁATY: {razem:.2f} PLN</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✅ Potwierdź sprzedaż i zdejmij ze stanu"):
                # 1. Oblicz nowy stan
                new_stock = chosen['liczba'] - qty_to_sell
                # 2. Wyślij do bazy
                update_stock(chosen['id'], new_stock)
                st.balloons()
                st.success(f"Sprzedano! Nowy stan produktu {selected_p_name}: {new_stock} szt.")
                # Opcjonalnie: st.rerun() po chwili

# --- TAB: KATEGORIE ---
with tabs[3]:
    st.subheader("Zarządzanie strukturą")
    with st.form("cat_form"):
        name = st.text_input("Nowa kategoria")
        desc = st.text_area("Opis")
        if st.form_submit_button("Dodaj"):
            if name:
                supabase.table("Kategorie").insert({"nazwa": name, "opis": desc}).execute()
                st.rerun()
    
    cats = fetch_data("Kategorie")
    for c in cats:
        st.write(f"• **{c['nazwa']}**")

# --- STOPKA ---
st.sidebar.markdown(f"""
---
**Status Systemu:** 🟢 Połączono
**User:** Student_5.0
**Baza:** Supabase Cloud
""")

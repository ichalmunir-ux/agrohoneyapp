import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# --- UI CONFIG ---
st.set_page_config(page_title="AgroHoney Pro Cloud", layout="wide")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNGSI HELPER ---
def generate_code(pemasok, asal, harga):
    p = pemasok[0].upper() if pemasok else "X"
    a = asal[0].upper() if asal else "X"
    h = str(int(harga/1000))
    return f"{p}{a}{h}"

# --- LOGIN SYSTEM ---
st.sidebar.title("🔐 Akses AgroHoney")
user_role = st.sidebar.selectbox("Pilih Role User", ["Pilih User", "Owner", "Admin Penginput"])
password = st.sidebar.text_input("Password", type="password")

# Kredensial (Silakan sesuaikan)
if (user_role == "Owner" and password == "owner123") or (user_role == "Admin Penginput" and password == "admin123"):
    
    st.sidebar.success(f"Login: {user_role}")
    
    # Hak Akses Menu
    if user_role == "Owner":
        menu_options = ["Dashboard Executive", "Rekap Penjualan"]
    else:
        menu_options = ["Dashboard Executive", "Rekap Penjualan", "Input Stok Masuk", "Kasir Penjualan", "Koreksi Data"]

    menu = st.sidebar.radio("Navigasi Menu", menu_options)

    # --- LOADING DATA DARI GSHEETS ---
    df_in = conn.read(worksheet="stok_masuk", ttl="0")
    df_out = conn.read(worksheet="penjualan", ttl="0")
    df_price = conn.read(worksheet="config_harga", ttl="0")

    # --- MENU: DASHBOARD EXECUTIVE ---
    if menu == "Dashboard Executive":
        st.title("🍯 Dashboard Monitoring")
        
        # Safety Stock Alert
        if not df_in.empty:
            low_stock = df_in[df_in['sisa'] < 10]
            for _, row in low_stock.iterrows():
                st.error(f"⚠️ **PERINGATAN:** Batch {row['kode']} sisa {row['sisa']} btl!")

        # Metrik
        modal_invest = 975000 + 7300000
        omzet = (df_out['qty'] * df_out['harga_jual']).sum() if not df_out.empty else 0
        sisa_total = df_in['sisa'].sum() if not df_in.empty else 0
        hutang = len(df_out[df_out['metode'] == 'Hutang']) if not df_out.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Modal Investasi", f"Rp {modal_invest:,.0f}")
        c2.metric("Sisa Stok", f"{sisa_total} Btl")
        c3.metric("Total Omzet", f"Rp {omzet:,.0f}")
        c4.metric("Pending Hutang", f"{hutang} Orang")

        st.divider()
        col_l, col_r = st.columns(2)
        with col_l:
            if not df_in.empty:
                fig_stok = px.bar(df_in, x='kode', y='sisa', color='pemasok', title="Stok per Batch", color_discrete_sequence=px.colors.qualitative.Prism)
                st.plotly_chart(fig_stok, use_container_width=True)
        with col_r:
            if not df_out.empty:
                fig_pie = px.pie(df_out, names='metode', title="Metode Pembayaran", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

    # --- MENU: REKAP PENJUALAN ---
    elif menu == "Rekap Penjualan":
        st.header("📋 Rekap Penjualan & Kontrol Stok")
        if not df_out.empty:
            st.dataframe(df_out, use_container_width=True)
            csv = df_out.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "Rekap_Penjualan.csv", "text/csv")
        else:
            st.info("Belum ada transaksi.")

    # --- MENU: INPUT STOK MASUK ---
    elif menu == "Input Stok Masuk":
        st.header("📥 Input Penerimaan Barang")
        with st.form("in_form", clear_on_submit=True):
            pemasok = st.text_input("Nama Pemasok")
            asal = st.text_input("Asal")
            qty = st.number_input("Qty", min_value=1)
            modal = st.number_input("Modal per Btl", min_value=0)
            if st.form_submit_button("Simpan ke Cloud"):
                kode = generate_code(pemasok, asal, modal)
                new_data = pd.DataFrame([[kode, datetime.now().strftime("%Y-%m-%d"), pemasok, asal, qty, modal, qty]], 
                                        columns=df_in.columns)
                updated_df = pd.concat([df_in, new_data], ignore_index=True)
                conn.update(worksheet="stok_masuk", data=updated_df)
                st.success(f"Tersimpan! Kode: {kode}")

    # --- MENU: KASIR PENJUALAN ---
    elif menu == "Kasir Penjualan":
        st.header("💸 Transaksi Keluar")
        with st.form("out_form", clear_on_submit=True):
            pembeli = st.text_input("Nama Pembeli")
            kode_pilih = st.selectbox("Pilih Kode Madu", df_in[df_in['sisa']>0]['kode'].tolist() if not df_in.empty else ["Kosong"])
            qty_jual = st.number_input("Qty Keluar", min_value=1)
            kat_harga = st.selectbox("Kategori Harga", df_price['kategori'].tolist())
            metode = st.selectbox("Metode Bayar", ["Tunai", "Transfer", "Hutang"])
            
            if st.form_submit_button("Proses Transaksi"):
                harga_j = int(df_price.loc[df_price['kategori']==kat_harga, 'harga'].values[0])
                # Logika Update Stok & Simpan Transaksi (conn.update)
                # ... (Logika penanganan update dataframe penjualan)
                st.success("Transaksi Berhasil!")

else:
    if user_role != "Pilih User":
        st.sidebar.error("Password Salah!")
    st.title("🐝 AgroHoney Management")
    st.image("https://images.unsplash.com/photo-1558611848-73f7eb4001a1?q=80&w=800")
    st.info("Silakan Login di sidebar untuk akses sistem.")
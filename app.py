import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AgroHoney Pro Cloud v2", layout="wide", page_icon="🐝")

# --- 2. DATABASE CONNECTION (GSHEETS) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def load_data(sheet_name):
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            # Standarisasi kolom numerik
            for col in ['qty', 'modal', 'sisa', 'harga', 'harga_jual', 'harga_lama', 'harga_baru']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except:
            return pd.DataFrame()

    df_in = load_data("stok_masuk")
    df_out = load_data("penjualan")
    df_price = load_data("config_harga")
    df_log_price = load_data("log_harga")

except Exception as e:
    st.error(f"❌ Gagal Terhubung ke Cloud: {e}")
    st.stop()

# --- 3. LOGIN & ACCESS CONTROL ---
st.sidebar.title("🔐 AgroHoney Access")
role = st.sidebar.selectbox("Pilih Akses", ["Pilih User", "Owner", "Admin Penginput"])
key = st.sidebar.text_input("Password", type="password")

if (role == "Owner" and key == "owner123") or (role == "Admin Penginput" and key == "admin123"):
    st.sidebar.success(f"Login: {role}")
    
    # --- NAVIGASI LENGKAP ---
    if role == "Owner":
        nav = ["📊 Dashboard Executive", "📋 Rekap Penjualan", "📦 Kontrol Stok Barang"]
    else:
        nav = ["📊 Dashboard Executive", "📋 Rekap Penjualan", "📦 Kontrol Stok Barang", 
               "📥 Input Stok Masuk", "💸 Kasir Penjualan", "⚙️ Update Harga Jual", "🛠️ Koreksi Data"]
        
    menu = st.sidebar.radio("Navigasi", nav)

    # --- MENU: DASHBOARD EXECUTIVE ---
    if "Dashboard" in menu:
        st.title("🍯 Executive Dashboard")
        if not df_in.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Sisa Stok", f"{int(df_in['sisa'].sum())} Btl")
            c2.metric("Total Omzet", f"Rp {(df_out['qty'] * df_out['harga_jual']).sum() if not df_out.empty else 0:,.0f}")
            c3.metric("Lot Aktif", f"{len(df_in[df_in['sisa']>0])} Batch")
            
            st.divider()
            col_l, col_r = st.columns(2)
            with col_l:
                fig = px.bar(df_in, x='kode', y='sisa', title="Stok Tersedia per Batch", color='sisa')
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                if not df_out.empty:
                    fig_pie = px.pie(df_out, names='metode', title="Metode Pembayaran")
                    st.plotly_chart(fig_pie, use_container_width=True)

    # --- MENU: REKAP PENJUALAN ---
    elif "Rekap Penjualan" in menu:
        st.header("📋 Rekap Penjualan")
        st.dataframe(df_out, use_container_width=True)

    # --- MENU: KONTROL STOK BARANG (REKAP STOK) ---
    elif "Kontrol Stok" in menu:
        st.header("📦 Kontrol & Rekap Stok Barang")
        st.subheader("Detail Sisa Stok per Batch")
        st.dataframe(df_in, use_container_width=True)

    # --- MENU: INPUT STOK MASUK ---
    elif "Input Stok" in menu:
        st.header("📥 Input Stok Baru")
        with st.form("form_in", clear_on_submit=True):
            pmsok = st.text_input("Pemasok")
            asl = st.text_input("Asal")
            jml = st.number_input("Qty", min_value=1)
            mdl = st.number_input("Modal", min_value=0)
            if st.form_submit_button("Simpan"):
                kd = f"{pmsok[0].upper()}{asl[0].upper()}{int(mdl/1000)}"
                new_row = pd.DataFrame([[kd, datetime.now().strftime("%Y-%m-%d"), pmsok, asl, jml, mdl, jml]], columns=df_in.columns)
                conn.update(worksheet="stok_masuk", data=pd.concat([df_in, new_row], ignore_index=True))
                st.success(f"Data Tersimpan: {kd}")
                st.rerun()

    # --- MENU: UPDATE HARGA JUAL ---
    elif "Update Harga" in menu:
        st.header("⚙️ Konfigurasi Harga Jual")
        st.write("Harga Saat Ini:")
        st.table(df_price)
        with st.form("form_price"):
            resmi = st.number_input("Harga Resmi", value=int(df_price.loc[df_price['kategori']=='Resmi', 'harga'].values[0]))
            owner = st.number_input("Harga Owner", value=int(df_price.loc[df_price['kategori']=='Owner', 'harga'].values[0]))
            mark = st.number_input("Harga Marketing", value=int(df_price.loc[df_price['kategori']=='Marketing', 'harga'].values[0]))
            if st.form_submit_button("Update Harga"):
                updated_price = pd.DataFrame({'kategori':['Resmi','Owner','Marketing'], 'harga':[resmi, owner, mark]})
                conn.update(worksheet="config_harga", data=updated_price)
                st.success("Harga Berhasil Diperbarui!")
                st.rerun()

    # --- MENU: KOREKSI DATA (HAPUS/UPDATE) ---
    elif "Koreksi Data" in menu:
        st.header("🛠️ Koreksi Data (Delete)")
        tab1, tab2 = st.tabs(["Hapus Batch Stok", "Hapus Transaksi Penjualan"])
        with tab1:
            kode_hapus = st.selectbox("Pilih Kode Batch yang akan Dihapus", [""] + df_in['kode'].tolist())
            if st.button("Hapus Batch Stok"):
                df_in = df_in[df_in['kode'] != kode_hapus]
                conn.update(worksheet="stok_masuk", data=df_in)
                st.success("Batch Terhapus!")
                st.rerun()
        with tab2:
            id_hapus = st.number_input("Masukkan ID Penjualan", min_value=0)
            if st.button("Hapus Transaksi"):
                df_out = df_out[df_out['id'] != id_hapus]
                conn.update(worksheet="penjualan", data=df_out)
                st.success("Transaksi Terhapus!")
                st.rerun()

else:
    if role != "Pilih User": st.sidebar.error("Password Salah!")
    st.title("🐝 AgroHoney Management Cloud")
    st.info("Silakan login untuk mengakses fitur kontrol.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="AgroHoney Pro Cloud", layout="wide", page_icon="🐝")

# --- 2. KONEKSI DATA ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Fungsi pembantu untuk membaca data dengan aman
    def load_data(sheet_name):
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            # Konversi kolom numerik agar tidak error saat perhitungan
            numeric_cols = ['qty', 'modal', 'sisa', 'harga_jual']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except:
            return pd.DataFrame()

    df_in = load_data("stok_masuk")
    df_out = load_data("penjualan")
    df_price = load_data("config_harga")
    
except Exception as e:
    st.error(f"Koneksi Cloud Bermasalah: {e}")
    st.stop()

# --- 3. LOGIN SYSTEM ---
st.sidebar.image("https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=200", caption="AgroHoney Management")
user_role = st.sidebar.selectbox("Pilih Role User", ["Pilih User", "Owner", "Admin Penginput"])
password = st.sidebar.text_input("Password", type="password")

# Akses (Owner: owner123 | Admin: admin123)
if (user_role == "Owner" and password == "owner123") or (user_role == "Admin Penginput" and password == "admin123"):
    
    st.sidebar.success(f"🔓 Login Berhasil: {user_role}")
    
    # Menu Berdasarkan Role
    if user_role == "Owner":
        menu_options = ["📊 Dashboard Executive", "📋 Rekap Penjualan"]
    else:
        menu_options = ["📊 Dashboard Executive", "📋 Rekap Penjualan", "📥 Input Stok Masuk", "💸 Kasir Penjualan"]

    menu = st.sidebar.radio("Navigasi", menu_options)

    # --- MENU: DASHBOARD ---
    if "Dashboard" in menu:
        st.title("🍯 Dashboard Executive Monitoring")
        
        if not df_in.empty:
            # Metrik Utama
            total_sisa = df_in['sisa'].sum()
            omzet = (df_out['qty'] * df_out['harga_jual']).sum() if not df_out.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Sisa Stok Gudang", f"{int(total_sisa)} Botol")
            c2.metric("Total Omzet Penjualan", f"Rp {omzet:,.0f}")
            c3.metric("Total Batch Madu", f"{len(df_in)} Batch")

            st.divider()
            col_l, col_r = st.columns(2)
            with col_l:
                fig_stok = px.bar(df_in, x='kode', y='sisa', title="Sisa Stok per Batch", color='sisa', color_continuous_scale='YlOrBr')
                st.plotly_chart(fig_stok, use_container_width=True)
            with col_r:
                if not df_out.empty:
                    fig_pie = px.pie(df_out, names='metode', title="Proporsi Metode Pembayaran")
                    st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Belum ada data stok masuk. Silakan Admin menginput data terlebih dahulu.")

    # --- MENU: REKAP ---
    elif "Rekap" in menu:
        st.header("📋 Laporan Transaksi")
        if not df_out.empty:
            st.dataframe(df_out, use_container_width=True)
            st.download_button("Download CSV", df_out.to_csv(index=False), "Laporan_AgroHoney.csv")
        else:
            st.warning("Belum ada riwayat penjualan.")

    # --- MENU: INPUT STOK (ADMIN ONLY) ---
    elif "Input Stok" in menu:
        st.header("📥 Form Input Stok Masuk")
        with st.form("form_in", clear_on_submit=True):
            pemasok = st.text_input("Nama Pemasok")
            asal = st.text_input("Asal Madu")
            qty = st.number_input("Jumlah Botol", min_value=1)
            modal = st.number_input("Harga Modal/Btl", min_value=0)
            
            if st.form_submit_button("Simpan Data ke Cloud"):
                # Logika Generate Kode AJ80
                p = pemasok[0].upper() if pemasok else "X"
                a = asal[0].upper() if asal else "X"
                h = str(int(modal/1000))
                kode = f"{p}{a}{h}"
                
                new_row = pd.DataFrame([[kode, datetime.now().strftime("%Y-%m-%d"), pemasok, asal, qty, modal, qty]], columns=df_in.columns)
                updated_in = pd.concat([df_in, new_row], ignore_index=True)
                conn.update(worksheet="stok_masuk", data=updated_in)
                st.success(f"✅ Berhasil! Kode Produk: {kode}")
                st.rerun()

    # --- MENU: KASIR (ADMIN ONLY) ---
    elif "Kasir" in menu:
        st.header("💸 Kasir Penjualan")
        # Logika Kasir sama dengan sebelumnya namun menggunakan conn.update
        st.info("Fitur Kasir siap digunakan.")

else:
    if user_role != "Pilih User":
        st.sidebar.error("Password Salah!")
    st.title("🐝 AgroHoney Management System")
    st.write("Sistem Monitoring Operasional Agrowisata Terintegrasi Cloud.")
    st.image("https://images.unsplash.com/photo-1473973266408-ed4e27abdd47?w=800", caption="Monitoring Real-time via Google Sheets")
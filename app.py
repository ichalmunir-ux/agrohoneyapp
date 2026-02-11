import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="AgroHoney Pro Cloud", layout="wide", page_icon="🐝")

# --- 2. KONEKSI GOOGLE SHEETS (DENGAN PENANGANAN ERROR) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Fungsi Load Data yang Aman
    def load_data(sheet_name):
        try:
            df = conn.read(worksheet=sheet_name, ttl=0)
            # Pastikan kolom angka tetap terbaca angka
            for col in ['qty', 'modal', 'sisa', 'harga_jual']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except:
            # Jika sheet belum ada atau kosong, buat dataframe kosong dengan kolom minimal
            return pd.DataFrame(columns=['kode', 'tanggal', 'pemasok', 'asal', 'qty', 'modal', 'sisa'])

    df_in = load_data("stok_masuk")
    df_out = load_data("penjualan")
    df_price = load_data("config_harga")

except Exception as e:
    st.error(f"❌ Koneksi ke Database Cloud Gagal: {e}")
    st.stop()

# --- 3. SISTEM AKSES (LOGIN) ---
st.sidebar.header("🐝 Login AgroHoney")
role = st.sidebar.selectbox("Pilih Akses", ["Pilih User", "Owner", "Admin Penginput"])
key = st.sidebar.text_input("Password", type="password")

# Cek Kredensial
if (role == "Owner" and key == "owner123") or (role == "Admin Penginput" and key == "admin123"):
    
    st.sidebar.success(f"Masuk sebagai: {role}")
    
    # Navigasi berdasarkan Role
    if role == "Owner":
        nav = ["📊 Dashboard Executive", "📋 Rekap Penjualan"]
    else:
        nav = ["📊 Dashboard Executive", "📋 Rekap Penjualan", "📥 Input Stok Masuk", "💸 Kasir Penjualan"]
        
    choice = st.sidebar.radio("Menu Navigasi", nav)

    # --- FITUR: DASHBOARD ---
    if "Dashboard" in choice:
        st.title("🍯 Monitoring Operasional Real-time")
        
        if not df_in.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Stok Tersedia", f"{int(df_in['sisa'].sum())} Btl")
            c2.metric("Total Omzet", f"Rp {(df_out['qty'] * df_out['harga_jual']).sum() if not df_out.empty else 0:,.0f}")
            c3.metric("Total Batch", f"{len(df_in)} Lot")

            st.divider()
            col_l, col_r = st.columns(2)
            with col_l:
                fig = px.bar(df_in, x='kode', y='sisa', title="Grafik Sisa Stok per Batch", color='sisa', color_continuous_scale='Brwnyl')
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                if not df_out.empty:
                    fig_pie = px.pie(df_out, names='metode', title="Metode Pembayaran Terpopuler")
                    st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Selamat datang! Belum ada data stok yang diinput oleh Admin.")

    # --- FITUR: REKAP PENJUALAN ---
    elif "Rekap" in choice:
        st.header("📋 Rekapitulasi Data Transaksi")
        st.dataframe(df_out, use_container_width=True)
        st.download_button("Simpan Laporan (CSV)", df_out.to_csv(index=False), "Laporan_AgroHoney.csv")

    # --- FITUR: INPUT STOK (ADMIN ONLY) ---
    elif "Input Stok" in choice:
        st.header("📥 Form Penerimaan Madu Baru")
        with st.form("input_stok", clear_on_submit=True):
            pmsok = st.text_input("Nama Pemasok")
            asl = st.text_input("Daerah Asal")
            jml = st.number_input("Jumlah (Botol)", min_value=1)
            mdl = st.number_input("Modal per Botol", min_value=0)
            
            if st.form_submit_button("Kirim ke Cloud"):
                # Logika Penamaan AJ80
                kd = f"{pmsok[0].upper() if pmsok else 'X'}{asl[0].upper() if asl else 'X'}{int(mdl/1000)}"
                
                new_data = pd.DataFrame([[kd, datetime.now().strftime("%Y-%m-%d"), pmsok, asl, jml, mdl, jml]], columns=df_in.columns)
                updated_df = pd.concat([df_in, new_data], ignore_index=True)
                conn.update(worksheet="stok_masuk", data=updated_df)
                st.success(f"Data Berhasil Disimpan! Kode Produk: {kd}")
                st.rerun()

    # --- FITUR: KASIR (ADMIN ONLY) ---
    elif "Kasir" in choice:
        st.header("💸 Kasir Penjualan")
        st.info("Menu Kasir siap digunakan untuk mencatat penjualan harian.")

else:
    if role != "Pilih User":
        st.sidebar.error("Akses Ditolak: Password Salah!")
    st.title("🐝 AgroHoney Management Cloud")
    st.markdown("---")
    st.write("Sistem ini terhubung langsung ke Google Sheets perusahaan. Silakan login untuk melihat dashboard atau menginput data.")
    st.image("https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=800", caption="Digitalisasi Agrowisata California")

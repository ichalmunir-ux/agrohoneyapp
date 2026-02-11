import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="AgroHoney Pro Cloud", layout="wide")

# --- KONEKSI DENGAN TRY-EXCEPT ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Gunakan TTL=0 agar data selalu fresh
    df_in = conn.read(worksheet="stok_masuk", ttl=0)
    st.sidebar.success("✅ Database Terhubung")
except Exception as e:
    st.error(f"❌ Koneksi GSheets Gagal: {e}")
    st.info("Pastikan URL di Secrets sudah benar dan Google Sheets sudah di-share ke 'Anyone with the link'.")
    st.stop()

# --- LOGIN SEDERHANA ---
st.sidebar.title("🔐 Login")
user = st.sidebar.selectbox("Role", ["Pilih User", "Owner", "Admin"])
passw = st.sidebar.text_input("Password", type="password")

if (user == "Owner" and passw == "owner123") or (user == "Admin" and passw == "admin123"):
    st.title(f"🐝 Selamat Datang, {user}")
    st.write("Aplikasi siap digunakan. Silakan pilih menu di sidebar.")
    # Tambahkan menu navigasi Anda di sini...
else:
    st.title("🐝 AgroHoney Management")
    st.warning("Silakan login untuk memulai.")
# Kredensial sesuai profil Anda
if (user_role == "Owner" and password == "owner123") or (user_role == "Admin Penginput" and password == "admin123"):
    st.sidebar.success(f"Login: {user_role}")
    
    # Hak Akses Menu
    menu_options = ["Dashboard Executive", "Rekap Penjualan"] if user_role == "Owner" else ["Dashboard Executive", "Rekap Penjualan", "Input Stok Masuk", "Kasir Penjualan", "Koreksi Data"]
    menu = st.sidebar.radio("Navigasi Menu", menu_options)

    # --- LOADING & CLEANING DATA ---
    try:
        df_in = clean_data(conn.read(worksheet="stok_masuk", ttl="0"))
        df_out = clean_data(conn.read(worksheet="penjualan", ttl="0"))
        df_price = clean_data(conn.read(worksheet="config_harga", ttl="0"))
    except Exception as e:
        st.error(f"Gagal memuat data dari Cloud: {e}")
        st.stop()

    # --- MENU: DASHBOARD EXECUTIVE ---
    if menu == "Dashboard Executive":
        st.title("🍯 Dashboard Monitoring")
        
        # Safety Stock Alert (< 10 botol)
        low_stock = df_in[df_in['sisa'] < 10]
        for _, row in low_stock.iterrows():
            st.error(f"⚠️ **PERINGATAN:** Batch {row['kode']} sisa {int(row['sisa'])} btl!")

        # Metrik Utama
        modal_invest = 975000 + 7300000 # Sesuai parameter modal Anda
        omzet = (df_out['qty'] * df_out['harga_jual']).sum()
        sisa_total = df_in['sisa'].sum()
        hutang = len(df_out[df_out['metode'] == 'Hutang'])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Modal Investasi", f"Rp {modal_invest:,.0f}")
        c2.metric("Sisa Stok", f"{int(sisa_total)} Btl")
        c3.metric("Total Omzet", f"Rp {omzet:,.0f}")
        c4.metric("Pending Hutang", f"{hutang} Orang")

        st.divider()
        col_l, col_r = st.columns(2)
        with col_l:
            fig_stok = px.bar(df_in, x='kode', y='sisa', color='pemasok', title="Stok per Batch")
            st.plotly_chart(fig_stok, use_container_width=True)
        with col_r:
            if not df_out.empty:
                fig_pie = px.pie(df_out, names='metode', title="Metode Pembayaran", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

    # --- MENU: REKAP PENJUALAN ---
    elif menu == "Rekap Penjualan":
        st.header("📋 Rekap Penjualan & Kontrol Stok")
        st.dataframe(df_out, use_container_width=True)
        csv = df_out.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "Rekap_Penjualan.csv", "text/csv")

    # --- MENU: INPUT STOK (ADMIN ONLY) ---
    elif menu == "Input Stok Masuk":
        st.header("📥 Input Penerimaan Barang")
        with st.form("in_form", clear_on_submit=True):
            pemasok = st.text_input("Nama Pemasok")
            asal = st.text_input("Asal")
            qty = st.number_input("Qty", min_value=1)
            modal = st.number_input("Modal per Btl", min_value=0)
            if st.form_submit_button("Simpan ke Cloud"):
                kode = generate_code(pemasok, asal, modal)
                new_row = pd.DataFrame([[kode, datetime.now().strftime("%Y-%m-%d"), pemasok, asal, qty, modal, qty]], columns=df_in.columns)
                updated_df = pd.concat([df_in, new_row], ignore_index=True)
                conn.update(worksheet="stok_masuk", data=updated_df)
                st.success(f"Tersimpan! Kode: {kode}")
                st.rerun()

    # --- MENU: KASIR PENJUALAN ---
    elif menu == "Kasir Penjualan":
        st.header("💸 Transaksi Keluar")
        with st.form("out_form", clear_on_submit=True):
            pembeli = st.text_input("Nama Pembeli")
            available_codes = df_in[df_in['sisa'] > 0]['kode'].tolist()
            kode_pilih = st.selectbox("Pilih Kode Madu", available_codes if available_codes else ["Kosong"])
            qty_jual = st.number_input("Qty Keluar", min_value=1)
            kat_harga = st.selectbox("Kategori Harga", df_price['kategori'].tolist())
            metode = st.selectbox("Metode Bayar", ["Tunai", "Transfer", "Hutang"])
            
            if st.form_submit_button("Proses Transaksi"):
                if kode_pilih != "Kosong":
                    harga_j = int(df_price.loc[df_price['kategori']==kat_harga, 'harga'].values[0])
                    sisa_skrg = df_in.loc[df_in['kode']==kode_pilih, 'sisa'].values[0]
                    
                    if qty_jual <= sisa_skrg:
                        # Update Penjualan
                        new_out = pd.DataFrame([[len(df_out)+1, datetime.now().strftime("%Y-%m-%d"), pembeli, kode_pilih, qty_jual, harga_j, metode]], columns=df_out.columns)
                        updated_out = pd.concat([df_out, new_out], ignore_index=True)
                        # Update Sisa Stok
                        df_in.loc[df_in['kode'] == kode_pilih, 'sisa'] -= qty_jual
                        
                        conn.update(worksheet="penjualan", data=updated_out)
                        conn.update(worksheet="stok_masuk", data=df_in)
                        st.success("Transaksi Berhasil!")
                        st.rerun()
                    else:
                        st.error("Stok tidak mencukupi!")

else:
    if user_role != "Pilih User":
        st.sidebar.error("Password Salah!")
    st.title("🐝 AgroHoney Management")
    st.info("Silakan Login di sidebar untuk akses sistem.")


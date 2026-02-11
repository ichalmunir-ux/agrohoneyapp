import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# --- 1. KONEKSI & DATABASE ---
def get_db_connection():
    conn = sqlite3.connect('agrohoney_pro.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stok_masuk 
                 (kode TEXT PRIMARY KEY, tanggal TEXT, pemasok TEXT, asal TEXT, 
                  qty INTEGER, modal INTEGER, sisa INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS penjualan 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tanggal TEXT, pembeli TEXT, 
                  kode TEXT, qty INTEGER, harga_jual INTEGER, metode TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config_harga (kategori TEXT PRIMARY KEY, harga INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS log_harga (id INTEGER PRIMARY KEY, kategori TEXT, harga_lama INTEGER, harga_baru INTEGER, tanggal TEXT)''')
    
    prices = [('Resmi', 120000), ('Owner', 110000), ('Marketing', 108000)]
    c.executemany("INSERT OR IGNORE INTO config_harga VALUES (?,?)", prices)
    conn.commit()
    conn.close()

init_db()

# --- 2. FUNGSI PENDUKUNG ---
def generate_code(pemasok, asal, harga):
    p = pemasok[0].upper() if pemasok else "X"
    a = asal[0].upper() if asal else "X"
    h = str(int(harga/1000))
    return f"{p}{a}{h}"

# --- 3. UI CONFIG ---
st.set_page_config(page_title="AgroHoney Pro", layout="wide")
st.sidebar.title("🐝 AgroHoney Management")
menu = st.sidebar.radio("Navigasi", [
    "Dashboard Executive", 
    "Rekap Penjualan",
    "Input Stok Masuk", 
    "Kasir Penjualan", 
    "Update Harga Jual", 
    "Koreksi Data"
])

# --- MENU: DASHBOARD EXECUTIVE ---
if menu == "Dashboard Executive":
    st.title("🍯 Executive Dashboard")
    conn = get_db_connection()
    df_in = pd.read_sql("SELECT * FROM stok_masuk", conn)
    df_out = pd.read_sql("SELECT * FROM penjualan", conn)
    conn.close()

    # Safety Stock Alert
    if not df_in.empty:
        low_stock = df_in[df_in['sisa'] < 10]
        for _, row in low_stock.iterrows():
            st.error(f"⚠️ **STOK KRITIS:** {row['kode']} sisa {row['sisa']} botol!")

    # Metrik Utama
    modal_invest = 975000 + 7300000
    total_omzet = (df_out['qty'] * df_out['harga_jual']).sum() if not df_out.empty else 0
    sisa_stok = df_in['sisa'].sum() if not df_in.empty else 0
    jml_hutang = len(df_out[df_out['metode'] == 'Hutang']) if not df_out.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Modal Investasi", f"Rp {modal_invest:,.0f}")
    c2.metric("Sisa Stok Total", f"{sisa_stok} Btl")
    c3.metric("Total Omzet", f"Rp {total_omzet:,.0f}")
    c4.metric("Pending Hutang", f"{jml_hutang} Trx")

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        if not df_in.empty:
            fig_stok = px.bar(df_in, x='kode', y='sisa', color='pemasok', title="Sisa Stok per Batch", color_discrete_sequence=px.colors.qualitative.Vivid)
            st.plotly_chart(fig_stok, use_container_width=True)
    with col_r:
        if not df_out.empty:
            fig_pie = px.pie(df_out, names='metode', title="Proporsi Metode Bayar", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Belum ada data penjualan untuk grafik.")

# --- MENU BARU: REKAP PENJUALAN ---
elif menu == "Rekap Penjualan":
    st.header("📋 Rekapitulasi Penjualan & Kontrol Stok")
    conn = get_db_connection()
    df_out = pd.read_sql("SELECT * FROM penjualan", conn)
    conn.close()

    if not df_out.empty:
        # Grouping data untuk kontrol stok
        rekap = df_out.groupby('kode').agg({
            'qty': 'sum',
            'harga_jual': lambda x: (x * df_out.loc[x.index, 'qty']).sum()
        }).reset_index()
        rekap.columns = ['Kode Barang', 'Total Terjual (Qty)', 'Total Nilai Terjual (Rp)']
        
        st.subheader("Ringkasan Penjualan per Batch")
        st.dataframe(rekap.style.format({'Total Nilai Terjual (Rp)': '{:,.0f}'}), use_container_width=True)
        
        # Detail Transaksi
        st.subheader("Detail Seluruh Transaksi")
        st.write(df_out)
    else:
        st.warning("Data penjualan masih kosong.")

# --- MENU: INPUT STOK MASUK ---
elif menu == "Input Stok Masuk":
    st.header("📥 Input Stok Masuk")
    with st.form("in_form", clear_on_submit=True):
        pemasok = st.text_input("Nama Pemasok")
        asal = st.text_input("Asal Pemasok")
        qty = st.number_input("Jumlah (Botol)", min_value=1)
        modal = st.number_input("Harga Modal (IDR)", min_value=0)
        if st.form_submit_button("Simpan"):
            kode = generate_code(pemasok, asal, modal)
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO stok_masuk VALUES (?,?,?,?,?,?,?)", (kode, datetime.now().strftime("%Y-%m-%d"), pemasok, asal, qty, modal, qty))
            conn.commit()
            conn.close()
            st.success(f"Kode: {kode} Berhasil Disimpan!")

# --- MENU: KASIR PENJUALAN ---
elif menu == "Kasir Penjualan":
    st.header("💸 Kasir Penjualan")
    conn = get_db_connection()
    df_stok = pd.read_sql("SELECT kode, sisa FROM stok_masuk WHERE sisa > 0", conn)
    df_price = pd.read_sql("SELECT * FROM config_harga", conn)
    
    with st.form("out_form", clear_on_submit=True):
        pembeli = st.text_input("Nama Pembeli")
        kode_pilih = st.selectbox("Pilih Kode Madu", df_stok['kode'].tolist() if not df_stok.empty else ["Kosong"])
        qty_jual = st.number_input("Qty", min_value=1)
        kat_harga = st.selectbox("Kategori Harga", ["Resmi", "Owner", "Marketing"])
        metode = st.selectbox("Metode Bayar", ["Tunai", "Transfer", "Hutang"])
        
        if st.form_submit_button("Proses"):
            if kode_pilih != "Kosong":
                harga_f = int(df_price.loc[df_price['kategori']==kat_harga, 'harga'].values[0])
                c = conn.cursor()
                sisa_skrg = df_stok.loc[df_stok['kode']==kode_pilih, 'sisa'].values[0]
                if qty_jual <= sisa_skrg:
                    c.execute("INSERT INTO penjualan (tanggal, pembeli, kode, qty, harga_jual, metode) VALUES (?,?,?,?,?,?)", 
                              (datetime.now().strftime("%Y-%m-%d"), pembeli, kode_pilih, qty_jual, harga_f, metode))
                    c.execute("UPDATE stok_masuk SET sisa = sisa - ? WHERE kode = ?", (qty_jual, kode_pilih))
                    conn.commit()
                    st.success("Berhasil!")
                    st.rerun()
                else: st.error("Stok Kurang!")
    conn.close()

# --- MENU: UPDATE HARGA JUAL ---
elif menu == "Update Harga Jual":
    st.header("⚙️ Update Harga Jual")
    conn = get_db_connection()
    df_p = pd.read_sql("SELECT * FROM config_harga", conn)
    with st.form("price_form"):
        resmi = st.number_input("Harga Resmi", value=int(df_p.loc[df_p['kategori']=='Resmi', 'harga'].values[0]))
        owner = st.number_input("Harga Owner", value=int(df_p.loc[df_p['kategori']=='Owner', 'harga'].values[0]))
        mark = st.number_input("Harga Marketing", value=int(df_p.loc[df_p['kategori']=='Marketing', 'harga'].values[0]))
        if st.form_submit_button("Simpan"):
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for cat, val in [('Resmi', resmi), ('Owner', owner), ('Marketing', mark)]:
                old_v = int(df_p.loc[df_p['kategori']==cat, 'harga'].values[0])
                if old_v != val:
                    c.execute("INSERT INTO log_harga (kategori, harga_lama, harga_baru, tanggal) VALUES (?,?,?,?)", (cat, old_v, val, now))
                    c.execute("UPDATE config_harga SET harga=? WHERE kategori=?", (val, cat))
            conn.commit()
            st.success("Harga Diupdate!")
    conn.close()

# --- MENU: KOREKSI DATA ---
elif menu == "Koreksi Data":
    st.header("🛠️ Koreksi Data")
    tab_in, tab_out = st.tabs(["Koreksi Stok", "Koreksi Penjualan"])
    with tab_in:
        conn = get_db_connection()
        df_in = pd.read_sql("SELECT * FROM stok_masuk", conn)
        st.dataframe(df_in, use_container_width=True)
        kode_h = st.selectbox("Pilih Kode Barang Hapus", [""] + df_in['kode'].tolist())
        if st.button("Hapus Batch"):
            c = conn.cursor()
            c.execute("DELETE FROM stok_masuk WHERE kode=?", (kode_h,))
            conn.commit()
            st.rerun()
        conn.close()
    with tab_out:
        conn = get_db_connection()
        df_out = pd.read_sql("SELECT * FROM penjualan", conn)
        st.dataframe(df_out, use_container_width=True)
        id_h = st.number_input("ID Penjualan untuk Hapus", min_value=0)
        if st.button("Hapus Penjualan & Restock"):
            c = conn.cursor()
            res = c.execute("SELECT kode, qty FROM penjualan WHERE id=?", (id_h,)).fetchone()
            if res:
                c.execute("UPDATE stok_masuk SET sisa = sisa + ? WHERE kode = ?", (res[1], res[0]))
                c.execute("DELETE FROM penjualan WHERE id = ?", (id_h,))
                conn.commit()
                st.success("Terhapus!")
                st.rerun()
        conn.close()
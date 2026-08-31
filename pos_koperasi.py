import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
from sqlalchemy import text

st.set_page_config(page_title="Sistem Koperasi Merah Putih", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #E3182D; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] button { background-color: #A3101F !important; color: white !important; border: 1px solid white !important; }
    [data-testid="stSidebar"] button:hover { background-color: white !important; color: #E3182D !important; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = ''
if 'keranjang' not in st.session_state:
    st.session_state['keranjang'] = []

def proses_login(username, password):
    if username == 'admin' and password == 'admin123':
        st.session_state['logged_in'] = True
        st.session_state['role'] = 'Admin'
    elif username == 'kasir' and password == 'kasir123':
        st.session_state['logged_in'] = True
        st.session_state['role'] = 'Kasir'
    else:
        st.error("Gagal: Username atau Password salah!")

if not st.session_state['logged_in']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if os.path.exists("Logo-Koperasi-Merah-Putih_2.png"):
            st.image("Logo-Koperasi-Merah-Putih_2.png", use_container_width=True)
        with st.form("form_login"):
            st.markdown("### 🔐 Login Sistem POS")
            input_user = st.text_input("Username")
            input_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True, type="primary"):
                proses_login(input_user, input_pass)
                st.rerun()
    st.stop()

# ==========================================
# KONEKSI CLOUD (SUPABASE via SQLAlchemy)
# ==========================================
conn = st.connection("supabase", type="sql")

with conn.session as session:
    session.execute(text('''
        CREATE TABLE IF NOT EXISTS stok_barang (
            id_barang SERIAL PRIMARY KEY, 
            nama_barang TEXT, 
            kategori TEXT, 
            harga_beli REAL, 
            harga_jual REAL, 
            stok INTEGER DEFAULT 0, 
            tanggal_kedaluwarsa TEXT
        )
    '''))
    session.execute(text('''
        CREATE TABLE IF NOT EXISTS riwayat_transaksi (
            id_trx SERIAL PRIMARY KEY, 
            tanggal TEXT, 
            nama_barang TEXT, 
            qty INTEGER, 
            omzet REAL, 
            laba REAL, 
            kasir TEXT, 
            no_struk TEXT, 
            pajak REAL DEFAULT 0
        )
    '''))
    session.commit()

with st.sidebar:
    if os.path.exists("Logo-Koperasi-Merah-Putih_2.png"):
        st.image("Logo-Koperasi-Merah-Putih_2.png", use_container_width=True)
    st.write("---")
    st.markdown("### 👨‍💼 Menu Utama")
    st.write(f"Hak Akses: **{st.session_state['role']}**")
    st.write("") 
    if st.button("Keluar (Logout)", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['keranjang'] = [] 
        st.rerun()

if st.session_state['role'] == 'Admin':
    tab_pos, tab_gudang, tab_laporan = st.tabs(["🛒 Etalase (POS)", "📦 Gudang", "📊 Laporan & Histori Bon"])
else:
    tab_pos, tab_laporan = st.tabs(["🛒 Etalase (POS)", "🧾 Cetak Struk"])
    tab_gudang = None

with tab_pos:
    st.markdown("### Proses Transaksi Kasir")
    col_produk, col_keranjang = st.columns([7, 3])
    
    with col_keranjang:
        st.markdown("#### 🛒 Keranjang")
        with st.container(border=True):
            pajak_persen = st.number_input("Pajak (%)", min_value=0, max_value=100, value=0, step=1)
            
            if len(st.session_state['keranjang']) == 0:
                st.info("Keranjang masih kosong.")
            else:
                total_belanja = 0
                total_pajak = 0
                
                for i, item in enumerate(st.session_state['keranjang']):
                    c_nama, c_hapus = st.columns([4, 1])
                    subtotal_item = item['qty'] * item['harga_jual']
                    pajak_item = subtotal_item * (pajak_persen / 100)
                    
                    c_nama.write(f"**{item['nama']}**\n{item['qty']} x Rp {item['harga_jual']:,.0f}")
                    if c_hapus.button("❌", key=f"del_{i}"):
                        st.session_state['keranjang'].pop(i)
                        st.rerun()
                        
                    total_belanja += subtotal_item
                    total_pajak += pajak_item
                    
                grand_total = total_belanja + total_pajak
                st.write("---")
                st.write(f"Subtotal: Rp {total_belanja:,.0f}")
                if total_pajak > 0:
                    st.write(f"Pajak: Rp {total_pajak:,.0f}")
                st.subheader(f"Total: Rp {grand_total:,.0f}")
                
                if st.button("💵 Bayar & Cetak Bon", type="primary", use_container_width=True):
                    # Injeksi Waktu WIB (UTC+7)
                    waktu_wib = datetime.utcnow() + timedelta(hours=7)
                    waktu_skrg = waktu_wib.strftime("%Y-%m-%d %H:%M")
                    tgl_db = waktu_wib.strftime("%Y-%m-%d")
                    id_struk_baru = f"INV-{waktu_wib.strftime('%Y%m%d%H%M%S')}"
                    kasir = st.session_state['role']
                    
                    struk_text = f"=================================\n      KOPERASI MERAH PUTIH\n=================================\nNo. Bon : {id_struk_baru}\nTanggal : {waktu_skrg}\nKasir   : {kasir}\n---------------------------------\n"
                    
                    with conn.session as session:
                        for item in st.session_state['keranjang']:
                            omzet = item['qty'] * item['harga_jual']
                            laba = omzet - (item['qty'] * item['harga_beli'])
                            pajak_item_db = omzet * (pajak_persen / 100)
                            
                            session.execute(text("UPDATE stok_barang SET stok = stok - :qty WHERE id_barang = :id"), 
                                            {"qty": item['qty'], "id": item['id_barang']})
                            
                            session.execute(text("INSERT INTO riwayat_transaksi (tanggal, nama_barang, qty, omzet, laba, kasir, no_struk, pajak) VALUES (:tgl, :nama, :qty, :omzet, :laba, :kasir, :struk, :pajak)"), 
                                            {"tgl": tgl_db, "nama": item['nama'], "qty": item['qty'], "omzet": omzet, "laba": laba, "kasir": kasir, "struk": id_struk_baru, "pajak": pajak_item_db})
                            
                            struk_text += f"{item['nama']}\n{item['qty']} x Rp {item['harga_jual']:,.0f} = Rp {omzet:,.0f}\n"
                        session.commit()
                        
                    struk_text += f"---------------------------------\nSubtotal: Rp {total_belanja:,.0f}\n"
                    if total_pajak > 0:
                        struk_text += f"Pajak   : Rp {total_pajak:,.0f}\n"
                    struk_text += f"TOTAL   : Rp {grand_total:,.0f}\n=================================\n Terima Kasih Atas Kunjungan Anda\n================================="
                    
                    st.session_state['struk_terakhir'] = struk_text
                    st.session_state['keranjang'] = [] 
                    st.success("Pembayaran Berhasil!")
                    st.rerun()

    with col_produk:
        cari_barang = st.text_input("🔍 Cari Barang di Etalase...", placeholder="Ketik nama barang...")
        
        df_barang = conn.query("SELECT * FROM stok_barang WHERE stok > 0", ttl=0)
        
        if cari_barang:
            df_barang = df_barang[df_barang['nama_barang'].str.contains(cari_barang, case=False, na=False)]
            
        if not df_barang.empty:
            cols = st.columns(3)
            for index, row in df_barang.iterrows():
                with cols[index % 3]:
                    with st.container(border=True):
                        st.subheader(row['nama_barang'])
                        st.write(f"**Harga:** Rp {row['harga_jual']:,.0f} | **Stok:** {row['stok']}")
                        with st.form(key=f"form_beli_{row['id_barang']}"):
                            qty = st.number_input("Jml Beli", min_value=1, max_value=int(row['stok']), step=1)
                            if st.form_submit_button("➕ Tambah", use_container_width=True):
                                idx_found = -1
                                for i, k in enumerate(st.session_state['keranjang']):
                                    if k['id_barang'] == row['id_barang']:
                                        idx_found = i
                                        break
                                if idx_found >= 0:
                                    if st.session_state['keranjang'][idx_found]['qty'] + qty > row['stok']:
                                        st.error("Gagal: Keranjang melebihi stok fisik!")
                                    else:
                                        st.session_state['keranjang'][idx_found]['qty'] += qty
                                        st.rerun()
                                else:
                                    st.session_state['keranjang'].append({'id_barang': row['id_barang'], 'nama': row['nama_barang'], 'harga_jual': row['harga_jual'], 'harga_beli': row['harga_beli'], 'qty': qty})
                                    st.rerun()
        else:
            st.warning("Barang tidak ditemukan atau stok kosong.")

if tab_gudang is not None:
    with tab_gudang:
        st.markdown("### ➕ Tambah Barang Baru")
        with st.form("form_tambah_barang"):
            c1, c2, c3 = st.columns(3)
            with c1: 
                nama = st.text_input("Nama Barang")
                kategori = st.selectbox("Kategori", ["Bahan Pokok", "Minuman", "Cemilan", "ATK"])
            with c2: 
                harga_beli = st.number_input("Harga Modal (Rp)", min_value=0)
                harga_jual = st.number_input("Harga Jual (Rp)", min_value=0)
            with c3:
                stok = st.number_input("Stok Awal", min_value=0)
                # Opsi penambahan waktu otomatis untuk kadaluwarsa bila diperlukan
                kedaluwarsa = st.date_input("Tanggal Kedaluwarsa", min_value=(datetime.utcnow() + timedelta(hours=7)).date())
            if st.form_submit_button("Simpan ke Database", type="primary") and nama:
                with conn.session as session:
                    session.execute(text("INSERT INTO stok_barang (nama_barang, kategori, harga_beli, harga_jual, stok, tanggal_kedaluwarsa) VALUES (:n, :k, :hb, :hj, :s, :t)"), 
                                    {"n": nama, "k": kategori, "hb": harga_beli, "hj": harga_jual, "s": stok, "t": str(kedaluwarsa)})
                    session.commit()
                st.success("Barang ditambahkan!")
                st.rerun()

        st.markdown("---")
        st.markdown("### ✏️ Edit atau Hapus Barang")
        
        df_all = conn.query("SELECT * FROM stok_barang", ttl=0)
        st.dataframe(df_all, use_container_width=True, hide_index=True)
        
        if not df_all.empty:
            opsi_barang = df_all.apply(lambda row: f"{row['id_barang']} - {row['nama_barang']}", axis=1).tolist()
            pilihan = st.selectbox("Pilih Barang yang akan diubah / dihapus:", opsi_barang)
            id_pilih = int(pilihan.split(" - ")[0])
            data_pilih = df_all[df_all['id_barang'] == id_pilih].iloc[0]
            
            with st.form("form_edit_hapus"):
                st.info(f"Mode Edit: **{data_pilih['nama_barang']}**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    e_nama = st.text_input("Nama Barang", value=data_pilih['nama_barang'])
                    kat_list = ["Bahan Pokok", "Minuman", "Cemilan", "ATK"]
                    idx_kat = kat_list.index(data_pilih['kategori']) if data_pilih['kategori'] in kat_list else 0
                    e_kat = st.selectbox("Kategori", kat_list, index=idx_kat)
                with c2:
                    e_beli = st.number_input("Harga Modal (Rp)", value=float(data_pilih['harga_beli']))
                    e_jual = st.number_input("Harga Jual (Rp)", value=float(data_pilih['harga_jual']))
                with c3:
                    e_stok = st.number_input("Stok", value=int(data_pilih['stok']))
                    e_tgl = st.text_input("Tanggal Kedaluwarsa", value=data_pilih['tanggal_kedaluwarsa'])
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Simpan Perubahan", type="primary"):
                        with conn.session as session:
                            session.execute(text("UPDATE stok_barang SET nama_barang=:n, kategori=:k, harga_beli=:hb, harga_jual=:hj, stok=:s, tanggal_kedaluwarsa=:t WHERE id_barang=:id"), 
                                            {"n": e_nama, "k": e_kat, "hb": e_beli, "hj": e_jual, "s": e_stok, "t": e_tgl, "id": id_pilih})
                            session.commit()
                        st.success("Data berhasil diubah!")
                        st.rerun()
                with col_btn2:
                    if st.form_submit_button("❌ Hapus Barang Permanen"):
                        with conn.session as session:
                            session.execute(text("DELETE FROM stok_barang WHERE id_barang=:id"), {"id": id_pilih})
                            session.commit()
                        st.error("Data berhasil dihapus!")
                        st.rerun()

with tab_laporan:
    if st.session_state['role'] == 'Admin':
        st.markdown("### 📊 Laporan Keuangan")
        
        df_trx = conn.query("SELECT * FROM riwayat_transaksi ORDER BY id_trx DESC", ttl=0)
        
        if not df_trx.empty:
            if 'pajak' not in df_trx.columns:
                df_trx['pajak'] = 0
            df_trx['pajak'] = df_trx['pajak'].fillna(0)
                
            df_trx['Bulan'] = df_trx['tanggal'].str[:7]
            daftar_bulan = ["Semua Waktu"] + df_trx['Bulan'].unique().tolist()
            
            pilih_bulan = st.selectbox("📅 Filter Berdasarkan Bulan:", daftar_bulan)
            
            if pilih_bulan != "Semua Waktu":
                df_filter = df_trx[df_trx['Bulan'] == pilih_bulan].copy()
            else:
                df_filter = df_trx.copy()
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Total Omzet", f"Rp {df_filter['omzet'].sum():,.0f}")
            c2.metric(f"Total Laba Kotor", f"Rp {df_filter['laba'].sum():,.0f}")
            c3.metric(f"Total Pajak Dipungut", f"Rp {df_filter['pajak'].sum():,.0f}")
            
            st.dataframe(df_filter.drop(columns=['Bulan']), use_container_width=True, hide_index=True)
            st.write("---")
            
            st.markdown("### 📜 Cetak Ulang Histori Bon")
            df_filter['no_struk'] = df_filter['no_struk'].fillna(df_filter['id_trx'].astype(str))
            
            unique_struk = df_filter[['no_struk', 'tanggal', 'kasir']].drop_duplicates()
            opsi_struk = []
            for _, row in unique_struk.iterrows():
                if str(row['no_struk']).startswith('INV-'):
                    opsi_struk.append(f"{row['no_struk']} | {row['tanggal']}")
                else:
                    opsi_struk.append(f"TRX-Lama-{row['no_struk']} | {row['tanggal']}")
            
            pilih_struk = st.selectbox("Pilih Nomor Bon untuk Dicetak Ulang:", opsi_struk)
            
            if pilih_struk:
                struk_id = pilih_struk.split(" | ")[0].replace("TRX-Lama-", "")
                items_struk = df_filter[df_filter['no_struk'] == struk_id]
                
                tgl_histori = items_struk.iloc[0]['tanggal']
                kasir_histori = items_struk.iloc[0]['kasir']
                
                teks_histori = f"=================================\n      KOPERASI MERAH PUTIH\n=================================\nNo. Bon : {struk_id}\nTanggal : {tgl_histori}\nKasir   : {kasir_histori}\n---------------------------------\n"
                total_histori = 0
                total_pajak_histori = 0
                
                for _, item in items_struk.iterrows():
                    harga_sat = item['omzet'] / item['qty'] if item['qty'] > 0 else 0
                    teks_histori += f"{item['nama_barang']}\n{item['qty']} x Rp {harga_sat:,.0f} = Rp {item['omzet']:,.0f}\n"
                    total_histori += item['omzet']
                    total_pajak_histori += item['pajak'] if pd.notna(item['pajak']) else 0
                    
                teks_histori += f"---------------------------------\nSubtotal: Rp {total_histori:,.0f}\n"
                if total_pajak_histori > 0:
                    teks_histori += f"Pajak   : Rp {total_pajak_histori:,.0f}\n"
                teks_histori += f"TOTAL   : Rp {(total_histori + total_pajak_histori):,.0f}\n=================================\n Terima Kasih Atas Kunjungan Anda\n================================="
                
                c3, c4 = st.columns([1, 2])
                with c3:
                    st.download_button(label="Cetak Bon Ini (TXT)", data=teks_histori, file_name=f"struk_{struk_id}.txt", mime="text/plain", type="primary")
                with c4:
                    st.code(teks_histori, language="text")
        else:
            st.info("Belum ada transaksi tercatat.")
    
    if st.session_state['role'] == 'Kasir' or 'struk_terakhir' in st.session_state:
        st.markdown("### 🖨️ Bon Transaksi Terakhir (Keranjang)")
        if 'struk_terakhir' in st.session_state:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.download_button(label="Cetak / Unduh Bon (TXT)", data=st.session_state['struk_terakhir'], file_name="struk_koperasi.txt", mime="text/plain", type="primary")
            with c2:
                st.code(st.session_state['struk_terakhir'], language="text")
        else:
            st.info("Belum ada transaksi baru untuk dicetak.")
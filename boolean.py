import streamlit as st
from sympy import symbols
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
import re
import pandas as pd

# Pengaturan halaman web Streamlit
st.set_page_config(page_title="Quine–McCluskey Solver", page_icon="🧮", layout="centered")

def bersihkan_ekspresi(teks):
    """Mengubah kata kunci umum ke standar operator SymPy dengan penyisipan AND (&) yang tegas"""
    teks = teks.upper().replace(" ", "")  # Hapus semua spasi
    
    # 1. Ubah kata kunci teks manual ke simbol jika ada
    teks = re.sub(r'\bAND\b', '&', teks)
    teks = re.sub(r'\bOR\b', '|', teks)
    teks = re.sub(r'\bNOT\b', '~', teks)
    
    # 2. Ubah format aksen A' menjadi ~A
    teks = re.sub(r"([A-Z])'", r"~\1", teks)
    
    # 3. Ubah tanda + tradisional menjadi | (OR)
    teks = teks.replace('+', '|')
    
    # 4. Sisipkan '&' secara tegas di antara dua huruf terpisah (Contoh: AB -> A&B)
    # Jalankan berulang kali untuk menangani variasi seperti ABC atau ~A~B~C
    for _ in range(3):
        teks = re.sub(r"([A-Z])([A-Z])", r"\1&\2", teks)
        teks = re.sub(r"([A-Z])(~[A-Z])", r"\1&\2", teks)
        teks = re.sub(r"([A-Z])\(", r"\1&(", teks)
        teks = re.sub(r"\)([A-Z])", r")&\1", teks)
        teks = re.sub(r"\)\(", r")&(", teks)
        
    return teks

def gabungkan_term(term1, term2):
    """Menggabungkan dua term biner jika hanya berbeda 1 bit"""
    perbedaan = 0
    posisi = -1
    for i in range(len(term1)):
        if term1[i] != term2[i]:
            perbedaan += 1
            posisi = i
    if perbedaan == 1:
        list_term = list(term1)
        list_term[posisi] = '-'
        return "".join(list_term)
    return None

def biner_ke_huruf(bin_str, nama_var):
    """Mengubah string biner seperti 0-01 menjadi ekspresi huruf seperti A'C'D"""
    ekspresi = []
    for i in range(len(bin_str)):
        if bin_str[i] == '1':
            ekspresi.append(nama_var[i])
        elif bin_str[i] == '0':
            ekspresi.append(f"{nama_var[i]}'")
    return "".join(ekspresi) if ekspresi else "1"

def proses_quine_mccluskey(jml_var, list_minterm, nama_var):
    """Algoritma utama Quine-McCluskey untuk mencari Prime Implicant"""
    term_saat_ini = {}
    for m in list_minterm:
        bin_str = format(m, f'0{jml_var}b')
        term_saat_ini[bin_str] = False

    all_prime_implicants = set()

    while True:
        terjadi_penggabungan = False
        term_baru = {}
        list_keys = list(term_saat_ini.keys())
        
        for i in range(len(list_keys)):
            for j in range(i + 1, len(list_keys)):
                t1, t2 = list_keys[i], list_keys[j]
                if all(t1[k] == '-' for k in range(jml_var) if t2[k] == '-'):
                    hasil_gabung = gabungkan_term(t1, t2)
                    if hasil_gabung:
                        term_saat_ini[t1] = True
                        term_saat_ini[t2] = True
                        term_baru[hasil_gabung] = False
                        terjadi_penggabungan = True
        
        for k, v in term_saat_ini.items():
            if not v:
                all_prime_implicants.add(k)
                
        if not terjadi_penggabungan:
            break
        term_saat_ini = term_baru

    sorted_primes = sorted(list(all_prime_implicants))
    detail_prime = []
    list_ekspresi_huruf = []
    for p in sorted_primes:
        huruf = biner_ke_huruf(p, nama_var)
        detail_prime.append(f"{p}  →  {huruf}")
        list_ekspresi_huruf.append(huruf)
        
    ekspresi_final = " + ".join(list_ekspresi_huruf)
    return detail_prime, ekspresi_final

def buat_tabel_kebenaran(simbol, minterms=None, ekspresi=None):
    """Men-generate tabel kebenaran interaktif"""
    nama_kolom = [str(s) for s in simbol] + ["Output (Y)"]
    baris_tabel = []
    jml_var = len(simbol)
    total_baris = 2 ** jml_var
    list_minterm_terdeteksi = []
    
    for i in range(total_baris):
        kombinasi_biner = [int(x) for x in format(i, f'0{jml_var}b')]
        
        if minterms is not None:
            output_val = 1 if i in minterms else 0
            baris_tabel.append(kombinasi_biner + [output_val])
        else:
            peta_nilai = dict(zip(simbol, [bool(b) for b in kombinasi_biner]))
            evaluasi = ekspresi.subs(peta_nilai)
            output_val = 1 if bool(evaluasi) else 0
            baris_tabel.append(kombinasi_biner + [output_val])
            if output_val == 1:
                list_minterm_terdeteksi.append(i)
                
    return pd.DataFrame(baris_tabel, columns=nama_kolom), list_minterm_terdeteksi


# --- TAMPILAN UTAMA APLIKASI WEB ---
st.title("🧮 Quine–McCluskey Solver")
st.write("Penyederhanaan Fungsi Boolean")
st.markdown("---")

st.sidebar.header("Menu Navigasi")
mode = st.sidebar.radio("Pilih Metode Input:", ("Input Angka (Minterm)", "Input Huruf (Ekspresi)"))

# ==================== MODE 1: INPUT ANGKA / MINTERM ====================
if mode == "Input Angka (Minterm)":
    minterm_input = st.text_input("Masukkan angka minterm (pisahkan dengan koma):", value="0,1,2,5,6,7,8,9,10,14")
    
    if st.button("Sederhanakan"):
        if minterm_input:
            try:
                list_minterm = sorted(list(set([int(x.strip()) for x in minterm_input.split(",") if x.strip().isdigit()])))
                if not list_minterm:
                    st.error("Format salah! Gunakan angka dipisahkan koma.")
                else:
                    angka_terbesar = max(list_minterm)
                    jml_var = 2 if angka_terbesar < 4 else (3 if angka_terbesar < 8 else (4 if angka_terbesar < 16 else 5))
                    
                    nama_var = [chr(65 + i) for i in range(jml_var)]
                    list_prime, ekspresi_final = proses_quine_mccluskey(jml_var, list_minterm, nama_var)
                    
                    st.subheader("HASIL PENYEDERHANAAN")
                    st.text("======================================")
                    st.write("**Prime Implicant:**")
                    for prime in list_prime:
                        st.code(prime, language="text")
                    st.write("**Ekspresi Boolean:**")
                    st.code(ekspresi_final, language="text")
                    
                    st.markdown("---")
                    st.subheader("📋 Tabel Kebenaran (Truth Table)")
                    df_tabel, _ = buat_tabel_kebenaran([symbols(x) for x in nama_var], minterms=list_minterm)
                    st.dataframe(df_tabel, width='stretch')
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

# ==================== MODE 2: INPUT HURUF / EKSPRESI ====================
else:
    st.header("🔤 Input Huruf / Ekspresi Logika")
    st.write("Format didukung: `AB + A'`, `A(B + C) + A'`, atau `(A AND B) OR NOT C`")
    input_user = st.text_input("Masukkan ekspresi logika Anda:", value="AB + A'")
    
    if st.button("Sederhanakan Ekspresi"):
        if input_user:
            try:
                # 1. Bersihkan string input dasar secara ketat
                ekspresi_clean = bersihkan_ekspresi(input_user)
                
                # 2. Ambil semua huruf variabel tunggal secara alfabetis (A-Z)
                nama_var_terdeteksi = sorted(list(set(re.findall(r'[A-Z]', ekspresi_clean))))
                simbol_terdeteksi = [symbols(v) for v in nama_var_terdeteksi]
                jml_var = len(simbol_terdeteksi)
                
                if jml_var == 0:
                    st.error("Tidak ada variabel huruf (A-Z) yang terdeteksi!")
                else:
                    # 3. Parsing langsung ekspresi yang sudah diberi tanda & eksplisit (A&B | ~A)
                    ekspresi = parse_expr(ekspresi_clean, local_dict={v: symbols(v) for v in nama_var_terdeteksi})
                    
                    # 4. Ambil list minterm dan dataframe tabel kebenaran
                    df_tabel, list_minterm = buat_tabel_kebenaran(simbol_terdeteksi, ekspresi=ekspresi)
                    
                    # 5. Hitung dengan algoritma Quine-McCluskey
                    list_prime, ekspresi_final = proses_quine_mccluskey(jml_var, list_minterm, nama_var_terdeteksi)
                    
                    st.subheader("HASIL PENYEDERHANAAN")
                    st.text("======================================")
                    st.write("**Prime Implicant:**")
                    for prime in list_prime:
                        st.code(prime, language="text")
                    st.write("**Ekspresi Boolean:**")
                    st.code(ekspresi_final, language="text")
                    
                    st.markdown("---")
                    st.subheader("📋 Tabel Kebenaran (Truth Table)")
                    st.dataframe(df_tabel, width='stretch')
                    
            except Exception as e:
                st.error(f"Format rumus tidak valid. Detail: {e}")
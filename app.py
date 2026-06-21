import streamlit as st
import pandas as pd
import re
from sympy import symbols, SOPform
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from itertools import combinations

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="Quine-McCluskey Solver",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Kustom
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4A90E2;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4A90E2;
        margin: 1rem 0;
    }
    .prime-box {
        background-color: #e8f4fd;
        padding: 0.8rem;
        border-radius: 5px;
        font-family: monospace;
        margin: 0.3rem 0;
    }
    .essential-box {
        background-color: #d4edda;
        padding: 0.8rem;
        border-radius: 5px;
        font-family: monospace;
        margin: 0.3rem 0;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FUNGSI UTILITAS ====================
def bersihkan_ekspresi(teks):
    """Mengubah kata kunci dan notasi ke operator SymPy, sisipkan & untuk AND implisit"""
    teks = teks.upper().replace(" ", "")
    # Ganti kata kunci
    teks = re.sub(r'\bAND\b', '&', teks)
    teks = re.sub(r'\bOR\b', '|', teks)
    teks = re.sub(r'\bNOT\b', '~', teks)
    teks = re.sub(r"([A-Z])'", r"~\1", teks)
    teks = teks.replace('+', '|')
    # Sisipkan & secara eksplisit di antara huruf dan kurung
    for _ in range(5):
        teks = re.sub(r'([A-Z])([A-Z])', r'\1&\2', teks)
        teks = re.sub(r'([A-Z])(\()', r'\1&(', teks)
        teks = re.sub(r'(\))([A-Z])', r')&\2', teks)
        teks = re.sub(r'(\))(\()', r')&(', teks)
    return teks

def bin_to_letters(bin_str, var_names):
    if all(b == '-' for b in bin_str):
        return "1"
    parts = []
    for i, ch in enumerate(bin_str):
        if ch == '1':
            parts.append(var_names[i])
        elif ch == '0':
            parts.append(f"{var_names[i]}'")
    return "".join(parts)

def count_ones(s):
    return s.count('1')

def combine_terms(t1, t2):
    diff = 0
    pos = -1
    for i, (a, b) in enumerate(zip(t1, t2)):
        if a != b:
            diff += 1
            pos = i
            if diff > 1:
                return None
    if diff == 1:
        return t1[:pos] + '-' + t1[pos+1:]
    return None

def covers(term, minterm):
    for t, m in zip(term, minterm):
        if t != '-' and t != m:
            return False
    return True

# ==================== ALGORITMA QM LENGKAP ====================
def quine_mccluskey(minterms, num_vars, var_names=None):
    if var_names is None:
        var_names = [chr(65+i) for i in range(num_vars)]

    terms = {format(m, f'0{num_vars}b'): [m] for m in minterms}
    steps = []
    step_num = 0

    while True:
        groups = {}
        for t in terms:
            ones = count_ones(t)
            groups.setdefault(ones, []).append(t)
        sorted_groups = sorted(groups.items())

        new_terms = {}
        used = set()
        combinations_found = []

        for i in range(len(sorted_groups)-1):
            group1 = sorted_groups[i][1]
            group2 = sorted_groups[i+1][1]
            for t1 in group1:
                for t2 in group2:
                    combined = combine_terms(t1, t2)
                    if combined:
                        used.add(t1)
                        used.add(t2)
                        new_terms[combined] = new_terms.get(combined, []) + terms[t1] + terms[t2]
                        combinations_found.append((t1, t2, combined))

        unused = [t for t in terms if t not in used]

        step_data = {
            'step': step_num,
            'groups': groups,
            'combinations': combinations_found,
            'unused': unused,
            'new_terms': new_terms
        }
        steps.append(step_data)

        if not new_terms:
            break
        terms = new_terms
        step_num += 1

    # Kumpulkan semua unused dari setiap tahap sebagai prime implicants
    all_unused = set()
    for step in steps:
        all_unused.update(step['unused'])
    prime_implicants = list(dict.fromkeys(all_unused))

    # Tabel PI chart
    all_minterms = sorted(set(minterms))
    prime_minterms = {}
    for p in prime_implicants:
        covered = [m for m in all_minterms if covers(p, format(m, f'0{num_vars}b'))]
        prime_minterms[p] = covered

    chart_data = []
    for m in all_minterms:
        row = {'Minterm': m}
        for p in prime_implicants:
            row[p] = 'X' if m in prime_minterms[p] else ''
        chart_data.append(row)
    chart_df = pd.DataFrame(chart_data)

    # Essential prime implicants
    essential = []
    for m in all_minterms:
        covering = [p for p in prime_implicants if m in prime_minterms[p]]
        if len(covering) == 1:
            essential.append(covering[0])
    essential = list(dict.fromkeys(essential))

    # Petrick's method (sederhana)
    non_essential = [p for p in prime_implicants if p not in essential]
    covered_by_essential = set()
    for p in essential:
        covered_by_essential.update(prime_minterms[p])
    uncovered = set(all_minterms) - covered_by_essential

    selected = []
    if uncovered:
        prime_coverage = {}
        for p in non_essential:
            covered_uncovered = set(prime_minterms[p]) & uncovered
            if covered_uncovered:
                prime_coverage[p] = covered_uncovered
        prime_list = list(prime_coverage.keys())
        if len(prime_list) <= 15:
            best = None
            best_cost = float('inf')
            for r in range(1, len(prime_list)+1):
                for combo in combinations(prime_list, r):
                    union = set()
                    for p in combo:
                        union.update(prime_coverage[p])
                    if union >= uncovered:
                        cost = sum(p.count('0') + p.count('1') for p in combo)
                        if cost < best_cost:
                            best_cost = cost
                            best = combo
            if best:
                selected = list(best)
        else:
            remaining = set(uncovered)
            while remaining:
                best_p = None
                best_count = -1
                for p in prime_list:
                    if p in selected:
                        continue
                    cnt = len(prime_coverage[p] & remaining)
                    if cnt > best_count:
                        best_count = cnt
                        best_p = p
                if best_p:
                    selected.append(best_p)
                    remaining -= prime_coverage[best_p]
                else:
                    break

    final_primes = essential + selected
    expr_parts = [bin_to_letters(p, var_names) for p in final_primes]
    minimal_expression = " + ".join(expr_parts)

    return {
        'steps': steps,
        'prime_implicants': prime_implicants,
        'essential': essential,
        'chart_df': chart_df,
        'minimal_expression': minimal_expression,
        'final_primes': final_primes,
        'all_minterms': all_minterms,
        'prime_minterms': prime_minterms
    }

# ==================== FUNGSI TABEL KEBENARAN ====================
def truth_table_from_minterms(minterms, num_vars, var_names):
    rows = []
    for i in range(2**num_vars):
        bits = [int(b) for b in format(i, f'0{num_vars}b')]
        output = 1 if i in minterms else 0
        rows.append(bits + [output])
    columns = var_names + ['Output']
    return pd.DataFrame(rows, columns=columns)

def truth_table_from_expression(expr_str):
    """Parse ekspresi boolean dan kembalikan df, minterms, var_names"""
    clean = bersihkan_ekspresi(expr_str)
    vars_found = sorted(set(re.findall(r'[A-Z]', clean)))
    if not vars_found:
        return None, [], []
    symbols_dict = {v: symbols(v) for v in vars_found}
    try:
        expr = parse_expr(clean, transformations=standard_transformations, local_dict=symbols_dict)
    except Exception as e:
        raise ValueError(f"Gagal parsing ekspresi: {e}")

    num_vars = len(vars_found)
    rows = []
    minterms = []
    for i in range(2**num_vars):
        bits = [int(b) for b in format(i, f'0{num_vars}b')]
        vals = {vars_found[j]: bool(bits[j]) for j in range(num_vars)}
        try:
            # Gunakan subs dengan nilai Boolean dan konversi ke bool
            result = bool(expr.subs(vals))
        except Exception:
            result = False
        out = 1 if result else 0
        rows.append(bits + [out])
        if out == 1:
            minterms.append(i)
    columns = vars_found + ['Output']
    return pd.DataFrame(rows, columns=columns), minterms, vars_found

# ==================== TAMPILAN UTAMA ====================
def main():
    st.markdown('<div class="main-header">🧮 Quine–McCluskey Solver</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Penyederhanaan Fungsi Boolean dengan Visualisasi Lengkap</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Pengaturan")
        mode = st.radio("Pilih Metode Input:", ("🔢 Minterm (Angka)", "🔤 Ekspresi Boolean"))
        st.markdown("---")
        st.info("Aplikasi ini menampilkan setiap langkah algoritma Quine-McCluskey, termasuk pengelompokan, penggabungan, dan penentuan prime implicant esensial.")
        st.caption("Dibuat dengan Streamlit & SymPy")

    if mode == "🔢 Minterm (Angka)":
        st.header("📥 Input Minterm")
        col1, col2 = st.columns([3, 1])
        with col1:
            minterm_input = st.text_input(
                "Masukkan angka minterm (pisahkan dengan koma):",
                value="0,1,2,5,6,7,8,9,10,14",
                help="Contoh: 0,2,3,5"
            )
        with col2:
            num_vars = st.number_input("Jumlah variabel", min_value=1, max_value=8, value=4, step=1)

        if st.button("🚀 Sederhanakan", type="primary"):
            if not minterm_input.strip():
                st.warning("Silakan masukkan minterm.")
                return

            try:
                minterms = sorted(set([int(x.strip()) for x in minterm_input.split(",") if x.strip().isdigit()]))
                if not minterms:
                    st.error("Format tidak valid. Gunakan angka dipisahkan koma.")
                    return
                max_val = 2**num_vars - 1
                if any(m > max_val for m in minterms):
                    st.error(f"Untuk {num_vars} variabel, minterm maksimum adalah {max_val}.")
                    return

                var_names = [chr(65+i) for i in range(num_vars)]

                with st.spinner("Menjalankan algoritma Quine-McCluskey..."):
                    result = quine_mccluskey(minterms, num_vars, var_names)

                tab1, tab2, tab3, tab4 = st.tabs(["📊 Hasil Akhir", "📝 Langkah-langkah", "📋 Tabel Kebenaran", "📈 Prime Implicant Chart"])

                with tab1:
                    st.success("Penyederhanaan selesai!")
                    st.markdown('<div class="result-box">', unsafe_allow_html=True)
                    st.subheader("🎯 Ekspresi Boolean Minimal (SOP)")
                    st.code(result['minimal_expression'], language="text")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.subheader("🔹 Prime Implicants")
                    for p in result['prime_implicants']:
                        if p in result['essential']:
                            st.markdown(f'<div class="essential-box">✅ {p}  →  {bin_to_letters(p, var_names)}  (Esensial)</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="prime-box">⬜ {p}  →  {bin_to_letters(p, var_names)}</div>', unsafe_allow_html=True)

                    st.subheader("📌 Prime Implicants Esensial")
                    if result['essential']:
                        ess_str = " + ".join([bin_to_letters(p, var_names) for p in result['essential']])
                        st.code(ess_str, language="text")
                    else:
                        st.write("Tidak ada prime implicant esensial.")

                    hasil_text = f"Ekspresi minimal: {result['minimal_expression']}\n\nPrime Implicants:\n"
                    for p in result['prime_implicants']:
                        label = " (Esensial)" if p in result['essential'] else ""
                        hasil_text += f"{p} → {bin_to_letters(p, var_names)}{label}\n"
                    st.download_button("💾 Unduh Hasil (TXT)", hasil_text, file_name="hasil_qm.txt")

                with tab2:
                    st.subheader("📖 Proses Quine-McCluskey")
                    for step in result['steps']:
                        with st.expander(f"Langkah {step['step']+1}", expanded=(step['step']==0)):
                            st.markdown(f"**Pengelompokan berdasarkan jumlah '1':**")
                            for ones, terms in sorted(step['groups'].items()):
                                st.write(f"Jumlah 1 = {ones}:  {', '.join(terms)}")
                            if step['combinations']:
                                st.markdown("**Penggabungan yang terjadi:**")
                                for t1, t2, combined in step['combinations']:
                                    st.write(f"{t1} + {t2} → {combined}")
                            else:
                                st.write("Tidak ada penggabungan pada langkah ini.")
                            if step['unused']:
                                st.markdown("**Prime Implicants sementara (tidak tergabung):**")
                                st.write(", ".join(step['unused']))

                with tab3:
                    st.subheader("📋 Tabel Kebenaran")
                    df_truth = truth_table_from_minterms(minterms, num_vars, var_names)
                    st.dataframe(df_truth, use_container_width=True)

                with tab4:
                    st.subheader("📈 Prime Implicant Chart")
                    st.dataframe(result['chart_df'], use_container_width=True)
                    st.caption("Tanda 'X' menunjukkan prime implicant mencakup minterm tersebut.")

            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

    else:  # mode ekspresi
        st.header("🔤 Input Ekspresi Boolean")
        st.write("Format yang didukung: `AB + A'`, `(A AND B) OR NOT C`, `A(B+C)`")
        expr_input = st.text_input("Masukkan ekspresi logika:", value="AB + A'")
        if st.button("🚀 Sederhanakan Ekspresi", type="primary"):
            if not expr_input.strip():
                st.warning("Silakan masukkan ekspresi.")
                return
            try:
                df_truth, minterms, var_names = truth_table_from_expression(expr_input)
                if df_truth is None:
                    st.error("Tidak ditemukan variabel.")
                    return
                num_vars = len(var_names)
                if not minterms:
                    st.warning("Ekspresi selalu FALSE (tidak ada minterm).")
                    st.dataframe(df_truth, use_container_width=True)
                    return

                with st.spinner("Menjalankan algoritma Quine-McCluskey..."):
                    result = quine_mccluskey(minterms, num_vars, var_names)

                tab1, tab2, tab3, tab4 = st.tabs(["📊 Hasil Akhir", "📝 Langkah-langkah", "📋 Tabel Kebenaran", "📈 Prime Implicant Chart"])

                with tab1:
                    st.success("Penyederhanaan selesai!")
                    st.markdown('<div class="result-box">', unsafe_allow_html=True)
                    st.subheader("🎯 Ekspresi Boolean Minimal (SOP)")
                    st.code(result['minimal_expression'], language="text")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.subheader("🔹 Prime Implicants")
                    for p in result['prime_implicants']:
                        if p in result['essential']:
                            st.markdown(f'<div class="essential-box">✅ {p}  →  {bin_to_letters(p, var_names)}  (Esensial)</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="prime-box">⬜ {p}  →  {bin_to_letters(p, var_names)}</div>', unsafe_allow_html=True)

                    st.subheader("📌 Prime Implicants Esensial")
                    if result['essential']:
                        ess_str = " + ".join([bin_to_letters(p, var_names) for p in result['essential']])
                        st.code(ess_str, language="text")
                    else:
                        st.write("Tidak ada prime implicant esensial.")

                    hasil_text = f"Ekspresi minimal: {result['minimal_expression']}\n\nPrime Implicants:\n"
                    for p in result['prime_implicants']:
                        label = " (Esensial)" if p in result['essential'] else ""
                        hasil_text += f"{p} → {bin_to_letters(p, var_names)}{label}\n"
                    st.download_button("💾 Unduh Hasil (TXT)", hasil_text, file_name="hasil_qm.txt")

                with tab2:
                    st.subheader("📖 Proses Quine-McCluskey")
                    for step in result['steps']:
                        with st.expander(f"Langkah {step['step']+1}", expanded=(step['step']==0)):
                            st.markdown(f"**Pengelompokan berdasarkan jumlah '1':**")
                            for ones, terms in sorted(step['groups'].items()):
                                st.write(f"Jumlah 1 = {ones}:  {', '.join(terms)}")
                            if step['combinations']:
                                st.markdown("**Penggabungan yang terjadi:**")
                                for t1, t2, combined in step['combinations']:
                                    st.write(f"{t1} + {t2} → {combined}")
                            else:
                                st.write("Tidak ada penggabungan pada langkah ini.")
                            if step['unused']:
                                st.markdown("**Prime Implicants sementara:**")
                                st.write(", ".join(step['unused']))

                with tab3:
                    st.subheader("📋 Tabel Kebenaran")
                    st.dataframe(df_truth, use_container_width=True)

                with tab4:
                    st.subheader("📈 Prime Implicant Chart")
                    st.dataframe(result['chart_df'], use_container_width=True)
                    st.caption("Tanda 'X' menunjukkan prime implicant mencakup minterm tersebut.")

            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()
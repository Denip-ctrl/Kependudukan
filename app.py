import glob
import os
import re
import pandas as pd
import plotly.express as px
import streamlit as st

import streamlit as st

# 1. Konfigurasi Halaman Wajib di Paling Atas
st.set_page_config(
    page_title="Dashboard Kependudukan - Prospek Indonesia",
    layout="wide"
)

# ==============================================================================
# CSS KUSTOM: KETERANGAN & TOMBOL KEMBALI KE BLOG "PROSPEK INDONESIA"
# ==============================================================================
st.markdown("""
    <style>
    /* Styling Banner Navigasi Kembali */
    .blog-nav-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .blog-nav-text {
        color: #f8fafc;
        font-size: 14px;
        margin: 0;
        line-height: 1.5;
    }
    .blog-nav-text strong {
        color: #38bdf8;
        font-size: 16px;
    }
    .blog-nav-button {
        background-color: #2563eb;
        color: #ffffff !important;
        padding: 10px 20px;
        text-decoration: none !important;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: all 0.3s ease;
        border: none;
    }
    .blog-nav-button:hover {
        background-color: #1d4ed8;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# Render Komponen Navigasi Kembali ke Blog
st.markdown("""
    <div class="blog-nav-container">
        <div class="blog-nav-text">
            💡 <strong>Bagian dari Analisis Ekonomi & Prospek Indonesia</strong><br>
            Untuk membaca artikel lengkap, ulasan metodologi, dan grafik analisis lainnya, silakan kembali ke blog.
        </div>
        <a href="https://www.denip.my.id" target="blank" class="blog-nav-button">
            ⬅️ Kembali ke Blog Prospek Indonesia
        </a>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# KODE APLIKASI UTAMA ANDA DI BAWAH INI
# ==============================================================================
# st.title("Dashboard Data Kependudukan Indonesia")
# df = load_data() ...

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Dashboard Data Kependudukan", page_icon="📊", layout="wide"
)


# Function untuk membaca, membersihkan, dan menggabungkan data
@st.cache_data
def load_and_combine_data(data_folder="data"):
  files = sorted(
      glob.glob(os.path.join(data_folder, "*.csv"))
      + glob.glob(os.path.join(data_folder, "*.parquet"))
  )

  if not files:
    return None

  list_df = []

  for file_path in files:
    file_name = os.path.basename(file_path)

    # 1. BACA FILE
    if file_path.endswith(".csv"):
      try:
        df = pd.read_csv(file_path)
        if len(df.columns) <= 1:
          df = pd.read_csv(file_path, sep=";")
      except Exception:
        df = pd.read_csv(file_path, sep=";")
    elif file_path.endswith(".parquet"):
      df = pd.read_parquet(file_path)
    else:
      continue

    # Clean nama kolom
    df.columns = df.columns.str.strip()

    # Cari kolom Provinsi
    prov_col = None
    for col in ["Provinsi", "Provinsi/Kabupaten", "Wilayah", "Province"]:
      if col in df.columns:
        prov_col = col
        break

    if not prov_col:
      continue

    # Clean isi kolom provinsi
    df[prov_col] = df[prov_col].astype(str).str.strip()

    # 2. POTONG BARIS "Indonesia" DAN SESUDAHNYA
    idx_indonesia = df[
        df[prov_col].str.contains(r"^indonesia$", case=False, na=False)
    ].index

    if not idx_indonesia.empty:
      first_idx = idx_indonesia[0]
      df = df.iloc[:first_idx].copy()

    # 3. KELOLA KOLOM TAHUN
    if "Tahun" not in df.columns:
      match = re.search(r"\b(19|20)\d{2}\b", file_name)
      if match:
        df["Tahun"] = int(match.group(0))
      else:
        continue

    df = df.rename(columns={prov_col: "Provinsi"})

    # 4. KONVERSI DAN NORMALISASI SKALA ANGKA
    for col in df.columns:
      if col not in ["Provinsi", "Tahun"]:
        # Konversi ke string & hapus spasi
        s = df[col].astype(str).str.strip()

        # Jika format angka menggunakan koma sebagai desimal (misal 1,4 atau 106,0)
        # Ganti koma dengan titik
        s = s.str.replace(",", ".", regex=False)

        # Ubah ke numerik
        numeric_s = pd.to_numeric(s, errors="coerce")

        # LOGIKA NORMALISASI SKALA BPS:
        col_lower = col.lower()

        # A. Laju Pertumbuhan / Persentase Penduduk (misal: 140 -> 1.4, 160 -> 16.0)
        if "pertumbuhan" in col_lower or "persentase" in col_lower or "%" in col:
          # Jika rata-rata nilainya di atas 10, kemungkinan besar skala terkalikan 100
          if numeric_s.dropna().mean() > 10:
            numeric_s = numeric_s / 100.0

        # B. Rasio Jenis Kelamin (misal: 1060 -> 106.0)
        elif "rasio" in col_lower or "kelamin" in col_lower:
          # Jika nilainya di atas 500, terkalikan 10
          if numeric_s.dropna().mean() > 500:
            numeric_s = numeric_s / 10.0

        df[col] = numeric_s

    list_df.append(df)

  if list_df:
    master_df = pd.concat(list_df, ignore_index=True)
    master_df["Tahun"] = pd.to_numeric(master_df["Tahun"], errors="coerce")
    master_df = master_df.sort_values(by="Tahun")
    return master_df

  return None

# --- APLIKASI UTAMA ---
st.title("📊 Dashboard Tren Kependudukan Antar Tahun")

df_all = load_and_combine_data("data")

if df_all is None or df_all.empty:
  st.error(
      " 📁 Data tidak ditemukan atau format tidak sesuai! Pastikan file"
      " `.csv` / `.parquet` berada di folder `data/`."
  )
else:
  # Sidebar Controls
  st.sidebar.header("⚙️ Pengaturan Grafik")

  # 1. Pilih Indikator (Sumbu Y)
  numeric_cols = [
      col
      for col in df_all.select_dtypes(include=["number"]).columns
      if col != "Tahun"
  ]

  if not numeric_cols:
    st.error("Tidak ditemukan kolom angka untuk ditampilkan pada grafik.")
  else:
    selected_metric = st.sidebar.selectbox(
        "Pilih Indikator (Sumbu Y):", options=numeric_cols, index=0
    )

    # 2. Filter Provinsi
    st.sidebar.subheader("Filter Provinsi")
    list_provinsi = sorted(df_all["Provinsi"].unique())

    mode_prov = st.sidebar.radio(
        "Tampilkan Provinsi:",
        options=["Semua Provinsi", "Pilih Spesifik (Maks. 5)"],
    )

    if mode_prov == "Pilih Spesifik (Maks. 5)":
      selected_prov = st.sidebar.multiselect(
          "Pilih maksimal 5 Provinsi:",
          options=list_provinsi,
          default=list_provinsi[:3] if len(list_provinsi) >= 3 else list_provinsi,
          max_selections=5,
      )
      df_filtered = df_all[df_all["Provinsi"].isin(selected_prov)]
    else:
      df_filtered = df_all.copy()

    # Tampilkan Grafik
    st.subheader(f"📈 Grafik Tren {selected_metric} per Provinsi")

    if df_filtered.empty:
      st.warning("Silakan pilih setidaknya 1 provinsi.")
    else:
      fig = px.line(
          df_filtered,
          x="Tahun",
          y=selected_metric,
          color="Provinsi",
          markers=True,
          # labels={"Tahun": "Tahun", selected_metric: selected_metric},
      )

      fig.update_layout(
          xaxis=dict(type="category"),
          hovermode="x unified",
          legend=dict(
              orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
          ),
          # Catatan / Sumber Data di sudut kiri bawah
            annotations=[
                dict(
                    text="Sumber Data: Badan Pusat Statistik (BPS) Indonesia, diolah kembali.<br>Source: BPS (diakses pada 2026).",
                    xref="paper",
                    yref="paper",
                    x=0,          # Posisi rata kiri
                    y=-0.22,      # Posisi di bawah sumbu X (kiri bawah)
                    showarrow=False,
                    font=dict(size=10, color="gray"),
                    align="left"
                )
            ],
            # Menambah margin bawah agar teks sumber data tidak terpotong
            margin=dict(b=90)
      )

      st.plotly_chart(fig, use_container_width=True)

    # Tabel Data
    with st.expander("👀 Lihat Data Mentah Terfilter"):
      st.dataframe(df_filtered, use_container_width=True)

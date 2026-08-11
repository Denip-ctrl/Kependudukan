import glob
import os
import re
import pandas as pd
import plotly.express as px
import streamlit as st

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

    # 1. BACA FILE (Mendukung pemisah koma maupun titik koma)
    if file_path.endswith(".csv"):
      try:
        df = pd.read_csv(file_path)
        # Jika kolom cuma 1, kemungkinan delimiter-nya titik koma (;)
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

    # 4. KONVERSI SEMUA KOLOM LAIN MENJADI ANGKA (NUMERIC)
    for col in df.columns:
      if col not in ["Provinsi", "Tahun"]:
        # Ubah ke string dulu
        s = df[col].astype(str).str.strip()

        # Hilangkan pemisah ribuan (titik) dan ubah koma desimal menjadi titik
        # Contoh: "1.234,56" -> "1234.56"
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)

        # Ubah teks non-angka (seperti "-", "N/A", "...") menjadi NaN lalu ubah ke float
        df[col] = pd.to_numeric(s, errors="coerce")

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
          title=f"Tren {selected_metric} per Provinsi",
          labels={"Tahun": "Tahun", selected_metric: },
      )

      fig.update_layout(
          xaxis=dict(type="category"),
          hovermode="x unified",
          legend=dict(
              orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
          ),
      )

      st.plotly_chart(fig, use_container_width=True)

    # Tabel Data
    with st.expander("👀 Lihat Data Mentah Terfilter"):
      st.dataframe(df_filtered, use_container_width=True)

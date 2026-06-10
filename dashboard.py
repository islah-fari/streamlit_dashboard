import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN UTAMA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="NafasJakarta - Dashboard ISPU 2022",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kustomisasi Tema dan Desain Kartu KPI menggunakan CSS (Aksesibilitas & Kontras Tinggi)
st.markdown("""
    <style>
    /* Styling Kartu KPI */
    .kpi-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 180px;
    }
    .kpi-title {
        font-size: 13px;
        font-weight: 800;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 40px;
        font-weight: 800;
        color: #0f172a;
        margin: 10px 0;
    }
    .kpi-badge {
        display: inline-block;
        padding: 6px 12px;
        font-size: 11px;
        font-weight: 800;
        border-radius: 30px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        width: fit-content;
    }
    /* Styling Kartu Rekomendasi Kesehatan */
    .reco-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
        color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .reco-header {
        font-size: 11px;
        font-weight: 800;
        color: #c7d2fe;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .reco-title {
        font-size: 18px;
        font-weight: 700;
        margin-top: 4px;
        color: #ffffff;
    }
    .reco-text {
        font-size: 13.5px;
        line-height: 1.6;
        color: #e0e7ff;
        margin-top: 10px;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ETL & PENYIAPAN DATASET (Membaca file CSV lokal)
# ==============================================================================
@st.cache_data
def load_data():
    file_path = "ISPU 2022.xlsx"
    try:
        # Menangani nilai kosong, tanda strip, atau tanda tanya
        df = pd.read_excel(file_path, na_values=['', ' ', '-', '?'])
    except FileNotFoundError:
        st.error(f"Berkas '{file_path}' tidak ditemukan. Pastikan berkas tersebut berada di folder yang sama dengan aplikasi.")
        st.stop()
        
    # Pembersihan format & tipe data tanggal
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    
    # Standarisasi kolom polutan ke format numerik float/integer
    kolom_polutan = ['pm_10', 'pm_duakomalima', 'so2', 'co', 'o3', 'no2', 'max']
    for kol in kolom_polutan:
        df[kol] = pd.to_numeric(df[kol], errors='coerce')
        
    # Mengisi nilai kosong dengan median per stasiun agar perhitungan tetap akurat
    for kol in kolom_polutan:
        df[kol] = df.groupby('lokasi_spku')[kol].transform(lambda x: x.fillna(x.median()))
        
    # Standarisasi teks kategori polusi udara
    df['categori'] = df['categori'].str.strip().str.upper()
    
    # Map koordinat geografis stasiun SPKU di Jakarta untuk visualisasi spasial (Peta)
    spku_coor = {
        'DKI1': {'lat': -6.1950, 'lon': 106.8228, 'nama_panjang': 'DKI1 - Bundaran HI (Jakarta Pusat)'},
        'DKI2': {'lat': -6.1553, 'lon': 106.9015, 'nama_panjang': 'DKI2 - Kelapa Gading (Jakarta Utara)'},
        'DKI3': {'lat': -6.3421, 'lon': 106.8229, 'nama_panjang': 'DKI3 - Jagakarsa (Jakarta Selatan)'},
        'DKI4': {'lat': -6.2891, 'lon': 106.9007, 'nama_panjang': 'DKI4 - Lubang Buaya (Jakarta Timur)'},
        'DKI5': {'lat': -6.1944, 'lon': 106.7633, 'nama_panjang': 'DKI5 - Kebon Jeruk (Jakarta Barat)'}
    }
    
    df['lat'] = df['lokasi_spku'].map(lambda x: spku_coor.get(x, {}).get('lat', -6.2088))
    df['lon'] = df['lokasi_spku'].map(lambda x: spku_coor.get(x, {}).get('lon', 106.8456))
    df['nama_stasiun'] = df['lokasi_spku'].map(lambda x: spku_coor.get(x, {}).get('nama_panjang', 'Stasiun Tidak Terdaftar'))
    
    return df

df = load_data()

# ==============================================================================
# 3. KONTROL FILTER PADA SIDEBAR (Dinamis & Responsif)
# ==============================================================================
st.sidebar.image("https://img.icons8.com/clouds/150/000000/wind.png", width=90)
st.sidebar.title("Kontrol Filter")
st.sidebar.markdown("Atur parameter di bawah ini untuk menyaring visualisasi data kualitas udara.")

# Filter 1: Pilihan Stasiun Pemantau (Multi-select)
semua_stasiun = sorted(df['nama_stasiun'].dropna().unique())
stasiun_dipilih = st.sidebar.multiselect(
    "Pilih Stasiun Pemantau (SPKU):",
    options=semua_stasiun,
    default=semua_stasiun
)

# Filter 2: Filter Rentang Tanggal
min_tgl = df['tanggal'].min().to_pydatetime()
max_tgl = df['tanggal'].max().to_pydatetime()
rentang_tanggal = st.sidebar.date_input(
    "Rentang Waktu:",
    value=(min_tgl, max_tgl),
    min_value=min_tgl,
    max_value=max_tgl
)

# Filter 3: Kategori Kualitas Udara
kategori_tersedia = sorted(df['categori'].dropna().unique())
kategori_dipilih = st.sidebar.multiselect(
    "Kategori Kualitas Udara:",
    options=kategori_tersedia,
    default=kategori_tersedia
)

# Proses Penyaringan Dataset Berdasarkan Input Pengguna
df_filtered = df[df['nama_stasiun'].isin(stasiun_dipilih)]
df_filtered = df_filtered[df_filtered['categori'].isin(kategori_dipilih)]

if isinstance(rentang_tanggal, tuple) and len(rentang_tanggal) == 2:
    start_date, end_date = rentang_tanggal
    df_filtered = df_filtered[(df_filtered['tanggal'] >= pd.to_datetime(start_date)) & 
                              (df_filtered['tanggal'] <= pd.to_datetime(end_date))]

# Urutkan berdasarkan tanggal demi konsistensi visualisasi tren
df_filtered = df_filtered.sort_values(by='tanggal')

# ==============================================================================
# 4. TAMPILAN BANNER & HEADER UTAMA
# ==============================================================================
st.title("🍃 NafasJakarta - Dashboard Kualitas Udara")
st.markdown("Platform visualisasi Indeks Standar Pencemar Udara (ISPU) interaktif untuk memantau kesehatan lingkungan DKI Jakarta.")
st.markdown("---")

# ==============================================================================
# 5. KARTU METRIK UTAMA (KPI CARDS)
# ==============================================================================
if not df_filtered.empty:
    avg_ispu = int(round(df_filtered['max'].mean()))
    zat_kritis = df_filtered['critical'].mode().iloc[0] if not df_filtered['critical'].empty else "N/A"
    
    # Standarisasi Warna, Kategori, dan Rekomendasi Kesehatan
    if avg_ispu <= 50:
        kategori_status = "BAIK"
        warna_tema = "#22c55e" # Hijau
        warna_bg = "#dcfce7"
        warna_teks = "#15803d"
        rekomendasi = "Kualitas udara sangat baik! Sangat aman dan sehat untuk melakukan aktivitas di luar ruangan tanpa masker serta membuka jendela rumah."
    elif avg_ispu <= 100:
        kategori_status = "SEDANG"
        warna_tema = "#eab308" # Kuning
        warna_bg = "#fef9c3"
        warna_teks = "#854d0e"
        rekomendasi = "Tingkat kualitas udara masih dapat diterima untuk masyarakat umum. Kelompok sensitif disarankan untuk waspada terhadap munculnya gejala pernapasan."
    elif avg_ispu <= 200:
        kategori_status = "TIDAK SEHAT"
        warna_tema = "#f97316" # Oranye
        warna_bg = "#ffedd5"
        warna_teks = "#c2410c"
        rekomendasi = "Kurangi durasi beraktivitas di luar ruangan. Dianjurkan menggunakan masker penyaring partikel (seperti KN95/KF94) bagi warga yang harus bepergian."
    else:
        kategori_status = "SANGAT TIDAK SEHAT"
        warna_tema = "#ef4444" # Merah
        warna_bg = "#fee2e2"
        warna_teks = "#b91c1c"
        rekomendasi = "Hindari aktivitas di luar ruangan sepenuhnya. Tutup rapat pintu dan ventilasi rumah, serta nyalakan perangkat pembersih udara di dalam ruangan."

    # Grid Layout untuk KPI
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="kpi-card" style="border-top: 6px solid {warna_tema};">
                <div class="kpi-title">Rata-Rata Nilai ISPU</div>
                <div class="kpi-value">{avg_ispu}</div>
                <div class="kpi-badge" style="background-color: {warna_bg}; color: {warna_teks};">
                    {kategori_status}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="kpi-card" style="border-top: 6px solid #6366f1;">
                <div class="kpi-title">Polutan Dominan</div>
                <div class="kpi-value">{zat_kritis}</div>
                <div class="kpi-badge" style="background-color: #e0e7ff; color: #4338ca;">
                    Zat Kritis Terdeteksi
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="reco-card">
                <div>
                    <div class="reco-header">Saran Aktivitas Warga</div>
                    <div class="reco-title">Rekomendasi Kesehatan</div>
                </div>
                <div class="reco-text">"{rekomendasi}"</div>
            </div>
        """, unsafe_allow_html=True)

else:
    st.warning("⚠️ Tidak ada data yang sesuai dengan kombinasi filter Anda. Silakan ubah filter pada sidebar.")

# ==============================================================================
# 6. VISUALISASI UTAMA: PETA DAN PROPORSI KONDISI (2 Kolom)
# ==============================================================================
st.markdown("### 📊 Analisis Geospasial & Statistik Kategori")
col_peta, col_proporsi = st.columns([3, 2])

with col_peta:
    st.subheader("📍 Sebaran Lokasi Pemantauan ISPU")
    if not df_filtered.empty:
        # Agregasi data per lokasi stasiun
        map_data = df_filtered.groupby(['nama_stasiun', 'lat', 'lon']).agg(
            Rata_Rata_ISPU=('max', 'mean'),
            Hari_Terpantau=('max', 'count')
        ).reset_index()
        
        # Plot peta interaktif Mapbox
        fig_map = px.scatter_mapbox(
            map_data,
            lat="lat",
            lon="lon",
            size="Rata_Rata_ISPU",
            color="Rata_Rata_ISPU",
            color_continuous_scale=["#22c55e", "#eab308", "#f97316", "#ef4444"],
            range_color=[0, 150],
            hover_name="nama_stasiun",
            hover_data={"lat": False, "lon": False, "Rata_Rata_ISPU": ":.1f", "Hari_Terpantau": True},
            zoom=10.2,
            height=400
        )
        
        fig_map.update_layout(
            mapbox_style="carto-positron",
            margin={"r":0, "t":10, "l":0, "b":0}
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Peta tidak dapat ditampilkan karena tidak ada data yang terpilih.")

with col_proporsi:
    st.subheader("🍰 Distribusi Kesehatan Udara")
    if not df_filtered.empty:
        prop_data = df_filtered['categori'].value_counts().reset_index()
        prop_data.columns = ['Kategori', 'Jumlah Hari']
        
        skema_warna = {
            'BAIK': '#22c55e',
            'SEDANG': '#eab308',
            'TIDAK SEHAT': '#f97316',
            'SANGAT TIDAK SEHAT': '#ef4444'
        }
        
        fig_pie = px.pie(
            prop_data,
            values='Jumlah Hari',
            names='Kategori',
            color='Kategori',
            color_discrete_map=skema_warna,
            hole=0.4,
            height=400
        )
        fig_pie.update_traces(textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Visualisasi lingkaran tidak tersedia.")

# ==============================================================================
# 7. VISUALISASI TREN HISTORIS HARIAN (1 Kolom Penuh)
# ==============================================================================
st.markdown("---")
st.subheader("📈 Fluktuasi Tren Polutan Udara (PM2.5 vs PM10)")

if not df_filtered.empty:
    tren_harian = df_filtered.groupby('tanggal')[['pm_duakomalima', 'pm_10']].mean().reset_index()
    
    fig_tren = go.Figure()
    
    # Tren PM2.5 (Zat yang relatif lebih krusial untuk kesehatan umum)
    fig_tren.add_trace(go.Scatter(
        x=tren_harian['tanggal'],
        y=tren_harian['pm_duakomalima'],
        mode='lines',
        name='Konsentrasi PM2.5 (Partikel Halus)',
        line=dict(color='#f97316', width=2.5),
        fill='tozeroy',
        fillcolor='rgba(249, 115, 22, 0.08)'
    ))
    
    # Tren PM10
    fig_tren.add_trace(go.Scatter(
        x=tren_harian['tanggal'],
        y=tren_harian['pm_10'],
        mode='lines',
        name='Konsentrasi PM10 (Partikel Kasar)',
        line=dict(color='#3b82f6', width=1.5, dash='dash')
    ))
    
    # Garis Batas Kritis Konsentrasi Aman PM2.5 (Standar KLHK: 55 µg/m³)
    fig_tren.add_hline(
        y=55,
        line_dash="dot",
        line_color="#22c55e",
        annotation_text="Batas Konsentrasi Aman PM2.5 (55 µg/m³)",
        annotation_position="bottom right"
    )
    
    fig_tren.update_layout(
        xaxis_title="Tanggal Pemantauan",
        yaxis_title="Konsentrasi Zat (µg/m³)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=30, b=20, l=30, r=30),
        height=350
    )
    st.plotly_chart(fig_tren, use_container_width=True)
else:
    st.info("Data tidak cukup untuk menampilkan tren.")

# ==============================================================================
# 8. EKSPLORASI DATA DALAM TABEL (PAGINASI & SEARCH)
# ==============================================================================
st.markdown("---")
st.subheader("🔍 Penelusuran Tabel Data Historis")
st.markdown("Gunakan pencarian dan penyaringan di bawah ini untuk melihat rekaman mentah ISPU harian.")

pencarian = st.text_input("Cari berdasarkan tanggal atau nama stasiun:", "")

if not df_filtered.empty:
    df_tabel = df_filtered[['tanggal', 'lokasi_spku', 'categori', 'pm_duakomalima', 'pm_10', 'critical', 'max']].copy()
    
    # Konversi tanggal ke format string yang mudah dibaca masyarakat
    df_tabel['tanggal'] = df_tabel['tanggal'].dt.strftime('%Y-%m-%d')
    
    # Terapkan fungsionalitas pencarian teks jika diisi oleh pengguna
    if pencarian:
        df_tabel = df_tabel[
            df_tabel['tanggal'].str.contains(pencarian) | 
            df_tabel['lokasi_spku'].str.contains(pencarian, case=False) |
            df_tabel['categori'].str.contains(pencarian, case=False)
        ]
        
    st.dataframe(
        df_tabel, 
        column_config={
            "tanggal": "Tanggal Pemantauan",
            "lokasi_spku": "Kode SPKU",
            "categori": "Kategori Kesehatan",
            "pm_duakomalima": "PM2.5 (µg/m³)",
            "pm_10": "PM10 (µg/m³)",
            "critical": "Zat Kritis",
            "max": "Indeks Maksimal (ISPU)"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Tidak ada data yang tersedia untuk ditampilkan dalam tabel.")

# ==============================================================================
# FOOTER DENGAN INFORMASI TEKNIS
# ==============================================================================
st.markdown("---")
st.caption("🍃 **Informasi Tambahan:** Aplikasi ini dirancang menggunakan Python, Streamlit, dan Plotly. Data yang disajikan berasal dari Laporan Historis Indeks Standar Pencemar Udara (ISPU) DKI Jakarta tahun 2022.")
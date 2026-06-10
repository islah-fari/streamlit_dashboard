import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(
    page_title="Dashboard Kualitas Udara Historis",
    page_icon="🌍",
    layout="wide"
)

# Kustomisasi Style CSS untuk Tampilan Dashboard BI yang Kontras
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MEMUAT & MEMBERSIHKAN DATA (CACHE)
# ==========================================
@st.cache_data
def load_data():
    # Membaca data asli dari file yang Anda unggah
    df = pd.read_csv('data.csv')
    
    # Konversi kolom tanggal ke format datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Bersihkan baris yang tanggalnya tidak valid atau kosong
    df = df.dropna(subset=['date'])
    
    # Isi missing value numerik secara cepat dengan median agar grafik tidak putus
    num_cols = ['pm2_5', 'rspm', 'so2', 'no2', 'spm']
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
            
    # Standardisasi teks kategori
    df['state'] = df['state'].fillna('Unknown').str.strip()
    df['type'] = df['type'].fillna('Lainnya').str.strip()
    df['location'] = df['location'].fillna('Unknown').str.strip()
    
    # Buat kolom Tahun untuk mempermudah filter jangka panjang
    df['year'] = df['date'].dt.year
    return df

try:
    df_clean = load_data()
except FileNotFoundError:
    st.error("File 'data.csv' tidak ditemukan. Pastikan file berada di direktori yang sama dengan skrip ini.")
    st.stop()

# ==========================================
# 3. SIDEBAR / PANEL FILTER UTAMA
# ==========================================
st.sidebar.title("🎛️ Panel Kontrol BI")
st.sidebar.markdown("Saring data historis menggunakan filter di bawah ini:")

# Filter 1: Negara Bagian / Provinsi (State)
states = sorted(df_clean['state'].unique().tolist())
selected_state = st.sidebar.selectbox("Pilih Wilayah/Negara Bagian:", ["Semua Wilayah"] + states)

# Filter 2: Tipe Area (Type)
types = sorted(df_clean['type'].unique().tolist())
selected_type = st.sidebar.selectbox("Tipe Area Udara:", ["Semua Tipe"] + types)

# Filter 3: Rentang Tahun (Guna mengakomodasi rentang data tahun 1990 - 2015)
min_year = int(df_clean['year'].min())
max_year = int(df_clean['year'].max())
selected_years = st.sidebar.slider(
    "Rentang Tahun Pengamatan:",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)

# Proses Penyaringan Data Berdasarkan Filter Sidebar
df_filtered = df_clean.copy()

if selected_state != "Semua Wilayah":
    df_filtered = df_filtered[df_filtered['state'] == selected_state]

if selected_type != "Semua Tipe":
    df_filtered = df_filtered[df_filtered['type'] == selected_type]

df_filtered = df_filtered[
    (df_filtered['year'] >= selected_years[0]) & 
    (df_filtered['year'] <= selected_years[1])
]

# ==========================================
# 4. TATA LETAK UTAMA & HEADLINE KPI
# ==========================================
st.title("📊 Dashboard Historis Pemantauan Kualitas Udara")
st.markdown(f"Menampilkan data analisis untuk periode tahun **{selected_years[0]} s.d {selected_years[1]}**")
st.markdown("---")

# Hitung Metrik Rata-rata Utama
if not df_filtered.empty:
    m_pm25 = round(df_filtered['pm2_5'].mean(), 1)
    m_rspm = round(df_filtered['rspm'].mean(), 1)
    m_so2 = round(df_filtered['so2'].mean(), 1)
    m_no2 = round(df_filtered['no2'].mean(), 1)
else:
    m_pm25, m_rspm, m_so2, m_no2 = 0, 0, 0, 0

# Tampilkan ke dalam 4 Kolom Kustom
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label="Rata-rata PM2.5", value=f"{m_pm25} µg/m³", delta="Parameter Utama")
kpi2.metric(label="Rata-rata RSPM / PM10", value=f"{m_rspm} µg/m³", delta="Partikel Kasar")
kpi3.metric(label="Rata-rata SO2", value=f"{m_so2} µg/m³", delta="Gas Industri")
kpi4.metric(label="Rata-rata NO2", value=f"{m_no2} µg/m³", delta="Emisi Kendaraan")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. BARIS GRAFIK TREN DAN PROPORSI
# ==========================================
col_graph1, col_graph2 = st.columns([2, 1])

with col_graph1:
    st.subheader("📈 Tren Perkembangan Polutan dari Tahun ke Tahun")
    if not df_filtered.empty:
        # Agregasikan data per tahun agar grafik tren tidak terlalu padat bergigi
        df_yearly_trend = df_filtered.groupby('year')[['pm2_5', 'rspm', 'so2', 'no2']].mean().reset_index()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_yearly_trend['year'], y=df_yearly_trend['pm2_5'], mode='lines+markers', name='PM2.5', line=dict(color='#6366f1', width=3)))
        fig_trend.add_trace(go.Scatter(x=df_yearly_trend['year'], y=df_yearly_trend['rspm'], mode='lines', name='RSPM', line=dict(color='#f59e0b', width=2)))
        fig_trend.add_trace(go.Scatter(x=df_yearly_trend['year'], y=df_yearly_trend['no2'], mode='lines', name='NO2', line=dict(color='#3b82f6', width=1.5)))
        
        fig_trend.update_layout(
            hovermode="x unified",
            xaxis_title="Tahun Pengamatan",
            yaxis_title="Konsentrasi (µg/m³)",
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, dtick=2)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Data kosong pada kombinasi filter ini.")

with col_graph2:
    st.subheader("🍩 Distribusi Berdasarkan Tipe Area")
    if not df_filtered.empty:
        df_pie = df_filtered['type'].value_counts().reset_index()
        fig_pie = px.pie(df_pie, values='count', names='type', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Tidak ada data.")

# ==========================================
# 6. BARIS ANALISIS AREA BERMASALAH (TOP 5)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
col_bar1, col_bar2 = st.columns(2)

with col_bar1:
    st.subheader("🚨 Top 5 Lokasi Spesifik Paling Tercemar (Rata-rata RSPM)")
    if not df_filtered.empty:
        df_top_loc = df_filtered.groupby('location')['rspm'].mean().reset_index()
        df_top_loc = df_top_loc.sort_values(by='rspm', ascending=True).tail(5)
        
        fig_loc = px.bar(df_top_loc, x='rspm', y='location', orientation='h', color_discrete_sequence=['#ef4444'])
        fig_loc.update_layout(xaxis_title="Rata-rata RSPM", yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_loc, use_container_width=True)
    else:
        st.info("Tidak ada data.")

with col_bar2:
    st.subheader("🏢 Tingkat Polusi Udara per Lembaga Pengawas (Agency)")
    if not df_filtered.empty:
        # Filter agency yang tidak kosong untuk analisis valid
        df_agency = df_filtered[df_filtered['agency'].notna() & (df_filtered['agency'] != "")]
        if not df_agency.empty:
            df_agency_agg = df_agency.groupby('agency')['pm2_5'].mean().reset_index().sort_values(by='pm2_5', ascending=False).head(5)
            fig_agency = px.bar(df_agency_agg, x='agency', y='pm2_5', color_discrete_sequence=['#64748b'])
            fig_agency.update_layout(xaxis_title=None, yaxis_title="Rata-rata PM2.5", plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_agency, use_container_width=True)
        else:
            st.info("Kolom 'agency' tidak memiliki data terisi pada filter ini.")
    else:
        st.info("Tidak ada data.")

# ==========================================
# 7. TABEL DETAIL & FITUR UNDUH DATA
# ==========================================
st.markdown("---")
st.subheader("📋 Eksplorasi Data Rincian Stasiun")

# Fitur Pencarian Cepat Teks
search_txt = st.text_input("🔍 Cari berdasarkan Nama Lokasi / Negara Bagian / Kode Stasiun:", "")
if search_txt:
    df_filtered = df_filtered[
        df_filtered['location'].str.lower().str.contains(search_txt.lower()) |
        df_filtered['state'].str.lower().str.contains(search_txt.lower()) |
        df_filtered['stn_code'].astype(str).str.lower().str.contains(search_txt.lower())
    ]

# Render Tabel Data Aktif (Maksimal ditampilkan 500 baris agar performa web tetap ringan)
max_display_rows = 500
st.dataframe(
    df_filtered[['stn_code', 'sampling_date', 'state', 'location', 'type', 'pm2_5', 'rspm', 'so2', 'no2']].head(max_display_rows),
    use_container_width=True,
    hide_index=True
)
st.caption(f"Menampilkan maksimum {max_display_rows} baris dari total {len(df_filtered)} baris data hasil filter.")

# Fitur Tambahan: Tombol Unduh CSV untuk keperluan pelaporan internal/eksternal
if not df_filtered.empty:
    csv_data = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Unduh Data Hasil Filter (.CSV)",
        data=csv_data,
        file_name="kualitas_udara_filtered.csv",
        mime="text/csv",
        use_container_width=True
    )
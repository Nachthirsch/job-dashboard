# 🦌 Handra Job Application Dashboard

Read-only Streamlit dashboard yang membaca data dari Google Sheets **"List Lamaran Kerjaan"**.

## ✨ Fitur

- 📊 **Real-time metrics**: Total, Applied, Interview, Rejected, No Response
- 📈 **Charts interaktif** (Plotly): status distribution, trend, source breakdown, day-of-week pattern
- 🔍 **Filter lengkap**: Source, Status, CV Used, Date Range
- 📥 **Export CSV** untuk data yang sudah difilter
- 🔄 **Auto-refresh** setiap 5 menit (atau klik tombol Refresh)
- 🎨 **Color-coded status** + table interaktif dengan link "View"

## 🚀 Cara Menjalankan

### Pertama kali (sudah dilakukan untuk Anda):

1. ✅ Virtual environment dibuat di `venv/`
2. ✅ Dependencies terinstall (streamlit, pandas, plotly, google-api-python-client)

### Menjalankan dashboard:

Buka terminal di folder ini, lalu:

```bash
cd C:\LAMARAN\Streamlit
venv\Scripts\activate
streamlit run app.py
```

Atau langsung tanpa aktivasi venv:

```bash
cd C:\LAMARAN\Streamlit
venv\Scripts\streamlit.exe run app.py
```

Browser akan otomatis terbuka di **http://localhost:8501**

## 🔐 Setup OAuth (Sudah Dilakukan)

Dashboard ini **re-use** OAuth token dari skill `google-workspace` yang sudah di-setup:
- Token: `C:\Users\Handra\AppData\Local\hermes\google_token.json`
- Client secret: `C:\Users\Handra\AppData\Local\hermes\google_client_secret.json`

Kalau token belum ada, jalankan setup dulu (lihat skill `google-workspace`).

## 🛠️ Tech Stack

- **Streamlit** — UI framework
- **Pandas** — data manipulation
- **Plotly** — interactive charts
- **Google Sheets API** — data source

## 📝 Catatan

- Dashboard ini **read-only** — tidak mengubah data di spreadsheet
- Data di-cache selama 5 menit, klik **🔄 Refresh Data** di sidebar untuk refresh manual
- Pastikan spreadsheet ID di `app.py` (line 22) sesuai dengan spreadsheet kamu

## 🐛 Troubleshooting

**Error: No module named 'streamlit'**
- Pastikan Anda menjalankan dari `venv\Scripts\` atau dalam venv yang aktif
- Coba: `venv\Scripts\python.exe -m streamlit run app.py`

**Error: NOT_AUTHENTICATED**
- Token Google belum disetup. Lihat skill `google-workspace` untuk setup OAuth.

**Dashboard loading lambat**
- Normal untuk pertama kali (Google Sheets API call)
- Setelah 5 menit, akan auto-refresh

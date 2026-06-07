# Scraping Data Sekolah Indonesia (DAPODIK & EMIS Kemenag)

Proyek ini adalah seperangkat alat (tools) berbasis Python untuk melakukan *scraping* (pengambilan data) informasi sekolah di Indonesia baik dari API Data Pokok Pendidikan (DAPO) Kemendikdasmen (SD, SMP, SMA, SMK) maupun dari portal data referensi EMIS Kemenag (RA, MI, MTs, MA, MAK). Proyek ini juga dilengkapi dengan alat untuk membangun *dashboard web interaktif* secara lokal berdasarkan data yang berhasil diekstrak.

## 🎯 Tujuan
Tujuan dari repositori ini adalah:
1. Mengekstrak data sekolah resmi Kemendikdasmen (termasuk nama sekolah, NPSN, status, alamat kecamatan, jumlah siswa, guru, sarana-prasarana, dll) langsung dari *endpoint* DAPO.
2. Mengekstrak data madrasah/sekolah Islam resmi di bawah Kemenag (RA, MI, MTs, MA, MAK) dari portal data referensi dengan format kolom yang 100% kompatibel dengan data DAPO.
3. Menyediakan script yang tahan banting (fault-tolerant) dengan mekanisme *retry*, *progress tracking*, dan *resume* untuk menangani skala data nasional (Seluruh Indonesia).
4. Menyediakan antarmuka visual (dashboard web) yang dinamis untuk melihat, mencari, menyortir, dan mem-filter data yang sudah ditarik secara offline.

## ✨ Fitur Utama
- **Scraper Sekolah Dapodik** (`scrape_indonesia.py`): Mengambil data dari tingkat Provinsi, Kabupaten, Kecamatan, hingga Sekolah untuk seluruh Indonesia di bawah Kemendikdasmen. Mendukung fitur *resume* apabila proses terhenti di tengah jalan.
- **Scraper Madrasah EMIS Kemenag** (`scrape_emis.py`): Mengunduh data 5 bentuk pendidikan Islam (RA, MI, MTs, MA, MAK) secara paralel (multi-threaded dengan 5 workers per kecamatan) untuk seluruh Indonesia dengan pemetaan wilayah yang sesuai dengan data Dapodik. Mendukung *resume* otomatis dan penanganan kegagalan request yang aman (failed requests will retry/skip and can be resumed).
- **Generator Web Dashboard** (`generate_web.py`): Bertindak sebagai *local API server* yang membaca file CSV raksasa hasil ekstraksi dengan efisien, serta menyajikan HTML dashboard yang cantik dengan styling moderen, dan langsung menjalankannya di localhost. Terdapat fitur filter berjenjang (Provinsi, Kabupaten, Kecamatan, Jenjang Pendidikan, Status) dan kolom *search*.

## ⚙️ Persyaratan (Requirements)
Pastikan Anda memiliki Python 3.x terinstal. Kemudian instal *library* tambahan yang dibutuhkan:
```bash
pip install requests pandas openpyxl beautifulsoup4
```

## 🚀 Cara Penggunaan

### 1. Scraping Data Dapodik (SD, SMP, SMA, SMK)
Proses ini mengambil data sekolah Kemendikdasmen. Data disimpan berjenjang di folder `output_indonesia/` per provinsi dan kabupaten, serta satu CSV gabungan nasional.
```bash
# Menjalankan scraping seluruh Indonesia
python scrape_indonesia.py

# Melanjutkan scraping yang terhenti (Resume)
python scrape_indonesia.py --resume

# Scraping hanya untuk satu provinsi tertentu
python scrape_indonesia.py --provinsi "Prov. Jawa Timur"
```

### 2. Scraping Data Madrasah EMIS Kemenag (RA, MI, MTs, MA, MAK)
Proses ini mengambil data madrasah Kemenag. Data disimpan secara paralel per kecamatan dan disusun berjenjang di folder `output_emis/` per provinsi dan kabupaten, serta satu CSV gabungan nasional.
```bash
# Menjalankan scraping EMIS seluruh Indonesia
python scrape_emis.py

# Melanjutkan scraping EMIS yang terhenti (Resume)
python scrape_emis.py --resume

# Scraping EMIS hanya untuk satu provinsi tertentu
python scrape_emis.py --provinsi "Prov. Jawa Timur"
```

### 3. Menjalankan Dashboard Web Interaktif
Setelah Anda memiliki data berupa file `data_sekolah_indonesia.csv` di dalam folder `output_indonesia/` (hasil dari `scrape_indonesia.py`), jalankan perintah ini untuk melihat data tersebut dalam bentuk web:
```bash
python generate_web.py
```
Aplikasi akan secara otomatis membukakan browser (biasanya http://localhost:8000) yang menampilkan data dengan visual bergaya premium *glassmorphism*, lengkap dengan statistik agregat yang dinamis dan fitur filter wilayah.

## 📁 Struktur Output Data

### Output Dapodik:
```
output_indonesia/
├── Prov. Jawa Timur/
│   ├── Kota Surabaya/
│   │   ├── Kec. Tambaksari.csv
│   │   └── _gabungan_Kota Surabaya.csv
│   └── _gabungan_Prov. Jawa Timur.csv
└── data_sekolah_indonesia.csv   (gabungan nasional Dapodik)
```

### Output EMIS Kemenag:
```
output_emis/
├── Prov. Jawa Timur/
│   ├── Kota Surabaya/
│   │   ├── Kec. Tambaksari.csv
│   │   └── _gabungan_Kota Surabaya.csv
│   └── _gabungan_Prov. Jawa Timur.csv
├── data_sekolah_emis.csv        (gabungan nasional EMIS)
└── _progress.json               (catatan progress scraping EMIS)
```

## ⚠️ Disklaimer
- Repository ini dibuat untuk tujuan pembelajaran dan riset data publik.
- Script ini dirancang agar tidak membebani server tujuan (menggunakan sistem *delay*). Harap gunakan secara bertanggung jawab dan jangan melakukan *request* berlebihan / *spamming*.

---
*Dibuat oleh Bernaldo Napitupulu*

# Scraping Data Sekolah DAPO Kemendikdasmen

Proyek ini adalah seperangkat alat (tools) berbasis Python untuk melakukan *scraping* (pengambilan data) informasi sekolah (SD, SMP, SMA, SMK) dari API Data Pokok Pendidikan (DAPO) Kemendikdasmen. Proyek ini juga dilengkapi dengan alat untuk membangun *dashboard web interaktif* secara lokal berdasarkan data yang berhasil diekstrak.

## 🎯 Tujuan
Tujuan dari repositori ini adalah:
1. Mengekstrak data sekolah resmi (termasuk nama sekolah, NPSN, status, alamat kecamatan, jumlah siswa, guru, sarana-prasarana, dll) langsung dari *endpoint* DAPO Kemendikdasmen.
2. Menyediakan script yang tahan banting (fault-tolerant) dengan mekanisme *retry* dan *progress tracking* untuk menangani skala data nasional (Seluruh Indonesia).
3. Menyediakan antarmuka visual (dashboard web) yang dinamis untuk melihat, mencari, menyortir, dan mem-filter data yang sudah ditarik secara offline.

## ✨ Fitur Utama
- **Scraper Nasional** (`scrape_indonesia.py`): Mengambil data dari tingkat Provinsi, Kabupaten, Kecamatan, hingga Sekolah untuk seluruh Indonesia. Mendukung fitur *resume* apabila proses terhenti di tengah jalan. Data disusun secara rapi di dalam folder terstruktur per provinsi. Anda juga dapat menentukan argumen untuk scraping spesifik provinsi tertentu.
- **Generator Web Dashboard** (`generate_web.py`): Bertindak sebagai *local API server* yang membaca file CSV raksasa hasil ekstraksi dengan efisien, serta menyajikan HTML dashboard yang cantik dengan styling moderen, dan langsung menjalankannya di localhost. Terdapat fitur filter berjenjang (Provinsi, Kabupaten, Kecamatan, Jenjang Pendidikan, Status) dan kolom *search*.

## ⚙️ Persyaratan (Requirements)
Pastikan Anda memiliki Python 3.x terinstal. Kemudian instal *library* tambahan yang dibutuhkan:
```bash
pip install requests pandas openpyxl
```

## 🚀 Cara Penggunaan

### 1. Scraping Data Skala Nasional (Seluruh Indonesia)
Script ini dirancang untuk mengambil data se-Indonesia. Proses ini memakan waktu yang cukup lama. Hasil data akan disimpan berjenjang di dalam folder `output_indonesia/` per provinsi dan kabupaten, serta satu CSV gabungan raksasa.
```bash
# Menjalankan scraping seluruh Indonesia
python scrape_indonesia.py

# Melanjutkan scraping yang terhenti (Resume)
python scrape_indonesia.py --resume

# Scraping hanya untuk satu provinsi tertentu
python scrape_indonesia.py --provinsi "Prov. Jawa Timur"
```

### 2. Menjalankan Dashboard Web Interaktif
Setelah Anda memiliki data berupa file `data_sekolah_indonesia.csv` di dalam folder `output_indonesia/` (hasil dari `scrape_indonesia.py`), jalankan perintah ini untuk melihat data tersebut dalam bentuk web:
```bash
python generate_web.py
```
Aplikasi akan secara otomatis membukakan browser (biasanya http://localhost:8000) yang menampilkan data dengan visual bergaya premium *glassmorphism*, lengkap dengan statistik agregat yang dinamis dan fitur filter wilayah.

## ⚠️ Disklaimer
- Repository ini dibuat untuk tujuan pembelajaran dan riset data publik.
- Script ini dirancang agar tidak membebani server tujuan (menggunakan sistem *delay*). Harap gunakan secara bertanggung jawab dan jangan melakukan *request* berlebihan / *spamming*.

---
*Dibuat oleh Bernaldo Napitupulu*

# Scraping Data Sekolah DAPO Kemendikdasmen

Proyek ini adalah seperangkat alat (tools) berbasis Python untuk melakukan *scraping* (pengambilan data) informasi sekolah (SD, SMP, SMA, SMK) dari API Data Pokok Pendidikan (DAPO) Kemendikdasmen. Proyek ini juga dilengkapi dengan alat untuk membangun *dashboard web interaktif* secara lokal berdasarkan data yang berhasil diekstrak.

## 🎯 Tujuan
Tujuan dari repositori ini adalah:
1. Mengekstrak data sekolah resmi (termasuk nama sekolah, NPSN, status, alamat kecamatan, jumlah siswa, guru, sarana-prasarana, dll) langsung dari *endpoint* DAPO Kemendikdasmen.
2. Menyediakan script yang tahan banting (fault-tolerant) dengan mekanisme *retry* dan *progress tracking* untuk menangani skala data nasional (Seluruh Indonesia).
3. Menyediakan antarmuka visual (dashboard web) yang dinamis untuk melihat, mencari, menyortir, dan mem-filter data yang sudah ditarik secara offline.

## ✨ Fitur Utama
- **Scraper Spesifik (Surabaya/Kustom)** (`scrape_dapo.py`): Mengambil data sekolah secara rinci untuk wilayah spesifik dan menyimpan hasilnya dalam bentuk CSV, Excel (dengan multi-sheet), dan JSON.
- **Scraper Nasional** (`scrape_indonesia.py`): Mengambil data dari tingkat Provinsi, Kabupaten, Kecamatan, hingga Sekolah untuk seluruh Indonesia. Mendukung fitur *resume* apabila proses terhenti di tengah jalan. Data disusun secara rapi di dalam folder terstruktur per provinsi.
- **Generator Web Dashboard** (`generate_web.py`): Membaca file JSON hasil ekstraksi, mengubahnya menjadi HTML dashboard statis yang cantik dengan styling moderen, dan langsung menjalankannya di localhost. Terdapat fitur filter (Jenjang, Kecamatan, Status) dan *search*.

## ⚙️ Persyaratan (Requirements)
Pastikan Anda memiliki Python 3.x terinstal. Kemudian instal *library* tambahan yang dibutuhkan:
```bash
pip install requests pandas openpyxl
```

## 🚀 Cara Penggunaan

### 1. Scraping Data Spesifik (Contoh: Kota Surabaya)
Jika Anda hanya ingin mengambil data sekolah untuk satu daerah tertentu, Anda dapat mengedit variabel `TARGET_PROVINSI` dan `TARGET_KABUPATEN` di dalam `scrape_dapo.py`, lalu jalankan:
```bash
python scrape_dapo.py
```
Output berupa file `.csv`, `.xlsx`, dan `.json` akan tersimpan di dalam folder `output/`.

### 2. Scraping Data Skala Nasional (Seluruh Indonesia)
Script ini dirancang untuk mengambil data se-Indonesia. Proses ini memakan waktu yang cukup lama. Hasil data akan disimpan berjenjang di dalam folder `output_indonesia/` per provinsi dan kebupaten, serta satu CSV gabungan raksasa.
```bash
# Menjalankan scraping seluruh Indonesia
python scrape_indonesia.py

# Melanjutkan scraping yang terhenti (Resume)
python scrape_indonesia.py --resume

# Scraping hanya untuk satu provinsi tertentu
python scrape_indonesia.py --provinsi "Prov. Jawa Timur"
```

### 3. Menjalankan Dashboard Web Interaktif
Setelah Anda memiliki data berupa `.json` di dalam folder `output/` (hasil dari `scrape_dapo.py`), jalankan perintah ini untuk melihat data tersebut dalam bentuk web (tabel interaktif):
```bash
python generate_web.py
```
Aplikasi akan secara otomatis membukakan browser (biasanya http://localhost:8000) yang menampilkan data dengan visual yang menarik, lengkap dengan statistik, dan fitur *searching* & filter.

## ⚠️ Disklaimer
- Repository ini dibuat untuk tujuan pembelajaran dan riset data publik.
- Script ini dirancang agar tidak membebani server tujuan (menggunakan sistem *delay*). Harap gunakan secara bertanggung jawab dan jangan melakukan *request* berlebihan / *spamming*.

---
*Dibuat oleh Bernaldo Napitupulu*

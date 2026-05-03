"""
Scraper Data Sekolah - DAPO Kemendikdasmen
==========================================
Mengambil data sekolah dari https://dapo.kemendikdasmen.go.id/sp

API Endpoints:
- Provinsi   : /rekap/dataSekolah?id_level_wilayah=0&kode_wilayah=000000&semester_id=20252
- Kabupaten   : /rekap/dataSekolah?id_level_wilayah=1&kode_wilayah={kode_provinsi}&semester_id=20252
- Kecamatan   : /rekap/dataSekolah?id_level_wilayah=2&kode_wilayah={kode_kabupaten}&semester_id=20252
- Sekolah     : /rekap/progresSP?id_level_wilayah=3&kode_wilayah={kode_kecamatan}&semester_id=20252&bentuk_pendidikan_id=

Usage:
    python scrape_dapo.py
"""

import requests
import pandas as pd
import json
import time
import os
import sys
from datetime import datetime

# ============================================================
# KONFIGURASI - Ubah sesuai kebutuhan
# ============================================================
BASE_URL = "https://dapo.kemendikdasmen.go.id"
SEMESTER_ID = "20252"

# Target wilayah
TARGET_PROVINSI = "050000"       # Jawa Timur
TARGET_KABUPATEN = "056000"      # Kota Surabaya

# Jenjang yang ingin diambil
TARGET_JENJANG = ["SD", "SMP", "SMA", "SMK"]

# Retry & delay settings
MAX_RETRIES = 5
RETRY_DELAY = 3        # detik antar retry
REQUEST_DELAY = 1      # detik antar request (agar tidak terlalu cepat)
REQUEST_TIMEOUT = 30   # timeout per request

# Output
OUTPUT_DIR = "output"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ============================================================
# HEADERS - Mirip browser agar tidak di-block
# ============================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://dapo.kemendikdasmen.go.id/sp",
    "X-Requested-With": "XMLHttpRequest",
}

# ============================================================
# FUNGSI UTAMA
# ============================================================

def fetch_json(url, label=""):
    """Fetch JSON dari URL dengan retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if label:
                print(f"  📡 [{attempt}/{MAX_RETRIES}] Fetching {label}...")
            
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data
                elif isinstance(data, list) and len(data) == 0:
                    print(f"  ⚠️  Data kosong untuk {label}")
                    return []
                return data
            elif response.status_code == 500:
                print(f"  ⚠️  Server error 500, retry in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ❌ HTTP {response.status_code}")
                time.sleep(RETRY_DELAY)
                
        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout, retry in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError:
            print(f"  🔌 Connection error, retry in {RETRY_DELAY * 2}s...")
            time.sleep(RETRY_DELAY * 2)
        except json.JSONDecodeError:
            print(f"  ⚠️  Invalid JSON response, retry in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            time.sleep(RETRY_DELAY)
    
    print(f"  ❌ Gagal setelah {MAX_RETRIES} percobaan untuk {label}")
    return None


def get_wilayah_list(level, kode_wilayah):
    """Ambil daftar wilayah (provinsi/kabupaten/kecamatan)."""
    url = (
        f"{BASE_URL}/rekap/dataSekolah"
        f"?id_level_wilayah={level}"
        f"&kode_wilayah={kode_wilayah}"
        f"&semester_id={SEMESTER_ID}"
    )
    return fetch_json(url, f"wilayah level {level} ({kode_wilayah})")


def get_sekolah_by_kecamatan(kode_kecamatan, nama_kecamatan=""):
    """Ambil data sekolah di satu kecamatan."""
    url = (
        f"{BASE_URL}/rekap/progresSP"
        f"?id_level_wilayah=3"
        f"&kode_wilayah={kode_kecamatan}"
        f"&semester_id={SEMESTER_ID}"
        f"&bentuk_pendidikan_id="
    )
    label = f"sekolah di {nama_kecamatan} ({kode_kecamatan})"
    return fetch_json(url, label)


def filter_by_jenjang(schools, jenjang_list):
    """Filter sekolah berdasarkan bentuk pendidikan (SD, SMP, SMA, SMK)."""
    if not schools:
        return []
    return [s for s in schools if s.get("bentuk_pendidikan", "").strip() in jenjang_list]


def clean_school_data(school):
    """Bersihkan dan format data sekolah untuk output."""
    return {
        "nama_sekolah": school.get("nama", "").strip(),
        "npsn": school.get("npsn", ""),
        "bentuk_pendidikan": school.get("bentuk_pendidikan", "").strip(),
        "status_sekolah": school.get("status_sekolah", "").strip(),
        "kecamatan": school.get("induk_kecamatan", "").strip(),
        "kode_kecamatan": school.get("kode_wilayah_induk_kecamatan", "").strip(),
        "kabupaten": school.get("induk_kabupaten", "").strip(),
        "kode_kabupaten": school.get("kode_wilayah_induk_kabupaten", "").strip(),
        "provinsi": school.get("induk_provinsi", "").strip(),
        "kode_provinsi": school.get("kode_wilayah_induk_provinsi", "").strip(),
        "jumlah_guru_ptk": school.get("ptk", 0),
        "jumlah_pegawai": school.get("pegawai", 0),
        "jumlah_peserta_didik": school.get("pd", 0),
        "jumlah_rombel": school.get("rombel", 0),
        "jumlah_ruang_kelas": school.get("jml_rk", 0),
        "jumlah_lab": school.get("jml_lab", 0),
        "jumlah_perpustakaan": school.get("jml_perpus", 0),
        "jumlah_kirim_sinkron": school.get("jumlah_kirim", 0),
        "sinkron_terakhir": school.get("sinkron_terakhir", ""),
        "sekolah_id_enkrip": school.get("sekolah_id_enkrip", "").strip(),
    }


def print_banner():
    """Tampilkan banner program."""
    print("=" * 65)
    print("  📚 SCRAPER DATA SEKOLAH - DAPO KEMENDIKDASMEN")
    print("  📅 Semester: " + SEMESTER_ID)
    print("  🎯 Target: Jawa Timur > Kota Surabaya > Semua Kecamatan")
    print("  🏫 Jenjang: " + ", ".join(TARGET_JENJANG))
    print("=" * 65)


def print_summary(all_schools):
    """Tampilkan ringkasan hasil."""
    df = pd.DataFrame(all_schools)
    
    print("\n" + "=" * 65)
    print("  📊 RINGKASAN HASIL")
    print("=" * 65)
    
    print(f"\n  Total sekolah: {len(df)}")
    
    if len(df) > 0:
        # Per jenjang
        print("\n  Per Jenjang:")
        for jenjang in TARGET_JENJANG:
            count = len(df[df["bentuk_pendidikan"] == jenjang])
            print(f"    • {jenjang}: {count} sekolah")
        
        # Per status
        print("\n  Per Status:")
        for status in df["status_sekolah"].unique():
            count = len(df[df["status_sekolah"] == status])
            print(f"    • {status}: {count} sekolah")
        
        # Total peserta didik
        total_pd = df["jumlah_peserta_didik"].sum()
        print(f"\n  Total Peserta Didik: {total_pd:,}")
        
        # Per kecamatan
        print("\n  Per Kecamatan:")
        kec_counts = df.groupby("kecamatan").size().sort_values(ascending=False)
        for kec, count in kec_counts.items():
            print(f"    • {kec}: {count} sekolah")


# ============================================================
# MAIN
# ============================================================

def main():
    print_banner()
    
    # 1. Ambil daftar kecamatan di Kota Surabaya
    print("\n📍 Mengambil daftar kecamatan di Kota Surabaya...")
    kecamatan_list = get_wilayah_list(2, TARGET_KABUPATEN)
    
    if not kecamatan_list:
        print("❌ Gagal mengambil daftar kecamatan! Coba lagi nanti.")
        sys.exit(1)
    
    print(f"✅ Ditemukan {len(kecamatan_list)} kecamatan\n")
    
    # Tampilkan daftar kecamatan
    for i, kec in enumerate(kecamatan_list, 1):
        nama = kec.get("nama", "").strip()
        kode = kec.get("kode_wilayah", "").strip()
        total = kec.get("sekolah", 0)
        sd = kec.get("sd", 0)
        smp = kec.get("smp", 0) 
        sma = kec.get("sma", 0)
        smk = kec.get("smk", 0)
        print(f"  {i:2}. {nama:<25} [{kode}] - SD:{sd} SMP:{smp} SMA:{sma} SMK:{smk}")
    
    # 2. Ambil data sekolah per kecamatan
    print(f"\n{'=' * 65}")
    print(f"  🏫 Mulai mengambil data sekolah ({', '.join(TARGET_JENJANG)})...")
    print(f"{'=' * 65}\n")
    
    all_schools = []
    failed_kecamatan = []
    
    for i, kec in enumerate(kecamatan_list, 1):
        nama_kec = kec.get("nama", "").strip()
        kode_kec = kec.get("kode_wilayah", "").strip()
        
        print(f"[{i}/{len(kecamatan_list)}] 📍 {nama_kec} ({kode_kec})")
        
        # Fetch data sekolah
        schools_raw = get_sekolah_by_kecamatan(kode_kec, nama_kec)
        
        if schools_raw is None:
            print(f"  ❌ GAGAL - akan dicoba ulang nanti")
            failed_kecamatan.append(kec)
            time.sleep(REQUEST_DELAY)
            continue
        
        # Filter jenjang
        schools_filtered = filter_by_jenjang(schools_raw, TARGET_JENJANG)
        
        # Clean data
        schools_clean = [clean_school_data(s) for s in schools_filtered]
        all_schools.extend(schools_clean)
        
        # Progress
        jenjang_breakdown = {}
        for s in schools_filtered:
            bp = s.get("bentuk_pendidikan", "").strip()
            jenjang_breakdown[bp] = jenjang_breakdown.get(bp, 0) + 1
        
        breakdown_str = ", ".join(f"{k}:{v}" for k, v in sorted(jenjang_breakdown.items()))
        print(f"  ✅ {len(schools_filtered)} sekolah ({breakdown_str})")
        
        # Delay agar tidak membebani server
        time.sleep(REQUEST_DELAY)
    
    # 3. Retry kecamatan yang gagal
    if failed_kecamatan:
        print(f"\n🔄 Retry {len(failed_kecamatan)} kecamatan yang gagal...\n")
        time.sleep(RETRY_DELAY * 2)
        
        for kec in failed_kecamatan:
            nama_kec = kec.get("nama", "").strip()
            kode_kec = kec.get("kode_wilayah", "").strip()
            
            print(f"  🔄 Retry: {nama_kec} ({kode_kec})")
            
            schools_raw = get_sekolah_by_kecamatan(kode_kec, nama_kec)
            if schools_raw is not None:
                schools_filtered = filter_by_jenjang(schools_raw, TARGET_JENJANG)
                schools_clean = [clean_school_data(s) for s in schools_filtered]
                all_schools.extend(schools_clean)
                print(f"  ✅ Berhasil: {len(schools_filtered)} sekolah")
            else:
                print(f"  ❌ Tetap gagal: {nama_kec}")
            
            time.sleep(REQUEST_DELAY)
    
    # 4. Simpan hasil
    if not all_schools:
        print("\n❌ Tidak ada data yang berhasil diambil!")
        sys.exit(1)
    
    # Buat output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    df = pd.DataFrame(all_schools)
    
    # Urutkan berdasarkan jenjang, kecamatan, nama
    jenjang_order = {j: i for i, j in enumerate(TARGET_JENJANG)}
    df["_sort"] = df["bentuk_pendidikan"].map(jenjang_order)
    df = df.sort_values(["_sort", "kecamatan", "nama_sekolah"]).drop(columns=["_sort"])
    df = df.reset_index(drop=True)
    
    # Simpan CSV
    csv_path = os.path.join(OUTPUT_DIR, f"data_sekolah_surabaya_{TIMESTAMP}.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 CSV tersimpan: {csv_path}")
    
    # Simpan Excel dengan formatting
    xlsx_path = os.path.join(OUTPUT_DIR, f"data_sekolah_surabaya_{TIMESTAMP}.xlsx")
    
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Sheet 1: Semua data
        df.to_excel(writer, sheet_name="Semua Sekolah", index=False)
        
        # Sheet per jenjang
        for jenjang in TARGET_JENJANG:
            df_jenjang = df[df["bentuk_pendidikan"] == jenjang]
            if len(df_jenjang) > 0:
                df_jenjang.to_excel(writer, sheet_name=jenjang, index=False)
        
        # Sheet ringkasan per kecamatan
        summary_data = []
        for kec_name in sorted(df["kecamatan"].unique()):
            df_kec = df[df["kecamatan"] == kec_name]
            row = {"kecamatan": kec_name}
            for jenjang in TARGET_JENJANG:
                row[f"jumlah_{jenjang}"] = len(df_kec[df_kec["bentuk_pendidikan"] == jenjang])
                row[f"siswa_{jenjang}"] = df_kec[df_kec["bentuk_pendidikan"] == jenjang]["jumlah_peserta_didik"].sum()
            row["total_sekolah"] = len(df_kec)
            row["total_siswa"] = df_kec["jumlah_peserta_didik"].sum()
            summary_data.append(row)
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name="Ringkasan", index=False)
        
        # Auto-fit column widths
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for column_cells in ws.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter
                for cell in column_cells:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
    
    print(f"💾 Excel tersimpan: {xlsx_path}")
    
    # Simpan raw JSON juga
    json_path = os.path.join(OUTPUT_DIR, f"data_sekolah_surabaya_{TIMESTAMP}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_schools, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON tersimpan: {json_path}")
    
    # 5. Tampilkan ringkasan
    print_summary(all_schools)
    
    print(f"\n✅ Selesai! {len(all_schools)} sekolah berhasil diambil.")
    print(f"📁 File output ada di folder: {OUTPUT_DIR}/")

    
if __name__ == "__main__":
    main()

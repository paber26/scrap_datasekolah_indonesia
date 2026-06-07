"""
Scraper Data Sekolah/Madrasah EMIS Kemenag (RA, MI, MTs, MA, MAK)
================================================================
Struktur Output:
  output_emis/
  ├── Prov. Jawa Timur/
  │   ├── Kota Surabaya/
  │   │   ├── Kec. Tambaksari.csv
  │   │   ├── ...
  │   │   └── _gabungan_Kota Surabaya.csv
  │   ├── Kab. Malang/
  │   │   ├── Kec. Singosari.csv
  │   │   └── _gabungan_Kab. Malang.csv
  │   └── _gabungan_Prov. Jawa Timur.csv
  ├── ...
  ├── data_sekolah_emis.csv   (gabungan nasional)
  └── _progress.json

Usage:
    python3 scrape_emis.py
    python3 scrape_emis.py --resume
    python3 scrape_emis.py --provinsi "Prov. Jawa Timur"
"""

import requests, json, time, os, sys, csv, argparse, re
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://referensi.data.kemendikdasmen.go.id"
MAX_RETRIES = 5
RETRY_DELAY = 3
REQUEST_DELAY = 0.8
REQUEST_TIMEOUT = 30
OUTPUT_DIR = "output_emis"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "_progress.json")
NATIONAL_CSV = os.path.join(OUTPUT_DIR, "data_sekolah_emis.csv")

# Mappings for Kemenag Shapes
SHAPES = [
    {"id": "34", "name": "RA", "level": "paud"},
    {"id": "9", "name": "MI", "level": "dikdas"},
    {"id": "10", "name": "MTs", "level": "dikdas"},
    {"id": "16", "name": "MA", "level": "dikmen"},
    {"id": "17", "name": "MAK", "level": "dikmen"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

COLS = [
    "nama_sekolah","npsn","bentuk_pendidikan","status_sekolah",
    "kecamatan","kode_kecamatan","kabupaten","kode_kabupaten",
    "provinsi","kode_provinsi","jumlah_guru_ptk","jumlah_pegawai",
    "jumlah_peserta_didik","jumlah_rombel","jumlah_ruang_kelas",
    "jumlah_lab","jumlah_perpustakaan","jumlah_kirim_sinkron",
    "sinkron_terakhir","sekolah_id_enkrip",
]

session = requests.Session()
session.headers.update(HEADERS)

# ── helpers ──────────────────────────────────────────────────
def safe_name(name):
    """Buat nama folder/file aman."""
    return re.sub(r'[<>:"/\\|?*]', '_', name.strip())

def fetch_html(url, label=""):
    for i in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.text
            time.sleep(RETRY_DELAY * i)
        except Exception as e:
            time.sleep(RETRY_DELAY * i)
    print(f"    ❌ GAGAL request HTML: {label}")
    return None

def write_csv(path, rows, mode="w"):
    with open(path, mode, newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if mode == "w":
            w.writeheader()
        w.writerows(rows)

def append_national(rows):
    mode = "a" if os.path.exists(NATIONAL_CSV) else "w"
    with open(NATIONAL_CSV, mode, newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if mode == "w":
            w.writeheader()
        w.writerows(rows)

# ── progress tracker ─────────────────────────────────────────
class Progress:
    def __init__(self):
        self.d = {"done_kec": [], "done_kab": [], "done_prov": [],
                  "total": 0, "started": None}
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE) as f:
                    self.d = json.load(f)
            except Exception as e:
                print(f"Warning: Gagal membaca progress file ({e}), membuat progress baru.")
    def save(self):
        with open(PROGRESS_FILE, "w") as f:
            json.dump(self.d, f)
    def kec_done(self, k): return k in self.d["done_kec"]
    def kab_done(self, k): return k in self.d["done_kab"]
    def prov_done(self, k): return k in self.d["done_prov"]
    def mark_kec(self, k, n):
        if k not in self.d["done_kec"]: self.d["done_kec"].append(k)
        self.d["total"] += n; self.save()
    def mark_kab(self, k):
        if k not in self.d["done_kab"]: self.d["done_kab"].append(k)
        self.save()
    def mark_prov(self, k):
        if k not in self.d["done_prov"]: self.d["done_prov"].append(k)
        self.save()

def fmt_time(s):
    if s < 60: return f"{s:.0f}s"
    if s < 3600: return f"{s//60:.0f}m {s%60:.0f}s"
    return f"{s//3600:.0f}h {(s%3600)//60:.0f}m"

# ── load region mapping ──────────────────────────────────────
def load_regions():
    """Load map wilayah dari JSON cache / CSV lokal, atau fallback ke Dapodik API."""
    regions_json = "/Users/bernaldonapitupulu/.gemini/antigravity-ide/brain/3f42b0fe-3998-45d7-ae99-a6c9176920a2/scratch/regions.json"
    if os.path.exists(regions_json):
        print(f"✅ Memuat struktur wilayah dari cache: {regions_json}")
        with open(regions_json, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to reading Dapodik CSV
    dapodik_csv = "output_indonesia/data_sekolah_indonesia.csv"
    if os.path.exists(dapodik_csv):
        print(f"🔄 Memproses wilayah dari CSV Dapodik: {dapodik_csv}")
        regions = {}
        with open(dapodik_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p_name, p_code = row["provinsi"].strip(), row["kode_provinsi"].strip()
                kb_name, kb_code = row["kabupaten"].strip(), row["kode_kabupaten"].strip()
                kc_name, kc_code = row["kecamatan"].strip(), row["kode_kecamatan"].strip()
                if not p_code or not kb_code or not kc_code:
                    continue
                if p_code not in regions:
                    regions[p_code] = {"name": p_name, "kabs": {}}
                if kb_code not in regions[p_code]["kabs"]:
                    regions[p_code]["kabs"][kb_code] = {"name": kb_name, "kecs": {}}
                regions[p_code]["kabs"][kb_code]["kecs"][kc_code] = kc_name
        return regions

    # Absolute fallback to Dapodik public API
    print("🌐 Mengunduh daftar wilayah dari API Dapodik...")
    regions = {}
    semester_id = "20252"
    prov_url = f"https://dapo.kemendikdasmen.go.id/rekap/dataSekolah?id_level_wilayah=0&kode_wilayah=000000&semester_id={semester_id}"
    try:
        prov_list = session.get(prov_url, timeout=15).json()
        for prov in prov_list:
            p_name, p_code = prov["nama"].strip(), prov["kode_wilayah"].strip()
            print(f"  - Mengambil kabs untuk {p_name}...")
            regions[p_code] = {"name": p_name, "kabs": {}}
            kab_url = f"https://dapo.kemendikdasmen.go.id/rekap/dataSekolah?id_level_wilayah=1&kode_wilayah={p_code}&semester_id={semester_id}"
            kab_list = session.get(kab_url, timeout=15).json()
            for kab in kab_list:
                kb_name, kb_code = kab["nama"].strip(), kab["kode_wilayah"].strip()
                regions[p_code]["kabs"][kb_code] = {"name": kb_name, "kecs": {}}
                kec_url = f"https://dapo.kemendikdasmen.go.id/rekap/dataSekolah?id_level_wilayah=2&kode_wilayah={kb_code}&semester_id={semester_id}"
                kec_list = session.get(kec_url, timeout=15).json()
                for kec in kec_list:
                    kc_name, kc_code = kec["nama"].strip(), kec["kode_wilayah"].strip()
                    regions[p_code]["kabs"][kb_code]["kecs"][kc_code] = kc_name
    except Exception as e:
        print(f"❌ Gagal memuat wilayah: {e}")
        sys.exit(1)
    return regions

# ── scrape leaf page ─────────────────────────────────────────
def scrape_shape(kec_code, shape, info):
    """Scrape satu bentuk pendidikan di satu kecamatan."""
    url = f"{BASE_URL}/pendidikan/{shape['level']}/{kec_code}/3/all/{shape['id']}/all"
    html = fetch_html(url, f"{info['kec_name']} ({shape['name']})")
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'id': 'table1'})
    if not table:
        return []

    schools = []
    rows = table.find_all('tr')
    for tr in rows:
        tds = [td.get_text(strip=True) for td in tr.find_all('td')]
        if len(tds) >= 6:
            schools.append({
                "nama_sekolah": tds[2].upper(),
                "npsn": tds[1],
                "bentuk_pendidikan": shape["name"],
                "status_sekolah": tds[5].upper(),
                "kecamatan": info["kec_name"],
                "kode_kecamatan": kec_code,
                "kabupaten": info["kab_name"],
                "kode_kabupaten": info["kab_code"],
                "provinsi": info["prov_name"],
                "kode_provinsi": info["prov_code"],
                # Kolom kosong / 0 agar kompatibel dengan schema Dapodik
                "jumlah_guru_ptk": 0,
                "jumlah_pegawai": 0,
                "jumlah_peserta_didik": 0,
                "jumlah_rombel": 0,
                "jumlah_ruang_kelas": 0,
                "jumlah_lab": 0,
                "jumlah_perpustakaan": 0,
                "jumlah_kirim_sinkron": 0,
                "sinkron_terakhir": "",
                "sekolah_id_enkrip": ""
            })
    return schools

# ── main ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--provinsi", type=str)
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    p = Progress()

    print("=" * 70)
    print("  🕌 SCRAPER DATA MADRASAH NASIONAL (EMIS/REFERENSI)")
    print(f"  🏫 Jenjang: {', '.join([x['name'] for x in SHAPES])}")
    print("=" * 70)

    if args.resume and p.d["started"]:
        print(f"\n🔄 Resume: {len(p.d['done_prov'])} prov, "
              f"{len(p.d['done_kab'])} kab, {len(p.d['done_kec'])} kec, "
              f"{p.d['total']:,} madrasah")
    else:
        p.d["started"] = datetime.now().isoformat()
        p.d["done_kec"] = []
        p.d["done_kab"] = []
        p.d["done_prov"] = []
        p.d["total"] = 0
        p.save()
        # Reset national CSV
        if os.path.exists(NATIONAL_CSV):
            os.remove(NATIONAL_CSV)

    regions_map = load_regions()
    t0 = time.time()

    prov_list = list(regions_map.items())
    if args.provinsi:
        prov_list = [x for x in prov_list if x[1]["name"] == args.provinsi]
        if not prov_list:
            print(f"❌ Provinsi '{args.provinsi}' tidak ditemukan!")
            sys.exit(1)

    print(f"✅ {len(prov_list)} provinsi siap diproses\n")

    for ip, (prov_code, prov_data) in enumerate(prov_list, 1):
        prov_name = prov_data["name"]

        if p.prov_done(prov_code):
            print(f"[{ip}/{len(prov_list)}] ⏭️  {prov_name}")
            continue

        print(f"\n{'='*70}")
        print(f"[{ip}/{len(prov_list)}] 🗺️  {prov_name}")
        print(f"{'='*70}")

        prov_dir = os.path.join(OUTPUT_DIR, safe_name(prov_name))
        os.makedirs(prov_dir, exist_ok=True)
        prov_schools = []

        kab_list = list(prov_data["kabs"].items())
        print(f"  📊 {len(kab_list)} kabupaten/kota")
        prov_failed = False

        for ik, (kab_code, kab_data) in enumerate(kab_list, 1):
            kab_name = kab_data["name"]

            if p.kab_done(kab_code):
                kab_csv = os.path.join(prov_dir, safe_name(kab_name),
                                       f"_gabungan_{safe_name(kab_name)}.csv")
                if os.path.exists(kab_csv):
                    with open(kab_csv, "r", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        prov_schools.extend(list(reader))
                continue

            print(f"\n  [{ik}/{len(kab_list)}] 📍 {kab_name}")
            kab_dir = os.path.join(prov_dir, safe_name(kab_name))
            os.makedirs(kab_dir, exist_ok=True)
            kab_schools = []

            kec_list = list(kab_data["kecs"].items())
            print(f"    📊 {len(kec_list)} kecamatan")
            kab_failed = False

            for ikec, (kec_code, kec_name) in enumerate(kec_list, 1):

                if p.kec_done(kec_code):
                    # Baca dari file kecamatan yang sudah ada
                    kec_csv = os.path.join(kab_dir, f"{safe_name(kec_name)}.csv")
                    if os.path.exists(kec_csv):
                        with open(kec_csv, "r", encoding="utf-8-sig") as f:
                            kab_schools.extend(list(csv.DictReader(f)))
                    continue

                # Context info untuk threads
                info = {
                    "prov_name": prov_name,
                    "prov_code": prov_code,
                    "kab_name": kab_name,
                    "kab_code": kab_code,
                    "kec_name": kec_name
                }

                # Ambil 5 bentuk pendidikan secara paralel
                kec_schools = []
                failed = False
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {
                        executor.submit(scrape_shape, kec_code, shape, info): shape
                        for shape in SHAPES
                    }
                    for future in as_completed(futures):
                        shape = futures[future]
                        try:
                            res = future.result()
                            if res is None:
                                failed = True
                            else:
                                kec_schools.extend(res)
                        except Exception as e:
                            print(f"      ⚠️ Gagal memproses bentuk {shape['name']} untuk kecamatan {kec_name}: {e}")
                            failed = True

                if failed:
                    print(f"    [{ikec}/{len(kec_list)}] ⚠️ SKIP kecamatan {kec_name} karena ada request yang gagal. Akan diulang pada resume berikutnya.")
                    kab_failed = True
                    # Jeda sopan sebelum lanjut
                    time.sleep(REQUEST_DELAY)
                    continue

                # Simpan CSV per kecamatan jika ada data
                if kec_schools:
                    kec_csv = os.path.join(kab_dir, f"{safe_name(kec_name)}.csv")
                    write_csv(kec_csv, kec_schools)
                    kab_schools.extend(kec_schools)
                    append_national(kec_schools)

                p.mark_kec(kec_code, len(kec_schools))

                elapsed = time.time() - t0
                done = len(p.d["done_kec"])
                rate = done / elapsed if elapsed > 0 else 0
                print(f"    [{ikec}/{len(kec_list)}] ✅ {kec_name}: "
                      f"{len(kec_schools)} madrasah | Total: {p.d['total']:,} | "
                      f"{rate:.1f} kec/s")

                # Jeda sopan antar kecamatan
                time.sleep(REQUEST_DELAY)

            # Gabungan per kabupaten
            if kab_schools:
                kab_csv = os.path.join(kab_dir, f"_gabungan_{safe_name(kab_name)}.csv")
                write_csv(kab_csv, kab_schools)
                prov_schools.extend(kab_schools)
                print(f"    💾 Gabungan {kab_name}: {len(kab_schools)} madrasah")

            if not kab_failed:
                p.mark_kab(kab_code)
            else:
                prov_failed = True
                print(f"    ⚠️ Kabupaten {kab_name} tidak ditandai selesai karena ada kecamatan yang gagal.")

        # Gabungan per provinsi
        if prov_schools:
            prov_csv = os.path.join(prov_dir, f"_gabungan_{safe_name(prov_name)}.csv")
            write_csv(prov_csv, prov_schools)
            print(f"\n  💾 Gabungan {prov_name}: {len(prov_schools)} madrasah")

        if not prov_failed:
            p.mark_prov(prov_code)
            print(f"  ✅ {prov_name} selesai!")
        else:
            print(f"  ⚠️ Provinsi {prov_name} tidak ditandai selesai karena ada kabupaten/kecamatan yang gagal.")

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  ✅ SELESAI! | {p.d['total']:,} madrasah | {fmt_time(elapsed)}")
    print(f"  📁 {NATIONAL_CSV}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

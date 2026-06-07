"""
Scraper Data Sekolah SELURUH INDONESIA - DAPO Kemendikdasmen
============================================================
Struktur Output:
  output_indonesia/
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
  ├── data_sekolah_indonesia.csv   (gabungan nasional)
  └── _progress.json

Usage:
    python3 scrape_dapodik.py
    python3 scrape_dapodik.py --resume
    python3 scrape_dapodik.py --provinsi "Prov. Jawa Timur"
"""

import requests, json, time, os, sys, csv, argparse, re
from datetime import datetime

BASE_URL = "https://dapo.kemendikdasmen.go.id"
SEMESTER_ID = "20252"
TARGET_JENJANG = ["SD", "SMP", "SMA", "SMK"]
MAX_RETRIES = 5
RETRY_DELAY = 3
REQUEST_DELAY = 0.8
REQUEST_TIMEOUT = 30
OUTPUT_DIR = "output_indonesia"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "_progress.json")
NATIONAL_CSV = os.path.join(OUTPUT_DIR, "data_sekolah_indonesia.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://dapo.kemendikdasmen.go.id/sp",
    "X-Requested-With": "XMLHttpRequest",
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

def fetch(url, label=""):
    for i in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json() if isinstance(r.json(), list) else []
            time.sleep(RETRY_DELAY * i)
        except:
            time.sleep(RETRY_DELAY * i)
    print(f"    ❌ GAGAL: {label}")
    return None

def clean(s):
    return {
        "nama_sekolah": (s.get("nama") or "").strip(),
        "npsn": s.get("npsn", ""),
        "bentuk_pendidikan": (s.get("bentuk_pendidikan") or "").strip(),
        "status_sekolah": (s.get("status_sekolah") or "").strip(),
        "kecamatan": (s.get("induk_kecamatan") or "").strip(),
        "kode_kecamatan": (s.get("kode_wilayah_induk_kecamatan") or "").strip(),
        "kabupaten": (s.get("induk_kabupaten") or "").strip(),
        "kode_kabupaten": (s.get("kode_wilayah_induk_kabupaten") or "").strip(),
        "provinsi": (s.get("induk_provinsi") or "").strip(),
        "kode_provinsi": (s.get("kode_wilayah_induk_provinsi") or "").strip(),
        "jumlah_guru_ptk": s.get("ptk", 0),
        "jumlah_pegawai": s.get("pegawai", 0),
        "jumlah_peserta_didik": s.get("pd", 0),
        "jumlah_rombel": s.get("rombel", 0),
        "jumlah_ruang_kelas": s.get("jml_rk", 0),
        "jumlah_lab": s.get("jml_lab", 0),
        "jumlah_perpustakaan": s.get("jml_perpus", 0),
        "jumlah_kirim_sinkron": s.get("jumlah_kirim", 0),
        "sinkron_terakhir": s.get("sinkron_terakhir") or "",
        "sekolah_id_enkrip": (s.get("sekolah_id_enkrip") or "").strip(),
    }

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
            with open(PROGRESS_FILE) as f:
                self.d = json.load(f)
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

# ── main ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--provinsi", type=str)
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    p = Progress()

    print("=" * 70)
    print("  📚 SCRAPER DATA SEKOLAH SELURUH INDONESIA")
    print(f"  🏫 Jenjang: {', '.join(TARGET_JENJANG)} | Semester: {SEMESTER_ID}")
    print("=" * 70)

    if args.resume and p.d["started"]:
        print(f"\n🔄 Resume: {len(p.d['done_prov'])} prov, "
              f"{len(p.d['done_kab'])} kab, {len(p.d['done_kec'])} kec, "
              f"{p.d['total']:,} sekolah")
    else:
        p.d["started"] = datetime.now().isoformat()
        p.save()
        # Reset national CSV
        if os.path.exists(NATIONAL_CSV):
            os.remove(NATIONAL_CSV)

    # 1. Daftar provinsi
    print("\n📍 Mengambil daftar provinsi...")
    prov_list = fetch(f"{BASE_URL}/rekap/dataSekolah?id_level_wilayah=0"
                      f"&kode_wilayah=000000&semester_id={SEMESTER_ID}", "provinsi")
    if not prov_list:
        print("❌ Gagal!"); sys.exit(1)

    if args.provinsi:
        prov_list = [x for x in prov_list if x.get("nama","").strip() == args.provinsi]
        if not prov_list:
            print(f"❌ Provinsi '{args.provinsi}' tidak ditemukan!"); sys.exit(1)

    print(f"✅ {len(prov_list)} provinsi\n")
    t0 = time.time()

    for ip, prov in enumerate(prov_list, 1):
        prov_nama = prov["nama"].strip()
        prov_kode = prov["kode_wilayah"].strip()

        if p.prov_done(prov_kode):
            print(f"[{ip}/{len(prov_list)}] ⏭️  {prov_nama}")
            continue

        print(f"\n{'='*70}")
        print(f"[{ip}/{len(prov_list)}] 🗺️  {prov_nama}")
        print(f"{'='*70}")

        prov_dir = os.path.join(OUTPUT_DIR, safe_name(prov_nama))
        os.makedirs(prov_dir, exist_ok=True)
        prov_schools = []

        time.sleep(REQUEST_DELAY)
        kab_list = fetch(f"{BASE_URL}/rekap/dataSekolah?id_level_wilayah=1"
                         f"&kode_wilayah={prov_kode}&semester_id={SEMESTER_ID}",
                         f"kab {prov_nama}")
        if not kab_list:
            p.mark_prov(prov_kode); continue

        print(f"  📊 {len(kab_list)} kabupaten/kota")

        for ik, kab in enumerate(kab_list, 1):
            kab_nama = kab["nama"].strip()
            kab_kode = kab["kode_wilayah"].strip()

            if p.kab_done(kab_kode):
                # Masih perlu baca CSV untuk gabungan provinsi
                kab_csv = os.path.join(prov_dir, safe_name(kab_nama),
                                       f"_gabungan_{safe_name(kab_nama)}.csv")
                if os.path.exists(kab_csv):
                    with open(kab_csv, "r", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        prov_schools.extend(list(reader))
                continue

            print(f"\n  [{ik}/{len(kab_list)}] 📍 {kab_nama}")

            kab_dir = os.path.join(prov_dir, safe_name(kab_nama))
            os.makedirs(kab_dir, exist_ok=True)
            kab_schools = []

            time.sleep(REQUEST_DELAY)
            kec_list = fetch(f"{BASE_URL}/rekap/dataSekolah?id_level_wilayah=2"
                             f"&kode_wilayah={kab_kode}&semester_id={SEMESTER_ID}",
                             f"kec {kab_nama}")
            if not kec_list:
                p.mark_kab(kab_kode); continue

            print(f"    📊 {len(kec_list)} kecamatan")

            for ikec, kec in enumerate(kec_list, 1):
                kec_nama = kec["nama"].strip()
                kec_kode = kec["kode_wilayah"].strip()

                if p.kec_done(kec_kode):
                    # Baca dari file kecamatan yang sudah ada
                    kec_csv = os.path.join(kab_dir, f"{safe_name(kec_nama)}.csv")
                    if os.path.exists(kec_csv):
                        with open(kec_csv, "r", encoding="utf-8-sig") as f:
                            kab_schools.extend(list(csv.DictReader(f)))
                    continue

                time.sleep(REQUEST_DELAY)
                raw = fetch(f"{BASE_URL}/rekap/progresSP?id_level_wilayah=3"
                            f"&kode_wilayah={kec_kode}&semester_id={SEMESTER_ID}"
                            f"&bentuk_pendidikan_id=", f"sekolah {kec_nama}")

                if raw is None:
                    print(f"    [{ikec}/{len(kec_list)}] ❌ {kec_nama}")
                    continue

                schools = [clean(s) for s in raw
                           if (s.get("bentuk_pendidikan") or "").strip() in TARGET_JENJANG]

                # Simpan CSV per kecamatan
                if schools:
                    kec_csv = os.path.join(kab_dir, f"{safe_name(kec_nama)}.csv")
                    write_csv(kec_csv, schools)
                    kab_schools.extend(schools)
                    append_national(schools)

                p.mark_kec(kec_kode, len(schools))

                elapsed = time.time() - t0
                done = len(p.d["done_kec"])
                rate = done / elapsed if elapsed > 0 else 0
                print(f"    [{ikec}/{len(kec_list)}] ✅ {kec_nama}: "
                      f"{len(schools)} | Total: {p.d['total']:,} | "
                      f"{rate:.1f} kec/s")

            # Gabungan per kabupaten
            if kab_schools:
                kab_csv = os.path.join(kab_dir, f"_gabungan_{safe_name(kab_nama)}.csv")
                write_csv(kab_csv, kab_schools)
                prov_schools.extend(kab_schools)
                print(f"    💾 Gabungan {kab_nama}: {len(kab_schools)} sekolah")

            p.mark_kab(kab_kode)

        # Gabungan per provinsi
        if prov_schools:
            prov_csv = os.path.join(prov_dir, f"_gabungan_{safe_name(prov_nama)}.csv")
            write_csv(prov_csv, prov_schools)
            print(f"\n  💾 Gabungan {prov_nama}: {len(prov_schools)} sekolah")

        p.mark_prov(prov_kode)
        print(f"  ✅ {prov_nama} selesai!")

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  ✅ SELESAI! | {p.d['total']:,} sekolah | {fmt_time(elapsed)}")
    print(f"  📁 {NATIONAL_CSV}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

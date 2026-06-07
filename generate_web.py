"""
Generate halaman web interaktif berbasis API lokal dari data sekolah JSON/CSV.
Jalankan: python3 generate_web.py
Lalu buka: http://localhost:8000
"""
import os
import json
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse, parse_qs
import pandas as pd

CSV_PATH = "output_indonesia/data_sekolah_indonesia.csv"
HTML_DIR = "output_indonesia"

if not os.path.exists(CSV_PATH):
    print(f"❌ File {CSV_PATH} tidak ditemukan.")
    print("Pastikan Anda sudah menjalankan scrape_dapodik.py terlebih dahulu.")
    exit(1)

print("⏳ Memuat data nasional (mungkin butuh waktu beberapa detik)...")
# Menggunakan pandas untuk memuat data agar pencarian lebih cepat
df = pd.read_csv(CSV_PATH, dtype=str).fillna("")

# Precompute mapping wilayah untuk dropdown
print("🗺️  Membangun struktur hierarki wilayah...")
wilayah_dict = {}
for prov, kab, kec in df[['provinsi', 'kabupaten', 'kecamatan']].drop_duplicates().values:
    if prov not in wilayah_dict:
        wilayah_dict[prov] = {}
    if kab not in wilayah_dict[prov]:
        wilayah_dict[prov][kab] = []
    if kec not in wilayah_dict[prov][kab]:
        wilayah_dict[prov][kab].append(kec)

# Mengurutkan array agar rapi di UI
for prov in wilayah_dict:
    for kab in wilayah_dict[prov]:
        wilayah_dict[prov][kab] = sorted(wilayah_dict[prov][kab])

wilayah_json = json.dumps(wilayah_dict)

class APIServer(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        # Endpoint API: Daftar Wilayah
        if parsed.path == "/api/wilayah":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(wilayah_json.encode('utf-8'))
            return
            
        # Endpoint API: Filter Data Sekolah
        elif parsed.path == "/api/sekolah":
            qs = parse_qs(parsed.query)
            prov = qs.get("provinsi", [""])[0]
            kab = qs.get("kabupaten", [""])[0]
            kec = qs.get("kecamatan", [""])[0]
            
            filtered_df = df
            if prov:
                filtered_df = filtered_df[filtered_df['provinsi'] == prov]
            if kab:
                filtered_df = filtered_df[filtered_df['kabupaten'] == kab]
            if kec:
                filtered_df = filtered_df[filtered_df['kecamatan'] == kec]
            
            # Ubah tipe data kolom agar bisa dijumlahkan di frontend jika diperlukan
            numeric_cols = ['jumlah_peserta_didik', 'jumlah_guru_ptk', 'jumlah_rombel', 'jumlah_ruang_kelas', 'jumlah_lab', 'jumlah_perpustakaan']
            for col in numeric_cols:
                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)
            
            # Jika tidak ada filter yang dipilih, jangan kembalikan semua 450k data (browser bisa crash)
            # Batasi hingga 5000 baris pertama
            is_limited = False
            if len(filtered_df) > 5000:
                res_df = filtered_df.head(5000)
                is_limited = True
            else:
                res_df = filtered_df
                
            response = {
                "count": len(filtered_df),
                "limited": is_limited,
                "data": res_df.to_dict('records')
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
            
        # Jika route lain, biarkan SimpleHTTPRequestHandler menghandle (seperti memuat index.html)
        else:
            if parsed.path == "/":
                self.path = "/index.html"
            return super().do_GET()

# Pindah ke directory html output
os.makedirs(HTML_DIR, exist_ok=True)
os.chdir(HTML_DIR)
PORT = 8000

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), APIServer) as httpd:
    url = f"http://localhost:{PORT}"
    print(f"\n🌐 Server berjalan di: {url}")
    print("   Tekan Ctrl+C untuk stop\n")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server dihentikan")

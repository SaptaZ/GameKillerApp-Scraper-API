from fastapi import FastAPI, HTTPException, Query
import httpx
from bs4 import BeautifulSoup
import uvicorn
import os
from urllib.parse import unquote, urlparse, parse_qs
from contextlib import asynccontextmanager
import asyncio
import re
import json

# Setup Async Client
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    # Timeout di-disable agar tidak error saat koneksi lambat atau proses proxy lama
    client = httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True, timeout=None)
    yield
    await client.aclose()

app = FastAPI(title="GameKillerApp Scraper", lifespan=lifespan)

BASE_DOMAIN = "https://gamekillerapp.com"

def unwrap_google_url(url: str) -> str:
    """Membersihkan URL dari wrapper Google Translate."""
    if not url: return ""
    clean = unquote(url)
    
    # Decode jika URL terbungkus format /website?u=...
    if "google" in clean and "/website" in clean and "u=" in clean:
        try:
            parsed = urlparse(clean)
            qs = parse_qs(parsed.query)
            if 'u' in qs:
                return unwrap_google_url(qs['u'][0])
        except:
            pass

    # Bersihkan domain translate
    clean = clean.replace("gamekillerapp-com.translate.goog", "gamekillerapp.com")
    
    # Hapus parameter google translate
    clean = clean.split("?_x_tr_")[0]
    clean = clean.split("&_x_tr_")[0]
    
    # Handle relative URL
    if clean.startswith("/"):
        clean = BASE_DOMAIN + clean
        
    return clean

async def fetch_until_success(url: str, validator_func) -> BeautifulSoup:
    """
    Core Logic: Terus melakukan request ke URL sampai validator_func mengembalikan True.
    """
    current_url = url 
    
    while True:
        try:
            res = await client.get(current_url)
            
            # Jika terkena limit (429) dan sedang menggunakan proxy translate, switch ke direct
            if res.status_code == 429 and "translate.goog" in current_url:
                current_url = unwrap_google_url(current_url)
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            # Cek validasi konten
            if validator_func(soup):
                return soup
            
        except Exception:
            pass
        # Retry logic implicit

async def extract_links_from_nuxt_data(soup: BeautifulSoup) -> list:
    """
    Ekstrak link download dari script JSON Nuxt (__NUXT_DATA__).
    LOGIKA BARU: Filter path '/download/' untuk membedakan file game dan video iklan.
    """
    links = []
    try:
        # Mengambil script data Nuxt
        script = soup.select_one('script#__NUXT_DATA__')
        if script:
            try:
                data = json.loads(script.string)
            except:
                data = []

            # Data Nuxt 3 berbentuk array flat. Kita iterasi semua item.
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        # --- FILTER KETAT ---
                        # 1. Harus link HTTP/HTTPS
                        # 2. Harus domain 'gamercdn.top' atau 'willcheat'
                        # 3. WAJIB mengandung path '/download/'
                        if "http" in item and ("gamercdn.top" in item or "cfdownload.willcheat.com" in item) and "/download/" in item:
                            links.append(item)
    except Exception as e:
        print(f"Error extracting Nuxt data: {e}")
    
    # Hapus duplikat dan return
    return list(set(links))

async def get_final_download_links(download_page_url: str) -> list:
    """
    Masuk ke halaman download intermediate (/download).
    Mengambil link dari JSON data Nuxt.
    """
    # Convert ke Proxy URL
    target_url = download_page_url.replace("https://gamekillerapp.com", "https://gamekillerapp-com.translate.goog")
    if "?" not in target_url:
        target_url += "?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"
    else:
        target_url += "&_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"

    def is_valid_download_page(soup):
        has_nuxt = bool(soup.select_one('script#__NUXT_DATA__'))
        has_box = bool(soup.select_one('.download-btn-box'))
        return has_nuxt or has_box

    soup = await fetch_until_success(target_url, is_valid_download_page)
    
    # Ekstrak dari Data Nuxt menggunakan logika path /download/
    final_links = await extract_links_from_nuxt_data(soup)
    
    return final_links

async def process_item_fully(name, detail_url, image, initial_size):
    """
    Memproses satu item app secara lengkap.
    """
    while True:
        try:
            # Convert ke Proxy URL untuk halaman detail
            target_detail_url = detail_url.replace("https://gamekillerapp.com", "https://gamekillerapp-com.translate.goog")
            if "?" not in target_detail_url:
                target_detail_url += "?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"
            else:
                target_detail_url += "&_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"

            # 1. Fetch Halaman Detail
            def detail_page_valid(s):
                return bool(s.select('a.apk-download-btn'))
            
            app_soup = await fetch_until_success(target_detail_url, detail_page_valid)

            # 2. Cari link menuju halaman download intermediate
            download_page_btn = app_soup.select_one('a.apk-download-btn')
            
            if not download_page_btn:
                return None 

            intermediate_url = unwrap_google_url(download_page_btn.get('href'))
            
            # 3. Masuk ke halaman intermediate dan ambil link final dari JSON
            final_data_list = await get_final_download_links(intermediate_url)
            
            return {
                "name": name,
                "link": unwrap_google_url(detail_url), 
                "image": image,
                "download": ", ".join(final_data_list) if final_data_list else "Not Found",
                "size": initial_size 
            }
            
        except Exception:
            break
        
    return None

@app.get("/")
async def root():
    return {
        "message": "Search API for GameKillerApp.com by Bowo",
        "example_usage": "/search?query=minecraft&limit=5"
    }

@app.get("/search")
async def search_apps(
    query: str = Query(..., description="App name"),
    limit: int = Query(5, description="Limit results (will fetch multiple pages if needed)")
):
    tasks = []
    page = 1
    
    # Validator Search Page
    def search_page_valid(s):
        has_items = bool(s.select('.column-games-item'))
        text_content = s.get_text()
        no_result = "no results" in text_content.lower() or "nothing found" in text_content.lower()
        is_search_page = bool(s.select('.column-title'))
        return has_items or no_result or is_search_page

    while len(tasks) < limit:
        # Construct URL Proxy dengan pagination
        # Page 1: /search/{query}
        # Page N: /search/{query}/page/{N}
        if page == 1:
            path = f"/search/{query}"
        else:
            path = f"/search/{query}/page/{page}"
            
        search_url = f"https://gamekillerapp-com.translate.goog{path}?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"
        
        # print(f"Scraping Page {page}...") # Debugging purposes
        
        soup = await fetch_until_success(search_url, search_page_valid)
        
        # 1. Ambil items
        items = soup.select('.column-games-item')
        
        # Jika tidak ada item di halaman ini, berarti halaman habis -> STOP
        if not items:
            break

        for item in items:
            # Jika limit sudah tercapai di tengah loop, berhenti
            if len(tasks) >= limit:
                break

            # Nama
            title_el = item.select_one('.column-games-item-info-name')
            if not title_el: continue
            name = title_el.get_text(strip=True)
            
            # Link Detail
            detail_link = unwrap_google_url(item.get('href'))
            
            # Gambar
            img_el = item.select_one('.column-games-item-icon')
            image = ""
            if img_el:
                image = unwrap_google_url(img_el.get('src') or img_el.get('data-src') or "")
            
            # Size & Version
            meta_el = item.select_one('.column-games-item-info-version')
            size_text = "Unknown"
            if meta_el:
                full_text = meta_el.get_text(strip=True)
                if "+" in full_text:
                    parts = full_text.split("+")
                    if len(parts) > 1:
                        size_text = parts[1].strip()
                else:
                    size_text = full_text

            tasks.append(process_item_fully(name, detail_link, image, size_text))
        
        # Lanjut ke halaman berikutnya
        page += 1

    # Jalankan semua task yang terkumpul secara parallel
    raw_results = await asyncio.gather(*tasks)
    results = [res for res in raw_results if res is not None]

    return {
        "success": True,
        "query": query,
        "limit": limit,
        "count": len(results),
        "results": results
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
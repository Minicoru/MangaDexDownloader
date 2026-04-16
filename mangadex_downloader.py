import argparse
import os
import re
import sys
import time
import requests

API_BASE = "https://api.mangadex.org"

def sanitize_filename(name: str) -> str:
    """Sanitize the directory/file name by removing illegal characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def extract_manga_id(url: str) -> str:
    """Extracts the manga UUID from a MangaDex URL."""
    match = re.search(r'/title/([a-f0-9-]+)', url)
    if match:
        return match.group(1)
    
    # Also handle straight ID being passed in
    if re.match(r'^[a-f0-9-]+$', url):
        return url
        
    return None

def get_manga_info(manga_id: str):
    """Fetches metadata about the manga."""
    resp = requests.get(f"{API_BASE}/manga/{manga_id}")
    resp.raise_for_status()
    data = resp.json()['data']
    
    title_data = data['attributes']['title']
    title = title_data.get('en') or list(title_data.values())[0]
    return title

def get_chapters(manga_id: str):
    """Fetches all English chapters for a given manga, handling pagination."""
    chapters = []
    limit = 500
    offset = 0
    
    while True:
        params = {
            "translatedLanguage[]": "en",
            "order[chapter]": "asc",
            "limit": limit,
            "offset": offset,
            "includes[]": ["scanlation_group"]
        }
        resp = requests.get(f"{API_BASE}/manga/{manga_id}/feed", params=params)
        resp.raise_for_status()
        data = resp.json()
        
        feed = data.get('data', [])
        chapters.extend(feed)
        
        total = data.get('total', 0)
        offset += limit
        
        if offset >= total:
            break
            
        time.sleep(0.5) # Be nice to the API
        
    # Deduplicate chapters based on chapter number
    unique_chapters = {}
    for ch in chapters:
        ch_num = ch['attributes']['chapter']
        key = ch_num if ch_num is not None else ch['id']
        if key not in unique_chapters:
            unique_chapters[key] = ch
            
    # Return sorted list (by chapter number where possible)
    def sort_key(ch):
        num = ch['attributes']['chapter']
        try:
            return float(num) if num else -1
        except ValueError:
            return -1
            
    sorted_chapters = sorted(unique_chapters.values(), key=sort_key)
    return sorted_chapters

def get_chapter_pages(chapter_id: str):
    """Gets the image URLs for a specific chapter."""
    resp = requests.get(f"{API_BASE}/at-home/server/{chapter_id}")
    resp.raise_for_status()
    data = resp.json()
    
    base_url = data['baseUrl']
    hash_val = data['chapter']['hash']
    pages = data['chapter']['data']
    
    page_urls = [f"{base_url}/data/{hash_val}/{page}" for page in pages]
    return page_urls

def download_image(url: str, filepath: str):
    """Downloads an image from a URL to a specified filepath."""
    if os.path.exists(filepath):
        return # Skip if already downloaded
        
    # Use a generic user-agent, MangaDex network servers are generally okay with standard requests
    headers = {"User-Agent": "MangaDexDownloader/1.0"}
    
    # Retry mechanism for robust downloading
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=10)
            resp.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return
        except requests.exceptions.RequestException as e:
            if attempt == 2:
                print(f"\nFailed to download {url}: {e}")
            else:
                time.sleep(2) # Wait before retry

def main():
    parser = argparse.ArgumentParser(description="Download manga from MangaDex.")
    parser.add_argument("url", help="MangaDex URL or Manga ID")
    parser.add_argument("--chapters", type=int, default=None, help="Number of chapters to download (default: all)")
    args = parser.parse_args()

    manga_id = extract_manga_id(args.url)
    if not manga_id:
        print("Error: Invalid MangaDex URL or ID.")
        sys.exit(1)
        
    print(f"Extracting Manga ID: {manga_id}")
    
    try:
        title = get_manga_info(manga_id)
        safe_title = sanitize_filename(title)
        print(f"Manga Title: {title}")
        
        # Create manga directory
        os.makedirs(safe_title, exist_ok=True)
        
        print("Fetching chapter list...")
        chapters = get_chapters(manga_id)
        print(f"Found {len(chapters)} unique English chapters.")
        
        # Limit chapters if specified
        if args.chapters is not None:
            chapters = chapters[:args.chapters]
            print(f"Limiting to the first {args.chapters} chapters.")
        
        if chapters:
            for ch in chapters:
                ch_num = ch['attributes']['chapter']
                ch_title = ch['attributes']['title'] or ''
                ch_id = ch['id']
                
                # Format chapter folder name
                folder_name = f"Chapter {ch_num}" if ch_num else "Oneshot"
                if ch_title:
                    safe_ch_title = sanitize_filename(ch_title)
                    folder_name += f" - {safe_ch_title}"
                    
                ch_dir = os.path.join(safe_title, folder_name)
                os.makedirs(ch_dir, exist_ok=True)
                
                print(f"Downloading {folder_name}...")
                
                try:
                    pages = get_chapter_pages(ch_id)
                    total_pages = len(pages)
                    
                    for i, page_url in enumerate(pages):
                        # Use 3 digits for page number to keep them sorted (e.g., 001.jpg)
                        page_ext = page_url.split('.')[-1]
                        if len(page_ext) > 4 or not page_ext.isalnum():
                            page_ext = "jpg" # fallback
                            
                        page_filename = f"{i+1:03d}.{page_ext}"
                        page_filepath = os.path.join(ch_dir, page_filename)
                        
                        sys.stdout.write(f"\r  Page {i+1}/{total_pages}")
                        sys.stdout.flush()
                        
                        download_image(page_url, page_filepath)
                        
                    print() # New line after chapter finishes
                except requests.exceptions.RequestException as e:
                    print(f"\n  Error fetching pages for chapter {ch_num}: {e}")
                
                time.sleep(1) # Be nice between chapters
                
        print("\nDownload complete!")
                
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to MangaDex API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

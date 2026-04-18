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
    """Fetches metadata about the manga, including title and available languages."""
    resp = requests.get(f"{API_BASE}/manga/{manga_id}")
    resp.raise_for_status()
    data = resp.json()['data']
    
    title_data = data['attributes']['title']
    title = title_data.get('en') or list(title_data.values())[0]

    languages = data['attributes'].get('availableTranslatedLanguages', ['en'])
    # Sometimes availableTranslatedLanguages can contain None, filter it out
    languages = [lang for lang in languages if lang is not None]

    return title, languages

def get_chapters(manga_id: str, language: str = "en"):
    """Fetches all chapters for a given manga in a specific language, handling pagination."""
    chapters = []
    limit = 500
    offset = 0
    
    while True:
        params = {
            "translatedLanguage[]": language,
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

def download_chapter(ch, safe_title, show_progress=True):
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

    if show_progress:
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

            if show_progress:
                sys.stdout.write(f"\r  Page {i+1}/{total_pages}")
                sys.stdout.flush()

            download_image(page_url, page_filepath)

        if show_progress:
            print() # New line after chapter finishes
        else:
            print(f"Finished {folder_name}")
    except requests.exceptions.RequestException as e:
        print(f"\n  Error fetching pages for chapter {ch_num}: {e}")

    time.sleep(1) # Be nice between chapters

import concurrent.futures

def main():
    parser = argparse.ArgumentParser(description="Download manga from MangaDex.")
    parser.add_argument("url", nargs="?", help="MangaDex URL or Manga ID")
    parser.add_argument("-f", "--file", help="Text file containing multiple MangaDex URLs or IDs (one per line)")
    parser.add_argument("-p", "--parallel", type=int, default=1, help="Number of concurrent chapter downloads (default: 1)")
    parser.add_argument("--chapters", type=int, default=None, help="Number of chapters to download (default: all)")
    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        try:
            with open(args.file, "r") as f:
                urls.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            sys.exit(1)

    if not urls:
        print("Error: Please provide a MangaDex URL/ID or a file containing URLs/IDs.")
        parser.print_help()
        sys.exit(1)

    for url in urls:
        manga_id = extract_manga_id(url)
        if not manga_id:
            print(f"Error: Invalid MangaDex URL or ID: {url}")
            continue
        
        print(f"\n--- Extracting Manga ID: {manga_id} ---")
    
        try:
            title, languages = get_manga_info(manga_id)
            safe_title = sanitize_filename(title)
            print(f"Manga Title: {title}")

            # Present languages and prompt
            if not languages:
                print("No translated languages found for this manga.")
                continue
                
            print("Available languages:")
            for i, lang in enumerate(languages):
                print(f"{i+1}. {lang}")
                
            selected_lang = None
            while selected_lang is None:
                try:
                    choice = input(f"Select a language (1-{len(languages)}) [default: 1]: ").strip()
                    if not choice:
                        selected_lang = languages[0]
                    else:
                        idx = int(choice) - 1
                        if 0 <= idx < len(languages):
                            selected_lang = languages[idx]
                        else:
                            print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    
            print(f"Selected language: {selected_lang}")

            # Create manga directory
            os.makedirs(safe_title, exist_ok=True)

            print(f"Fetching chapter list for language '{selected_lang}'...")
            chapters = get_chapters(manga_id, selected_lang)
            print(f"Found {len(chapters)} unique chapters.")

            # Limit chapters if specified
            if args.chapters is not None:
                chapters = chapters[:args.chapters]
                print(f"Limiting to the first {args.chapters} chapters.")

            if chapters:
                show_progress = (args.parallel == 1)
                if args.parallel > 1:
                    print(f"Starting download of {len(chapters)} chapters in parallel ({args.parallel} workers)...")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
                        futures = [executor.submit(download_chapter, ch, safe_title, show_progress) for ch in chapters]
                        concurrent.futures.wait(futures)
                else:
                    for ch in chapters:
                        download_chapter(ch, safe_title, show_progress)

            print("\nDownload complete!")

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to MangaDex API: {e}")
            # continue with next url instead of exiting
            continue

if __name__ == "__main__":
    main()

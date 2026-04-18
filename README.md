# MangaDex Downloader

A simple Python application to download manga chapters directly from MangaDex. It features interactive translated language selection, parallel chapter downloading to maximize speed, and supports downloading multiple mangas sequentially from a text file of URLs. It handles pagination, deduplicates chapters from different scanlation groups, and downloads the pages organized by chapter.

## Installation

1. Ensure you have Python 3 installed.
2. Install the script globally as a terminal command using `pip`:

```bash
pip install .
```

This will make the `mangadex-dl` command available in your terminal across your operating system.

*(Alternatively, you can just install the dependencies using `pip install -r requirements.txt` and run `python3 mangadex_downloader.py` manually).*

## Usage

Run the script by providing a MangaDex URL or a Manga ID. When a manga is selected, the application will detect all available translated languages and prompt you to choose one before starting the download.

```bash
mangadex-dl <url_or_id>
```

**Example:**
```bash
mangadex-dl https://mangadex.org/title/801513ba-a712-498c-8f57-cae55b38cc92/berserk
```

### Options

You can customize the download behavior with several flags:

```bash
# Download the first 5 chapters only
mangadex-dl <url> --chapters 5

# Download multiple chapters concurrently (e.g. 4 at a time) for much faster speeds
mangadex-dl <url> --parallel 4

# Provide a text file containing multiple MangaDex URLs (one per line) to batch download
mangadex-dl --file my_urls.txt
```

## Output

The script will create a directory named after the manga title in your current working directory. Inside, it will create subdirectories for each chapter and save the images sequentially inside them.

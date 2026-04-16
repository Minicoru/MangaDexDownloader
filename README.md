# MangaDex Downloader

A simple Python application to download manga chapters directly from MangaDex. It fetches English chapters, handles pagination, deduplicates chapters from different scanlation groups, and downloads the pages organized by chapter.

## Installation

1. Ensure you have Python 3 installed.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script by providing a MangaDex URL or a Manga ID.

```bash
python3 mangadex_downloader.py <url_or_id>
```

**Example:**
```bash
python3 mangadex_downloader.py https://mangadex.org/title/801513ba-a712-498c-8f57-cae55b38cc92/berserk
```

### Options

You can limit the number of chapters to download using the `--chapters` flag:

```bash
# Only download the first 5 chapters
python3 mangadex_downloader.py https://mangadex.org/title/801513ba-a712-498c-8f57-cae55b38cc92/berserk --chapters 5
```

## Output

The script will create a directory named after the manga title in your current working directory. Inside, it will create subdirectories for each chapter and save the images sequentially inside them.

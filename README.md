# GameKillerApp Scraper API

A high-performance, asynchronous REST API built with FastAPI that scrapes game and application data from `gamekillerapp.com`. This tool provides a programmatic interface to search for applications, retrieve metadata, and extract direct download links, including those hidden behind dynamic Nuxt.js hydration scripts.

## Table of Contents

* [Features](#features)
* [Technical Architecture](#technical-architecture)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Usage](#usage)
* [API Documentation](#api-documentation)
* [Legal Disclaimer](#legal-disclaimer)
* [License](#license)

## Features

* **Asynchronous Execution**: Utilizes `asyncio` and `httpx` for concurrent page fetching, allowing for rapid search results across multiple pagination levels.
* **Proxy Bypass Mechanism**: Implements a creative routing strategy via Google Translate (`translate.goog`) to bypass regional restrictions and basic IP-based rate limiting.
* **Dynamic Data Extraction**: Capable of parsing `__NUXT_DATA__` JSON blobs to extract download links that are not present in the initial static HTML.
* **Resilient Polling**: Includes a `fetch_until_success` validator that ensures complete page loads before attempting data extraction.

## Technical Architecture

This scraper employs several advanced techniques to ensure reliability and data accessibility:

### 1. Google Translate as a Proxy Layer

To mitigate direct IP blocking and handle potential geo-restrictions, all outgoing requests are routed through Google Translate's infrastructure. The application dynamically rewrites target URLs to the `gamekillerapp-com.translate.goog` domain. The scraper includes an `unwrap_google_url` utility to decode the resulting redirected URLs back to their original form.

### 2. Nuxt.js Hydration Parsing

Modern web applications often load data dynamically using JavaScript frameworks. This scraper detects when standard HTML parsing fails to find download buttons. It then parses the `script#__NUXT_DATA__` tag—a JSON object used by Nuxt.js for client-side hydration. The script filters this JSON specifically for known content delivery networks (e.g., `download.gamercdn.top`, `cfdownload.willcheat.com`) to locate the final download links.

### 3. Recursive Link Resolution

The scraping process follows a multi-step resolution path:

1. **Search Page**: Extracts basic metadata (Title, Icon, Version).
2. **Detail Page**: Locates the intermediate download button.
3. **Intermediate Page**: Resolves the final direct download link from the Nuxt data structure.

## Prerequisites

* Python 3.8 or higher
* pip (Python Package Manager)

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/SaptaZ/GameKillerApp-Scraper-API.git
   cd gamekillerapp-scraper-api
   ```

2. **Create a Virtual Environment (Recommended)**

   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**

   Create a `requirements.txt` file with the following content, or install directly:

   ```bash
   pip install fastapi uvicorn httpx beautifulsoup4
   ```

## Usage

### Starting the Server

Run the application using Uvicorn:

```bash
python main.py
```

*Alternatively, you can run uvicorn directly:*

```bash
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

The server will start at `http://0.0.0.0:7860`.

## API Documentation

### Health Check

**GET** `/`

Returns the API status and usage examples.

### Search Applications

**GET** `/search`

Searches for applications and retrieves their details, including resolved download links.

**Parameters:**

| Parameter | Type    | Required | Description                                       |
| --------- | ------- | -------- | ------------------------------------------------- |
| `query`   | string  | Yes      | The name of the game or app to search for.        |
| `limit`   | integer | No       | Maximum number of results to return (default: 5). |

**Response Example:**

```json
{
  "success": true,
  "query": "minecraft",
  "limit": 1,
  "count": 1,
  "results": [
    {
      "name": "Minecraft Trial",
      "link": "https://gamekillerapp.com/games/minecraft-trial",
      "image": "https://images.gamekillerapp.com/images/171420860444152kB.webp",
      "download": "https://download.gamercdn.top/download/minecraft-trial-v1.20.80.05-MOD1-gamekillerapp.com.apk",
      "size": "323.19MB"
    }
  ]
}
```

### Example Request

```bash
curl "http://localhost:7860/search?query=minecraft&limit=5"
```

## Legal Disclaimer

This tool is developed strictly for **educational purposes** to demonstrate techniques in web scraping, asynchronous programming, and handling dynamic JavaScript content.

* The developer of this repository is not affiliated with GameKillerApp.
* Users are responsible for ensuring their usage complies with the Terms of Service of the target website.
* Do not use this tool for mass scraping that may degrade the performance of the target server.

## License

Distributed under the MIT License. See `LICENSE` for more information.
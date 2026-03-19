"""Handles fetching HTML contents from websites Supports both static and dynamic content"""

import requests
from playwright.sync_api import sync_playwright
from typing import Optional


# Minimum HTML length threshold for validation
MIN_HTML_LENGTH = 500


def fetch_with_requests(url: str) -> Optional[str]:
    """
    Fetch HTML from a URL using the requests library.
    
    Args:
        url: The URL to fetch
        
    Returns:
        HTML text if successful, None otherwise
    """
    print(f"Trying requests for: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        # Validate response
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            return None
            
        if not response.text or len(response.text) < MIN_HTML_LENGTH:
            print("Error: Response is empty or too small")
            return None
        
        return response.text
        
    except requests.exceptions.Timeout:
        print("Error: Request timed out (10 seconds)")
        return None
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to the URL")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        return None


def fetch_with_playwright(url: str) -> Optional[str]:
    """
    Fetch HTML from a URL using Playwright with JavaScript rendering support.
    
    Args:
        url: The URL to fetch
        
    Returns:
        Rendered HTML text if successful, None otherwise
    """
    print(f"Trying Playwright for: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ...
        finally:
            browser.close()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, timeout=10000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)  # wait 2 seconds
            
            html = page.content()
            
            if not html or len(html) < MIN_HTML_LENGTH:
                print("Error: Response is empty or too small")
                return None
            
            page.close()
            browser.close()
            return html
            
    except Exception as e:
        print(f"Error: Playwright failed - {str(e)}")
        if browser:
            browser.close()
        return None


def fetch_html(url: str) -> Optional[str]:
    """
    Fetch HTML from a URL with fallback mechanism.
    
    Attempts to fetch HTML using requests first. If that fails, falls back
    to Playwright for JavaScript-heavy websites.
    
    Args:
        url: The URL to fetch
        
    Returns:
        HTML text if successful, None otherwise
    """
    # Validate URL
    if not url.startswith("http"):
        print("Invalid URL. Please include http/https")
        return None
    # Try requests first (faster)
    html = fetch_with_requests(url)
    if html:
        print("Fetched using requests")
        return html
    
    # Fallback to Playwright for JS-heavy sites
    print("Requests failed, trying Playwright...")
    html = fetch_with_playwright(url)
    if html:
        print("Fetched using Playwright")
        return html
    
    print("Error: Failed to fetch content from both methods")
    return None


if __name__ == "__main__":
    try:
        url = input("Enter the URL to fetch: ").strip()
        
        if not url:
            print("Error: URL cannot be empty")
        else:
            html = fetch_html(url)
            
            if html:
                print(f"\n{'='*60}")
                print("First 500 characters of fetched HTML:")
                print(f"{'='*60}")
                print(html[:500])
            else:
                print("Failed to fetch content")
                
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")

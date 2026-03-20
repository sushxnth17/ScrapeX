"""Extracts clean readable content from raw HTML.

This module provides multiple methods to extract clean, readable content
from HTML pages, with fallback mechanisms to ensure content extraction
even if primary methods fail.
"""

from typing import Optional, Dict
import trafilatura
import re
from bs4 import BeautifulSoup


# Minimum text length threshold for valid content
MIN_TEXT_LENGTH = 200


def extract_with_trafilatura(html: str) -> Optional[Dict[str, str]]:
    """
    Extract content using trafilatura library.
    
    Trafilatura is specialized for extracting main article/content text from
    web pages with high accuracy.
    
    Args:
        html: Raw HTML string from a web page
        
    Returns:
        Dictionary with 'title' and 'text' keys if successful, None otherwise.
        Returns None if extraction fails, text is empty, or text is < 200 chars.
        
    Example:
        >>> result = extract_with_trafilatura(html)
        >>> if result:
        ...     print(result['title'])
        ...     print(result['text'][:100])
    """
    
    try:
        # Extract metadata (includes title)
        metadata = trafilatura.extract_metadata(html)
        
        # Extract main content text
        text = trafilatura.extract(html)
        
        if not text:
            return None
        text = re.sub(r'\[\d+\]', '', text or "")  # remove [1], [2], etc. references
        text = ' '.join(text.split())  # normalize whitespace

        # Validate extraction
        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            return None
        
        # Get title, fallback to empty string if not available
        title = metadata.title if metadata and metadata.title else "Untitled"
        
        return {
            "title": title,
            "text": text.strip()
        }
        
    except Exception as e:
        print(f"Trafilatura extraction error: {str(e)}")
        return None


def extract_basic(html: str) -> Optional[Dict[str, str]]:
    """
    Extract content using BeautifulSoup (basic parsing).
    
    This is a fallback method that extracts title and paragraph text
    using simple HTML parsing.
    
    Args:
        html: Raw HTML string from a web page
        
    Returns:
        Dictionary with 'title' and 'text' keys if successful, None otherwise.
        Returns None if no meaningful content is found.
        
    Example:
        >>> result = extract_basic(html)
        >>> if result:
        ...     print(result['title'])
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else "Untitled"
        
        # Extract all paragraph text
        paragraphs = soup.find_all('p')
        text_blocks = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
        text = ' '.join(text_blocks)

        if not paragraphs:
            return None
        
        # Combine all paragraphs into single text
        text = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        # Validate text
        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            return None
        
        return {
            "title": title,
            "text": text.strip()
        }
        
    except Exception as e:
        print(f"Basic extraction error: {str(e)}")
        return None


def extract_content(html: str) -> Optional[Dict[str, str]]:
    """
    Main extraction function with fallback mechanism.
    
    Attempts to extract content using trafilatura first. If that fails,
    falls back to basic BeautifulSoup extraction. Returns None if both fail.
    
    Args:
        html: Raw HTML string from a web page
        
    Returns:
        Dictionary with 'title' and 'text' keys if successful, None otherwise.
        
    Extraction Process:
        1. Try trafilatura (high accuracy, handles complex layouts)
        2. Fallback to BeautifulSoup basic parsing
        3. Return None if both methods fail
    """
    # Try trafilatura first (more powerful)
    result = extract_with_trafilatura(html)
    if result:
        print("Content extracted using trafilatura")
        return result
    
    # Fallback to basic extraction
    print("Trafilatura failed, using basic extraction...")
    result = extract_basic(html)
    if result:
        print("Content extracted using BeautifulSoup")
        return result
    
    # Both methods failed
    print("Failed to extract meaningful content")
    return None


if __name__ == "__main__":
    """Test block: Fetch and extract content from a URL"""
    try:
        from fetcher import fetch_html
        
        # Get URL from user
        url = input("Enter the URL to extract content from: ").strip()
        
        if not url:
            print("Error: URL cannot be empty")
        else:
            # Fetch HTML
            print("\nFetching HTML...")
            html = fetch_html(url)
            
            if not html:
                print("Failed to fetch HTML content")
            else:
                # Extract content
                print("\nExtracting content...")
                result = extract_content(html)
                
                if result:
                    print(f"\n{'='*60}")
                    print(f"Title: {result['title']}")
                    print(f"{'='*60}")
                    print("Content (first 500 characters):")
                    print(f"{result['text'][:500]}...")
                    print(f"{'='*60}")
                    print(f"Total text length: {len(result['text'])} characters")
                else:
                    print("Failed to extract meaningful content from the page")
                    
    except ImportError:
        print("Error: Could not import fetch_html from fetcher")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
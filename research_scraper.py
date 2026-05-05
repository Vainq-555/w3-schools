import httpx
from bs4 import BeautifulSoup
import sys

def research():
    url = "https://www.w3schools.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"Fetching {url}...")
        response = httpx.get(url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the sidebar or top navigation categories
        print("\n--- Potential Tutorial Categories ---")
        # W3Schools typically has links like /html/, /css/, /js/, etc.
        nav_links = soup.find_all('a', href=True)
        categories = []
        for link in nav_links:
            href = link['href']
            # Filter for tutorial-like paths
            if href.startswith('/') and href.endswith('/') and len(href) > 2:
                text = link.text.strip()
                if text and text not in [c['text'] for c in categories]:
                    categories.append({'text': text, 'href': href})
                    print(f"- {text}: {href}")
        
        # Check a specific tutorial (HTML) for sub-navigation
        html_url = "https://www.w3schools.com/html/default.asp"
        print(f"\nFetching {html_url} to check lesson list...")
        response = httpx.get(html_url, headers=headers, follow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Usually, left navigation is in a div with id="leftmenuinnerinner"
        left_menu = soup.find('div', id="leftmenuinnerinner")
        if left_menu:
            print("\n--- Sub-lessons for HTML ---")
            lessons = left_menu.find_all('a', target="_top")
            for i, lesson in enumerate(lessons[:10]):
                print(f"  {i+1}. {lesson.text.strip()} -> {lesson['href']}")
        else:
            print("\nCould not find left menu for HTML.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    research()

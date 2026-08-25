import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import ssl
import re

def fetch_oem_news_rss(oem_name):
    query = f'"{oem_name}" new products OR offerings OR services OR launch'
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-us&gl=US&ceid=US:en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    articles = []
    try:
        req = urllib.request.Request(rss_url, headers=headers)
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=8, context=context) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:5]:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')
            
            title_text = title.text if title is not None else ""
            link_url = link.text if link is not None else ""
            pub_date_text = pub_date.text if pub_date is not None else ""
            source_text = source.text if source is not None else ""
            
            description = item.find('description')
            snippet_text = ""
            if description is not None and description.text:
                clean_desc = re.sub(r'<[^>]+>', '', description.text)
                snippet_text = clean_desc[:250].strip()
                
            clean_title = title_text
            if " - " in title_text:
                parts = title_text.rsplit(" - ", 1)
                if len(parts) > 1:
                    clean_title = parts[0].strip()
                    
            if title_text and link_url:
                articles.append({
                    "oem_name": oem_name,
                    "title": clean_title,
                    "link": link_url,
                    "pub_date": pub_date_text,
                    "source": source_text,
                    "snippet": snippet_text
                })
    except Exception as e:
        print(f"Error fetching news for {oem_name}: {e}")
        
    return articles

if __name__ == '__main__':
    res = fetch_oem_news_rss("Cisco")
    print(f"Fetched {len(res)} articles.")
    for a in res[:2]:
        print(f"Title: {a['title']}")
        print(f"Link: {a['link']}")
        print(f"Source: {a['source']}")
        print(f"PubDate: {a['pub_date']}")
        print(f"Snippet: {a['snippet']}\n")

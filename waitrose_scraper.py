import re
import requests

def get_product_page_link(product_name: str, product_id: str) -> str:
    BASE_URL = "https://www.waitrose.com/ecom/products"
    normalized_string = product_name.lower().strip()
    slug = re.sub(r'[-_\s]+', '-', normalized_string)
    return f"{BASE_URL}/{slug}/{product_id}"

def run_waitrose_scraper():
    pass

if __name__ == '__main__':
    run_waitrose_scraper()
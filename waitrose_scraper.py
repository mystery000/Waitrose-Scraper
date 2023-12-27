import re
import os
import csv
import math
import json
import logging
import requests
from tqdm import tqdm
from typing import List
import multiprocessing as mp
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver import Remote
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection

class ProductScraper:
    _sbr_connection: ChromiumRemoteConnection
    _products: List[any]
    
    def __init__(self, products: List[any], sbr_connection: ChromiumRemoteConnection) -> None:
        self._products = products
        self._sbr_connection = sbr_connection
        
    def get_product_page_link(self, product_name: str, product_id: str) -> str:
        BASE_URL = "https://www.waitrose.com/ecom/products"
        normalized_string = product_name.lower().replace("&", "").strip()
        slug = re.sub(r'[-_\s]+', '-', normalized_string)
        return f"{BASE_URL}/{slug}/{product_id}"

    def scrape_products(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--start-maximized")
        for product in self._products:
            try:
                with Remote(self._sbr_connection, options=chrome_options) as driver:
                    product_url = self.get_product_page_link(product["name"], product["id"])
                    
                    driver.get(product_url)
                    
                    html = driver.page_source
                    
                    page = BeautifulSoup(html, "html5lib")
                    
                    with open("waitrose_products.csv", 'a', newline='') as csv_file:
                        fieldnames = [
                            'source',
                            'title', 
                            'description',
                            'item_price',
                            'unit_price',
                            'average_rating',
                            'review_count',
                            'categories',
                            'tags',
                            'nutrition',
                            'product_url',
                            'image_url',
                            'size',
                            'last_updated' 
                        ]
                        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    
                        if csv_file.tell() == 0:
                            writer.writeheader()
                            
                        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        source = "Waitrose"
                        title = product["name"]
                        
                        prd_section = page.find('section', id="productDescription")
                        description = prd_section.get_text(strip=True) if prd_section else None
                        
                        if description is None:
                            summary_section = page.find('section', id="summary")
                            description = summary_section.get_text(strip=True) if summary_section else ''
                        
                        if description is None:
                            marketing_section_element = page.find('section', id="marketingDescription")
                            description = marketing_section_element.get_text(strip=True) if marketing_section_element else ''
                        
                        item_price = product["displayPrice"]
                        unit_price = product["displayPriceQualifier"]
                        average_rating = product["reviews"]["averageRating"]
                        review_count = product["reviews"]["reviewCount"]
                        categories = ','.join([category["name"] for category in product["categories"]])
                        tags = ','.join([tag["name"] for tag in product["productTags"]] if product["productTags"] else [])
                        product_url = product_url
                        image_url = product["productImageUrls"]["large"]
                        size = product["size"]
                        
                        nutritions = { "values": [] }
                        
                        try:
                            nutrition_element = page.find("div", class_="nutrition___VCHp1")
                            nutrition_titles = [child.get_text(strip=True) for child in nutrition_element.thead.tr.children]
                            nutrition_rows = nutrition_element.table.tbody.find_all("tr")

                            for _id, nutrition_title in enumerate(nutrition_titles):
                              
                              if _id == 0 : continue

                              nutrition = { "unit" : nutrition_title }

                              for row in nutrition_rows:
                                if 'class' not in row.th.attrs: 
                                  nutrition_cells = list(row.children)
                                  nutrition[nutrition_cells[0].get_text(strip=True)] = nutrition_cells[_id].get_text(strip=True)

                              nutritions["values"].append(nutrition)
                        except:
                            nutritions = { "values": [] }
                        
                        logging.info({
                            'source': source,
                            'title': title, 
                            'description': description,
                            'item_price': item_price,
                            'unit_price': unit_price,
                            'average_rating': average_rating,
                            'review_count': review_count,
                            'categories': categories,
                            'tags': tags,
                            'nutrition': nutritions,
                            'product_url': product_url,
                            'image_url': image_url,
                            'size': size,
                            'last_updated': now 
                        })
                    
                        writer.writerow({
                            'source': source,
                            'title': title, 
                            'description': description,
                            'item_price': item_price,
                            'unit_price': unit_price,
                            'average_rating': average_rating,
                            'review_count': review_count,
                            'categories': categories,
                            'tags': tags,
                            'nutrition': nutritions,
                            'product_url': product_url,
                            'image_url': image_url,
                            'size': size,
                            'last_updated': now 
                        })
                    
            except Exception as e:
                logging.info(f"Exception: {str(e)}")
                
    
def run_waitrose_scraper():
    logging.info("Waitrose scraper running...")
    
    csv_file_name = "waitrose_products.csv"
    if os.path.exists(csv_file_name):
        os.remove(csv_file_name)
            
    # Get the total count of Waitrose products
    url = "https://www.waitrose.com/api/graphql-prod/graph/live"
    payload = {
        "query": "fragment ProductFragment on Product {\n  availableDays\n  barCodes\n  conflicts {\n    lineNumber\n    messages\n    nextSlotDate\n    outOfStock\n    priority\n    productId\n    prohibitedActions\n    resolutionActions\n    slotOptionDates {\n      type\n      date\n    }\n  }\n  containsAlcohol\n  lineNumber\n  images {\n    extraLarge\n    large\n    medium\n    small\n  }\n  id\n  productType\n  size\n  brand\n  thumbnail\n  name\n  leadTime\n  reviews {\n    averageRating\n    total\n  }\n  customerProductDetails {\n    customerFavourite\n    customerPyo\n  }\n  currentSaleUnitPrice {\n    quantity {\n      amount\n      uom\n    }\n    price {\n      amount\n      currencyCode\n    }\n  }\n  defaultQuantity {\n    amount\n    uom\n  }\n  depositCharge {\n    amount\n    currencyCode\n  }\n  pricing {\n    displayPrice\n    displayUOMPrice\n    displayPriceQualifier\n    displayPriceEstimated\n    formattedPriceRange\n    currentSaleUnitRetailPrice {\n      price {\n        amount\n        currencyCode\n      }\n      quantity {\n        amount\n        uom\n      }\n    }\n    promotions {\n      groups {\n        threshold\n        name\n        lineNumbers\n      }\n      promotionDescription\n      promotionExpiryDate\n      promotionId\n      pyoPromotion\n      myWaitrosePromotion\n      wasDisplayPrice\n      promotionType\n    }\n  }\n  persistDefault\n  markedForDelete\n  substitutionsProhibited\n  displayPrice\n  displayPriceEstimated\n  displayPriceQualifier\n  leadTime\n  productShelfLife\n  maxPersonalisedMessageLength\n  summary\n  supplierOrder\n  restriction {\n    availableDates {\n      restrictionId\n      startDate\n      endDate\n      cutOffDate\n    }\n  }\n  weights {\n    pricePerUomQualifier\n    defaultQuantity {\n      amount\n      uom\n    }\n    servings {\n      min\n      max\n    }\n    sizeDescription\n    uoms\n    formattedWeightRange\n  }\n  categories {\n    id\n    name\n    urlName\n  }\n  productTags {\n    name\n  }\n  marketingBadges {\n    name\n  }\n}\nfragment ProductPod on Product {\n              adTechSponsoredPosition,\n              brand,\n              categories {\n                  name,\n                  urlName,\n                  id\n              },\n              cqResponsive {\n                deviceBreakpoints {\n                  name\n                  visible\n                  width\n                }\n              },\n              currentSaleUnitPrice {\n                price {\n                  amount\n                  currencyCode\n                }\n                quantity {\n                  amount\n                  uom\n                }\n              },\n              customerProductDetails {\n                customerInTrolleyQuantity {\n                  amount\n                  uom\n                }\n                customerPyo\n              },\n              defaultQuantity {\n                  uom\n              },\n              depositCharge {\n                amount,\n                currencyCode\n              },\n              displayPrice,\n              displayPriceEstimated,\n              displayPriceQualifier,\n              formattedWeightRange,\n              formattedPriceRange,\n              id,\n              leadTime,\n              lineNumber\n              maxPersonalisedMessageLength,\n              name,\n              markedForDelete,\n              persistDefault,\n              productImageUrls {\n                  extraLarge,\n                  large,\n                  medium,\n                  small\n              }\n              productType,\n              promotion {\n                groups {\n                  threshold\n                  name\n                  lineNumbers\n                }\n                myWaitrosePromotion\n                promotionDescription\n                promotionId\n                promotionTypeCode\n                wasDisplayPrice\n              },\n              promotions {\n                groups {\n                  threshold\n                  name\n                  lineNumbers\n                }\n                myWaitrosePromotion\n                promotionDescription\n                promotionId\n                promotionTypeCode\n                wasDisplayPrice\n              },\n              restriction {\n                  availableDates {\n                      restrictionId,\n                      startDate,\n                      endDate,\n                      cutOffDate\n                  },\n              },\n              resultType,\n              reviews {\n                averageRating\n                reviewCount\n              },\n              size,\n              sponsored,\n              sponsorshipId,\n              substitutionsProhibited,\n              thumbnail\n              typicalWeight {\n                amount\n                uom\n              }\n              servings {\n                min\n                max\n              }\n              weights {\n                  uoms ,\n                  pricePerUomQualifier,\n                  perUomQualifier,\n                  defaultQuantity {\n                      amount,\n                      uom\n                  },\n                  servings {\n                      max,\n                      min\n                  },\n                  sizeDescription\n              },\n              productTags {\n                name\n              },\n              marketingBadges {\n                name\n              },\n            }query(\n  $customerId: String!\n  $withRecommendations: Boolean!\n  $size: Int\n  $start: Int\n  $category: String\n  $filterTags: [filterTag]\n  $recommendationsSize: Int\n  $recommendationsStart: Int\n  $sortBy: String\n  $trolleyId: String\n  $withFallback: Boolean\n) {\n  getProductListPage(\n    category: $category\n    customerId: $customerId\n    filterTags: $filterTags\n    recommendationsSize: $recommendationsSize\n    recommendationsStart: $recommendationsStart\n    size: $size\n    start: $start\n    sortBy: $sortBy\n    trolleyId: $trolleyId\n    withFallback: $withFallback\n  ) {\n  productGridData {\n      failures{\n          field\n          message\n          type\n      }\n      componentsAndProducts {\n        __typename\n        ... on GridProduct {\n          searchProduct {\n            ...ProductPod\n          }\n        }\n        ... on GridCmsComponent {\n          aemComponent\n        }\n        ... on GridSponsoredBannerComponent {\n          sponsoredBanner\n        }\n      }\n      conflicts {\n        messages\n        outOfStock\n        priority\n        productId\n        prohibitedActions\n        resolutionActions\n        nextSlotDate\n    }\n      criteria {\n        alternative\n        sortBy\n        filters {\n          group\n          filters {\n            applied\n            filterTag {\n              count\n              group\n              id\n              text\n              value\n            }\n          }\n        }\n        searchTags {\n          group\n          text\n          value\n        }\n        suggestedSearchTags {\n          group\n          text\n          value\n        }\n      }\n      locations {\n        header\n        masthead\n        seoContent\n      }\n      metaData {\n        description\n        title\n        keywords\n        turnOffIndexing\n        pageTitle\n        canonicalTag\n      }\n      productsInResultset\n      relevancyWeightings\n      searchTime\n      showPageTitle\n      subCategories {\n        name\n        categoryId\n        expectedResults\n        hiddenInNav\n      }\n      totalMatches\n      totalTime\n    }\n    recommendedProducts @include(if: $withRecommendations) {\n      failures{\n        field\n        message\n        type\n      }\n      fallbackRecommendations\n      products {\n        ...ProductFragment\n        metadata {\n          recToken\n          monetateId\n        }\n      }\n      totalResults\n    }\n  }\n}\n",
        "variables": {
            "start": 0,
            "size": 4,
            "sortBy": "MOST_POPULAR",
            "trolleyId": "0",
            "recommendationsSize": 0,
            "withRecommendations": False,
            "withFallback": True,
            "category": "10051",
            "customerId": "-1",
            "filterTags": []
        }
    }
    response = requests.post(url,json=payload, headers={"Authorization": "Bearer unauthenticated"})
    content = json.loads(response.content)
    totalMatches = content["data"]["getProductListPage"]["productGridData"]["totalMatches"]
    
    start: int = 0
    size: int = 80
    request_count = math.ceil(totalMatches / size)
    
    products = []
    
    for _ in tqdm(range(request_count)):
        response = requests.post(url,json={**payload, "variables": {**payload["variables"], "start": start, "size": size}}, headers={"Authorization": "Bearer unauthenticated"})
        content = json.loads(response.content)
        start += size
        page_products = content["data"]["getProductListPage"]["productGridData"]["componentsAndProducts"]
        for product in page_products:
            if product["__typename"] == "GridProduct":
                products.append(product["searchProduct"])
        
    process_count = 6
    unit = math.ceil(len(products) / process_count)
    
    try:
        SELENIUM_GRID_IP_ADDRESSES = [
            "18.169.27.82:9515",
            "13.42.66.41:9515",
            "18.171.169.136:9515"
        ]
        
        sbr_connections = [ChromiumRemoteConnection(f"http://{IP}", "goog", "chrome") for IP in SELENIUM_GRID_IP_ADDRESSES]
        
        processes = [
            mp.Process(target=ProductScraper(products[unit * i :], sbr_connections[i % len(SELENIUM_GRID_IP_ADDRESSES)]).scrape_products)
            if i == (process_count - 1) else 
            mp.Process(target=ProductScraper(products[unit * i : unit * (i + 1)], sbr_connections[i % len(SELENIUM_GRID_IP_ADDRESSES)]).scrape_products)
            for i in range(process_count)
        ]

        for process in processes:
            process.start()
        for process in processes:
            process.join()

        logging.info("Waitrose scraper finished")
        
    except Exception as e:
        logging.info(f"Exception: {str(e)}")

if __name__ == '__main__':
    run_waitrose_scraper()
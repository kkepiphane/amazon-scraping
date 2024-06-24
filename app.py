import csv
import time
import random
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime

_amazon_urls = [
    'https://www.amazon.fr/gp/bestsellers/books/302004/ref=zg_bs_nav_books_1',
    'https://www.amazon.fr/gp/bestsellers/books/355635011/ref=zg_bs_nav_books_1',
    'https://www.amazon.fr/gp/bestsellers/books/301137/ref=zg_bs_nav_books_1'
]

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/602.3.12 (KHTML, like Gecko) Version/10.0.3 Safari/602.3.12',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:55.0) Gecko/20100101 Firefox/55.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
]

def get_random_user_agent():
    return random.choice(user_agents)

def random_delay(min_delay=3, max_delay=10):
    time.sleep(random.randint(min_delay, max_delay))

def lazy_loading(driver, count=20):
    element = driver.find_element(By.TAG_NAME, 'body')
    for _ in range(count):
        element.send_keys(Keys.PAGE_DOWN)
        random_delay()

def _parse_categories_data(driver, category_urls):
    category_with_products = []
    for url_link in category_urls:
        category = url_link.split('/')[-2]  # Extract category from URL
        current_url = url_link
        while True:
            driver.get(current_url)
            lazy_loading(driver)  # Simulate scrolling for lazy loading
            
            # Using Selenium to get page source after lazy loading
            response = driver.page_source
            soup = BeautifulSoup(response, "html.parser")
            all_product_divs = soup.find_all("div", {"id": "gridItemRoot"})
            _parse_product(category_with_products, category, all_product_divs)
            
            if len([p for p in category_with_products if p['Category'] == category]) >= 100:
                break
            
            next_page = soup.find("li", {"class": "a-last"})
            if next_page and next_page.find("a"):
                current_url = f"https://www.amazon.fr{next_page.find('a')['href']}"
                random_delay()
            else:
                break

    return category_with_products

def _parse_product(category_with_products, category, all_product_divs):
    for count, div in enumerate(all_product_divs, start=len([p for p in category_with_products if p['Category'] == category]) + 1):
        if len([p for p in category_with_products if p['Category'] == category]) >= 100:
            break
        
        product_name_tag = (
            div.find("div", {"class": "_cDEzb_p13n-sc-css-line-clamp-1_1Fn1y"}) or
            div.find("div", {"class": "_cDEzb_p13n-sc-css-line-clamp-3_g3dy1"}) or
            div.find("span", {"id": "productTitle"}) or
            div.find("span", {"class": "p13n-sc-truncate-desktop-type2 p13n-sc-truncated"})
        )
        product_name = product_name_tag.get_text().strip() if product_name_tag else 'Missing'
        
        product_price_tag = (
            div.find("span", {"class": "p13n-sc-price"}) or
            div.find("span", {"class": "a-price-whole"}) or
            div.find("span", {"class": "a-size-base a-color-price"})
        )
        product_price = product_price_tag.get_text().strip() if product_price_tag else 'Missing'

        rating_row = div.find("div", {"class": "a-icon-row"})
        if rating_row:
            product_rating = rating_row.find("span", {"class": "a-icon-alt"})
            users_count = rating_row.find("span", {"class": "a-size-small"})
        else:
            product_rating = div.find("span", {"class": "a-icon-alt"})
            users_count = div.find("span", {"class": "a-size-small"})

        product_rating = product_rating.get_text().strip()[:3] if product_rating else 'None'
        users_count = users_count.get_text().replace(",", ".").strip() if users_count else 'None'
        
        try:
            float(users_count)
        except ValueError:
            users_count = 'None'

        product_img = div.find("img")
        product_img = product_img['src'] if product_img and product_img.has_attr('src') else 'Missing'

        product_link = div.find("a", {"class": "a-link-normal"})
        if product_link and product_link.has_attr('href'):
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_link['href'])
            product_asin = asin_match.group(1) if asin_match else 'Missing'
            product_url = f"https://www.amazon.fr{product_link['href']}"
        else:
            product_asin = 'Missing'
            product_url = 'Missing'

        category_with_products.append(
            {
                "No": count,
                "ASIN": product_asin,
                "Name": product_name,
                "Price": product_price,
                "Rating": product_rating,
                "Count of Users Rated": users_count,
                "Image": product_img,
                "URL": product_url,
                "Category": category
            }
        )

def _create_best_sellers_csv(category_with_products, csv_file, csv_columns):
    try:
        with open(csv_file, 'w', newline="", encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            _write_data_to_csv(category_with_products, writer)
    except IOError as error_io:
        print(f"I/O error: {error_io}")

def _write_data_to_csv(category_with_products, writer):
    for product in category_with_products:
        writer.writerow(product)

if __name__ == "__main__":
    start_time = time.time()

    driver_options = webdriver.ChromeOptions()
    driver_options.add_argument("--headless")  # Pour exécuter Chrome en mode sans tête
    driver_options.add_argument(f"user-agent={get_random_user_agent()}")  # Utilisez un agent utilisateur aléatoire

    driver = webdriver.Chrome(options=driver_options)  # Initialisez le pilote Chrome avec les options spécifiées
    
    try:
        category_with_products = _parse_categories_data(driver, _amazon_urls)

        current_date_time = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        csv_file = f"amazon_best_sellers_{current_date_time}.csv"
        csv_columns = ["No", "ASIN", "Name", "Price", "Rating", "Count of Users Rated", "Image", "URL", "Category"]

        _create_best_sellers_csv(category_with_products, csv_file, csv_columns)
    finally:
        driver.quit()
   
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time} seconds")

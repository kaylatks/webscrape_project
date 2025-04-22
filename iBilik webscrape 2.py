import json
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import traceback
import os
from openpyxl import load_workbook
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import cloudscraper
import random

# Get the directory where the script is located
script_directory = os.getcwd()
scraper = cloudscraper.create_scraper()
def request_page(url, retries=3, delay=random.uniform(1,3)):
    """
    Attempts to request the page and parse it. Retries on failure.

    Args:
    - url: The URL to fetch.
    - retries: Number of retries on failure (default is 3).
    - delay: Delay between retries in seconds (default is 2).

    Returns:
    - BeautifulSoup object if successful, None if failed after retries.
    """
    
    attempt = 0
    while attempt < retries:
        response = scraper.get(url)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the page content with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        else:
            # If request fails, print error message and retry
            print(f"Attempt {attempt + 1} failed. Status code: {response.status_code}")
            attempt += 1
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)  # Wait for a specified delay before retrying
    
    # If all attempts fail, return None
    print(f"Failed to retrieve the page after multiple attempts.{url}")
    return None

# Set up Chrome options
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


# site = 'https://www.ibilik.my/rooms/brickfields'

search_content = ['Kuala Lumpur','Selangor']
room_types = ['Master Room','Middle Room','Single Room', 'Soho','Studio','Suite']

for location in search_content:
    for room_type in room_types:
        
        # service = Service(ChromeDriverManager().install())

        # # Initialize WebDriver
        # driver = webdriver.Chrome(service=service,options=chrome_options)

        site = f"https://www.ibilik.my/rooms/{location}?location_search_name={location}&room_preferences%5B0%5D=&room_types%5B0%5D={room_type}"
        # print(site)
        # # Navigate to the target website
        # driver.get(site)

        # # Get the page source
        # html = driver.page_source

        # soup = BeautifulSoup(html, 'html.parser')

        # driver.quit()

        soup = request_page(site)

        meta_tag = soup.find('meta', {'name': 'search_results_num'})
        results_num = meta_tag.get('content')
        housecount = int(results_num)
        max_page = housecount // 20 + (housecount % 20 > 0)
        # Initialize an empty list to store data
        data = []
        ## DEBUG
        if location == 'Kuala Lumpur' and room_type == 'Master Room':
            number = 1
        else:
            number = 1

        for page in range(number, max_page+1):
            # if page>10:
            #     continue
            # Initialize WebDriver
            # driver = webdriver.Chrome(service=service,options=chrome_options)
            page_url = f'{site}&page={page}'
           
            # driver.get(page_url)

            # pagination = WebDriverWait(driver, 20).until(
            #     EC.presence_of_element_located((By.ID, "colophon"))
            # )

            # Get the page source
            # html = driver.page_source
            # title = driver.title
            # print(f'{title} of {max_page}, {room_type}')
            # driver.quit()
            # soup = BeautifulSoup(html, 'html.parser')
            soup = request_page(page_url)
            title = soup.title.string if soup.title else "No title found"
            

            listings = soup.find_all('div', class_='home-list-pop')
            
            # Loop through listings and extract the desired data
            for listing in listings:
                try:
                    # Extract title, rental price, publish date, and views
                    title = listing.find('a').get('title')
                    rental = listing.find('div', class_='room_price').span.text.strip()
                    publish_date = listing.find('i').text.strip()
                    views = (el := listing.find('span', class_='home-list-pop-rat')) and el.text.strip() or None

                    if datetime.strptime(publish_date.split(": ")[1], "%d/%m/%Y").date() < datetime.now().date() - timedelta(days=9):
                        break_page_loop = True
                        break
                    else:
                        break_page_loop = False
                    # Extract all <p> tags for location, room type, etc.
                    # p_tags = listing.find_all('p')
                    # details = [p.text.strip() for p in p_tags]
                    # locations = (el := listing.find_all('i', class_='fas fa-map-marker-alt').find_parent('p')) and el.text.strip() or None
                     
                    room_location = next((i_tag.find_parent('p').text.strip() for i_tag in listing.find_all('i', class_='fas fa-map-marker-alt')), None)
                    tenant_info = next((i_tag.find_parent('p').text.strip() for i_tag in listing.find_all('i', class_='fas fa-users')), None)
                    room_type = next((i_tag.find_parent('p').text.strip() for i_tag in listing.find_all('i', class_='fas fa-bed')), None)
                    facility = next((i_tag.find_parent('p').text.strip() for i_tag in listing.find_all('i', class_='far fa-plus-square')), None)

                    # Get the current date and time
                    scrape_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                    # Create a dictionary to store the data for this listing
                    listing_data = {
                        'Title': title,
                        'Rental': rental,
                        'Publish Date': publish_date,
                        'Views': views,
                        'Location': room_location, ## details[0] if len(details) > 0 else None,
                        'Tenant Info': tenant_info, ## details[1] if len(details) == 4 else None,
                        'Room Type':  room_type, ## details[2] if len(details) == 4 else details[1],
                        'Facilities': facility, ## details[3] if len(details) == 4 else details[2],
                        'Scrape Time': scrape_time  # Add the scrape time here
                    }
                    
                    # Append the listing data to the main data list
                    data.append(listing_data)

                except Exception as e:
                    # Print the error message
                    print(f'An error occurred: {e}')
                    # Print the traceback to see where the error occurred
                    print("Traceback details:")
                    traceback.print_exc()  # This prints the full traceback to help identify the line
            if break_page_loop:
                break
            ## Convert the data into a DataFrame
            df = pd.DataFrame(data)
            excel_file = f'ibilik_{datetime.now().date()}.csv'
            # Create a new Excel file with pandas
            final_file_path = os.path.join(script_directory, excel_file)
            if os.path.exists(final_file_path):
                existing_df = pd.read_csv(final_file_path)
                combined_df = pd.concat([existing_df,df],ignore_index=True)
                combined_df.drop_duplicates(inplace=True)
                combined_df.to_csv(final_file_path, mode='w', header=True, index=False)
            else:
                df.to_csv(final_file_path, mode='w', header=True, index=False)
            
            print(f'{title}, total page: {page} of {max_page}, {room_type},{scrape_time}')
            time.sleep(random.uniform(1,3))
        
        # all_data_df = pd.read_csv(final_file_path)
        # all_data_df.drop_duplicates(inplace=True)
        # all_data_df.to_csv(final_file_path, mode='w', header=True, index=False)
        

    # Check if the Excel file exists
    # if not os.path.exists(excel_file):
    #     # If file doesn't exist, create it and write headers
    #     df.to_excel(excel_file, index=False, header=True, sheet_name='ibilik')
    # else:
    #     with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
    #         df.to_excel(writer, index=False, header=False, sheet_name='ibilik')



# Step 3: Define database connection parameters
# Adjust the connection string according to your database
# db_type = 'postgresql'  # Change to your DB type (mysql, sqlite, etc.)
# username = 'postgres'
# password = ']I*tR![N}eIyr{n)0-{j.<d!6:{$'
# host = 'livein-datawarehouse.cfh2nvb7huq1.ap-southeast-1.rds.amazonaws.com'
# port = '5432'  # Default PostgreSQL port
# database = 'livein-dwh'

# # Create the connection string
# connection_string = f"{db_type}://{username}:{password}@{host}:{port}/{database}"

# # Step 4: Create a database engine
# engine = create_engine(connection_string)

# # Step 5: Import DataFrame to the database
# df.to_sql('webscrape_ibilik_data', con=engine, schema='1.raw', if_exists='append', index=False)

# print("Data imported successfully!")

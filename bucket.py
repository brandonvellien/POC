# bucket.py - Final Version
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import time
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=chrome_options)

def upload_file_to_s3(file_name, bucket, object_name=None):
    if object_name is None: object_name = os.path.basename(file_name)
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_name, bucket, object_name)
        logging.info(f"File {file_name} uploaded to s3://{bucket}/{object_name}")
        return True
    except Exception as e:
        logging.error(f"S3 upload failed for {file_name}: {e}")
        return False

def download_image(url, output_path, index):
    try:
        response = requests.get(url, timeout=20, stream=True)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '')
        if 'image/jpeg' in content_type or 'image/jpg' in content_type:
            os.makedirs(output_path, exist_ok=True)
            filename = os.path.join(output_path, f'image_{index}.jpg')
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(8192): f.write(chunk)
            return True, filename
    except Exception as e:
        logging.warning(f"Failed to download {url}: {e}")
    return False, None

def scrape_images(url, local_temp_folder, s3_bucket_name, s3_folder_prefix, delete_local_after_upload=True):
    os.makedirs(local_temp_folder, exist_ok=True)
    driver = setup_driver()
    try:
        driver.get(url)
        time.sleep(5)
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(10): # Scroll 10 times
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height: break
            last_height = new_height
        
        img_elements = driver.find_elements(By.TAG_NAME, 'img')
        logging.info(f"Found {len(img_elements)} image elements.")
        
        for index, img_element in enumerate(img_elements):
            src = img_element.get_attribute('src')
            if src and src.startswith('http'):
                success, local_filename = download_image(src, local_temp_folder, index)
                if success:
                    s3_object_name = f"{s3_folder_prefix}/{os.path.basename(local_filename)}"
                    if upload_file_to_s3(local_filename, s3_bucket_name, s3_object_name):
                        if delete_local_after_upload:
                            os.remove(local_filename)
    finally:
        driver.quit()

if __name__ == '__main__':
    S3_BUCKET_NAME = 'trendsproject'
    s3_folder_root = 'images/tagwalk'
    
    if len(sys.argv) > 1:
        url_to_scrape = sys.argv[1]
    else:
        url_to_scrape = 'https://www.tag-walk.com/en/collection/woman/acne-studios/spring-summer-2025'
    
    # Create dynamic S3 prefix and local folder
    collection_name = url_to_scrape.split('/')[-1] or url_to_scrape.split('/')[-2]
    s3_folder_prefix = f"{s3_folder_root}/{collection_name}"
    local_temporary_folder = os.path.expanduser(f'~/scraped_images_temp/{collection_name}')
    
    scrape_images(url_to_scrape, local_temporary_folder, S3_BUCKET_NAME, s3_folder_prefix)
    
    # **CRUCIAL CHANGE**: Output the S3 path for the orchestrator
    print(f"S3_FOLDER_PATH:s3://{S3_BUCKET_NAME}/{s3_folder_prefix}")
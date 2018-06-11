import requests
import re
from time import sleep
from datetime import date, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from bs4 import BeautifulSoup



url = "https://nectar.community/#/listings"
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920x1080")
driver = webdriver.Chrome(chrome_options=chrome_options)

def get_votes_dynamic():
    driver.get(url)
    sleep(2)
    #driver.find_element_by_link_text("#/listings").click()
    countdown = driver.find_elements_by_class_name("countdown")[0].text.split(":")
    if countdown[0] in ("00", "0"):
      timeleft = "Only {} hours left!".format(int(countdown[1]))
    else:
      timeleft = "Only {} days and {} hours left!".format(int(countdown[0]), int(countdown[1]))
    pcs = driver.find_elements_by_class_name("listing-wrapper")
    pcs = pcs[:5]
    rankings = []
    for pc in pcs:
      title = pc.find_elements_by_class_name("title")[0].text
      votes = pc.find_elements_by_class_name("number")[0].text
      rankings.append((title, votes))
    return (rankings, timeleft)
  
def get_browser():
    driver.get(url)
    return driver
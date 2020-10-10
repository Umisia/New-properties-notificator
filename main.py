import time, config
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shelve
import jinja2, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def browser_init(websites):
    global browser
    browser = webdriver.Firefox()
    browser.implicitly_wait(10)
    browser.maximize_window()
    for url in websites:
        browser.execute_script(f'''window.open('{url}','_blank');''')
    WebDriverWait(browser, 10).until(EC.number_of_windows_to_be(len(websites)+1))
    time.sleep(3)
    #close 1st blank tab
    browser.switch_to.window(browser.window_handles[0])
    browser.close()

#match browser tab with scrapping function   
def fn_matcher(url, fn_list):    
    for fn in fn_list:
        if fn.__name__ in url:           
            return fn

def check_houses():  
    for handle in browser.window_handles:
        browser.switch_to.window(handle)
        fn_matcher(browser.current_url,fns)()

def save_to_shelve(dictionary):
    shelf_file = shelve.open("houses_data")
    for k, v in dictionary.items():
        shelf_file[k] = v 
    shelf_file.close()
    
def check_if_new(address):
    shelf_file = shelve.open("houses_data")
    if address not in list(shelf_file.keys()):
        return True
    else:
        return False
    
def createEmail(houses_dict):
    template_dir = "."
    jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir))
    template = jinja_env.get_template("template.html")
    content = ""
    for name, house in houses_dict.items():
        content = content + ('<li>{}, {}<a href="{}">link</a> <br> <img src="{}"/> </li>\n'.format(name, house[0], house[1], house[2]))
    return template.render(property = content)

def sendEmail(temp):
    msg = MIMEMultipart()
    msg['Subject'] = "New properties"
    msg['From'] = config.from_email
    msg['To'] = config.to_email  
    msg.attach(MIMEText(temp, 'html')) 
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login(config.from_email, config.from_password)
    mail.sendmail(msg['From'], msg['To'], msg.as_string())
    mail.quit()

def onthemarket():
    browser.get(websites[0])
    page_soup = BeautifulSoup(browser.page_source, "html.parser")
    ul = page_soup.find("ul", {"id":"properties"})   

    for li in ul.find_all('li', {"class":"property-result"}):
        address = li.find("span", {"class":"title"}).text + li.find("span", {"class":"address"}).text    
        
        is_new = check_if_new(address)   
        print(is_new)
        if is_new:
            price = li.find("p", {"class":"price-text"}).text.split()[0]
            link = f"https://www.onthemarket.com{li.a.get('href')}"
            browser.get(link)
            home_soup = BeautifulSoup(browser.page_source, "html.parser")
            for image in home_soup.find_all("img"):
                if "media.onthemarket.com" in image["src"] and not "epc" in image["src"]:
                    src = image["src"]
                    
            houses[address] = [price, link, src]

def rightmove():    
    browser.get(websites[1])
    page_soup = BeautifulSoup(browser.page_source, "html.parser")
    results = page_soup.find("div", {"id":"l-searchResults"})   

    for result in results.find_all('div', {"class":"l-searchResult is-list"}):
        address = result.find("h2", {"class":"propertyCard-title"}).text + "-"+ result.find("address", {"class":"propertyCard-address"}).text

        is_new = check_if_new(address) 
        print(is_new)
        if is_new:        
            price = result.find("span", {"class":"propertyCard-priceValue"}).text.split()[0]
            house_id = result.get('id').split("-")[1]
            link = f"https://www.rightmove.co.uk/properties/{house_id}/"
            browser.get(link)
            home_soup = BeautifulSoup(browser.page_source, "html.parser")
            for image in home_soup.find_all("img"):
                if "IMG" in image["src"]:
                    src =  image["src"]

            houses[address] = [price, link, src]

def zoopla():
    browser.get(websites[2])
    time.sleep(1)
    try: 
        browser.find_element_by_xpath("/html/body/div[2]/div[2]/form/div/div/div/button[2]").click()  
    except:
        pass
    time.sleep(2)
    page_soup = BeautifulSoup(browser.page_source, "html.parser")
    ul = page_soup.find("ul", {"class":"listing-results clearfix js-gtm-list"})

    for li in ul.find_all('li', {"class":"srp clearfix"}):
        address = li.find("h2", {"class":"listing-results-attr"}).find("a").text + "-" + li.find("a", {"class":"listing-results-address"}).text
        is_new = check_if_new(address) 
        print(is_new)
        if is_new:
            price = li.find("a", {"class":"listing-results-price text-price"}).text.split()[0]
            link = "https://www.zoopla.co.uk" + li.find("h2", {"class":"listing-results-attr"}).find("a").get("href")
            browser.get(link)
            time.sleep(1)
            home_soup = BeautifulSoup(browser.page_source, "html.parser")
            image = home_soup.find("img")
            src= image["src"]

            houses[address] = [price, link, src]


fns = [onthemarket, rightmove, zoopla]

websites = ["https://www.onthemarket.com/to-rent/property/birdlip/?max-price=900&radius=15.0&shared=false",
            "https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E3577&maxPrice=900&radius=15.0&propertyTypes=&includeLetAgreed=false&mustHave=&dontShow=houseShare%2Cstudent%2Cretirement&furnishTypes=&keywords=",
            "https://www.zoopla.co.uk/to-rent/property/birdlip/?include_shared_accommodation=false&price_frequency=per_month&price_max=900&q=Birdlip%2C%20Gloucestershire&radius=15&results_sort=newest_listings&search_source=home"
           ]
houses = {}

browser_init(websites)

while True: 
    check_houses()
    
    if houses:
        template = createEmail(houses)
        sendEmail(template) 
        save_to_shelve(houses)
        houses.clear()
        print("email sent")
    else:
        print("nothing new")
    time.sleep(1800)


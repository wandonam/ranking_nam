import undetected_chromedriver as uc

def create_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=146, driver_executable_path='../02_Driver/chromedriver-win64/chromedriver.exe')
    
    return driver

def close_driver(driver):
    try:
        driver.close()
    except:
        pass

    try:
        driver.quit()
    except:
        pass
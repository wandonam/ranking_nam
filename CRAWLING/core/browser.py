from pathlib import Path
import undetected_chromedriver as uc

DRIVER_PATH = Path(__file__).resolve().parent.parent.parent / "driver" / "chromedriver-win64" / "chromedriver.exe"

def create_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=146, driver_executable_path=str(DRIVER_PATH))
    
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
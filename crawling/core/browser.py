import time
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DRIVER_PATH = Path(__file__).resolve().parent.parent.parent / "driver" / "chromedriver-win64" / "chromedriver.exe"

# 한국 쇼핑몰 공통 팝업 닫기 버튼 패턴 (우선순위 순)
_POPUP_CLOSE_SELECTORS = [
    "[aria-label='닫기']",
    "[aria-label='close']",
    "[class*='popup'] button[class*='close']",
    "[class*='modal'] button[class*='close']",
    "[class*='layer'] button[class*='close']",
    "button[class*='close']",
    "a[class*='close']",
    "[class*='today'] button",
    "button[class*='no-today']",
]


def create_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=146, driver_executable_path=str(DRIVER_PATH))
    return driver


def close_driver(driver):
    try:
        driver.close()
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass


def safe_click(driver, css_selector, timeout=5, label=None):
    """
    셀렉터의 버튼을 클릭. 없으면 False 반환.
    label 지정 시 실패할 경우 경고 출력.
    """
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )
        el.click()
        return True
    except Exception:
        if label:
            print(f"[경고] '{label}' 버튼을 찾지 못했습니다 — 팝업이 가리고 있거나 셀렉터가 변경되었을 수 있습니다")
        return False


def _click_popups(driver, selectors, timeout):
    """주어진 컨텍스트(메인 또는 iframe)에서 팝업 닫기 버튼을 순서대로 시도."""
    for selector in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            driver.execute_script("arguments[0].click();", el)
            time.sleep(0.5)
        except Exception:
            continue


def dismiss_popups(driver, extra_selectors=None, timeout=1):
    """
    페이지 로드 후 팝업을 자동으로 닫는다.
    별도 창 → 메인 문서 → iframe 순으로 탐색.
    extra_selectors: 채널별 고유 팝업 셀렉터 (공통 목록보다 먼저 시도)
    """
    selectors = list(extra_selectors or []) + _POPUP_CLOSE_SELECTORS

    # 1. 별도 브라우저 창 처리 (팝업 창이 새 탭/창으로 열린 경우)
    main_handle = driver.current_window_handle
    for handle in driver.window_handles:
        if handle != main_handle:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except Exception:
                pass
    driver.switch_to.window(main_handle)

    # 2. 메인 문서
    _click_popups(driver, selectors, timeout)

    # 3. iframe 내부 (팝업이 iframe 안에 렌더링된 경우)
    for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.frame(iframe)
            _click_popups(driver, selectors, timeout)
        except Exception:
            pass
        finally:
            driver.switch_to.default_content()

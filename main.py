from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from accounts import save_cookies, load_cookies, add_new_account_cookies, select_account, get_account_settings, show_accounts
import time
import random
import json
import os
import argparse


class HHScraper():
    def __init__(self, options, max_pages: int = 5, account_id=None):
        self.all_vacancies = []
        self.seen = set()
        self.options = options
        self.driver = self.init_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.max_pages = max_pages

        self.account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"accounts/{select_account(account_id)}")
        self.cookie_path = os.path.join(self.account_path, "cookies.json")
        self.account_name = os.path.basename(self.account_path)
        self.excluded_words = get_account_settings(self.account_name)["excluded_words"]
        self.urls = get_account_settings(self.account_name)['urls']

    def init_driver(self):
        if self.options is None:
            self.options = Options()
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        return webdriver.Chrome(options=self.options)

    def is_logged_in(self):
        self.driver.get("https://hh.ru")
        time.sleep(2)
        return "logout" in self.driver.page_source.lower()

    def ensure_login(self):
        self.driver.get("https://hh.ru")

        if not self.account_path or not os.path.exists(os.path.dirname(os.path.abspath(self.account_path))):
            print("⚠️ Cookies не найдены. Войдите вручную.")
            input("🔐 Войдите и нажмите Enter...")
            self.cookie_path = add_new_account_cookies(self.driver)
        else:
            load_cookies(self.driver, self.cookie_path)
            if not self.is_logged_in():
                print("⚠️ Cookies невалидны. Войдите вручную.")
                input("🔐 Войдите и нажмите Enter...")
                save_cookies(self.driver, self.cookie_path)
                print(f"💾 Cookies обновлены в {self.cookie_path}")
        print(f"👤 Используется аккаунт: {os.path.basename(self.account_path)}")

    def is_valid_vacancy(self, title, employer):
        for word in self.excluded_words:
            if word.lower() in title.lower() or word.lower() in employer.lower():
                return False
        return True

    def update_url_with_page(self, url, page_number):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        query_params["page"] = [str(page_number)]
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed_url._replace(query=new_query))

    def parse_url(self, base_url):
        print(f"\n🌐 Парсим URL: {base_url}")
        page = 1

        while page <= self.max_pages:
            url = self.update_url_with_page(base_url, page)
            self.driver.get(url)
            print(f"\n🔄 Страница {page}: {url}")

            try:
                self.wait.until(EC.presence_of_all_elements_located((By.XPATH, "//span[@data-qa='serp-item__title-text']")))
                time.sleep(random.uniform(1.2, 2.5))

                vacancy_cards = self.driver.find_elements(By.XPATH, "//div[@data-qa='vacancy-serp__vacancy']")

                if not vacancy_cards:
                    print("📭 Вакансии на этой странице отсутствуют. Пропускаем дальнейший парсинг этого URL.")
                    break

                for card in vacancy_cards:
                    try:
                        card.find_element(By.CLASS_NAME, "workflow-status-container--cGFP1E5X940FGAbg")
                        print("⏩ Пропущена вакансия — уже просмотрена.")
                        continue
                    except:
                        pass

                    try:
                        title_elem = card.find_element(By.XPATH, ".//span[@data-qa='serp-item__title-text']")
                        link_elem = card.find_element(By.XPATH, ".//a[@data-qa='serp-item__title']")
                        company_elem = card.find_element(By.XPATH, ".//span[@data-qa='vacancy-serp__vacancy-employer-text']")

                        name = title_elem.text.strip()
                        href = link_elem.get_attribute("href")
                        employer = company_elem.text.strip()

                        if self.is_valid_vacancy(name, employer):
                            key = (name, employer, href)
                            if key not in self.seen:
                                self.seen.add(key)
                                self.all_vacancies.append({
                                    "title": name,
                                    "employer": employer,
                                    "link": href
                                })
                                print(f"✅ Найдена вакансия: {name} | {employer}")
                        else:
                            print(f"❌ Исключена: {name} | {employer}")
                    except Exception as e:
                        print(f"⚠️ Ошибка при обработке карточки: {e}")
                        continue

                print(f"📄 Страница {page} обработана. Найдено {len(self.all_vacancies)} вакансий.")
                page += 1
                time.sleep(random.uniform(1.5, 3.0))

            except Exception as e:
                print(f"⚠️ Ошибка на странице: {e}")
                break

    def run(self):

        self.ensure_login()

        for url in self.urls:
            self.parse_url(url)
            time.sleep(random.uniform(2.0, 4.0))

        self.driver.quit()
        self.save_vacancies()


    def save_vacancies(self):
        return self.all_vacancies


class HHResponder(HHScraper):
    def __init__(self, options, vacancies : list[dict], cookie_path : str, account_name: str):
        self.options = options
        self.response_text = get_account_settings(account_name)["vacancy_text"]
        self.vacancies = vacancies
        self.driver = self.init_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.redirected_responses = []
        self.cookie_path = cookie_path
        self.account_name = account_name

    def start(self):
        if os.path.exists(self.cookie_path):
            try:
                self.driver.get("https://hh.ru")
                load_cookies(self.driver, self.cookie_path)
                if self.is_logged_in():
                    print("✅ Успешно авторизован через cookies.")
                    return
                else:
                    print("⚠️ Cookies не сработали. Нужно вручную войти.")
            except Exception as e:
                print("⚠️ Ошибка при загрузке cookies:", e)

            input("🔐 Войдите вручную и нажмите Enter...")
            save_cookies(self.cookie_path)
            print(f"💾 Cookies обновлены в {self.cookie_path}")

    def _click_first_button(self):
        try:
            initial_url = self.driver.current_url
            button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[@data-qa='vacancy-response-link-top']")
            ))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(1)  # дождаться скролла и загрузки
            self.driver.execute_script("arguments[0].click();", button)

            print("✅ Первая кнопка нажата")
            time.sleep(2)

            current_url = self.driver.current_url
            was_redirected = initial_url != current_url
            has_error = self._has_response_error()

            return was_redirected, has_error

        except Exception as e:
            print(f"⚠️ Ошибка при нажатии кнопки 'Откликнуться': {e}")
            return False, False


    def _fill_response_text(self):
        try:
            wrapper = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[data-qa="textarea-native-wrapper"]')))
            textarea = wrapper.find_element(By.TAG_NAME, "textarea")
            textarea.send_keys(self.response_text)
            print("✅ Текст отклика вставлен в поле.")
        except Exception as e:
            print(f"⚠️ Не удалось найти и заполнить textarea: {e}")

    def _has_response_error(self):
        try:
            error_div = self.driver.find_element(By.XPATH, "//div[@data-qa='vacancy-response-error-notification']")
            if error_div.is_displayed():
                return True
            return False
        except:
            return False


    def _click_second_button(self):
        try:
            button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and (@data-qa='vacancy-response-letter-submit' or @data-qa='vacancy-response-submit-popup')]")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(1)  # дождаться скролла и загрузки
            self.driver.execute_script("arguments[0].click();", button)
            print(f"🎯 Кнопка сопроводительного письма нажата.")
            self.wait.until(EC.invisibility_of_element_located((By.XPATH, "//button[@type='submit' and (@data-qa='vacancy-response-letter-submit' or @data-qa='vacancy-response-submit-popup')]")))
            print(f"✅ Сопроводительное письмо отправлено.")
        except Exception as e:
            print(f"⚠️ Кнопка сопроводительного письма не нажалась. Ошибка: {e}")

    def _click_relocation_warning_confirm(self):
        try:
            button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-qa='relocation-warning-confirm']")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            button.click()
            print("✅ Кнопка подтверждения релокации нажата.")
            return True
        except Exception as e:
            print(f"⚠️ Кнопка подтверждения релокации не найдена или не нажалась: {e}")
            return False

    def _has_textarea(self):
        try:
            wrapper = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[data-qa="textarea-native-wrapper"]')))
            textarea = wrapper.find_element(By.TAG_NAME, "textarea")
            return bool(textarea)
        except:
            return False

    def _has_country_alert(self):
        try:
            WebDriverWait(self.driver, 0.2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-qa="magritte-alert"]'))
            )
            alert_div = self.driver.find_element(By.CSS_SELECTOR, 'div[data-qa="magritte-alert"]')
            return alert_div.is_displayed()
        except:
            return False


    def respond_to_all(self):

        count = 1
        for vacancy in self.vacancies:
            try:
                print(f"\n➡️ [{count}] Открываем вакансию: {vacancy['title']} | {vacancy['employer']}")
                self.driver.get(vacancy['link'])
                time.sleep(1 + random.uniform(0.5, 1))

                was_redirected, has_error = self._click_first_button()

                if has_error:
                    print("🛑 В течение 24 часов можно совершить не более 200 откликов. Вы исчерпали лимит откликов, попробуйте отправить отклик позднее.")
                    self.quit()
                    break

                if was_redirected:
                    print(f"🚫 [{count}] Пропущена — редирект на другую страницу.")
                    self.redirected_responses.append(vacancy)
                    count += 1
                    continue

                if self._has_country_alert():
                    print("🌍 Обнаружено предупреждение о стране.")
                    self._click_relocation_warning_confirm()

                if self._has_textarea():
                    print("📝 Обнаружено поле для ввода текста.")
                    self._fill_response_text()
                    self._click_second_button()
                else:
                    print("📭 Поле для текста не найдено. Будет отправлен простой отклик.")

                count += 1
                time.sleep(1 + random.uniform(0.5, 1))

            except Exception as e:
                print(f"⚠️ [{count}] Ошибка при отклике: {e}")
                continue
        if responder.redirected_responses:
            print("\n🔁 Вакансии, которые редиректят на другие сайты:")
            for v in responder.redirected_responses:
                print(f"🔗 {v['title']} | {v['employer']} | {v['link']}")

    def quit(self):
        self.driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HH.ru Вакансии парсер + автокликер")
    parser.add_argument("--max-pages", type=int, default=5, help="Максимум страниц на каждый URL")
    parser.add_argument("--account", type=str, help="Номер аккаунта из списка (1, 2, 3...)")
    parser.add_argument("--accounts", action="store_true", help="Вывести список доступных аккаунтов")
    parser.add_argument("--headless", action="store_true", help="Запускать браузер в headless режиме")
    parser.add_argument("--add-account", action="store_true", help="Добавить новый аккаунт и сохранить его cookies")

    args = parser.parse_args()

    if args.accounts:
        show_accounts()
        exit(0)

    chrome_options = None

    if args.headless:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

    if args.add_account:
        options = chrome_options if chrome_options else Options()
        driver = webdriver.Chrome(options=options)
        add_new_account_cookies(driver)
        driver.quit()
        exit(0)

    scraper = HHScraper(max_pages=args.max_pages, account_id=args.account, options=chrome_options)
    scraper.run()
    vacancies = scraper.save_vacancies()
    cookie_path = scraper.cookie_path
    account_name = scraper.account_name
    options = scraper.options

    if vacancies:
        print(f"\n📊 Найдено {len(vacancies)} вакансий.")
        responder = HHResponder(vacancies=vacancies, options=options, cookie_path=cookie_path, account_name=account_name)
        responder.start()
        responder.respond_to_all()
    else:
        print("❌ Вакансии не найдены или все исключены.")
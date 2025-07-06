import os
import json
from selenium.webdriver.remote.webdriver import WebDriver
import time

ACCOUNTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts")
os.makedirs(ACCOUNTS_DIR, exist_ok=True)

def list_account_dirs():
    def extract_timestamp(name):
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
        return 0
    dirs = [d for d in os.listdir(ACCOUNTS_DIR) if os.path.isdir(os.path.join(ACCOUNTS_DIR, d))]
    return sorted(dirs, key=extract_timestamp)

def get_account_dir(name: str) -> str:
    return os.path.join(ACCOUNTS_DIR, name)

def get_cookie_file_path(name: str) -> str:
    return os.path.join(get_account_dir(name), "cookies.json")

def get_account_settings(name: str):
    settings_path = get_settings_file_path(name)
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)
    return {
        "urls": settings.get("urls", []),
        "vacancy_text": settings.get("vacancy_text", ""),
        "excluded_words": settings.get("excluded_words", [])
    }
def get_settings_file_path(name: str) -> str:
    return os.path.join(get_account_dir(name), "settings.json")

def save_cookies(driver: WebDriver, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(driver.get_cookies(), f, ensure_ascii=False, indent=2)

def load_cookies(driver: WebDriver, path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cookie file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    driver.get("https://hh.ru")
    for cookie in cookies:
        cookie.pop("sameSite", None)
        driver.add_cookie(cookie)

def add_new_account_cookies(driver: WebDriver) -> str:
    base_name = input("📝 Введите имя нового аккаунта (например, texet, work, alt1): ").strip()
    dirs = list_account_dirs()
    existing = [d for d in dirs if d.rsplit("_", 1)[0] == base_name]
    if existing:
        name = existing[-1]
        print(f"⚠️  Аккаунт с именем '{base_name}' уже существует. Будет обновлён: {name}")
    else:
        timestamp = int(time.time())
        name = f"{base_name}_{timestamp}"

    account_dir = get_account_dir(name)
    os.makedirs(account_dir, exist_ok=True)
    cookie_path = get_cookie_file_path(name)
    settings_path = get_settings_file_path(name)

    print(f"🔐 Открывается сайт для аккаунта '{name}'.")
    driver.get("https://hh.ru")
    input("➡️  После входа в аккаунт нажмите Enter для сохранения cookies...")

    driver.refresh()
    save_cookies(driver, cookie_path)

    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings_data = json.load(f)
        urls = settings_data.get("urls", [])
        vacancy_text = settings_data.get("vacancy_text", "")
        excluded_words = settings_data.get("excluded_words", [])
    else:
        urls = []
        vacancy_text = ""
        excluded_words = []

    print("🔗 Введите ссылки (по одной на строку). Чтобы закончить, отправьте пустую строку.")
    print("   (Оставьте первую строку пустой, чтобы оставить текущие ссылки без изменений.)")
    new_urls = []
    first_url_input = input("URL: ").strip()
    if first_url_input:
        new_urls.append(first_url_input)
        while True:
            url = input("URL: ").strip()
            if not url:
                break
            new_urls.append(url)
        urls = new_urls
        
    vacancy_text_input = input("⌨️  Введите текст сопроводительного отклика (оставьте пустым для сохранения текущего): ")
    if vacancy_text_input.strip():
        vacancy_text = vacancy_text_input

    excluded_words_input = input("📛 Введите запрещённые слова через запятую (оставьте пустым для сохранения текущих): ")
    if excluded_words_input.strip():
        excluded_words = [word.strip() for word in excluded_words_input.split(",") if word.strip()]

    settings_data = {
        "urls": urls,
        "vacancy_text": vacancy_text,
        "excluded_words": excluded_words
    }
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=2)
    print(f"💾 Cookies сохранены в {cookie_path}")
    print(f"⚙️  Настройки созданы в {settings_path}")
    return cookie_path

def show_accounts():
    dirs = list_account_dirs()
    if not dirs:
        return None

    print("🔐 Доступные аккаунты:")
    print_account_list(dirs)

def print_account_list(dirs):
    for i, dir_name in enumerate(dirs):
        base_name = dir_name.rsplit("_", 1)[0]
        print(f"{i + 1}. {base_name}")

def select_account(account_id=None):
    dirs = list_account_dirs()
    if not dirs:
        return None

    if account_id is not None:
        if account_id.isdigit():
            index = int(account_id) - 1
            if 0 <= index < len(dirs):
                return dirs[index]
            else:
                print(f"❌ Неверный номер аккаунта: {account_id}")
                return None
        else:
            print(f"❌ Аргумент --account должен быть числом, получено: {account_id}")
            return None

    print("🔐 Выберите аккаунт:")
    print_account_list(dirs)

    while True:
        choice = input("🔢 Введите номер аккаунта: ")
        if choice.isdigit() and 1 <= int(choice) <= len(dirs):
            return dirs[int(choice) - 1]
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

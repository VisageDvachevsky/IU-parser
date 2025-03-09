import requests
import json
from datetime import datetime
import time
import random
import string
import uuid
import platform
import re
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(message)s")

class InternetUrokAPI:
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.base_url_psp = "https://api-psp.interneturok.ru/api/v2"
        self.base_url_gw = "https://api-gw.interneturok.ru/api/v2"
        self.base_url_ege = "https://api-ege.interneturok.ru/api/v2"
        self.access_token = None
        self.user_id = None
        self.global_id = None
        self.grade = None
        self.created_at = None
        self.user_agent = self._generate_user_agent()
        self.session_id = str(uuid.uuid4())
        self.client_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Language": self._random_choice([
                "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "ru-RU,ru;q=0.9,en;q=0.8"
            ]),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://interneturok.ru",
            "Referer": "https://interneturok.ru/",
            "User-Agent": self.user_agent,
            "sec-ch-ua": self._generate_sec_ch_ua(),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{platform.system()}"'
        })

    def _generate_user_agent(self) -> str:
        chrome_ver = random.choice(["110", "115", "120", "125", "130"])
        os_info = random.choice([
            "Windows NT 10.0; Win64; x64",
            "Macintosh; Intel Mac OS X 10_15_7"
        ])
        return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver}.0.0.0 Safari/537.36"

    def _generate_sec_ch_ua(self) -> str:
        version = re.search(r"Chrome/(\d+)", self.user_agent)
        version = version.group(1) if version else "133"
        return f'"Not(A:Brand";v="99", "Google Chrome";v="{version}", "Chromium";v="{version}"'

    def _random_choice(self, options: list) -> str:
        return random.choice(options)

    def _add_delay(self, min_sec: float = 0.8, max_sec: float = 3.5) -> None:
        time.sleep(random.uniform(min_sec, max_sec))

    def login_and_get_token(self) -> bool:
        self._add_delay()
        url = f"{self.base_url_gw}/psp/tokens"
        data = {"login": self.login, "password": self.password}
        try:
            response = self.session.post(url, data=data)
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("status") == "200_OK":
                    token_data = json_response.get("data", {}).get("psp", {}).get("response", {}).get("data", {})
                    self.access_token = token_data.get("access_token")
                    if self.access_token:
                        logging.info("Успешная авторизация. Токен получен.")
                        self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                        return True
            logging.error(f"Ошибка авторизации: {response.status_code}")
            return False
        except Exception as e:
            logging.error(f"Исключение при авторизации: {str(e)}")
            return False

    def get_user_info(self) -> bool:
        if not self.access_token and not self.login_and_get_token():
            return False
        self._add_delay()
        url = f"{self.base_url_gw}/homeschool/current_user"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("status") == "200_OK":
                    user_data = json_response.get("data", {}).get("homeschool", {}).get("response", {}).get("user", {})
                    self.user_id = user_data.get("id")
                    self.global_id = user_data.get("global_id")
                    self.grade = user_data.get("grade")
                    self.created_at = user_data.get("created_at")
                    logging.info(f"Получена информация: ID={self.user_id}, Класс={self.grade}")
                    return True
            logging.error(f"Ошибка получения информации о пользователе: {response.status_code}")
            return False
        except Exception as e:
            logging.error(f"Исключение: {str(e)}")
            return False

    def calculate_academic_years(self) -> list:
        if not self.created_at or not self.grade:
            if not self.get_user_info():
                return []
        created_date = datetime.strptime(self.created_at.split("T")[0], "%Y-%m-%d")
        current_date = datetime.now()
        registration_year = created_date.year
        years_since_registration = current_date.year - registration_year
        if current_date.month < 9:
            years_since_registration -= 1
        academic_years = []
        for offset in range(years_since_registration + 1):
            grade_val = self.grade + offset
            year_id = registration_year + offset
            if 1 <= grade_val <= 11:
                academic_years.append({"grade": grade_val, "year_id": year_id})
        return academic_years

    def check_journal_has_data(self, journal_data: dict) -> bool:
        if not journal_data.get("schedules"):
            return False
        if not journal_data.get("schedule_events"):
            return False
        return True

    def adjust_week_numbers(self, journal_data: dict) -> dict:
        if not journal_data or not isinstance(journal_data, dict):
            return journal_data
        if "weeks" in journal_data and isinstance(journal_data["weeks"], list):
            for week in journal_data["weeks"]:
                if "week_num" in week:
                    week["week_num"] += 1
        return journal_data

    def get_all_journal_data(self) -> dict:
        if not self.user_id and not self.get_user_info():
            return {}
        academic_years = self.calculate_academic_years()
        if not academic_years:
            logging.error("Не удалось определить учебные годы.")
            return {}
        all_journal_data = {}
        for academic_year in academic_years:
            grade_val = academic_year["grade"]
            year_id = academic_year["year_id"]
            grade_data = {}
            grade_has_data = False
            for quarter in range(1, 5):
                logging.info(f"Получение данных для класса {grade_val}, четверти {quarter}, ID года {year_id}...")
                self._add_delay(1.2, 4.5)
                url = f"{self.base_url_ege}/journal/student"
                params = {
                    "grade": grade_val,
                    "quarter": quarter,
                    "year_id": year_id,
                    "user_id": self.user_id,
                    "token": self.access_token
                }
                try:
                    response = self.session.get(url, params=params)
                    if response.status_code == 200:
                        journal_data = response.json()
                        journal_data = self.adjust_week_numbers(journal_data)
                        has_data = self.check_journal_has_data(journal_data)
                        grade_data[f"quarter_{quarter}"] = {"data": journal_data, "has_data": has_data}
                        if has_data:
                            grade_has_data = True
                            logging.info(f"  Успех: Получены данные для класса {grade_val}, четверти {quarter}")
                        else:
                            logging.info(f"  Получены данные для класса {grade_val}, четверти {quarter}, но журнал пуст")
                    else:
                        logging.error(f"  Ошибка: {response.status_code}")
                        grade_data[f"quarter_{quarter}"] = {"error": response.status_code, "has_data": False}
                except Exception as e:
                    logging.error(f"  Исключение: {str(e)}")
                    grade_data[f"quarter_{quarter}"] = {"error": "exception", "text": str(e), "has_data": False}
            all_journal_data[f"grade_{grade_val}"] = {"quarters": grade_data, "has_data": grade_has_data}
            if random.random() > 0.7:
                self._add_delay(5.0, 10.0)
        return all_journal_data

    def save_journal_data(self, filename: str = None) -> bool:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interneturok_journal_{timestamp}.json"
        all_data = self.get_all_journal_data()
        if all_data:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            summary = {"grades_with_data": [], "grades_without_data": [], "total_grades": len(all_data)}
            for grade_key, grade_info in all_data.items():
                grade_num = grade_key.replace("grade_", "")
                if grade_info["has_data"]:
                    summary["grades_with_data"].append(grade_num)
                else:
                    summary["grades_without_data"].append(grade_num)
            summary_filename = f"summary_{timestamp}.json"
            with open(summary_filename, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logging.info(f"Данные успешно сохранены в {filename}")
            logging.info(f"Сводка сохранена в {summary_filename}")
            logging.info("\n===== СВОДКА =====")
            logging.info(f"Всего классов: {summary['total_grades']}")
            logging.info(f"Классы с данными: {', '.join(sorted(summary['grades_with_data']))}")
            logging.info(f"Пустые журналы: {', '.join(sorted(summary['grades_without_data']))}")
            return True
        logging.error("Нет данных для сохранения.")
        return False

def main():
    load_dotenv() 

    login = os.getenv("API_LOGIN")
    password = os.getenv("API_PASSWORD")

    if not login or not password:
        logging.error("Переменные окружения API_LOGIN и API_PASSWORD не заданы!")
        return

    api = InternetUrokAPI(login=login, password=password)
    if api.login_and_get_token() and api.get_user_info():
        api.save_journal_data()
    else:
        logging.error("Не удалось инициализировать API клиент.")

if __name__ == "__main__":
    main()

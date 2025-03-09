import json
import logging
import random
import re
import time
import platform
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from http_client import create_session 
from state_manager import load_state, save_state

logging.basicConfig(level=logging.INFO, format="%(message)s")


class InternetUrokAPI:
    def __init__(self, login: str, password: str) -> None:
        self.login: str = login
        self.password: str = password
        self.urls: Dict[str, str] = {
            "psp": "https://api-psp.interneturok.ru/api/v2",
            "gw": "https://api-gw.interneturok.ru/api/v2",
            "ege": "https://api-ege.interneturok.ru/api/v2"
        }
        self.state: Dict[str, Any] = load_state()
        self.access_token: Optional[str] = self.state.get("access_token")
        self.user_id: Optional[str] = self.state.get("user_id")
        self.global_id: Optional[str] = self.state.get("global_id")
        self.grade: Optional[int] = self.state.get("grade")
        self.created_at: Optional[str] = self.state.get("created_at")
        
        self.session: requests.Session = create_session()

    def _gen_user_agent(self) -> str:
        chrome: str = random.choice(["110", "115", "120", "125", "130"])
        os_info: str = random.choice([
            "Windows NT 10.0; Win64; x64",
            "Macintosh; Intel Mac OS X 10_15_7"
        ])
        return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome}.0.0.0 Safari/537.36"

    def _gen_sec_ch_ua(self) -> str:
        m: Optional[re.Match] = re.search(r"Chrome/(\d+)", self.user_agent)
        version: str = m.group(1) if m else "133"
        return f'"Not(A:Brand";v="99", "Google Chrome";v="{version}", "Chromium";v="{version}"'

    def _delay(self, a: float = 0.8, b: float = 3.5) -> None:
        time.sleep(random.uniform(a, b))

    def update_state(self) -> None:
        self.state.update({
            "access_token": self.access_token,
            "user_id": self.user_id,
            "global_id": self.global_id,
            "grade": self.grade,
            "created_at": self.created_at
        })
        save_state(self.state)

    def login_and_get_token(self) -> bool:
        self._delay()
        try:
            resp = self.session.post(f"{self.urls['gw']}/psp/tokens", data={"login": self.login, "password": self.password})
            if resp.status_code == 200:
                data: Dict[str, Any] = resp.json().get("data", {}).get("psp", {}).get("response", {}).get("data", {})
                self.access_token = data.get("access_token")
                if self.access_token:
                    logging.info("Успешная авторизация. Токен получен.")
                    self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                    self.update_state()
                    return True
            logging.error(f"Ошибка авторизации: {resp.status_code}")
        except Exception as e:
            logging.error(f"Исключение при авторизации: {e}")
        return False

    def get_user_info(self) -> bool:
        if not self.access_token and not self.login_and_get_token():
            return False
        self._delay()
        try:
            resp = self.session.get(f"{self.urls['gw']}/homeschool/current_user")
            if resp.status_code == 200:
                user: Dict[str, Any] = resp.json().get("data", {}).get("homeschool", {}).get("response", {}).get("user", {})
                self.user_id = user.get("id")
                self.global_id = user.get("global_id")
                self.grade = user.get("grade")
                self.created_at = user.get("created_at")
                logging.info(f"Получена информация: ID={self.user_id}, Класс={self.grade}")
                self.update_state()
                return True
            logging.error(f"Ошибка получения информации: {resp.status_code}")
        except Exception as e:
            logging.error(f"Исключение: {e}")
        return False

    def calculate_academic_years(self) -> List[Dict[str, int]]:
        if not self.created_at or not self.grade:
            if not self.get_user_info():
                return []
        reg_year: int = datetime.strptime(self.created_at.split("T")[0], "%Y-%m-%d").year
        now: datetime = datetime.now()
        diff: int = now.year - reg_year - (1 if now.month < 9 else 0)
        return [{"grade": self.grade + off, "year_id": reg_year + off}
                for off in range(diff + 1) if 1 <= self.grade + off <= 11]

    def check_journal_has_data(self, data: Dict[str, Any]) -> bool:
        return bool(data.get("schedules") and data.get("schedule_events"))

    def adjust_week_numbers(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, dict) and (weeks := data.get("weeks")):
            for w in weeks:
                if "week_num" in w:
                    w["week_num"] += 1
        return data

    def get_all_journal_data(self) -> Dict[str, Any]:
        if not self.user_id and not self.get_user_info():
            return {}
        years: List[Dict[str, int]] = self.calculate_academic_years()
        if not years:
            logging.error("Не удалось определить учебные годы.")
            return {}
        all_data: Dict[str, Any] = {}
        for y in years:
            grade: int = y["grade"]
            year_id: int = y["year_id"]
            quarters: Dict[str, Any] = {}
            has_data: bool = False
            for q in range(1, 5):
                logging.info(f"Получение данных для класса {grade}, четверть {q}, год {year_id}...")
                self._delay(1.2, 4.5)
                try:
                    params: Dict[str, Any] = {
                        "grade": grade, "quarter": q, "year_id": year_id,
                        "user_id": self.user_id, "token": self.access_token
                    }
                    resp = self.session.get(f"{self.urls['ege']}/journal/student", params=params)
                    if resp.status_code == 200:
                        jdata: Dict[str, Any] = self.adjust_week_numbers(resp.json())
                        valid: bool = self.check_journal_has_data(jdata)
                        quarters[f"quarter_{q}"] = {"data": jdata, "has_data": valid}
                        logging.info("  " + ("Успех: данные получены." if valid else "Данные пусты."))
                        has_data |= valid
                    else:
                        logging.error(f"  Ошибка: {resp.status_code}")
                        quarters[f"quarter_{q}"] = {"error": resp.status_code, "has_data": False}
                except Exception as e:
                    logging.error(f"  Исключение: {e}")
                    quarters[f"quarter_{q}"] = {"error": "exception", "text": str(e), "has_data": False}
            all_data[f"grade_{grade}"] = {"quarters": quarters, "has_data": has_data}
            if random.random() > 0.7:
                self._delay(5.0, 10.0)
                
        return all_data


    def save_journal_data(self, filename: Optional[str] = None) -> Optional[str]:
        ts: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"interneturok_journal_{ts}.json"
        data: Dict[str, Any] = self.get_all_journal_data()
        if data:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            summary: Dict[str, Any] = {
                "grades_with_data": [],
                "grades_without_data": [],
                "total_grades": len(data)
            }
            for k, v in data.items():
                grade_str: str = k.split("_")[1]
                (summary["grades_with_data"] if v["has_data"] else summary["grades_without_data"]).append(grade_str)
            summary_filename: str = f"summary_{ts}.json"
            with open(summary_filename, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logging.info(f"Данные сохранены: {filename}, {summary_filename}")
            logging.info(f"Всего классов: {summary['total_grades']}; С данными: {', '.join(sorted(summary['grades_with_data']))}; Пустые: {', '.join(sorted(summary['grades_without_data']))}")
            return json.dumps(data, ensure_ascii=False, indent=2)
        logging.error("Нет данных для сохранения.")
        return None

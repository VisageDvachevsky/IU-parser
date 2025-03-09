# http_client.py
import random
import platform
import re
import requests

def gen_user_agent() -> str:
    chrome = random.choice(["110", "115", "120", "125", "130"])
    os_info = random.choice([
        "Windows NT 10.0; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_7"
    ])
    return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome}.0.0.0 Safari/537.36"

def gen_sec_ch_ua(user_agent: str) -> str:
    m = re.search(r"Chrome/(\d+)", user_agent)
    version = m.group(1) if m else "133"
    return f'"Not(A:Brand";v="99", "Google Chrome";v="{version}", "Chromium";v="{version}"'

def create_session() -> requests.Session:
    session = requests.Session()
    user_agent = gen_user_agent()
    headers = {
        "Accept": "*/*",
        "Accept-Language": random.choice([
            "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "ru-RU,ru;q=0.9,en;q=0.8"
        ]),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://interneturok.ru",
        "Referer": "https://interneturok.ru/",
        "User-Agent": user_agent,
        "sec-ch-ua": gen_sec_ch_ua(user_agent),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": f'"{platform.system()}"'
    }
    session.headers.update(headers)
    return session

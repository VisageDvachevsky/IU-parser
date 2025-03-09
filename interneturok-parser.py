from dotenv import load_dotenv
import os
import logging
from interneturok_api import InternetUrokAPI
from json_parser import run_parser  

def main():
    load_dotenv() 

    login = os.getenv("API_LOGIN")
    password = os.getenv("API_PASSWORD")

    if not login or not password:
        logging.error("Переменные окружения API_LOGIN и API_PASSWORD не заданы!")
        return

    api = InternetUrokAPI(login=login, password=password)
    if api.login_and_get_token() and api.get_user_info():
        journal_json = api.save_journal_data()
        if journal_json:
            run_parser(journal_json, output_folder=".")
        else:
            logging.error("Нет данных для обработки.")
    else:
        logging.error("Не удалось инициализировать API клиент.")

if __name__ == "__main__":
    main()

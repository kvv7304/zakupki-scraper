import json
import pprint
import re
import time
import traceback
from io import BytesIO
from urllib.parse import quote, unquote

import gspread
import requests
import vobject
from anticaptchaofficial.imagecaptcha import *
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import *
from main import *

from collections import OrderedDict

class Table:
    def __init__(self, key, filename, id):
        self.table = (
            gspread.service_account(filename=filename)
            .open_by_key(key)
            .get_worksheet_by_id(id)
        )
        self.headers = self.table.row_values(1)
        # print(self.table.title)

    def get_data(self):
        return self.table.get_all_values()

    def get_value(self, row, header):
        if header in self.headers:
            return row[self.headers.index(header)]
        else:
            return None

    def get_title(self):
        return self.table.title


def find_inn(data):
    pattern = re.compile(r"\b\d{9,12}\b")
    inn = pattern.search(data)
    if inn:
        inn = inn.group()
        if len(inn) == 9 or len(inn) == 11:
            return "0" + inn
        else:
            return inn
    else:
        return None


def find_email(text):
    # Находим все email-адреса в тексте с помощью регулярного выражения
    emails = re.findall(r"\S+@\S+", text)
    # Возвращаем список email-адресов
    return emails


def find_phone(text):
    words = text.split()
    matches = ""
    numers = []
    for word in words:
        if "@" not in word:
            matches += re.sub(r"\D", "", word)
    pattern = re.compile(
        r"(8|7)?\s*[\- ]?(9\d{2})[\- ]?(\d{3})[\- ]?(\d{2})[\- ]?(\d{2})"
    )
    matches = pattern.findall(matches)
    for match in matches:
        numers.append("+7" + "".join(match[1:]))
    return numers


def save_contacts(dict_data, filename):
    with open(filename, "a", encoding="utf-8-sig") as file:
        for value in dict_data.values():
            if value is not None:
                file.write(value)

    separation_contacts(filename)


    # print(f'Данные сохранены в файл {filename}')


def create_vcard_from_dict(data_dict):
    """
    Создает объект vCard из словаря данных
    :param data_dict: словарь, содержащий данные для создания vCard
    :return: строка, представляющая созданный объект vCard, в формате vCard
    """
    # Создаем объект vCard
    dataVcard = vobject.vCard()

    # Проходимся по каждому ключу в словаре и добавляем его и значение в объект vCard
    for key, value in data_dict.items():
        if key == "ADR":
            dataVcard.add("adr").value = vobject.vcard.Address(region=value)
        elif key == "NOTE":
            for note in sorted(value):
                dataVcard.add("note").value = note
        elif key == "EMAIL":
            for email in value:
                dataVcard.add("email").value = email
        elif key == "TEL":
            for tel in value:
                dataVcard.add("tel").value = tel
        else:
            dataVcard.add(key.lower()).value = value
    # Сериализуем объект vCard в строку
    return dataVcard.serialize(lineLength=128)


def getinfo(id, url, endUrl=""):
    time.sleep(1)
    response = getUrl(f"{url}{id}{endUrl}")
    # print(f'{url}{id}{endUrl}', response.elapsed)
    if response and response.status_code == 200:
        return response
    else:
        return None


def parserSbis(id, url, dict_vcf):
    # print("parserSbis")
    response = getinfo(id, url)
    if response:
        sbis = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )

        if sbis.find("div", {"itemprop": "address"}):
            region = (
                sbis.find("div", {"itemprop": "address"})
                .get_text()
                .split(",", maxsplit=1)[0]
            )
            dict_vcf["ADR"] = region

        if sbis.find("a", {"itemprop": "email"}):
            dict_vcf["EMAIL"].update(
                find_email(
                    sbis.find(
                        "a", {"itemprop": "email"}
                    ).parent.parent.get_text(separator=" ")
                )
            )

        if sbis.find("div", {"itemprop": "telephone"}):
            # print(sbis.find('div', {'itemprop': 'telephone'}).get_text())
            dict_vcf["TEL"].update(
                find_phone(
                    sbis.find("div", {"itemprop": "telephone"}).get_text(
                        separator=" "
                    )
                )
            )

        if sbis.find("div", class_="cCard__Director-Name"):
            if sbis.find("div", class_="cCard__Director-Name").find(
                "span", {"itemprop": "employee"}
            ):
                directorName = (
                    sbis.find("div", class_="cCard__Director-Name")
                    .find("span", {"itemprop": "employee"})
                    .get_text()
                )
            else:
                directorName = str(None)

            if sbis.find("div", class_="cCard__Director-Name").find(
                "div", class_="cCard__Director-Position"
            ):
                directorPosition = (
                    sbis.find("div", class_="cCard__Director-Name")
                    .find("div", class_="cCard__Director-Position")
                    .get_text()
                )
            else:
                directorPosition = str(None)

            dict_vcf["TITLE"] = f"{directorPosition} {directorName}"

        """
        if sbis.find('div', class_="cCard__Owners-OwnerList-block"):
            founders = sbis.find('div', class_="cCard__Owners-OwnerList-block").findAll('div', {'itemprop': 'founder'})
            for founder in founders:
                dict_vcf['NOTE'].update([f'Учредитель {founder.get_text()}'])
        """
        FN = sbis.h1.get_text().replace('"', "").replace("`", "")
        dict_vcf["FN"] = f"{FN}"

    return dict_vcf


def parserChecko(id, url, dict_vcf):
    response = getinfo(id, url)

    if response:
        checko = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )

        if checko.find("section", {"id": "management"}).find(string="ИНН "):
            dict_vcf["TITLE"] += (
                checko.find("section", {"id": "management"})
                .find(string="ИНН ")
                .parent.get_text()[:-2]
            )

        founders = (
            checko.find("section", {"id": "founders"})
            .get_text(separator=" ")
            .replace("\n", " ")
        )
        for founder in re.findall(r"\.\s*([^.]*?\s*ИНН\s*\d+)", founders):
            dict_vcf["NOTE"].update([f"Учредитель {founder}"])

        # time.sleep(1)
        response = getinfo(id, url, endUrl="?extra=contacts")
        checko = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )

        if checko.find(string="Телефон"):
            dict_vcf["TEL"].update(
                find_phone(
                    checko.find(string="Телефон").parent.parent.get_text(
                        separator=" "
                    )
                )
            )

        if checko.find(string="Телефоны"):
            dict_vcf["TEL"].update(
                find_phone(
                    checko.find(string="Телефоны").parent.parent.get_text(
                        separator=" "
                    )
                )
            )

        if checko.find(string="Электронная почта"):
            dict_vcf["EMAIL"].update(
                find_email(
                    checko.find(
                        string="Электронная почта"
                    ).parent.parent.get_text(separator=" ")
                )
            )

    return dict_vcf


def parserVbankcenter(id, url, dict_vcf):
    response = getinfo(id, url)
    Vbankcenter = BeautifulSoup(
        response.content.decode("utf8"), features="html.parser"
    )
    state = Vbankcenter.find("script", {"id": "gweb-app-state"})
    data = state.get_text().replace("&q;", '"')
    data = json.loads(data)
    for key in data.keys():
        if "contacts/list" in key:
            contacts = data[f"{key}"]["body"]
            # Обход и вывод #телефонов и #почты для каждого контакта
            for contact in contacts:
                for phone in contact["phones"]:
                    dict_vcf["TEL"].update(find_phone(phone))
                for email in contact["emails"]:
                    dict_vcf["EMAIL"].update(find_email(email))
            break
    return dict_vcf


def parserExcheck(id, url, dict_vcf):
    # print("parserExcheck")
    response = getinfo(id, url, "/contacts")
    if response:
        excheck = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )

        if excheck.find(string="Телефон"):
            dict_vcf["TEL"].update(
                find_phone(
                    excheck.find(string="Телефон").parent.parent.get_text(
                        separator=" "
                    )
                )
            )

        if excheck.find(string="Телефоны"):
            dict_vcf["TEL"].update(
                find_phone(
                    excheck.find(string="Телефоны").parent.parent.get_text(
                        separator=" "
                    )
                )
            )

        if excheck.find(string="Email"):
            dict_vcf["EMAIL"].update(
                find_email(
                    excheck.find(string="Email").parent.parent.get_text(
                        separator=" "
                    )
                )
            )
    return dict_vcf


def deCFEmail(c):
    # Получаем первые два символа аргумента и преобразуем их в десятичное число
    k = int(c[0:2], 16)
    # Создаем пустую строку, где будем хранить результат дешифровки
    m = ""
    # Проходим по всем символам аргумента, начиная с третьего
    for i in range(2, len(c) - 1, 2):
        # Преобразуем каждую пару символов в десятичное число и выполняем
        # операцию XOR с переменной k, после чего преобразуем результат обратно в символ
        # и добавляем его к результирующей строке
        m += chr(int(c[i: i + 2], 16) ^ k)
    # Возвращаем результирующую строку
    return m

def normalize_url(url):
    decoded_link = unquote(url, "utf-8")
    encoded_link = quote(decoded_link, safe="/:?=&+")
    return encoded_link

"""
def get_find_org(url, base_url="https://www.find-org.com"):
    print("get_find_org", url)
    s = 0
    time.sleep(s)
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
    while s < 10:
        headers = {"User-Agent": UserAgent().random}
        try:
            contentext = requests.get(
                url,
                headers = headers,
                verify = False,
                timeout = 30,
                proxies = proxi
                # proxies={"https": proxy},
            )
            # print(f"{contentext.url}", contentext.content)
            while "bot.html" in contentext.url:
                content = contentext.content.decode("utf-8")
                m = re.search(r"(\/kcap.php\?PHPSESSID=\w+)", content)
                img_url = m[1]
                # cookies=contentext.cookies)
                img = requests.get(base_url + img_url)
                # print(f"{contentext.url}", img.elapsed)
                captcha_content = BytesIO(img.content)

                while True:
                    try:
                        solver = imagecaptcha()
                        solver.set_verbose(1)
                        # solver.set_verbose(0)
                        solver.set_key(captcha_key)
                        captcha_text = solver.solve_and_return_solution(
                            file_path=None, body=captcha_content.read()
                        )
                        break
                    except:
                        pass
                payload = {"keystring": captcha_text, "submit": " Проверить! "}
                contentext = requests.post(
                    base_url + "/bot.html",
                    data=payload,
                    cookies=img.cookies,
                    allow_redirects=True,
                    proxies=proxi
                )
                print(f"{contentext.url}", contentext.elapsed)

            if normalize_url(url) == contentext.url:
                return contentext
            else:
                raise Exception("")

        except Exception as e:
            # # Блок обработки исключений
            # print("Произошла ошибка:", e)
            # traceback.print_exc()
            s += 1
            # print(f"{normalize_url(url)} =//= {contentext.url}")
            # for i in tqdm(range(s)):
            #     time.sleep(1)
            continue
    return None
"""


def get_find_org(url, base_url="https://www.find-org.com"):
    s = 0
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
    headers = {"User-Agent": UserAgent().random}

    while True:
        try:

            contentext = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=30,
                proxies=proxi
            )
            # print(f"{contentext.url}", contentext.elapsed)

            while "bot.html" in contentext.url:
                # balance = solver.get_balance()
                print(solver.get_balance())
                content = contentext.content.decode("utf-8")
                m = re.search(r"(\/kcap.php\?PHPSESSID=\w+)", content)
                img_url = m[1]
                img = requests.get(base_url + img_url)
                captcha_content = BytesIO(img.content)

                while True:
                    try:
                        solver = imagecaptcha()
                        # solver.set_verbose(0)
                        solver.set_verbose(1)
                        solver.set_key(captcha_key)
                        captcha_text = solver.solve_and_return_solution(
                            file_path=None, body=captcha_content.read()
                        )
                        break
                    except:
                        pass

                payload = {"keystring": captcha_text, "submit": " Проверить! "}

                contentext = requests.post(
                    base_url + "/bot.html",
                    data=payload,
                    cookies=img.cookies,
                    allow_redirects=True,
                    proxies=proxi
                )

            if normalize_url(url) == contentext.url:
                return contentext
            else:
                time.sleep(1)
                raise Exception("")

        except Exception as e:
            s += 1
            if s >= 10:
                return None
            continue


def parserFindOrg(id, url, dict_vcf):
    response = get_find_org(f"{url}/search/all/?val={id}")
    if response:
        findOrg = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )
        for link in findOrg.select('a[href*="/cli/"]')[:2]:
            response = get_find_org(f"{url}{link.get('href')}")
            if response:
                findOrg = BeautifulSoup(
                    response.content.decode("utf8"), features="html.parser"
                )

                for string in findOrg.find_all(
                    string=re.compile(r".*Телефон\(ы\).*")
                ):
                    dict_vcf["TEL"].update(
                        find_phone(
                            findOrg.find(
                                string=string
                            ).parent.parent.get_text()
                        )
                    )

                for cfemail in findOrg.find_all(
                    "span", {"class": "__cf_email__"}
                ):
                    dict_vcf["EMAIL"].update(
                        find_email(deCFEmail(cfemail.get("data-cfemail")))
                    )
    return dict_vcf

def lowercase_email(dict_vcf):
    if "EMAIL" in dict_vcf:
        emails = dict_vcf["EMAIL"]
        lowercase_emails = set()
        for email in emails:
            lowercase_emails.add(email.lower())
        dict_vcf["EMAIL"] = lowercase_emails
    return dict_vcf

def contacts(dict_contacts, headers, fileNameContacts, id=0):
    table = Table(key, filename, id)

    data_list = [
        [table.get_value(row, header) for header in headers]
        for row in table.get_data()
    ]

    for data in tqdm(data_list[1:]):
        dict_vcf = {
            "ADR": str(),
            "EMAIL": set(),
            "FN": str(),
            "NOTE": set(),
            "TEL": set(),
            "TITLE": str(),
        }

        if data[0] and "(Код в стране регистрации -)" not in data[0]:
            inn = find_inn(data[0])

            if inn not in dict_contacts.keys():
                # print(inn)
                try:
                    parserSbis(inn, sbisUrl, dict_vcf)

                    parserExcheck(inn, excheckUrl, dict_vcf)

                    parserFindOrg(inn, findOrgUrl, dict_vcf)

                    # parserListOrg(inn, listOrgUrl, dict_vcf)

                    try:
                        dict_vcf["EMAIL"].update(find_email(data[1]))
                        dict_vcf["TEL"].update(find_phone(data[1]))
                    except IndexError:
                        pass
                    except Exception as e:
                        traceback.print_exc()

                    ogrn = findOgrn(inn)
                    if ogrn:
                        try:
                            parserVbankcenter(ogrn, vbankcenterUrl, dict_vcf)
                        except AttributeError:
                            pass
                        except Exception as e:
                            traceback.print_exc()
                        try:
                            parserChecko(ogrn, checkoUrl, dict_vcf)
                        except AttributeError:
                            pass
                        except Exception as e:
                            traceback.print_exc()
                    dict_vcf["FN"] += f" {inn}"
                    dict_vcf["NOTE"].update(
                        [
                            f'Дата создания контакта {time.strftime("%d-%m-%Y", time.localtime(time.time()))}'
                        ]
                    )
                    dict_vcf = lowercase_email(dict_vcf)

                    pprint.pprint(dict_vcf)

                    vcard_string = create_vcard_from_dict(dict_vcf)
                    dict_contacts.update({inn: vcard_string})
                    save_contacts({inn: vcard_string}, fileNameContacts)

                except Exception as e:
                    traceback.print_exc()
    return dict_contacts


def separation_contacts(vcf_file):
    max_records_per_file = 1000 # Задайте максимальное количество записей в каждом файле
    with open(f"{vcf_file}", "r", encoding="utf-8-sig") as old_file: # Откройте файл .vcf на чтение
        record_count = 0 # Инициируйте счетчик записей и номер файла
        file_number = 1
        new_file = open(f"{file_number}_{vcf_file}", "w", encoding="utf-8-sig") # Инициируйте новый файл для записей
        for line in old_file: # Прочитайте каждую строку из файла .vcf

            if line.strip(): # Проверяем, является ли строка пустой

                if line.startswith("BEGIN:VCARD"): # Если строка начинается со строки "BEGIN:VCARD", увеличиваем счетчик записей
                    record_count += 1
                    tel = 0

                if line.startswith("TEL"):
                    tel += 1
                    if tel == 200 :
                        new_file.write("NOTE: Более 200 телефонов")
                        continue
                    if tel > 200 :
                        continue

                if record_count == max_records_per_file: # Если количество записей превышает максимальное значение, закрываем текущий файл и создаем новый
                    new_file.close()
                    file_number += 1
                    new_file = open(f"{file_number}_{vcf_file}", "w", encoding="utf-8-sig")
                    record_count = 0

                new_file.write(line) # Записываем строку в новый файл

                if line.startswith("END:VCARD"):
                    new_file.write("\n")

        new_file.close() # Закрываем последний файл



def parser_contacts(fileNameContacts="contacts.vcf"):
    print(
        "Сбор контактов начат",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )
    dict_contacts = OrderedDict()

    try:
        with open(fileNameContacts, "r", encoding="utf-8-sig") as file:
            for line in file:
                if line.strip().startswith("FN"):
                    inn = find_inn(line)
                    dict_contacts[inn] = None
    except FileNotFoundError:
        pass

    try:
        contacts(
            dict_contacts,
            ["Организация", "Телефон, электронная почта"],
            fileNameContacts,
        )
        contacts(
            dict_contacts, ["ИНН (аналог ИНН)\n"], fileNameContacts, 1740992288
        )
        contacts(dict_contacts, ["ИНН"], fileNameContacts, 843115480)
        contacts(dict_contacts, ["ИНН"], fileNameContacts, 45528551)

        print(
            "Обработка контактов прошла успешно",
            time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
        )
    except:
        printRed(
            f"\n{time.strftime('%d.%m.%Y %H:%M', time.localtime(time.time()))}\n{traceback.format_exc()}"
        )
    # pprint.pprint(dict_contacts)
    print(
        "Сбор контактов закончен",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )
    print(f"Контактов собранно {len(dict_contacts)}")

    save_contacts(dict_contacts, fileNameContacts)

    # pprint.pprint(dict_contacts)

if __name__ == "__main__":
    parser_contacts(
        f"contacts_{time.strftime('%d.%m.%Y', time.localtime(time.time()))}.vcf"
    )


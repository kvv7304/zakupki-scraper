import os
import pprint
import re
import sys
import time
import traceback

import gspread
import requests
import urllib3 #urllib3==1.26.15

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm

from config import *
from contacts import *


class Cell:
    def __init__(self, c, r, v):
        self.col = c
        self.row = r
        self.value = v


def printRed(text):
    print("\033[31m" + text + "\033[39m")


def getUrl(url):
    s = 0
    time.sleep(s)
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
    proxies = None
    while s < 2:
        headers = {"User-Agent": UserAgent().random}
        try:
            contentext = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=10,
                proxies=proxies
            )
            return contentext
        except:
            # print(url, proxies)
            # print(f"Пауза {s}")
            proxies = proxi
            time.sleep(60*s)
            s += 1
            continue
    return None


def parserDizkCard(url, indexCol, table):
    while True:
        try:
            cells = list()
            response = getUrl(url)
            soup = BeautifulSoup(
                response.content.decode("utf8"), features="html.parser"
            )

            if "Тестовая организация" not in soup.text:
                if soup.find("span", class_="navBreadcrumb__text"):
                    HYPERLINK_text = re.findall(
                        "\d+",
                        soup.find(
                            "span", {"class": "navBreadcrumb__text"}
                        ).text.strip(),
                    )[0]
                    HYPERLINK = url
                    cells.append(
                        Cell(
                            1,
                            indexCol,
                            str(
                                f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                            ),
                        )
                    )

                rowList = table.row_values(1)

                # print(rowList)

                for findtext in rowList:
                    indexRow = rowList.index(findtext) + 1
                    if findtext and soup.find(string=findtext):
                        cells.append(
                            Cell(
                                indexRow,
                                indexCol,
                                soup.find(string=findtext)
                                .parent.parent.text.replace(findtext, "")
                                .replace("№", "")
                                .replace("\n", "")
                                .strip(),
                            )
                        )

                        if findtext == "Реестровый номер контракта":
                            HYPERLINK_text = (
                                soup.find(string=findtext)
                                .parent.parent.text.replace(findtext, "")
                                .replace("№", "")
                                .replace("\n", "")
                                .strip()
                            )
                            HYPERLINK = soup.find(string=findtext).parent.parent.find("a").get("href")
                            cells.append(
                                Cell(
                                    indexRow,
                                    indexCol,
                                    str(
                                        f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                                    ),
                                )
                            )

                contractUrl = HYPERLINK
                url = url.replace("generalInformation", "document-info")
                # print("   ", url)
                response = getUrl(url)
                soup = BeautifulSoup(
                    response.content.decode("utf8"), features="html.parser"
                )

                findtext = "Прикрепленные файлы"
                indexRow = rowList.index(findtext) + 1
                if soup.find(string=findtext):
                    HYPERLINK_text = (
                        soup.find(string=findtext)
                        .parent.parent.find("img", class_="pl-2")
                        .find("a")
                        .text.strip()
                    )
                    HYPERLINK = (
                        soup.find(string=findtext)
                        .parent.parent.find("img", class_="pl-2")
                        .find("a")
                        .get("href")
                    )
                    cells.append(
                        Cell(
                            indexRow,
                            indexCol,
                            str(
                                f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                            ),
                        )
                    )

                # print("   ",contractUrl)
                response = getUrl(contractUrl)
                soup = BeautifulSoup(
                    response.content.decode("utf8"), features="html.parser"
                )

                findtext = "Цена контракта"
                indexRow = rowList.index(findtext) + 1
                if soup.find(string=findtext):
                    cells.append(
                        Cell(
                            indexRow,
                            indexCol,
                            soup.find(string=findtext)
                            .parent.parent.text.replace(findtext, "")
                            .replace(" ", "")
                            .replace("\n", "")
                            .strip(),
                        )
                    )

                if soup.find(string="Информация о поставщиках"):
                    soup = soup.find(
                        string="Информация о поставщиках"
                    ).parent.parent.find("table")
                    th = soup.findAll("th")
                    td = soup.findAll("td")
                    for i, t in enumerate(th):
                        if t.text and t.text in rowList:
                            indexRow = rowList.index(t.text) + 1
                            text = (
                                td[i]
                                .get_text(separator=" ")
                                .replace("+", "")
                                .replace("\n", " ")
                                .strip()
                            )
                            while "  " in text:
                                text = text.replace("  ", " ")
                                # print(text)
                            cells.append(Cell(indexRow, indexCol, text))

                table.update_cells(cells, value_input_option="USER_ENTERED")
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке
            continue
        break


def parser44FZ():
    print(
        "Сбор дополнительная информация о закупках, контрактах по 44-ФЗ начат",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )
    while True:
        try:
            response = getUrl(url44fz)
            soup = BeautifulSoup(
                response.content.decode("utf8"), features="html.parser"
            )
            numbers = soup.find_all(
                "div", class_="registry-entry__header-mid__number"
            )

            table = (
                gspread.service_account(filename=filename)
                .open_by_key(key)
                .get_worksheet_by_id(0)
            )
            existent = table.col_values(1)
            col = len(existent)

            # for index, number in enumerate(tqdm(numbers)):
            for index, number in tqdm(enumerate(numbers)):
                if (
                    number.text.replace("№", "")
                    .replace(" ", "")
                    .replace("\n", "")
                    not in existent
                ):
                    time.sleep(1)
                    # table.update_cell(col + index + 1, 1, numberText)
                    parserDizkCard(
                        f"{URL}{number.find('a').get('href')}",
                        col + index + 1,
                        table,
                    )
                else:
                    col -= 1
            print(
                "Сбор дополнительная информация о закупках, контрактах по 44-ФЗ закончен успешно",
                time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
            )

        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке
            continue
        break


def linkSbis(inn, url="https://sbis.ru/contragents/"):
    return f"{url}{inn}"


def parserBrief(inn):
    url = "https://sbis.ru/contragents/" + inn
    # print(url)
    response = getUrl(url)
    soup = BeautifulSoup(
        response.content.decode("utf8"), features="html.parser"
    )
    # print(response)
    if response.status_code == 200:
        # print(soup.find(string="Краткая справка"))
        if soup.find(string="Краткая справка"):
            return (
                soup.find(string="Краткая справка")
                .parent.parent.get_text(separator=" ")
                .replace("Краткая справка ", "")
            )
            # return soup.find("div", class_="cCard__Contacts-AddressBlock cCard__Main-Grid-Element").get_text(separator="\n")
    else:
        return None


def linkEcolog(inn):
    url = "https://e-ecolog.ru/entity/" + inn
    return url


def findOgrn(inn):
    # print("findOgrn")
    url = "https://e-ecolog.ru/entity/" + inn
    response = getUrl(url)
    # print(response)
    if response and url == response.url:
        soup = BeautifulSoup( response.content.decode("utf8"), features="html.parser" )
        if soup.find(string="ОГРН"):
            return (
                soup.find(string="ОГРН")
                .parent.parent.get_text(separator=" ")
                .replace("ОГРН", "")
                .strip()
                .split(" ")[0]
            )
        else:
            return None
    else:
        return None


def linkChecko(ogrn):
    url = "https://checko.ru/company/" + ogrn
    return url


def linkVbankcenter(ogrn):
    url = "https://vbankcenter.ru/contragent/" + ogrn
    return url


def parserINN(claim, indexCol, table):
    time.sleep(1)
    cells = list()

    HYPERLINK_text = (
        claim.find(class_="registry-entry__header-mid__number")
        .find("a")
        .text.replace("№", "")
        .strip()
    )
    HYPERLINK = (
        claim.find(class_="registry-entry__header-mid__number")
        .find("a")
        .get("href")
    )
    cells.append(
        Cell(
            1, indexCol, str(f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")')
        )
    )
    cells.append(
        Cell(
            2,
            indexCol,
            claim.find(
                "div", class_="registry-entry__header-top__title text-truncate"
            ).text.strip(),
        )
    )
    cells.append(
        Cell(
            3,
            indexCol,
            claim.find_all("div", class_="data-block__value")[0].text,
        )
    )
    cells.append(
        Cell(
            4,
            indexCol,
            claim.find_all("div", class_="registry-entry__body-value")[0].text,
        )
    )
    cells.append(
        Cell(
            5,
            indexCol,
            claim.find_all("div", class_="registry-entry__body-value")[1].text,
        )
    )
    inn = claim.find_all("div", class_="registry-entry__body-value")[1].text

    cells.append(
        Cell(
            6,
            indexCol,
            str(f'=HYPERLINK("{linkSbis(inn)}"; "Перейти на СБИС")'),
        )
    )
    cells.append(
        Cell(
            7,
            indexCol,
            str(f'=HYPERLINK("{linkEcolog(inn)}"; "Перейти на Е-ДОСЬЕ")'),
        )
    )

    cells.append(Cell(10, indexCol, parserBrief(inn)))

    ogrn = findOgrn(inn)
    if ogrn:
        cells.append(
            Cell(
                8,
                indexCol,
                str(f'=HYPERLINK("{linkChecko(ogrn)}"; "Перейти на ЧЕККО")'),
            )
        )
        cells.append(
            Cell(
                9,
                indexCol,
                str(
                    f'=HYPERLINK("{linkVbankcenter(ogrn)}"; "Перейти на ВБЦ")'
                ),
            )
        )
    # print(table)

    table.update_cells(cells, value_input_option="USER_ENTERED")


def parserDishonestsupplier():
    print(
        "Сбор сведений из реестра недобросовестных поставщиков начат",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )

    try:
        table = (
            gspread.service_account(filename=filename)
            .open_by_key(key)
            .get_worksheet_by_id(1740992288)
        )
        pageNumber = 2
        urlNext = urlDishonestsupplier
        # print(urlNext)
        while True:
            response = getUrl(urlNext)
            soup = BeautifulSoup(
                response.content.decode("utf8"), features="html.parser"
            )
            claims = soup.find_all(
                "div",
                class_="search-registry-entry-block box-shadow-search-input",
            )
            if claims:
                for claim in tqdm(claims):
                    time.sleep(1)
                    existent = table.col_values(5)
                    col = len(existent)
                    inn = claim.find_all(
                        "div", class_="registry-entry__body-value"
                    )[1].text

                    if inn.isdigit():
                        # print("ИНН является числом")
                        inn = str(int(inn))
                        if (
                            "Исключено" not in claim.text
                            and inn not in existent
                        ):
                            # print("Запуск",inn)
                            parserINN(claim, col + 1, table)

                urlNext = str(
                    urlDishonestsupplier + "&pageNumber=" + str(pageNumber)
                )
                pageNumber += 1
            else:
                break

            break

        print(
            "Сбор сведений из реестра недобросовестных поставщиков закончен успешно",
            time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
        )

    except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке



def parserInformation(url, table, rowList, indexCol, cells):
    try:
        response = getUrl(url)
        # print("    ",url)
        soup = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )
        # soup.prettify()
        i = 0
        for findtext in rowList:
            indexRow = rowList.index(findtext) + 1
            if soup.find(string=findtext):
                cells.append(
                    Cell(
                        indexRow,
                        indexCol,
                        soup.find(string=findtext)
                        .parent.parent.get_text(separator="\n")
                        .replace(findtext, "")
                        .replace("№", "")
                        .replace("\n", "")
                        .strip(),
                    )
                )
                if findtext == "Номер извещения":
                    HYPERLINK_text = (
                        soup.find(string=findtext)
                        .parent.parent.get_text(separator="\n")
                        .replace(findtext, "")
                        .replace("№", "")
                        .replace("\n", "")
                        .strip()
                    )
                    HYPERLINK = (
                        "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber="
                        + HYPERLINK_text
                    )
                    cells.append(
                        Cell(
                            indexRow,
                            indexCol,
                            str(
                                f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                            ),
                        )
                    )
                if findtext == "Содержание жалобы":
                    cells.append(
                        Cell(
                            indexRow,
                            indexCol,
                            soup.find(string=findtext)
                            .parent.parent.parent.find(
                                "div", class_="common-text__value"
                            )
                            .text.strip(),
                        )
                    )
                if findtext == "Жалоба":
                    for link in soup.find(
                        string=findtext
                    ).parent.parent.find_all("a"):
                        if (
                            link.get("title")
                            and link.get("title")
                            != "Печатная форма документа, подписанного поставщиком.XML"
                        ):
                            HYPERLINK = link.get("href")
                            HYPERLINK_text = link.get("title")
                            links_html = str(
                                f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}\n")'
                            )
                            cells.append(
                                Cell(indexRow, indexCol + i, links_html)
                            )
                            i += 1
                    if i > 0:
                        time.sleep(1)
                        table.merge_cells(
                            indexCol,
                            1,
                            indexCol + i - 1,
                            indexRow - 1,
                            merge_type="MERGE_COLUMNS",
                        )
                        time.sleep(1)
                        table.merge_cells(
                            indexCol,
                            indexRow + 1,
                            indexCol + i - 1,
                            len(rowList) + 1,
                            merge_type="MERGE_COLUMNS",
                        )
                        time.sleep(1)
                    else:
                        cells.append(Cell(indexRow, indexCol, " "))
                        i = 1

                if findtext in ("Решение", "Предписание"):
                    # print(soup.find(string=findtext).parent.parent.find("img").find("a").prettify(),"\n")
                    HYPERLINK_text = (
                        soup.find(string=findtext)
                        .parent.parent.find("img")
                        .find("a")
                        .get("title")
                    )
                    HYPERLINK = (
                        soup.find(string=findtext)
                        .parent.parent.find("img")
                        .find("a")
                        .get("href")
                    )
                    cells.append(
                        Cell(
                            indexRow,
                            indexCol,
                            str(
                                f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                            ),
                        )
                    )

        table.update_cells(cells, value_input_option="USER_ENTERED")

    except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке
            # print(url)


def saveTable(numers, table, rowList):
    s = 1
    time.sleep(s)
    while True:
        try:
            existent = table.col_values(1)
            numer = numers["TEXT"]
            if numer not in existent:
                time.sleep(1)
                indexCol = len(table.col_values(10)) + 1
                cells = list()
                HYPERLINK = numers["HYPERLINK"]
                cells.append(
                    Cell(
                        1,
                        indexCol,
                        str(f'=HYPERLINK("{HYPERLINK}"; "{numer}")'),
                    )
                )
                parserInformation(HYPERLINK, table, rowList, indexCol, cells)
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке

            s += 1
            time.sleep(s)
            continue
        break


def parserPetition():
    print(
        "Сбор сведений из реестра жалоб начат",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )

    try:
        table = (
            gspread.service_account(filename=filename)
            .open_by_key(key)
            .get_worksheet_by_id(843115480)
        )
        rowList = table.row_values(1)
        all = list()
        # for pageNumber in tqdm(range(1,11)):
        for pageNumber in range(1, 11):
            time.sleep(1)
            urlNext = str(urlPetition + "&pageNumber=" + str(pageNumber))
            addRows = 0
            response = getUrl(urlNext)
            soup = BeautifulSoup(
                response.content.decode("utf8"), features="html.parser"
            )
            petitions = soup.find_all(
                "div",
                class_="search-registry-entry-block box-shadow-search-input",
            )

            for petition in petitions:
                numers = dict()
                # numer = petition.find("span", class_="registry-entry__header-mid__number").text.replace('№', '').replace(' ', '').replace('\n', '')
                numer = petition.find(
                    "span", class_="registry-entry__header-mid__number"
                ).find("a")
                numers["HYPERLINK"] = URL + numer.get("href")
                numers["TEXT"] = (
                    numer.text.replace("№", "")
                    .replace(" ", "")
                    .replace("\n", "")
                )
                numers["id"] = numers["HYPERLINK"].split("__")[-1]
                all.append(numers)

        all = sorted(all, key=lambda numers: numers["id"])

        """
        print(len(all))
        text = set()
        for numers in all:
            text.add(numers["id"])
        print(len(text))
        """

        existent = table.col_values(1)
        # for numers in tqdm(all) :
        for numers in tqdm(all):
            numer = numers["TEXT"]
            if numer not in existent:
                saveTable(numers, table, rowList)
            # break

        print(
            "Сбор сведений из реестра жалоб закончен успешно",
            time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
        )

    except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке
            # printRed("numer")


def updateInformation(url, table, rowList, indexCol, cells, numer, existent):
    try:
        response = getUrl(url)
        soup = BeautifulSoup(
            response.content.decode("utf8"), features="html.parser"
        )
        # i = 0
        result = "Сведения о результатах рассмотрения жалобы"
        # print(result)
        # print("***",soup.find(string=result))#.parent.parent.get_text(separator="\n").replace(result, ''))
        # .parent.parent.get_text(separator="\n").replace(result, '') :
        if soup.find(string=result):
            for findtext in rowList:
                indexRow = rowList.index(findtext) + 1
                if soup.find(string=findtext):
                    cells.append(
                        Cell(
                            indexRow,
                            indexCol,
                            soup.find(string=findtext)
                            .parent.parent.get_text(separator="\n")
                            .replace(findtext, "")
                            .replace("№", "")
                            .replace("\n", "")
                            .strip(),
                        )
                    )
                    if findtext == "Номер извещения":
                        HYPERLINK_text = (
                            soup.find(string=findtext)
                            .parent.parent.get_text(separator="\n")
                            .replace(findtext, "")
                            .replace("№", "")
                            .replace("\n", "")
                            .strip()
                        )
                        HYPERLINK = (
                            "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber="
                            + HYPERLINK_text
                        )
                        cells.append(
                            Cell(
                                indexRow,
                                indexCol,
                                str(
                                    f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                                ),
                            )
                        )
                    if findtext == "Содержание жалобы":
                        cells.append(
                            Cell(
                                indexRow,
                                indexCol,
                                soup.find(string=findtext)
                                .parent.parent.parent.find(
                                    "div", class_="common-text__value"
                                )
                                .text.strip(),
                            )
                        )
                    if findtext == "Жалоба":
                        for link in soup.find(
                            string=findtext
                        ).parent.parent.find_all("a")[1:2]:
                            if (
                                link.get("title")
                                and link.get("title")
                                != "Печатная форма документа, подписанного поставщиком.XML"
                            ):
                                HYPERLINK = link.get("href")
                                HYPERLINK_text = link.get("title")
                                links_html = str(
                                    f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}\n")'
                                )
                                cells.append(
                                    Cell(indexRow, indexCol, links_html)
                                )

                    if findtext in ("Решение", "Предписание"):
                        # print(soup.find(string=findtext).parent.parent.find("img"),"\n")
                        HYPERLINK_text = (
                            soup.find(string=findtext)
                            .parent.parent.find_all("a")[1]
                            .get("title")
                        )
                        HYPERLINK = (
                            soup.find(string=findtext)
                            .parent.parent.find_all("a")[1]
                            .get("href")
                        )
                        cells.append(
                            Cell(
                                indexRow,
                                indexCol,
                                str(
                                    f'=HYPERLINK("{HYPERLINK}"; "{HYPERLINK_text}")'
                                ),
                            )
                        )
            table.update_cells(cells, value_input_option="USER_ENTERED")
            existent.append(numer)
            # print(f"Данные по жалобе {numer} добавлены")

    except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке




def updateTable(numers, table, rowList, existent):
    # s=0
    # time.sleep(s)
    while True:
        try:
            # existent = table.col_values(1)
            numer = numers["TEXT"]
            if numer not in existent:
                # time.sleep(1)
                indexCol = len(existent) + 1
                cells = list()
                HYPERLINK = numers["HYPERLINK"]
                # print(HYPERLINK)
                cells.append(
                    Cell(
                        1,
                        indexCol,
                        str(f'=HYPERLINK("{HYPERLINK}"; "{numer}")'),
                    )
                )
                updateInformation(
                    HYPERLINK, table, rowList, indexCol, cells, numer, existent
                )

        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке
            printRed("numer")
            continue
        break


def updatePetition():
    # worksheet_by_id(45528551)
    print(
        "Обновление сведений из реестра жалоб начат",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )
    try:
        table = (
            gspread.service_account(filename=filename)
            .open_by_key(key)
            .get_worksheet_by_id(45528551)
        )
        rowList = table.row_values(1)
        all = list()
        for pageNumber in range(1, 51):
            time.sleep(1)
            urlNext = str(urlPetition + "&pageNumber=" + str(pageNumber))
            response = getUrl(urlNext)
            soup = BeautifulSoup(
                response.content.decode("utf8"), features="html.parser"
            )
            petitions = soup.find_all(
                "div",
                class_="search-registry-entry-block box-shadow-search-input",
            )
            for petition in petitions:
                numers = dict()
                numer = petition.find(
                    "span", class_="registry-entry__header-mid__number"
                ).find("a")
                numers["HYPERLINK"] = URL + numer.get("href")
                numers["TEXT"] = (
                    numer.text.replace("№", "")
                    .replace(" ", "")
                    .replace("\n", "")
                )
                numers["id"] = numers["HYPERLINK"].split("__")[-1]
                all.append(numers)
        all = sorted(all, key=lambda numers: numers["id"])
        existent = table.col_values(1)
        for numers in tqdm(all):
            numer = numers["TEXT"]
            if numer not in existent:
                updateTable(numers, table, rowList, existent)

    except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке
            printRed("numer")

    finally:
        print(
            "Обновление сведений из реестра жалоб завершен",
            time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
        )


if __name__ == "__main__":
    URL = "https://zakupki.gov.ru"
    print(
        "Начало работы",
        time.strftime("%d.%m.%Y %H:%M", time.localtime(time.time())),
    )

    while True:

        try:
            parser44FZ()
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке

        try:
            parserDishonestsupplier()
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке

        try:
            parserPetition()
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке

        try:
            updatePetition()
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке

        try:
            parser_contacts()
        except Exception as e:
            error_info = (
                traceback.format_exc()
            )  # получение строки с информацией об ошибке
            print(error_info)  # вывод строки с информацией об ошибке

        printRed("Пауза на час")
        time.sleep(3660)  # Пауза на час

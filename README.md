
# ZakupkiScraper

Этот проект предназначен для сбора и обработки информации о контактах и закупках из различных источников.

## Описание

Проект собирает и обрабатывает данные о закупках и контрактах, а также контактную информацию организаций с различных веб-сайтов. Скрипты включают функциональность для работы с Google Sheets, выполнения запросов к веб-сайтам, парсинга данных и обработки капчи.

## Установка

### Зависимости

Для работы проекта необходимы следующие библиотеки:

- anticaptchaofficial==1.0.52
- beautifulsoup4==4.12.2
- fake_useragent==1.1.3
- gspread==5.9.0
- pip==23.1.2
- requests==2.31.0
- tqdm==4.65.0
- urllib3==1.26.15
- vobject==0.9.6.1

Установить зависимости можно с помощью команды:

```bash
pip install -r requirements.txt
```

## Конфигурация

В файле config.py хранятся ключевые настройки проекта, такие как API-ключи, ссылки на веб-страницы и настройки прокси:

```python
key = "your_google_sheets_key"
filename = "config"

url44fz = "https://zakupki.gov.ru/epz/dizk/search/results.html?recordsPerPage=_100"
urlDishonestsupplier = "https://zakupki.gov.ru/epz/dishonestsupplier/search/results.html?morphology=on&search-filter=Дата+размещения&sortBy=DATE_OF_INCLUSION&sortDirection=false&recordsPerPage=_100&showLotsInfoHidden=false&fz94=on&fz223=on&ppRf615=on&inclusionDateFrom=01.01.2023"
urlPetition = "https://zakupki.gov.ru/epz/complaint/search/search_eis.html?morphology=on&search-filter=Дата+размещения&fz94=on&fz223=on&receiptDateStart=01.04.2023&sortBy=PO_DATE_POSTУПЛЕНИЯ&sortDirection=false&showLotsInfoHidden=false&recordsPerPage=_100"

sbisUrl = "https://sbis.ru/contragents/"
vbankcenterUrl = "https://vbankcenter.ru/contragent/"
checkoUrl = "https://checko.ru/company/"
excheckUrl = "https://excheck.pro/company/"
listOrgUrl = "https://www.list-org.com"
findOrgUrl = "https://www.find-org.com"

bot = "https://www.find-org.com/bot.html"
captcha_key = "your_captcha_key"

proxi = {
    'http': 'http://username:password@proxy_address:port',
    'https': 'http://username:password@proxy_address:port'
}
```

## Использование

### Основные скрипты

- `main.py`: Главный скрипт, который запускает процессы сбора данных о закупках, контрактах и контактах.
- `contacts.py`: Скрипт для работы с контактной информацией, включая парсинг, сохранение и создание vCard.
- `config.py`: Файл конфигурации с ключевыми параметрами и настройками.

### Запуск

Запуск основного скрипта:

```bash
python main.py
```

## Функции

- Сбор и обработка данных о закупках по 44-ФЗ.
- Сбор сведений из реестра недобросовестных поставщиков.
- Сбор и обновление сведений из реестра жалоб.
- Парсинг контактной информации организаций.
- Сохранение контактов в формате vCard.

## Контрибьютинг

Если вы хотите внести вклад в проект, пожалуйста, создайте pull request с вашими изменениями. Мы приветствуем любые улучшения и исправления.

## Лицензия

Этот проект лицензируется на условиях лицензии MIT.

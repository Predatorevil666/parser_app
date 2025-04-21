import logging
import re


from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import BASE_DIR,  MAIN_DOC_URL
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    # Вместо константы WHATS_NEW_URL, используйте переменную whats_new_url.
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')

    # Загрузка веб-страницы с кешированием.
    # response = session.get(whats_new_url)
    # response.encoding = 'utf-8'
    response = get_response(session, whats_new_url)
    soup = BeautifulSoup(response.text, 'lxml')
    # news = soup.find('div', class_='toctree-wrapper compound')
    news = find_tag(soup, 'div', class_='toctree-wrapper compound')
    news_link = news.find_all('li', class_='toctree-l1')
    # print(news_link[0].prettify())
    # for link in news_link:
    #     link_1 = link.find('a')
    #     href = link_1['href']
    #     version_link = urljoin(WHATS_NEW_URL, href)
    #     print(version_link)
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(news_link):
        # version_a_tag = section.find('a')
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        # Здесь начинается новый код!
        # Загрузите все страницы со статьями. Используйте кеширующую сессию.
        # response = session.get(version_link)
        # response.encoding = 'utf-8'  # Укажите кодировку utf-8.
        response = get_response(session, version_link)
        soup = BeautifulSoup(response.text, 'lxml')  # Сварите "супчик".
        # h1 = soup.find('h1')  # Найдите в "супе" тег h1.
        h1 = find_tag(soup, 'h1')  # Найдите в "супе" тег h1.
        # dl = soup.find('dl')  # Найдите в "супе" тег dl.
        dl = find_tag(soup, 'dl')  # Найдите в "супе" тег dl.
        dl_text = dl.text.replace('\n', ' ')
        # print(version_link, h1.text, dl_text)  # Добавьте в вывод на печать текст из тегов h1 и dl.
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):

    # response = session.get(MAIN_DOC_URL)
    # response.encoding = 'utf-8'
    response = get_response(session, MAIN_DOC_URL)
    soup = BeautifulSoup(response.text, 'lxml')
    # sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')

    # Список для хранения результатов.
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    # Шаблон для поиска версии и статуса:
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    # Цикл для перебора тегов <a>, полученных ранее.
    for a_tag in a_tags:
        # Извлечение ссылки.
        link = a_tag['href']
        # Поиск паттерна в ссылке.
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            # Если строка соответствует паттерну,
            # переменным присываивается содержимое групп, начиная с первой.
            version, status = text_match.groups()
        else:
            # Если строка не соответствует паттерну,
            # первой переменной присваивается весь текст, второй — пустая строка.
            version, status = a_tag.text, ''
            # Добавление полученных переменных в список в виде кортежа.
        results.append(
            (link, version, status)
        )

        # Печать результата.
    return results


def download(session):
    # Вместо константы DOWNLOADS_URL, используйте переменную downloads_url.
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')

    # response = session.get(downloads_url)
    # response.encoding = 'utf-8'
    response = get_response(session, downloads_url)
    soup = BeautifulSoup(response.text, 'lxml')
    table_tag = soup.find('table', attrs={'class': 'docutils'})
    table_tag = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag,
        'a',
        {'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    # Сохраните в переменную содержимое атрибута href.
    pdf_a4_link = pdf_a4_tag['href']

    # Получите полную ссылку с помощью функции urljoin.
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    # Сформируйте путь до директории downloads.
    downloads_dir = BASE_DIR / 'downloads'
    # Создайте директорию.
    downloads_dir.mkdir(exist_ok=True)
    # Получите путь до архива, объединив имя файла с директорией.
    archive_path = downloads_dir / filename

    # # Загрузка архива по ссылке.
    # response = session.get(archive_url)

    # # В бинарном режиме открывается файл на запись по указанному пути.
    # with open(archive_path, 'wb') as file:
    #     # Полученный ответ записывается в файл.
    #     file.write(response.content)

    # Загрузка с tqdm (упрощенный вариант)
    response = session.get(archive_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    with open(archive_path, 'wb') as file:
        # Просто оборачиваем response.iter_content() в tqdm
        for chunk in tqdm(
                response.iter_content(chunk_size=1024),
                total=total_size // 1024 + 1,  # Округляем до количества чанков
                unit='KB',  # Кибибайты вместо байтов
                desc=filename,
                leave=True  # Оставляет прогресс-бар после завершения
        ):
            if chunk:
                file.write(chunk)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
}


def main():
    # Запускаем функцию с конфигурацией логов.
    configure_logging()
    # Отмечаем в логах момент запуска программы.
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    # Логируем переданные аргументы командной строки.
    logging.info(f'Аргументы командной строки: {args}')

    # Создание кеширующей сессии.
    session = requests_cache.CachedSession()
    # Если был передан ключ '--clear-cache', то args.clear_cache == True.
    if args.clear_cache:
        # Очистка кеша.
        session.cache.clear()

    parser_mode = args.mode
    # С вызовом функции передаётся и сессия.
    results = MODE_TO_FUNCTION[parser_mode](session)
    # Если из функции вернулись какие-то результаты,
    if results is not None:
        # передаём их в функцию вывода вместе с аргументами командной строки.
        control_output(results, args)
    # Логируем завершение работы парсера.
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()

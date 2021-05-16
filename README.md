# Прокси сервер

Автор: Нечуговских Антон (nechugovskihanton@gmail.com)

## Описание
Данное решение является реализацией прокси сервера http/https

## Требования
* Python версии не ниже 3.6
* aiounittest (tests)
* pytest-asyncio (tests)

## Состав
* Серверная часть: `proxy/async_server.py`
* Объект запроса к proxy: `proxy/request.py`
* Тесты: `tests/`

Справка по запуску: `./main.py --help`

Примеры запуска:
* `./main.py` 
* `python main.py -H 127.0.0.1 -p 1234 --auth -b banlist.json -t tokens.json`

## Подробности реализации

На модуль server написаны тесты, их можно найти в `tests/`.
Покрытие по строкам составляет около 93%:

    proxy/async_proxy.py        157      35      81% 
    proxy/request.py             38       0     100%
    proxy/token_auth.py          22       0     100%
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Превращает source.json (собранные факты) в products.js для каталога.
Описания генерируются из фактов (характеристик), маркетинговый текст источника НЕ используется."""
import json, re, html

src = json.load(open('merged_source.json', encoding='utf-8'))

def brand_of(name):
    n = name.lower()
    table = [('МЗСА','мзса'),('Титан','титан'),('Кремень','кремень'),('Трейлер','трейлер|treiler'),
             ('ССТ','сст|sst'),('Avtos','avtos|автос'),('Экспедиция','экспедици'),
             ('MULLERWAGEN','mullerwagen|мюллер'),('Уралец','уралец|uralets'),('Славич','славич'),
             ('Русич','русич|rusich'),('LAV','\\blav\\b|лав '),('RINAL','rinal'),('Атлет','атлет|atlet'),
             ('Спутник','спутник|sputnik'),('ДОН','\\bдон\\b'),('Багем','багем'),('ИСТОК','исток|istok'),
             ('Партнёр','партнер|partner'),('Композит','композит|kompozit'),('Викинг','викинг|viking'),
             ('Крепыш','крепыш'),('ALASKA','alaska|аляска'),('GTS','\\bgts\\b'),('Кремень','кремень')]
    for b, rx in table:
        if re.search(rx, n):
            return b
    return 'Другой'

def has_brake(specs, name):
    for s in specs:
        low = s.lower()
        if 'тормоз' in low:
            return 'без' not in low
    if 'тормоз' in name.lower():
        return True
    return False

def num(s):
    m = re.search(r'(\d[\d\s]*)', s.replace(' ', ' '))
    return int(m.group(1).replace(' ', '')) if m else None

def find_spec(specs, *keys):
    for s in specs:
        low = s.lower()
        for k in keys:
            if k in low:
                return s
    return None

def spec_val(specs, *keys):
    s = find_spec(specs, *keys)
    if not s:
        return None
    # значение — часть после метки
    return s

def derive(p):
    specs = p['specs']
    name = p['name']
    low = name.lower()

    # оси
    axes = None
    ax = find_spec(specs, 'осей/колёс', 'осей/колес', 'кол-во осей', 'количество осей')
    if ax:
        m = re.search(r'(\d)\s*/', ax) or re.search(r'осей\D*(\d)', ax.lower())
        if m: axes = int(m.group(1))
    if axes is None:
        if 'двухосн' in low or '2-х ос' in low or '2 ос' in low: axes = 2
        elif 'одноос' in low or '1 ос' in low: axes = 1
        else: axes = 1
    if axes and axes > 2:
        axes = 2

    # грузоподъёмность
    gruz = None
    g = find_spec(specs, 'грузоподъем', 'грузоподъём')
    if g: gruz = num(g)

    # полная масса
    massa = None
    mm = find_spec(specs, 'полная масса')
    if mm: massa = num(mm)

    # габариты кузова
    kuzov = None
    kz = find_spec(specs, 'размеры кузова', 'длина кузова')
    if kz: kuzov = re.sub(r'^[^\d]*', '', kz).strip()

    # тип
    if 'платформ' in low: kind = 'Платформа'
    elif 'лодоч' in low or 'катер' in low or 'водной техник' in low or 'плавсредств' in low: kind = 'Лодочный'
    elif 'крышк' in low or 'кофр' in low: kind = 'С крышкой'
    elif 'тент' in low: kind = 'С тентом'
    elif 'мото' in low: kind = 'Для мототехники'
    elif 'самосвал' in low: kind = 'Самосвальный'
    else: kind = 'Бортовой'

    # оригинальное описание из фактов
    parts = []
    parts.append(('Двухосный' if axes == 2 else 'Одноосный') + ' прицеп' +
                 ({'С тентом': ' с тентом', 'С крышкой': ' с пластиковой крышкой',
                   'Платформа': ' — открытая платформа', 'Лодочный': ' для перевозки лодок и катеров',
                   'Для мототехники': ' для мототехники', 'Самосвальный': ' с самосвальным кузовом',
                   'Бортовой': ''}[kind]) + '.')
    if massa or gruz:
        seg = []
        if massa: seg.append(f'полная масса {massa} кг')
        if gruz: seg.append(f'грузоподъёмность {gruz} кг')
        s = ', '.join(seg)
        parts.append(s[0].upper() + s[1:] + '.')
    if kuzov:
        parts.append(f'Размеры кузова {kuzov}.')
    susp = find_spec(specs, 'подвеска', 'рессор')
    wheels = find_spec(specs, 'размер колёс', 'размер колес')
    tail = []
    if susp and 'рессор' in susp.lower(): tail.append('рессорная подвеска')
    if wheels:
        wm = re.search(r'R\d{2}', wheels)
        if wm: tail.append(f'колёса {wm.group(0)}')
    if tail:
        parts.append((', '.join(tail)).capitalize() + '.')
    descr = ' '.join(parts)

    return {
        'name': name,
        'price': p['price'],
        'old': p.get('old'),
        'img': (p['imgs'][0] if p['imgs'] else ''),
        'imgs': p['imgs'][:5],
        'brand': brand_of(name),
        'kind': kind,
        'axes': axes,
        'gruz': gruz,
        'massa': massa,
        'brake': has_brake(specs, name),
        'descr': descr,
        'specs': specs,
    }

DROP = re.compile(r'тележк|напольн|яхт|d3 \(zn\)|6,5х2,45|напольная', re.I)
out = []
for p in src:
    if not p.get('price'):
        continue
    if p['price'] > 700000:          # отсечь крупные/коммерческие, проскочившие фильтр
        continue
    if DROP.search(p['name']):
        continue
    d = derive(p)
    if d['gruz'] and d['gruz'] > 2200:   # реально тяжёлые — не для этой аудитории
        continue
    out.append(d)

# сортировка по цене
out.sort(key=lambda x: x['price'])
# id
for i, x in enumerate(out, 1):
    x['id'] = i

json.dump(out, open('products.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'Готово: {len(out)} товаров -> products.json')
from collections import Counter
print('Типы:', dict(Counter(x['kind'] for x in out)))
print('Оси:', dict(Counter(x['axes'] for x in out)))
print('Пример descr:', out[0]['descr'])
print('Цены:', out[0]['price'], '..', out[-1]['price'])

import json
import time
import urllib.parse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

dates = [(datetime.today() + timedelta(days=i)).strftime('%d/%m/%Y') for i in range(8)]
result = {'lastUpdate': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), 'days': {}}

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        locale='es-ES',
        viewport={'width': 1280, 'height': 800},
        extra_http_headers={'Accept-Language': 'es-ES,es;q=0.9'}
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    page = context.new_page()

    print('Warmup...')
    try:
        page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                  wait_until='domcontentloaded', timeout=30000)
        time.sleep(5)
    except Exception as e:
        print(f'  Warmup error (ignorato): {e}')

    for date in dates:
        print(f'Fetching {date}...')
        captured = {}

        def on_response(response):
            if 'hexagonal/horarios' in response.url and response.status == 200:
                parsed = urllib.parse.urlparse(response.url)
                params = urllib.parse.parse_qs(parsed.query)
                fecha = params.get('fechaIda', [''])[0]
                print(f'  Intercettata API fecha={fecha} -> HTTP {response.status}')
                try:
                    body = response.body()
                    captured['data'] = json.loads(body.decode('utf-8'))
                    captured['fecha'] = fecha
                    print(f'  Body OK: {len(body)} bytes')
                except Exception as e:
                    print(f'  Parse error: {e}')

        page.on('response', on_response)

        d, m, y = date.split('/')
        url = f'https://www.balearia.com/es/horarios-ibiza-formentera?fechaIda={y}-{m}-{d}'
        print(f'  Navigating: {url}')

        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            print(f'  Goto error: {e}')

        time.sleep(5)

        if 'data' in captured:
            result['days'][date] = captured['data']
            ida = len((captured['data'].get('horariosIda') or [{}])[0].get('horarios', []))
            vuelta = len((captured['data'].get('horariosVuelta') or [{}])[0].get('horarios', []))
            print(f'  OK: {date} - {ida} corse andata, {vuelta} ritorno')
        else:
            print(f'  FAIL: nessuna API intercettata per {date}')

        page.remove_listener('response', on_response)
        time.sleep(3)

    browser.close()

with open('orari.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

giorni = len(result['days'])
print(f'\nSalvato orari.json con {giorni} giorni')

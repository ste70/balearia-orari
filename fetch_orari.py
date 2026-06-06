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

    all_captured = {}

    def on_response(response):
        if 'hexagonal/horarios' in response.url and response.status == 200:
            parsed = urllib.parse.urlparse(response.url)
            params = urllib.parse.parse_qs(parsed.query)
            fecha = params.get('fechaIda', [''])[0]
            print(f'  Intercettata API fecha={fecha} -> HTTP {response.status}')
            try:
                body = response.body()
                data = json.loads(body.decode('utf-8'))
                all_captured[fecha] = data
                print(f'  Salvato fecha={fecha} ({len(body)} bytes)')
            except Exception as e:
                print(f'  Parse error: {e}')

    page = context.new_page()
    page.on('response', on_response)

    print('Warmup...')
    try:
        page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                  wait_until='domcontentloaded', timeout=30000)
        time.sleep(4)
    except Exception as e:
        print(f'  Warmup error (ignorato): {e}')

    for date in dates:
        print(f'Fetching {date}...')
        d, m, y = date.split('/')
        url = f'https://www.balearia.com/es/horarios-ibiza-formentera?fechaIda={y}-{m}-{d}'
        print(f'  Navigating: {url}')
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            print(f'  Goto error: {e}')
        time.sleep(4)

    browser.close()

print(f'\nCapturati {len(all_captured)} giorni: {list(all_captured.keys())}')

for fecha, data in all_captured.items():
    parts = fecha.split('/')
    if len(parts) == 3:
        date_key = fecha
        result['days'][date_key] = data
        ida = len((data.get('horariosIda') or [{}])[0].get('horarios', []))
        vuelta = len((data.get('horariosVuelta') or [{}])[0].get('horarios', []))
        print(f'  OK: {date_key} - {ida} corse andata, {vuelta} ritorno')

with open('orari.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

giorni = len(result['days'])
print(f'Salvato orari.json con {giorni} giorni')

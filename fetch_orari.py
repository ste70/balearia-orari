import json
import time
import urllib.parse
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

today = datetime.today()
date_display = today.strftime('%d/%m/%Y')
date_iso = today.strftime('%Y-%m-%d')

result = {'lastUpdate': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), 'days': {}}

print('Fetching Trasmapi...')
trasmapi = {'ida': [], 'vuelta': []}

for endpoint, key in [('ws_horariosida.php', 'ida'), ('ws_horariosvue.php', 'vuelta')]:
    try:
        r = requests.post(
            f'https://www.trasmapi.com/lib/php/{endpoint}',
            data={'fecha': date_iso, 'ruta': 'if'},
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
                'Referer': 'https://www.trasmapi.com/horarios',
                'Origin': 'https://www.trasmapi.com',
            },
            timeout=15
        )
        print(f'  Trasmapi {key}: HTTP {r.status_code}')
        if r.status_code == 200:
            trasmapi[key] = r.json()
            print(f'  OK: {len(str(trasmapi[key]))} bytes')
    except Exception as e:
        print(f'  Trasmapi error {key}: {e}')

print('Fetching Balearia...')
balearia = {'ida': [], 'vuelta': []}

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        locale='es-ES',
        viewport={'width': 1280, 'height': 800},
        extra_http_headers={'Accept-Language': 'es-ES,es;q=0.9'}
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)

    page = context.new_page()

    try:
        # Warmup
        page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                  wait_until='domcontentloaded', timeout=30000)
        time.sleep(5)

        # Seconda visita con expect_response sincrono
        with page.expect_response(
            lambda r: 'hexagonal/horarios' in r.url and r.status == 200,
            timeout=20000
        ) as response_info:
            page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                      wait_until='domcontentloaded', timeout=30000)

        response = response_info.value
        body = response.body()
        data = json.loads(body.decode('utf-8'))
        balearia['ida']    = (data.get('horariosIda') or [{}])[0].get('horarios', [])
        balearia['vuelta'] = (data.get('horariosVuelta') or [{}])[0].get('horarios', [])
        print(f'  Balearia OK: {len(balearia["ida"])} ida, {len(balearia["vuelta"])} vuelta')

    except Exception as e:
        print(f'  Balearia errore: {e}')

    browser.close()

result['days'][date_display] = {
    'balearia': balearia,
    'trasmapi': trasmapi,
}

with open('orari.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'\nSalvato orari.json - {date_display}')
print(f'  Balearia ida: {len(balearia["ida"])} corse')
print(f'  Balearia vuelta: {len(balearia["vuelta"])} corse')
print(f'  Trasmapi ida: {len(trasmapi["ida"])}')
print(f'  Trasmapi vuelta: {len(trasmapi["vuelta"])}')

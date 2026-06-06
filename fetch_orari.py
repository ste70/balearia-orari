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

# ── TRASMAPI ──────────────────────────────────────────────────────────────────
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

# ── BALEARIA ──────────────────────────────────────────────────────────────────
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

    captured = {}

    def on_response(response):
        if 'hexagonal/horarios' in response.url and response.status == 200:
            parsed = urllib.parse.urlparse(response.url)
            params = urllib.parse.parse_qs(parsed.query)
            fecha = params.get('fechaIda', [''])[0]
            try:
                body = response.body()
                captured[fecha] = json.loads(body.decode('utf-8'))
                print(f'  Balearia salvato {fecha} ({len(body)} bytes)')
            except Exception as e:
                print(f'  Balearia parse error: {e}')

    page = context.new_page()
    page.on('response', on_response)

    try:
        # Prima visita warmup
        page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                  wait_until='domcontentloaded', timeout=30000)
        time.sleep(8)
        # Seconda visita - cattura i dati
        page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                  wait_until='domcontentloaded', timeout=30000)
        time.sleep(10)
    except Exception as e:
        print(f'  Balearia errore: {e}')

    browser.close()

if date_display in captured:
    data = captured[date_display]
    balearia['ida']    = (data.get('horariosIda') or [{}])[0].get('horari

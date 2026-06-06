import json
import time
import urllib.parse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

days_needed = 7
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

    captured = {}

    def on_response(response):
        if 'hexagonal/horarios' in response.url and response.status == 200:
            parsed = urllib.parse.urlparse(response.url)
            params = urllib.parse.parse_qs(parsed.query)
            fecha = params.get('fechaIda', [''])[0]
            print(f'  Intercettata API fecha={fecha} -> HTTP {response.status}')
            try:
                body = response.body()
                captured[fecha] = json.loads(body.decode('utf-8'))
                print(f'  Salvato {fecha} ({len(body)} bytes)')
            except Exception as e:
                print(f'  Parse error: {e}')

    page = context.new_page()
    page.on('response', on_response)

    print('Caricamento pagina...')
    try:
        page.goto('https://www.balearia.com/es/horarios-ibiza-formentera',
                  wait_until='domcontentloaded', timeout=30000)
        time.sleep(4)
    except Exception as e:
        print(f'  Errore caricamento: {e}')

    print(f'Pagina caricata, oggi catturato. Avanzo di {days_needed-1} giorni...')

    for i in range(days_needed - 1):
        try:
            # Clicca freccia avanti >
            next_btn = page.locator('button:has-text(">"), [aria-label*="siguiente"], [aria-label*="next"]').first
            if not next_btn.count():
                # Prova con SVG o altri selettori
                next_btn = page.locator('.date-nav button:last-child, .calendar-nav button:last-child').first
            next_btn.click(timeout=5000)
            print(f'  Click giorno +{i+1}')
            time.sleep(3)
        except Exception as e:
            print(f'  Click error giorno +{i+1}: {e}')

    browser.close()

print(f'\nCapturati {len(captured)} giorni: {list(captured.keys())}')

for fecha, data in captured.items():
    result['days'][fecha] = data
    ida = len((data.get('horariosIda') or [{}])[0].get('horarios', []))
    vuelta = len((data.get('horariosVuelta') or [{}])[0].get('horarios', []))
    print(f'  OK: {fecha} - {ida} corse andata, {vuelta} ritorno')

with open('orari.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'Salvato orari.json con {len(result["days"])} giorni')

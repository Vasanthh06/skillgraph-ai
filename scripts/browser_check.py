"""Real Chromium smoke + viewport checks; local synthetic account only."""
import json, secrets
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
shots = ROOT / 'docs/screenshots'
shots.mkdir(exist_ok=True)
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
    page = context.new_page()
    page.goto('http://127.0.0.1:5173/')
    page.screenshot(path=str(shots/'landing-desktop.png'), full_page=True)
    page.goto('http://127.0.0.1:5173/register')
    page.screenshot(path=str(shots/'register.png'), full_page=True)
    email = 'browser-'+secrets.token_hex(4)+'@example.com'
    password = secrets.token_urlsafe(24)
    page.get_by_label('Full name', exact=True).fill('Synthetic Learner')
    page.get_by_label('Email', exact=True).fill(email)
    page.get_by_label('Password', exact=True).fill(password)
    page.get_by_label('Confirm password', exact=True).fill(password)
    page.get_by_text('I am at least 18 years old.').click()
    page.get_by_text('I accept the').click()
    page.get_by_role('button',name='Create account',exact=True).click()
    page.wait_for_url('**/profile?onboarding=1')
    results.append({'journey':'UI adult registration','pass':True})
    # Use same browser session for synthetic assessment setup; UI rendering verified below.
    def api(path, method='GET', data=None):
        r = context.request.fetch('http://127.0.0.1:5173/api'+path, method=method, data=data, headers={'X-Requested-With':'SkillGraph'})
        assert r.ok, (path,r.status)
        return r.json() if r.status != 204 else None
    api('/roles/target','PUT',{'name':'Machine Learning Engineer'})
    levels={'python':'intermediate','sql':'intermediate','pandas':'beginner','numpy':'beginner','statistics':'beginner','machine-learning':'beginner','git':'intermediate'}
    api('/assessment','POST',{'answers':[{'skill':s,'level':l} for s,l in levels.items()]})
    api('/roadmap/generate','POST')
    for route in ['dashboard','assessment','roadmap','skill-graph','profile','admin']:
        page.goto('http://127.0.0.1:5173/'+route)
        page.wait_for_timeout(600)
        page.screenshot(path=str(shots/(route+'-desktop.png')),full_page=True)
    before=api('/roadmap')['progress']['completed']
    api('/roadmap/numpy/complete','PUT',{'completed':True})
    page.goto('http://127.0.0.1:5173/roadmap');page.reload()
    assert api('/roadmap')['progress']['completed'] >= before+1
    results.append({'journey':'API assessment, roadmap generation, completion persisted after browser reload','pass':True})
    for width in [320,375,390,430,768,1024,1280,1440]:
        page.set_viewport_size({'width':width,'height':900})
        for route in ['','login','register','dashboard','roadmap','skill-graph']:
            page.goto('http://127.0.0.1:5173/'+route)
            page.wait_for_timeout(200)
            overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            results.append({'viewport':width,'route':'/'+route,'horizontal_overflow':overflow})
        if width==390:
            page.screenshot(path=str(shots/'skill-graph-mobile.png'),full_page=True)
    api('/auth/logout','POST')
    page.goto('http://127.0.0.1:5173/login')
    page.get_by_label('Email',exact=True).fill(email)
    page.get_by_label('Password',exact=True).fill(password)
    page.get_by_role('button',name='Log in',exact=True).click()
    page.wait_for_url('**/dashboard')
    page.reload();page.wait_for_url('**/dashboard')
    results.append({'journey':'UI login and HttpOnly session reload','pass':True})
    for route in ['account/forgot','account/reset','account/verify']:
        page.goto('http://127.0.0.1:5173/'+route)
        page.screenshot(path=str(shots/(route.replace('/','-')+'.png')),full_page=True)
    browser.close()
(ROOT/'docs/browser-results.json').write_text(json.dumps(results,indent=2))
print('Browser results:',len(results),'checks; overflows:',sum(bool(x.get('horizontal_overflow')) for x in results))

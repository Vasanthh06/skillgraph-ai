"""Local-only synthetic administrator + normal-motion smoke evidence. Never use on production.
Requires the isolated preview SQLite path in UI_TEST_DB. No credentials are written to disk.
"""
import json,os,secrets,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]; E=R/'docs/ui-evidence'; S=E/'screenshots'
BASE=os.getenv('UI_BASE_URL','http://127.0.0.1:5174')
DB=os.environ['UI_TEST_DB']
checks=[]
def record(name,ok):
    checks.append({'check':name,'pass':bool(ok)});assert ok,name
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-sandbox'])
    c=b.new_context(viewport={'width':1440,'height':1000},color_scheme='light',reduced_motion='no-preference')
    page=c.new_page();page.goto(BASE)
    page.get_by_role('link',name='Explore how it works',exact=True).click()
    page.locator('#how-it-works').wait_for()
    page.wait_for_timeout(800)
    record('normal motion anchor reaches workflow',page.evaluate('Math.abs(document.querySelector("#how-it-works").getBoundingClientRect().top-80)<150'))
    page.get_by_role('link',name='Build my roadmap',exact=True).click();page.wait_for_url('**/register')
    record('normal motion does not block CTA',page.url.endswith('/register'))
    page.goto(BASE);page.get_by_role('button',name='Select JavaScript',exact=True).click()
    record('normal motion graph remains interactive',page.get_by_role('button',name='Select JavaScript',exact=True).get_attribute('aria-pressed')=='true')
    page.emulate_media(reduced_motion='reduce')
    record('runtime reduced-motion change disables animation',page.locator('.demo-node').first.evaluate('(e)=>getComputedStyle(e).animationName')=='none')
    # Synthetic admin provisioning is restricted to the isolated local QA database.
    password=secrets.token_urlsafe(28);email='admin-ui-'+secrets.token_hex(4)+'@example.com'
    response=c.request.post(BASE+'/api/auth/register',headers={'X-Requested-With':'SkillGraph'},data={
        'full_name':'Synthetic Administrator','email':email,'password':password,'confirm_password':password,'adult_eligible':True,'terms_accepted':True})
    assert response.status==201,response.status
    uid=response.json()['user']['id']
    with sqlite3.connect(DB) as connection:
        assert connection.execute('SELECT email FROM users WHERE id=?',(uid,)).fetchone()[0]==email
        connection.execute('UPDATE account_security SET is_admin=1 WHERE user_id=?',(uid,))
    for theme in ['light','dark']:
        page.goto(BASE+'/admin');page.get_by_role('button',name=theme.title()+' theme',exact=True).click()
        page.get_by_role('heading',name='Account administration').wait_for()
        page.get_by_label('Search names').fill('Synthetic Administrator')
        page.wait_for_timeout(300)
        record('authorized admin table '+theme,page.get_by_role('cell',name='Synthetic Administrator',exact=True).is_visible())
        page.screenshot(path=str(S/('admin-'+theme+'-desktop.png')),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(S/'admin-dark-mobile.png'),full_page=True)
    # The normal user access-denial path is separately tested in the main browser suite.
    c.request.post(BASE+'/api/auth/logout',headers={'X-Requested-With':'SkillGraph'})
    b.close()
E.joinpath('supplemental-results.json').write_text(json.dumps(checks,indent=2))
print(json.dumps({'checks':len(checks),'failed':sum(not x['pass'] for x in checks)},indent=2))

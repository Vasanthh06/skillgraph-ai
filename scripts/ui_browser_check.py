"""Premium UI browser acceptance. Requires running API + Vite at UI_BASE_URL.
Synthetic local accounts only; no email requests. Playwright is QA tooling, not a runtime dependency.
"""
import json, os, secrets
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/ui-evidence'
SHOTS=EVIDENCE/'screenshots'
SHOTS.mkdir(parents=True,exist_ok=True)
BASE=os.getenv('UI_BASE_URL','http://127.0.0.1:5174')
AXE=os.getenv('AXE_PATH','/home/user/skillgraph_ui/qa-tools/node_modules/axe-core/axe.min.js')
results=[];errors=[];violations=[]

def record(name, condition, **extra):
    results.append({'check':name,'pass':bool(condition),**extra})
    assert condition, (name,extra)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1050},color_scheme='light',reduced_motion='reduce')
    page=context.new_page()
    page.on('pageerror',lambda e:errors.append(str(e)))
    def ready(path):
        page.goto(BASE+path)
        page.get_by_role('switch',name='Dark mode',exact=True).wait_for()
        page.wait_for_timeout(160)
    def theme(name):
        if name == 'system':
            page.evaluate("localStorage.removeItem('sg_theme')")
            page.reload()
        elif page.locator('html').get_attribute('data-theme') != name:
            page.get_by_role('switch',name='Dark mode',exact=True).click()
        expected=name if name!='system' else 'light'
        page.wait_for_function('(v)=>document.documentElement.dataset.theme===v',arg=expected)
    def shot(name):
        # Scroll real sections into view so finite IntersectionObserver reveals complete.
        page.evaluate('async()=>{for(let y=0;y<document.body.scrollHeight;y+=650){scrollTo(0,y);await new Promise(r=>requestAnimationFrame(r));}scrollTo(0,0)}')
        page.wait_for_timeout(100)
        page.screenshot(path=str(SHOTS/(name+'.png')),full_page=True)
    def axe(route,mode):
        if not Path(AXE).exists(): return
        page.add_script_tag(path=AXE)
        report=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
        for v in report['violations']:
            violations.append({'route':route,'theme':mode,'id':v['id'],'impact':v['impact'],'nodes':[{'html':n['html'],'failure':n.get('failureSummary','')} for n in v['nodes']]})
    # Public routes and persistence, including System OS changes.
    ready('/')
    record('initial system follows light OS',page.locator('html').get_attribute('data-theme')=='light')
    theme('dark'); page.reload();record('dark survives refresh',page.locator('html').get_attribute('data-theme')=='dark')
    theme('light'); page.reload();record('light survives refresh',page.locator('html').get_attribute('data-theme')=='light')
    theme('system');page.emulate_media(color_scheme='dark');page.wait_for_timeout(100)
    record('system reacts to OS dark',page.locator('html').get_attribute('data-theme')=='dark')
    page.emulate_media(color_scheme='light');page.wait_for_timeout(100)
    record('system reacts to OS light',page.locator('html').get_attribute('data-theme')=='light')
    for mode in ['light','dark']:
        theme(mode)
        for route in ['/','/login','/register','/account/forgot','/account/reset','/account/verify','/privacy','/terms']:
            ready(route)
            record('public theme '+mode+' '+route,page.locator('html').get_attribute('data-theme')==mode)
        ready('/');shot('landing-'+mode+'-desktop');axe('/',mode)
    page.get_by_role('button',name='Select APIs',exact=True).focus();page.keyboard.press('Enter')
    record('illustrative graph keyboard selection',page.get_by_role('button',name='Select APIs',exact=True).get_attribute('aria-pressed')=='true')
    page.get_by_role('button',name='03 Apply & refine',exact=True).click()
    record('example roadmap interaction',page.get_by_text('Put the pieces together',exact=True).is_visible())
    page.get_by_role('link',name='Build my roadmap',exact=True).click();page.wait_for_url('**/register')
    record('landing registration CTA',page.url.endswith('/register'))
    # Real UI registration.
    email='ui-'+secrets.token_hex(4)+'@example.com';password=secrets.token_urlsafe(24)
    page.get_by_label('Full name',exact=True).fill('Demo Learner')
    page.get_by_label('Email',exact=True).fill(email)
    page.get_by_label('Password',exact=True).fill(password)
    page.get_by_label('Confirm password',exact=True).fill(password)
    page.get_by_text('I am at least 18 years old.').click();page.get_by_text('I accept the').click()
    page.get_by_role('button',name='Create account',exact=True).click();page.wait_for_url('**/profile?onboarding=1')
    record('UI registration',True)
    def api(path,method='GET',body=None):
        response=context.request.fetch(BASE+'/api'+path,method=method,data=body,headers={'X-Requested-With':'SkillGraph'})
        assert response.ok,(path,response.status)
        return response.json() if response.status!=204 else None
    api('/roles/target','PUT',{'name':'Machine Learning Engineer'})
    levels={'python':'intermediate','sql':'intermediate','pandas':'beginner','numpy':'beginner','statistics':'beginner','machine-learning':'beginner','git':'intermediate'}
    api('/assessment','POST',{'answers':[{'skill':s,'level':l} for s,l in levels.items()]})
    api('/roadmap/generate','POST')
    # History buttons and browser history. Start direct so Back cannot leave the application.
    ready('/dashboard')
    record('direct dashboard back unavailable',page.get_by_role('button',name='Back',exact=True).is_disabled())
    page.get_by_role('navigation',name='Main',exact=True).get_by_role('link',name='Profile',exact=True).click();page.wait_for_url('**/profile')
    page.get_by_role('navigation',name='Profile sections',exact=True).get_by_role('link',name='Assessment',exact=True).click();page.wait_for_url('**/assessment')
    page.get_by_role('navigation',name='Main',exact=True).get_by_role('link',name='Learning Roadmap',exact=True).click();page.wait_for_url('**/roadmap')
    history_length=page.evaluate('history.length')
    page.get_by_role('button',name='Back',exact=True).click();page.wait_for_url('**/assessment')
    record('router Back previous real entry',page.url.endswith('/assessment'))
    page.get_by_role('button',name='Forward',exact=True).click();page.wait_for_url('**/roadmap')
    record('router Forward restores next entry',page.url.endswith('/roadmap'))
    page.go_back();page.wait_for_url('**/assessment');page.go_forward();page.wait_for_url('**/roadmap')
    record('browser back and forward',True)
    record('history controls create no extra entries',page.evaluate('history.length')==history_length)
    page.go_back();page.wait_for_url('**/assessment');page.reload();page.get_by_role('button',name='Forward',exact=True).wait_for();page.wait_for_timeout(100)
    record('forward availability survives reload',page.get_by_role('button',name='Forward',exact=True).is_enabled())
    page.get_by_role('button',name='Forward',exact=True).click();page.wait_for_url('**/roadmap')
    # Dirty forms: guard route links, our controls and native browser history without losing draft.
    page.get_by_role('navigation',name='Main',exact=True).get_by_role('link',name='Profile',exact=True).click();page.wait_for_url('**/profile')
    page.get_by_label('Location',exact=True).fill('Unsaved draft')
    page.get_by_role('button',name='Back',exact=True).click()
    dialog=page.get_by_role('alertdialog');dialog.wait_for()
    record('Back opens unsaved guard',dialog.is_visible())
    page.get_by_role('button',name='Stay and save',exact=True).click()
    record('cancel keeps draft',page.get_by_label('Location',exact=True).input_value()=='Unsaved draft')
    page.evaluate('history.back()');dialog.wait_for();page.keyboard.press('Escape');page.wait_for_timeout(100)
    record('browser Back guarded and Escape cancels',page.url.endswith('/profile'))
    page.get_by_role('navigation',name='Main',exact=True).get_by_role('link',name='Learning Roadmap',exact=True).click();dialog.wait_for()
    page.get_by_role('button',name='Leave without saving',exact=True).click();page.wait_for_url('**/roadmap')
    record('confirmed route transition discards draft',True)
    # Verify real progress persistence unchanged.
    before=api('/roadmap')['progress']['completed'];api('/roadmap/numpy/complete','PUT',{'completed':True});page.reload()
    record('roadmap progress persists',api('/roadmap')['progress']['completed']>=before+1)
    direct=context.new_page();direct.goto(BASE+'/roadmap')
    direct.get_by_role('button',name='Back',exact=True).click();direct.wait_for_url('**/dashboard')
    record('direct-entry Back uses safe dashboard fallback',True)
    direct.close()
    page.get_by_role('navigation',name='Main',exact=True).get_by_role('link',name='Profile',exact=True).click();page.wait_for_url('**/profile')
    page.get_by_role('navigation',name='Profile sections',exact=True).get_by_role('link',name='Assessment',exact=True).click();page.wait_for_url('**/assessment')
    page.get_by_role('button',name='Back',exact=True).click();page.wait_for_url('**/profile')
    page.get_by_role('navigation',name='Main',exact=True).get_by_role('link',name='Learning Roadmap',exact=True).click();page.wait_for_url('**/roadmap')
    record('branching clears unavailable Forward',page.get_by_role('button',name='Forward',exact=True).is_disabled())
    ready('/')
    page.get_by_role('link',name='Open my dashboard',exact=True).click();page.wait_for_url('**/dashboard')
    record('authenticated landing CTA avoids registration',True)
    private=['/dashboard','/profile','/onboarding','/assessment','/role','/skill-graph','/projects','/skill-gap','/roadmap','/learn','/jobs','/interview','/resume','/explore','/admin']
    for mode in ['light','dark']:
        theme(mode)
        for route in private:
            ready(route)
            record('private theme '+mode+' '+route,page.locator('html').get_attribute('data-theme')==mode)
            record('history visible '+mode+' '+route,page.get_by_role('navigation',name='Page history',exact=True).is_visible())
            if route in ['/dashboard','/roadmap','/skill-graph','/profile']:
                shot(route[1:]+'-'+mode+'-desktop');axe(route,mode)
        record('normal user still denied admin', 'Administrator permission required' in page.locator('main').inner_text())
    # Every implemented private route at every requested width in both themes.
    for mode in ['light','dark']:
        theme(mode)
        for width in [320,375,390,430,768,1024,1280,1440]:
            page.set_viewport_size({'width':width,'height':900})
            for route in private:
                ready(route)
                overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                results.append({'check':'viewport','theme':mode,'route':route,'width':width,'pass':not overflow})
            if width==390:
                ready('/dashboard');shot('dashboard-'+mode+'-mobile')
                ready('/skill-graph');shot('skill-graph-'+mode+'-mobile')
    # Real login, refresh session, protected route after logout; public mobile matrix signed out.
    api('/auth/logout','POST');ready('/login')
    page.get_by_label('Email',exact=True).fill(email);page.get_by_label('Password',exact=True).fill(password)
    page.get_by_role('button',name='Log in',exact=True).click();page.wait_for_url('**/dashboard');page.reload()
    record('UI login plus refresh stays authenticated','/dashboard' in page.url)
    api('/auth/logout','POST');ready('/roadmap');page.wait_for_url('**/login')
    record('protected route remains protected',page.url.endswith('/login'))
    for mode in ['light','dark']:
        theme(mode)
        for width in [320,375,390,430,768,1024,1280,1440]:
            page.set_viewport_size({'width':width,'height':900})
            for route in ['/','/login','/register','/account/forgot','/account/reset','/account/verify','/privacy','/terms']:
                ready(route)
                overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                results.append({'check':'viewport','theme':mode,'route':route,'width':width,'pass':not overflow})
            if width==390:
                ready('/');shot('landing-'+mode+'-mobile');ready('/login');shot('login-'+mode+'-mobile')
    record('no JavaScript page errors',not errors,errors=errors)
    # Reduced motion static computed state; browser has no WebGL dependency.
    ready('/')
    record('reduced motion disables graph animation',page.locator('.demo-node').first.evaluate('(e)=>getComputedStyle(e).animationName')=='none')
    browser.close()
EVIDENCE.joinpath('browser-results.json').write_text(json.dumps(results,indent=2))
EVIDENCE.joinpath('axe-results.json').write_text(json.dumps(violations,indent=2))
EVIDENCE.joinpath('page-errors.json').write_text(json.dumps(errors,indent=2))
print(json.dumps({'checks':len(results),'failed':sum(not r['pass'] for r in results),'viewport_checks':sum(r['check']=='viewport' for r in results),'axe_violations':len(violations),'screenshots':len(list(SHOTS.glob('*.png')))},indent=2))

assert all(r["pass"] for r in results), "Browser checks failed; inspect browser-results.json"

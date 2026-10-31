from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'docs/ui-evidence'; checks=[]
BASE=os.getenv('UI_BASE_URL','http://127.0.0.1:5174')
with sync_playwright() as p:
 b=p.chromium.launch(args=['--no-sandbox']);c=b.new_context(viewport={'width':1440,'height':1050},color_scheme='light',reduced_motion='reduce');page=c.new_page()
 for width in [320,375,390,430,768,1024,1280,1440]:
  page.set_viewport_size({'width':width,'height':1000});page.goto(BASE+'/')
  switch=page.get_by_role('switch',name='Dark mode',exact=True);switch.wait_for()
  assert switch.count()==1
  assert page.get_by_text('Your space. Your perspective.',exact=True).count()==0
  for mode in ['light','dark']:
   if page.locator('html').get_attribute('data-theme')!=mode:switch.click()
   assert switch.get_attribute('aria-checked')==('true' if mode=='dark' else 'false')
   page.reload();assert page.locator('html').get_attribute('data-theme')==mode
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   card=page.locator('.hero-graph-card').bounding_box();label=page.locator('.graph-floating-label')
   if label.is_visible():
    box=label.bounding_box();assert box['y']>=card['y']+card['height']+10
   checks.append({'width':width,'theme':mode,'single_switch':True,'persistence':True,'no_overflow':True,'callout_no_overlap':True})
  if width in [390,1440]:
   page.screenshot(path=str(root/'screenshots'/f'toggle-fix-{width}.png'))
 page.goto(BASE+'/login');switch=page.get_by_role('switch',name='Dark mode',exact=True);switch.focus();old=switch.get_attribute('aria-checked');page.keyboard.press('Space');assert switch.get_attribute('aria-checked')!=old
 page.add_script_tag(path=os.environ['AXE_PATH']);report=page.evaluate('async()=>await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})');assert not report['violations'],report['violations']
 b.close()
(root/'toggle-results.json').write_text(json.dumps({'viewport_theme_checks':checks,'keyboard_toggle':True,'sample_login_axe_violations':0},indent=2))
print('16 viewport/theme checks passed; keyboard and sampled login accessibility checks passed.')

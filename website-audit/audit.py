"""Bounded website audit prototype; run against the included local fixture only."""
import argparse
from collections import Counter, deque
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin, urlsplit, urldefrag
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

AGENT = 'GEOAuditDemo'
PAGES = {
    '/': '<title>Programs</title><meta name="description" content="Find programs"><h1>Programs</h1><a href="/a">A</a><a href="/b">B</a><a href="/old">Old</a><a href="/missing">Missing</a><a href="/private">Private</a><a href="/dynamic">Dynamic</a>',
    '/a': '<title>Degree</title><h1>Data science</h1><img src="/image.png"><link rel="canonical" href="/a">',
    '/b': '<title>Degree</title><h1>Analytics</h1><img src="/image.png" alt="">',
    '/dynamic': '<title>Dynamic</title><script>document.addEventListener("DOMContentLoaded",()=>{document.body.insertAdjacentHTML("beforeend","<h1>Rendered program</h1>")})</script>',
}

@contextmanager
def fixture():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/old':
                self.send_response(301); self.send_header('Location', '/a'); self.end_headers(); return
            status = 200 if path in PAGES or path == '/robots.txt' else 404
            body = 'User-agent: *\nDisallow: /private\n' if path == '/robots.txt' else '<html><body>' + PAGES.get(path, 'Not found') + '</body></html>'
            self.send_response(status)
            self.send_header('Content-Type', 'text/plain' if path == '/robots.txt' else 'text/html; charset=utf-8')
            self.end_headers(); self.wfile.write(body.encode())
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}'
    finally: server.shutdown(); server.server_close(); thread.join()


def crawl(base, limit=20):
    # Only the fixture's exact origin is eligible; do not follow external redirects.
    if not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    origin = urlsplit(base)
    def in_scope(url):
        u = urlsplit(url)
        return (u.scheme, u.netloc) == (origin.scheme, origin.netloc)
    if origin.hostname != '127.0.0.1': raise ValueError('Local fixture only')
    session = requests.Session(); session.trust_env = False
    session.headers['User-Agent'] = AGENT
    robots_response = session.get(base+'/robots.txt', timeout=5, allow_redirects=False)
    robots_response.raise_for_status()
    if robots_response.status_code != 200: raise RuntimeError('robots.txt unavailable')
    robots = RobotFileParser(); robots.parse(robots_response.text.splitlines())
    queue, seen, rows = deque([base+'/']), set(), []
    while queue and len(seen) < limit:
        url = queue.popleft()
        if url in seen or not in_scope(url) or not robots.can_fetch(AGENT, url): continue
        seen.add(url)
        row = dict(path=urlsplit(url).path, status=None, is_html=False, title='', description='', h1_count=0, canonical='', missing_alt=0, redirect='', error='')
        try:
            r = session.get(url, timeout=5, allow_redirects=False)
            row['status'] = r.status_code
            if 300 <= r.status_code < 400 and r.headers.get('Location'):
                target = urljoin(url, r.headers['Location']); row['redirect'] = urlsplit(target).path if in_scope(target) else target
                if in_scope(target): queue.append(target)
            elif r.ok and 'text/html' in r.headers.get('Content-Type', ''):
                row['is_html'] = True
                soup = BeautifulSoup(r.text, 'html.parser')
                title = soup.find('title'); meta = soup.find('meta', attrs={'name':'description'}); canonical = soup.find('link', rel='canonical')
                row.update(title=title.get_text(strip=True) if title else '', description=meta.get('content','').strip() if meta else '', h1_count=len(soup.find_all('h1')), canonical=canonical.get('href','') if canonical else '', missing_alt=sum(not i.has_attr('alt') for i in soup.find_all('img')))
                for link in soup.select('a[href]'):
                    target = urldefrag(urljoin(url, link['href'])).url
                    if in_scope(target): queue.append(target)
        except requests.RequestException as exc: row['error'] = type(exc).__name__
        rows.append(row)
    session.close()
    titles = Counter(r['title'] for r in rows if r['title'])
    for r in rows:
        issues = []
        if r['error']: issues.append('request_error')
        elif r['status'] >= 400: issues.append('http_error')
        elif r['redirect']: issues.append('redirect')
        elif r['is_html']:
            if not r['title']: issues.append('missing_title')
            if not r['description']: issues.append('missing_description')
            if not r['h1_count']: issues.append('missing_static_h1')
            if titles[r['title']] > 1: issues.append('duplicate_title')
            if r['missing_alt']: issues.append('missing_alt_attribute')
        r['issues'] = ';'.join(issues)
    columns = ['path', 'status', 'is_html', 'title', 'description', 'h1_count',
               'canonical', 'missing_alt', 'redirect', 'error', 'issues']
    return pd.DataFrame(rows, columns=columns).sort_values('path').reset_index(drop=True)


def browser_check(base, executable=None):
    if urlsplit(base).hostname != '127.0.0.1':
        raise ValueError('Local fixture only')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        try:
            page = browser.new_page()
            page.route('**/*', lambda route: route.abort())
            with requests.Session() as session:
                session.trust_env = False
                response = session.get(base+'/dynamic', timeout=5, allow_redirects=False)
                response.raise_for_status()
            page.set_content(response.text, wait_until='domcontentloaded')
            return page.locator('h1').inner_text(timeout=5000)
        finally: browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='sample_outputs/audit.csv')
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--chromium-path', default=None)
    args = parser.parse_args()
    with fixture() as base:
        frame = crawl(base)
        output = Path(args.out); output.parent.mkdir(parents=True, exist_ok=True); frame.to_csv(output, index=False)
        print(f'{len(frame)} pages recorded; {sum(frame.issues != "")} pages flagged')
        if args.browser: print('Rendered H1:', browser_check(base, args.chromium_path))

if __name__ == '__main__': main()

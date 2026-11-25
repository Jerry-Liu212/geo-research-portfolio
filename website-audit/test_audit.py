from audit import fixture, crawl, browser_check
import os
import pytest


def test_crawl():
    with fixture() as base:
        rows = crawl(base).set_index('path')
    assert len(rows) == 6
    assert '/private' not in rows.index
    assert rows.loc['/missing', 'status'] == 404
    assert rows.loc['/old', 'redirect'] == '/a'
    assert rows.loc['/a', 'canonical'] == '/a'
    assert 'duplicate_title' in rows.loc['/a', 'issues']
    assert rows.loc['/a', 'missing_alt'] == 1
    assert rows.loc['/b', 'missing_alt'] == 0
    assert rows.loc['/dynamic', 'h1_count'] == 0


def test_limit():
    with fixture() as base:
        assert len(crawl(base, limit=2)) == 2


def test_browser():
    if not os.getenv('RUN_BROWSER_TEST'): pytest.skip('Set RUN_BROWSER_TEST=1 to enable Chromium')
    with fixture() as base:
        assert browser_check(base, os.getenv('CHROMIUM_PATH')) == 'Rendered program'


@pytest.mark.parametrize('limit', [0, -1, 101])
def test_invalid_limit(limit):
    with pytest.raises(ValueError, match='limit'):
        crawl('http://127.0.0.1:1', limit=limit)


def test_external_scope_rejected():
    with pytest.raises(ValueError, match='Local fixture only'):
        crawl('https://example.com')
    with pytest.raises(ValueError, match='Local fixture only'):
        browser_check('https://example.com')


def test_non_html_and_blocked_root(monkeypatch):
    import requests
    def fake_get(self, url, **kwargs):
        response = requests.Response()
        response.status_code = 200
        response.headers['Content-Type'] = 'text/plain'
        response._content = (b'User-agent: *\nDisallow: /\n' if url.endswith('/robots.txt') else b'plain text')
        return response
    monkeypatch.setattr(requests.Session, 'get', fake_get)
    assert crawl('http://127.0.0.1:1').empty
    def allowed_get(self, url, **kwargs):
        response = fake_get(self, url, **kwargs)
        if url.endswith('/robots.txt'):
            response._content = b'User-agent: *\nDisallow:\n'
        return response
    monkeypatch.setattr(requests.Session, 'get', allowed_get)
    result = crawl('http://127.0.0.1:1')
    assert len(result) == 1
    assert not result.iloc[0]['is_html']
    assert result.iloc[0]['issues'] == ''

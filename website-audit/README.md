# Website Audit — Local proof of concept

A standalone AI-assisted experiment for testing a bounded website crawler and HTML diagnostics with a synthetic local fixture.

## Reproduce the results

Requirements: Python 3.10+ and the dependencies in `requirements.txt`. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python audit.py
python -m pytest -q
```

To include Chromium rendering:

```bash
python -m playwright install chromium
python audit.py --browser
RUN_BROWSER_TEST=1 python -m pytest -q
```

An existing Chromium binary can be used through `--chromium-path /path/to/chromium` and `CHROMIUM_PATH` for the tests. The demo starts its own HTTP fixture on loopback. No real website or paid model is required.

## Diagnostic outputs

The crawler visits up to 20 URLs by default, applies robots.txt rules and stays within the fixture's exact origin. It extracts title, description, H1 count, canonical link and missing image-alt attributes; records redirects and HTTP errors; and writes a CSV with diagnostic flags. The browser experiment loads the retrieved local HTML into Chromium, blocks network requests, and verifies a dynamically generated H1.

The [CSV](sample_outputs/audit.csv) contains six URL records, five flagged. See the [run output](sample_outputs/run.txt) and [pytest output](sample_outputs/test-results.txt). All eight cases passed during local Linux verification. Exact package versions appear in [environment.txt](sample_outputs/environment.txt).

## Limits

Synthetic fixtures only; no live-site browser navigation, no complete WCAG audit, no PDF audit, and no search-relevance or TF-IDF analysis. An empty alt attribute may be appropriate on decorative images. Production use requires additional scope controls, rate limiting, resource limits, retry logic, and URL normalization. AI-assisted initial implementation; portfolio owner reproduction is not yet verified.

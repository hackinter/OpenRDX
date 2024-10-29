import asyncio
import aiohttp
import argparse
import sys
import socket
from aiohttp import (
    ClientConnectorError,
    ClientOSError,
    ServerDisconnectedError,
    ServerTimeoutError,
    ServerConnectionError,
    TooManyRedirects,
)
from tqdm import tqdm
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from typing import List
import logging

# Color constants
LIGHT_GREEN = '\033[92m'  # Light Green
DARK_GREEN = '\033[32m'   # Dark Green
ENDC = '\033[0m'          # Reset to default color

# Default payloads
redirect_payloads = [
    "//example.com@google.com/%2f..",
    "///google.com/%2f..",
    "///example.com@google.com/%2f..",
    "////google.com/%2f..",
    "https://google.com/%2f..",
]

# Setting up logging
logging.basicConfig(filename='error_log.txt', level=logging.ERROR, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

async def load_payloads(payloads_file):
    if payloads_file:
        with open(payloads_file) as f:
            return [line.strip() for line in f if line.strip()]
    return redirect_payloads

def fuzzify_url(url: str, keyword: str) -> str:
    if keyword in url:
        return url

    parsed_url = urlparse(url)
    params = parse_qsl(parsed_url.query)
    fuzzed_params = [(k, "FUZZ") for k, _ in params]  # Replace with FUZZ for all params
    fuzzed_query = urlencode(fuzzed_params)

    fuzzed_url = urlunparse(
        [parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, fuzzed_query, parsed_url.fragment]
    )

    return fuzzed_url

def load_urls() -> List[str]:
    return [line.strip() for line in sys.stdin]

async def fetch_url(session, url, method='HEAD'):
    try:
        async with session.request(method, url, allow_redirects=True, timeout=10) as response:
            return response
    except (ClientConnectorError, ClientOSError, ServerDisconnectedError, 
            ServerTimeoutError, ServerConnectionError, TooManyRedirects, 
            UnicodeDecodeError, socket.gaierror, asyncio.exceptions.TimeoutError) as e:
        tqdm.write(f'[ERROR] Error fetching: {url} - {str(e)}', file=sys.stderr)
        logging.error(f'Error fetching: {url} - {str(e)}')
        return None

async def process_url(semaphore, session, url, payloads, keyword, pbar):
    async with semaphore:
        for payload in payloads:
            filled_url = url.replace(keyword, payload)
            response = await fetch_url(session, filled_url, method='GET')
            if response:
                locations = " --> ".join(str(r.url) for r in response.history)
                status_code = response.status
                if status_code == 200:
                    tqdm.write(f'{DARK_GREEN}[FOUND]{ENDC} {LIGHT_GREEN}{filled_url} redirects to {locations}{ENDC}')
                else:
                    tqdm.write(f'[INFO] {filled_url} responded with status code {status_code}')
            pbar.update()

async def process_urls(semaphore, session, urls, payloads, keyword):
    with tqdm(total=len(urls) * len(payloads), ncols=70, desc='Processing', unit='url', position=0) as pbar:
        tasks = []
        for url in urls:
            tasks.append(process_url(semaphore, session, url, payloads, keyword, pbar))
        await asyncio.gather(*tasks, return_exceptions=True)

async def save_results(results: List[str], filename: str):
    with open(filename, 'w') as f:
        for result in results:
            f.write(result + '\n')

async def main(args):
    payloads = await load_payloads(args.payloads)
    urls = load_urls()
    tqdm.write(f'[INFO] Processing {len(urls)} URLs with {len(payloads)} payloads.')
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(args.concurrency)
        results = await process_urls(semaphore, session, urls, payloads, args.keyword)

    if args.output:
        await save_results(results, args.output)

if __name__ == "__main__":
    banner = """\
   ██████  ██████  ███████ ███    ██       ██████  ██████  ██   ██ 
  ██    ██ ██   ██ ██      ████   ██       ██   ██ ██   ██  ██ ██  
  ██    ██ ██████  █████   ██ ██  ██ █████ ██████  ██   ██   ███   
  ██    ██ ██      ██      ██  ██ ██       ██   ██ ██   ██  ██ ██  
   ██████  ██      ███████ ██   ████       ██   ██ ██████  ██   ██ 
                                                                   
    """
    print(banner)
    parser = argparse.ArgumentParser(description="OpenRedireX: A fuzzer for detecting open redirect vulnerabilities")
    parser.add_argument('-p', '--payloads', help='file of payloads', required=False)
    parser.add_argument('-k', '--keyword', help='keyword in URLs to replace with payload (default is FUZZ)', default="FUZZ")
    parser.add_argument('-c', '--concurrency', help='number of concurrent tasks (default is 100)', type=int, default=100)
    parser.add_argument('-o', '--output', help='file to save results', required=False)
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
        sys.exit(0)

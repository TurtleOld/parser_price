from urllib.parse import urlparse


def parse_url(url):
    r_url = urlparse(url)
    return r_url.path

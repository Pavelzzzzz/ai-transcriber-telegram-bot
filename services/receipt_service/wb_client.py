import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

logger = logging.getLogger(__name__)

WB_API_URL = "https://card.wb.ru/cards/v1/detail"
REQUEST_TIMEOUT = 10
MAX_WORKERS = 4


class WBClient:
    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

    def extract_article_from_url(self, url: str) -> str | None:
        match = re.search(r"/catalog/(\d+)", url)
        if match:
            return match.group(1)
        return None

    def get_product_info(self, article: str) -> dict[str, Any]:
        try:
            params = {"appType": 1, "curr": "rub", "dest": -2228342, "nm": article}
            response = self.session.get(WB_API_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            products = data.get("data", {}).get("products", [])
            if not products:
                return {"error": "not_found", "article": article}

            product = products[0]
            return {
                "article": article,
                "name": product.get("name", "Неизвестно"),
                "brand": product.get("brand", ""),
                "price": product.get("priceU", 0) / 100,
                "error": None,
            }

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for article {article}")
            return {"error": "timeout", "article": article}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for article {article}: {e}")
            return {"error": "request_failed", "article": article}
        except (ValueError, KeyError) as e:
            logger.error(f"Parse error for article {article}: {e}")
            return {"error": "parse_error", "article": article}

    def get_products_batch(self, articles: list[str]) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_article = {
                executor.submit(self.get_product_info, article): article for article in articles
            }

            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    result = future.result()
                    results[article] = result
                except Exception as e:
                    logger.error(f"Future failed for article {article}: {e}")
                    results[article] = {"error": "future_failed", "article": article}

        return results


def parse_items_input(text: str) -> list[dict[str, str | int]]:
    items: list[dict[str, str | int]] = []
    article_pattern = re.compile(r"^(.+?)\s*[xXхХ]\s*(\d+)$")

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        match = article_pattern.match(line)
        if not match:
            continue

        raw = match.group(1).strip()
        quantity = int(match.group(2))

        if quantity <= 0:
            continue

        if "wildberries" in raw.lower():
            article = extract_article_from_url_static(raw)
        else:
            article = raw

        if article and article.isdigit():
            items.append({"article": article, "quantity": quantity})

    return items


def extract_article_from_url_static(url: str) -> str | None:
    match = re.search(r"/catalog/(\d+)", url)
    if match:
        return match.group(1)
    return None

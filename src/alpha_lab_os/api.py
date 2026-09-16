from __future__ import annotations

from typing import Any


PRICE_INFO = "/api/v1/dex/market/price-info"
CANDLES = "/api/v1/dex/market/candles"
ADVANCED_INFO = "/api/v1/dex/market/token/advanced-info"
TRADES = "/api/v1/dex/market/trades"
QUOTE = "/api/v1/dex/aggregator/quote"
HOT_TOKEN = "/api/v1/dex/market/token/hot-token"


def _data(response: Any) -> Any:
    return response.body.get("data") if isinstance(response.body, dict) else None


def request_data(client: Any, method: str, path: str, params: dict[str, Any] | None = None, body: Any | None = None) -> tuple[Any, Any]:
    response = client.request(method, path, params=params, body=body)
    return response, _data(response)


def price_info(client: Any, tokens: list[dict[str, str]]) -> tuple[Any, list[dict[str, Any]]]:
    if not 1 <= len(tokens) <= 100:
        raise ValueError("price-info accepts 1-100 tokens")
    body = [{"binanceChainId": item["chain"], "tokenContractAddress": item["token"]} for item in tokens]
    response, data = request_data(client, "POST", PRICE_INFO, body=body)
    return response, data if isinstance(data, list) else []


def candles(client: Any, token: dict[str, str], bar: str = "1m", limit: int = 60) -> tuple[Any, list[Any]]:
    params = {"binanceChainId": token["chain"], "tokenContractAddress": token["token"], "bar": bar, "limit": str(limit)}
    response, data = request_data(client, "GET", CANDLES, params=params)
    return response, data if isinstance(data, list) else []


def advanced_info(client: Any, token: dict[str, str]) -> tuple[Any, dict[str, Any]]:
    params = {"binanceChainId": token["chain"], "tokenContractAddress": token["token"]}
    response, data = request_data(client, "GET", ADVANCED_INFO, params=params)
    return response, data if isinstance(data, dict) else {}


def token_trades(client: Any, token: dict[str, str], limit: int = 100) -> tuple[Any, Any]:
    params = {"binanceChainId": token["chain"], "tokenContractAddress": token["token"], "limit": str(min(500, max(1, limit)))}
    return request_data(client, "GET", TRADES, params=params)


def quote(client: Any, pair: dict[str, str], amount: str) -> tuple[Any, list[dict[str, Any]]]:
    params = {"binanceChainId": pair["chain"], "amount": str(amount), "fromTokenAddress": pair["from_token"], "toTokenAddress": pair["to_token"]}
    response, data = request_data(client, "GET", QUOTE, params=params)
    return response, data if isinstance(data, list) else []

#!/usr/bin/env python3
import os
from datetime import date
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from fastmcp import FastMCP

mcp = FastMCP("Plaid MCP Server")

configuration = plaid.Configuration(
    host=getattr(plaid.Environment, os.environ.get("PLAID_ENV", "Sandbox")),
    api_key={
        "clientId": os.environ["PLAID_CLIENT_ID"],
        "secret": os.environ["PLAID_SECRET"],
    },
)
plaid_client = plaid_api.PlaidApi(plaid.ApiClient(configuration))


def _access_token() -> str:
    token = os.environ.get("PLAID_ACCESS_TOKEN")
    if not token:
        raise ValueError("PLAID_ACCESS_TOKEN not set — complete the Plaid Link flow first.")
    return token


@mcp.tool(description="Create a Plaid Link token to start the one-time bank connection flow")
def create_link_token(
    user_id: str,
    products: list[str] = ["transactions"],
    country_codes: list[str] = ["US"],
    language: str = "en",
) -> dict:
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        client_name="MCP Plaid Server",
        products=[Products(p) for p in products],
        country_codes=[CountryCode(c) for c in country_codes],
        language=language,
    )
    response = plaid_client.link_token_create(request)
    return {"link_token": response["link_token"], "expiration": response["expiration"]}


@mcp.tool(description="Exchange a public token from Plaid Link for a permanent access token. After calling this, copy access_token into the PLAID_ACCESS_TOKEN Railway variable and redeploy.")
def exchange_public_token(public_token: str) -> dict:
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = plaid_client.item_public_token_exchange(request)
    return {
        "access_token": response["access_token"],
        "item_id": response["item_id"],
        "next_step": "Set PLAID_ACCESS_TOKEN to the access_token value in Railway → Variables, then redeploy.",
    }


@mcp.tool(description="List all linked bank accounts")
def get_accounts() -> dict:
    response = plaid_client.accounts_get(AccountsGetRequest(access_token=_access_token()))
    return {
        "accounts": [
            {
                "account_id": a["account_id"],
                "name": a["name"],
                "official_name": a.get("official_name"),
                "type": str(a["type"]),
                "subtype": str(a["subtype"]),
                "mask": a.get("mask"),
            }
            for a in response["accounts"]
        ]
    }


@mcp.tool(description="Get real-time balances for all linked accounts")
def get_balance() -> dict:
    response = plaid_client.accounts_balance_get(
        AccountsBalanceGetRequest(access_token=_access_token())
    )
    return {
        "balances": [
            {
                "account_id": a["account_id"],
                "name": a["name"],
                "available": a["balances"]["available"],
                "current": a["balances"]["current"],
                "currency": a["balances"]["iso_currency_code"],
            }
            for a in response["accounts"]
        ]
    }


@mcp.tool(description="Fetch transactions between start_date and end_date (YYYY-MM-DD). Use offset to paginate beyond max_results.")
def get_transactions(start_date: str, end_date: str, max_results: int = 100, offset: int = 0) -> dict:
    request = TransactionsGetRequest(
        access_token=_access_token(),
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        options=TransactionsGetRequestOptions(count=max_results, offset=offset),
    )
    response = plaid_client.transactions_get(request)
    return {
        "transactions": [
            {
                "transaction_id": t["transaction_id"],
                "date": str(t["date"]),
                "name": t["name"],
                "amount": t["amount"],
                "currency": t["iso_currency_code"],
                "category": t.get("category"),
                "account_id": t["account_id"],
            }
            for t in response["transactions"]
        ],
        "total_transactions": response["total_transactions"],
    }


if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class _APIKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            api_key = os.environ.get("MCP_API_KEY")
            if api_key and request.headers.get("X-API-Key") != api_key:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return await call_next(request)

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Plaid MCP server on 0.0.0.0:{port}")
    app = mcp.http_app(stateless_http=True)
    app.add_middleware(_APIKeyMiddleware)
    uvicorn.run(app, host="0.0.0.0", port=port)

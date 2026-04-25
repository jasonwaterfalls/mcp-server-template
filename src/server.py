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
    host=getattr(plaid.Environment, os.environ.get("PLAID_ENV", "Development")),
    api_key={
        "clientId": os.environ["PLAID_CLIENT_ID"],
        "secret": os.environ["PLAID_SECRET"],
    },
)
plaid_client = plaid_api.PlaidApi(plaid.ApiClient(configuration))


@mcp.tool(description="Create a Plaid Link token to initiate the bank account connection flow for a given user")
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


@mcp.tool(description="Exchange a public token (from Plaid Link) for a permanent access token")
def exchange_public_token(public_token: str) -> dict:
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = plaid_client.item_public_token_exchange(request)
    return {"access_token": response["access_token"], "item_id": response["item_id"]}


@mcp.tool(description="List all accounts associated with a Plaid access token")
def get_accounts(access_token: str) -> dict:
    response = plaid_client.accounts_get(AccountsGetRequest(access_token=access_token))
    accounts = [
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
    return {"accounts": accounts}


@mcp.tool(description="Get real-time balances for all accounts tied to a Plaid access token")
def get_balance(access_token: str) -> dict:
    response = plaid_client.accounts_balance_get(
        AccountsBalanceGetRequest(access_token=access_token)
    )
    balances = [
        {
            "account_id": a["account_id"],
            "name": a["name"],
            "available": a["balances"]["available"],
            "current": a["balances"]["current"],
            "currency": a["balances"]["iso_currency_code"],
        }
        for a in response["accounts"]
    ]
    return {"balances": balances}


@mcp.tool(description="Fetch transactions for a Plaid access token between start_date and end_date (YYYY-MM-DD format). Use offset to paginate beyond max_results.")
def get_transactions(access_token: str, start_date: str, end_date: str, max_results: int = 100, offset: int = 0) -> dict:
    request = TransactionsGetRequest(
        access_token=access_token,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        options=TransactionsGetRequestOptions(count=max_results, offset=offset),
    )
    response = plaid_client.transactions_get(request)
    txns = [
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
    ]
    return {"transactions": txns, "total_transactions": response["total_transactions"]}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Plaid MCP server on 0.0.0.0:{port}")
    mcp.run(transport="http", host="0.0.0.0", port=port, stateless_http=True)

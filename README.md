# MCP Server Template

A minimal [FastMCP](https://github.com/jlowin/fastmcp) server template wrapping the [Plaid API](https://plaid.com/docs/), deployable to Railway with streamable HTTP transport.

## Local Development

### Setup

Fork the repo, then run:

```bash
git clone <your-repo-url>
cd mcp-server-template
conda create -n mcp-server python=3.13
conda activate mcp-server
pip install -r requirements.txt
```

### Test

```bash
python src/server.py
# then in another terminal run:
npx @modelcontextprotocol/inspector
```

Open http://localhost:3000 and connect to `http://localhost:8000/mcp` using "Streamable HTTP" transport (NOTE THE `/mcp`!).

## Deployment (Railway)

1. Fork this repository
2. Create a new project on [Railway](https://railway.app) and connect your forked repo
3. Railway will auto-detect Python via Nixpacks and use `railway.toml` for the start command
4. In the Railway service **Variables** tab, set:
   - `PLAID_CLIENT_ID` — your Plaid client ID
   - `PLAID_SECRET` — your Plaid production secret
5. Generate a public domain in Railway's **Settings → Networking**

Your server will be available at `https://your-service-name.up.railway.app/mcp` (NOTE THE `/mcp`!)

### Local environment variables

```bash
export PLAID_CLIENT_ID=...
export PLAID_SECRET=...
python src/server.py
```

## Poke Setup

You can connect your MCP server to Poke at (poke.com/settings/connections)[poke.com/settings/connections].
To test the connection explitly, ask poke somethink like `Tell the subagent to use the "{connection name}" integration's "{tool name}" tool`.
If you run into persistent issues of poke not calling the right MCP (e.g. after you've renamed the connection) you may send `clearhistory` to poke to delete all message history and start fresh.
We're working hard on improving the integration use of Poke :)


## Customization

Add more tools by decorating functions with `@mcp.tool`:

```python
@mcp.tool
def calculate(x: float, y: float, operation: str) -> float:
    """Perform basic arithmetic operations."""
    if operation == "add":
        return x + y
    elif operation == "multiply":
        return x * y
    # ...
```

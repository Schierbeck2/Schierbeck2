# Housing Survey Agent - Setup Guide

## 1. Connect Claude Code to Your Database

To let Claude Code inspect and query your manufactured housing database directly,
add a PostgreSQL MCP server to your Claude Code config.

### Option A: Use the official PostgreSQL MCP server

Add this to your `~/.claude/claude_desktop_config.json` (or `settings.json` for CLI):

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://USER:PASSWORD@HOST:5432/DB_NAME"
      ]
    }
  }
}
```

Replace `USER`, `PASSWORD`, `HOST`, and `DB_NAME` with your actual credentials.

### Option B: Use the Python postgres MCP server

```bash
pip install mcp-server-postgres
```

Then add to your Claude Code config:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "mcp-server-postgres",
      "args": ["--connection-string", "postgresql://USER:PASSWORD@HOST:5432/DB_NAME"]
    }
  }
}
```

Once configured, Claude Code can:
- Inspect your actual table/column names
- Run queries to understand your schema
- Help adjust the `database.py` column mappings to match your real database

## 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```
MISTRAL_API_KEY=...
DB_HOST=...
DB_PORT=5432
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
```

## 3. Map Your Schema

If your database uses different table/column names, set these env vars
in `.env` to override the defaults:

```
MH_PROPERTY_TABLE=your_properties_table
MH_RENT_TABLE=your_rent_table
MH_COL_PROPERTY_ID=id
MH_COL_NAME=community_name
MH_COL_PHONE=phone_number
MH_COL_LAT=lat
MH_COL_LNG=lng
MH_COL_COUNTY=county_name
# ... etc
```

Or, once Claude Code has MCP access to your database, just ask it to
update `database.py` to match your real schema.

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Run

```bash
# Survey all communities near property ID 1234 (within 10 miles)
python voice_agent.py --subject-property 1234 --radius 10

# Survey all communities in a county
python voice_agent.py --county "Maricopa" --state "AZ"

# Review what the agent has learned
python voice_agent.py --learnings
```

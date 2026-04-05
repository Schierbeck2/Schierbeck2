# Housing Survey Agent - Setup Guide

## Architecture

```
                         ┌─────────────┐
  orchestrator.py        │  PostgreSQL  │
  "survey property 1234" │  MH Database │
         │               └──────┬──────┘
         ▼                      │
  ┌──────────────┐    query properties,
  │ Find nearby  │◄── write rent surveys
  │ properties   │
  └──────┬───────┘
         │ for each property
         ▼
  ┌──────────────┐     ┌───────────────┐
  │ Twilio call  │────▶│  call_server   │ (FastAPI webhooks)
  │ auto-dial    │     │               │
  └──────────────┘     │  Each turn:   │
                       │  Play TTS ──▶ Record ──▶ Transcribe
                       │       ▲                      │
                       │       │    Mistral LLM        │
                       │       └──── generate ◄────────┘
                       └───────┬───────┘
                               │ call complete
                               ▼
                       ┌───────────────┐
                       │ call_reviewer  │
                       │ Auto-approve   │
                       │ or flag review │
                       └───────┬───────┘
                               │
                       ┌───────▼───────┐
                       │   learning    │
                       │ Rank by score │
                       │ Keep best 20  │
                       └───────────────┘
```

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
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app
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
```

Or, once Claude Code has MCP access to your database, just ask it to
update `database.py` to match your real schema.

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Set Up Twilio

1. Create a Twilio account and get a phone number
2. Add credentials to `.env`
3. For local development, expose the call server with ngrok:

```bash
# Terminal 1: Start the call server
python call_server.py

# Terminal 2: Expose it publicly
ngrok http 8000
# Copy the https URL to WEBHOOK_BASE_URL in .env
```

## 6. Run

### Full automated campaign (production use)

```bash
# Start the call server first
python call_server.py

# In another terminal, run the campaign
# Survey all communities near property ID 1234 (within 10 miles)
python orchestrator.py --subject-property 1234 --radius 10

# Dry run - see what would be called without calling
python orchestrator.py --subject-property 1234 --radius 10 --dry-run

# Radius only, skip county-wide search
python orchestrator.py --subject-property 1234 --radius 5 --no-county
```

### Interactive text mode (testing/development)

```bash
# Practice the survey conversation without making real calls
python voice_agent.py -p "Sunset Mobile Home Park"
```

### Review learnings

```bash
python voice_agent.py --learnings
```

## Call Flow

1. **Orchestrator** finds properties near your subject property
2. **Twilio** auto-dials each number; detects voicemail and hangs up
3. **Call server** handles the conversation turn-by-turn:
   - Plays Voxtral TTS audio
   - Records the response (up to 60s per turn, 5s silence timeout)
   - Transcribes with Voxtral STT
   - Mistral Large generates the next question
   - Repeats until survey is complete (or max 15 turns)
4. **Call reviewer** evaluates each call:
   - Data completeness (weighted: rent/occupancy critical, rest secondary)
   - Data plausibility (rent $100-$2500, occupancy 30-100%, etc.)
   - AI quality assessment (cooperative respondent? reliable data?)
   - Auto-approves clean calls, flags others for review
5. **Database** saves results to rent survey table
6. **Learning system** evaluates what worked, ranks strategies, improves future calls

# MCP Server Setup Guide

This guide explains how to set up the Governance OS MCP server for use with Claude Desktop or other MCP-compatible AI assistants.

---

## Prerequisites

1. **PostgreSQL database running** with Governance OS data
2. **Python 3.11+** with project dependencies installed
3. **Claude Desktop** (or another MCP client)

---

## Option 1: Local Development Setup

### Step 1: Start PostgreSQL

```bash
# Using Docker Compose (recommended)
cd /path/to/Governance-OS
docker compose up -d postgres

# Verify postgres is running
docker compose ps | grep postgres
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r core/requirements.txt
```

### Step 3: Seed Demo Data (Optional)

```bash
# Set database URL
export DATABASE_URL="postgresql://govos:local_dev_password@localhost:5432/governance_os"

# Run migrations
cd /path/to/Governance-OS
alembic upgrade head

# Seed treasury data
python -m core.scripts.seed_fixtures --pack=treasury --scenarios
```

### Step 4: Configure Claude Desktop

Edit your Claude Desktop config file:

**macOS:** `~/.config/claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "governance-os": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Governance-OS",
      "env": {
        "DATABASE_URL": "postgresql://govos:local_dev_password@localhost:5432/governance_os"
      }
    }
  }
}
```

**Important:** Replace `/path/to/Governance-OS` with the actual path to your project.

### Step 5: Restart Claude Desktop

Quit and reopen Claude Desktop. You should see "governance-os" in the MCP servers list.

---

## Option 2: Docker Setup (Full Stack)

### Step 1: Start All Services

```bash
cd /path/to/Governance-OS
docker compose up -d
```

### Step 2: Configure Claude Desktop

```json
{
  "mcpServers": {
    "governance-os": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Governance-OS",
      "env": {
        "DATABASE_URL": "postgresql://govos:local_dev_password@localhost:5432/governance_os"
      }
    }
  }
}
```

**Note:** Even with Docker, the MCP server runs locally (Claude Desktop spawns it as a subprocess). The `localhost:5432` connection works because Docker exposes the postgres port.

---

## Testing the MCP Server

### Using MCP Inspector

```bash
# Start Inspector (opens browser at http://localhost:6274)
DATABASE_URL="postgresql://govos:local_dev_password@localhost:5432/governance_os" \
  npx @modelcontextprotocol/inspector python -m mcp_server.server
```

### Test Tools in Inspector

1. **get_open_exceptions** - Should list any open exceptions
2. **get_policies** - Should list active policies
3. **search_decisions** - Search for recent decisions

---

## Available MCP Tools

### Read Tools (Safe, No Approval Required)

| Tool | Description |
|------|-------------|
| `get_open_exceptions` | List exceptions requiring decisions |
| `get_exception_detail` | Full context for an exception |
| `get_policies` | List active policies |
| `get_policy_detail` | Full policy with rule definition |
| `get_evidence_pack` | Complete evidence for a decision |
| `search_decisions` | Search decision history |
| `get_recent_signals` | Recent signals |

### Write Tools (Require Human Approval)

| Tool | Description |
|------|-------------|
| `propose_signal` | Propose candidate signal → approval queue |
| `propose_policy_draft` | Propose policy draft → approval queue |
| `dismiss_exception` | Propose dismissal → approval queue |
| `add_exception_context` | Enrich exception (no approval needed) |

---

## Example Prompts for Claude

Once configured, try these prompts in Claude Desktop:

### View Open Exceptions
```
What exceptions are currently open in the governance system?
```

### Get Exception Details
```
Show me the details of exception [id]
```

### Review a Decision
```
Get the evidence pack for decision [id]
```

### Search History
```
Find decisions made in the last week
```

---

## Troubleshooting

### "Connection refused" to database

```bash
# Check if postgres is running
docker compose ps | grep postgres

# If not running, start it
docker compose up -d postgres
```

### "Module not found" errors

```bash
# Make sure you're in the project directory
cd /path/to/Governance-OS

# Install dependencies
pip install -r core/requirements.txt
```

### MCP server not appearing in Claude Desktop

1. Check the config file path is correct for your OS
2. Verify JSON syntax is valid
3. Restart Claude Desktop completely (Quit, not just close window)
4. Check Claude Desktop logs for errors

### "No data" in queries

```bash
# Seed demo data
DATABASE_URL="postgresql://govos:local_dev_password@localhost:5432/governance_os" \
  python -m core.scripts.seed_fixtures --pack=treasury --scenarios
```

---

## Safety Notes

1. **Read tools are safe** - They only query data, no mutations
2. **Write tools go through approval queue** - Human must approve before any data changes
3. **No policy evaluation** - AI cannot make policy decisions, only assist with data
4. **No recommendations** - Options are presented symmetrically (AI doesn't rank or suggest)

These boundaries are enforced at the MCP server level, not just by prompt engineering.

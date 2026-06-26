# App MCP Server — Build Guide

> A reusable blueprint for adding an MCP (Model Context Protocol) server to any Supabase-backed app, so AI agents can read and write your data through natural language.
>
> Based on the OpenLedger MCP implementation — a production-grade server with 30 tools, user data isolation, SHA-256 token auth, Streamable HTTP transport, comprehensive tests, and a real-world audit.
>
> **What you get:** AI agents (Claude Code, Claude Desktop, Cursor, Hermes, ChatGPT) can connect to your app via remote HTTP or local stdio and execute commands like "Show me my plants due for watering" or "Log that I watered my monstera."

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Architecture Overview](#2-architecture-overview)
3. [Project Setup](#3-project-setup)
4. [Database Setup (Supabase)](#4-database-setup-supabase)
5. [Auth Layer](#5-auth-layer)
6. [Server Entry Point (stdio)](#6-server-entry-point-stdio)
7. [Centralized Tool Registration](#7-centralized-tool-registration)
8. [Streamable HTTP / Vercel Transport](#8-streamable-http--vercel-transport)
9. [Writing Tools — The Pattern](#9-writing-tools--the-pattern)
10. [User Data Isolation — The Critical Rules](#10-user-data-isolation--the-critical-rules)
11. [Special Tool Patterns](#11-special-tool-patterns)
12. [Testing](#12-testing)
13. [Token Management API (Next.js)](#13-token-management-api-nextjs)
14. [MCP Tokens Panel UI Component](#14-mcp-tokens-panel-ui-component)
15. [Agent Configuration](#15-agent-configuration)
16. [Common Pitfalls](#16-common-pitfalls)
17. [Verification Checklist](#17-verification-checklist)
18. [Real-World Audit](#18-real-world-audit)

---

## 1. Core Philosophy

### MCP is a read/write bridge for AI agents, not an API.

An API is designed for other developers. An MCP server is designed for AI agents — it provides natural-language-optimized tool descriptions, parameter names that read like English, and error messages that help the agent self-correct.

Key differences from a traditional REST API:

| Aspect | REST API | MCP Server |
|--------|---------|------------|
| Consumer | Developers reading docs | AI agents reading tool descriptions |
| Authentication | API keys in headers | SHA-256 token validation, then user-isolated queries |
| Input validation | Manual | Zod schemas auto-generated for each tool |
| Error format | JSON error responses | Descriptive strings the agent can act on |
| Tool discovery | Out-of-band docs | Runtime tool listing via `listTools` |

**Design for the agent, not the developer.** Every tool description, parameter name, and error message should be optimized for an LLM reading it — not a human reading docs.

---

## 2. Architecture Overview

```
┌────────────────────────────┐     HTTP / stdio       ┌──────────────────────────┐
│      AI Agent              │◄─────────────────────►│      MCP Server          │
│  (Claude Code, Desktop,    │     JSON-RPC            │  (Node.js)               │
│   Cursor, Hermes, ChatGPT) │                        │                          │
└────────────────────────────┘                        │  ┌────────────────────┐  │
                                                      │  │ Auth: SHA-256     │  │
                                                      │  │ token hash lookup │  │
                  ┌───────────────────────────────────►  └────────┬───────────┘  │
                  │                                   │          │              │
          ┌───────┴────────┐                          │  ┌───────▼───────────┐  │
          │  Remote HTTP   │                          │  │ Supabase Service  │  │
          │  (Vercel/      │                          │  │ Role Client       │  │
          │   Streamable)  │                          │  │ (bypasses RLS)    │  │
          └───────┬────────┘                          │  └───────┬───────────┘  │
                  │                                   └─────────┼──────────────┘
          ┌───────┴────────┐                                     │
          │  Local stdio   │                            ┌────────▼────────┐
          │  (dev/debug)   │                            │   Supabase      │
          └────────────────┘                            │   (DB + Auth)   │
                                                        └─────────────────┘
```

### Two Transport Modes

- **Remote HTTP (production):** Deployed on Vercel/your host. Agents connect via URL + `Authorization: Bearer <token>`. No local setup needed — the service role key stays in server env vars.
- **Local stdio (development):** Run via CLI with `OPENLEDGER_ACCESS_TOKEN`. Useful for debugging and local-only agents.

### How It Works

1. **Agent sends a request** — via stdio (local) or HTTP (remote) with a bearer token.
2. **Server validates the token** — SHA-256 hashes the raw token, looks up the hash in the `mcp_tokens` table, checks `revoked_at`.
3. **Server creates a service-role Supabase client** — bypasses RLS. All queries must filter by `user_id` explicitly.
4. **Tool handler executes** — receives `userId` and `getClient()`, performs ownership check if needed, runs the query, returns JSON.

---

## 3. Project Setup

### 3a. Directory Structure

```
apps/mcp/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Entry point — stdio server bootstrap
│   ├── vercel-handler.ts     # Streamable HTTP handler (Vercel)
│   ├── supabase.ts           # Auth + Supabase client + token generation
│   ├── types.ts              # Database type definitions
│   ├── register-tools.ts     # Centralized tool registration
│   ├── tools/
│   │   ├── accounts.ts       # Tool registrations by domain
│   │   ├── transactions.ts
│   │   ├── dashboard.ts
│   │   └── ...
│   └── __tests__/
│       ├── auth.test.ts      # Auth validation tests
│       └── tools.test.ts     # Input schema + ownership tests
├── dist/                     # Compiled output
└── .env                      # Local dev environment
```

Also needed in your main app (e.g., `src/app/api/mcp/`):
```
src/app/
├── api/mcp/route.ts          # Next.js API → MCP server gateway
└── api/mcp/tokens/
    ├── route.ts              # POST (create), GET (list tokens)
    └── [id]/route.ts         # DELETE (revoke token)
```

Plus a UI component:
```
src/components/
└── mcp-tokens-panel.tsx      # Settings UI for create/list/revoke tokens
```

### 3b. package.json

```json
{
  "name": "@your-app/mcp",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "lint": "eslint src/"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.13.0",
    "@supabase/supabase-js": "^2.107.0",
    "zod": "^3.24.0"
  },
  "devDependencies": {
    "tsx": "^4.0.0",
    "typescript": "^5.8.0",
    "@types/node": "^22.0.0",
    "vitest": "^3.0.0"
  }
}
```

**Key choices:**
- `"type": "module"` — ESM is required for `@modelcontextprotocol/sdk`.
- Only three runtime deps: the MCP SDK, Supabase client, and Zod. Keep it lean.
- `tsx` for dev (fast, no build step), `tsc` for production builds.
- `zod` for input validation — used by every tool's parameter schema.

### 3c. tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "declaration": true,
    "types": ["node", "vitest/globals"]
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist", "src/__tests__"]
}
```

---

## 4. Database Setup (Supabase)

### 4a. Token Storage Table

Access tokens are stored **hashed** (SHA-256) — the raw token is returned to the user once at creation and never stored.

```sql
create table public.mcp_tokens (
  id uuid default gen_random_uuid() primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  token_hash text not null,
  token_prefix text not null,
  last_used_at timestamptz,
  created_at timestamptz default now(),
  revoked_at timestamptz
);

create index idx_mcp_tokens_user on public.mcp_tokens(user_id);
create index idx_mcp_tokens_hash on public.mcp_tokens(token_hash);

alter table public.mcp_tokens enable row level security;

-- Users can view their own tokens (never expose token_hash in UI)
create policy "Users view own MCP tokens"
  on public.mcp_tokens for select
  using (auth.uid() = user_id);

-- Users can create their own tokens
create policy "Users create own MCP tokens"
  on public.mcp_tokens for insert
  with check (auth.uid() = user_id);

-- Users can revoke (update) their own tokens
create policy "Users revoke own MCP tokens"
  on public.mcp_tokens for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Users can delete their own tokens
create policy "Users delete own MCP tokens"
  on public.mcp_tokens for delete
  using (auth.uid() = user_id);
```

**Why SHA-256 hashing?** The token is sensitive — it grants full API access. Storing a hash means a DB breach doesn't leak active tokens. The `token_prefix` (e.g., `app_abc...`) is used in the UI to let users identify tokens without exposing the full hash.

Add the `token_hash` index — without it, every auth request does a full table scan.

### 4b. Database Types (optional but recommended)

Define TypeScript types for your database tables to get type-safe Supabase queries. Generate them with the Supabase CLI:

```bash
npx supabase gen types typescript --linked > apps/mcp/src/types.ts
```

If your schema is large, just define the types your MCP tools need manually — the generated file can be thousands of lines. Strip it down to only the tables your MCP tools touch.

Example minimal type file:

```typescript
export interface DbProfile {
  id: string;
  user_id: string;
  display_name: string | null;
  email: string | null;
  created_at: string;
  updated_at: string;
}

export interface DbThing {
  id: string;
  user_id: string | null;
  name: string;
  category: string;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DbMcpToken {
  id: string;
  user_id: string;
  name: string;
  token_hash: string;
  token_prefix: string;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface Database {
  public: {
    Tables: {
      profiles: { Row: DbProfile };
      things: { Row: DbThing };
      mcp_tokens: { Row: DbMcpToken };
    };
  };
}
```

---

## 5. Auth Layer

This is the most critical file. It handles token authentication and returns a service-role Supabase client scoped to a specific user.

`apps/mcp/src/supabase.ts`:

```typescript
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "./types.js";

export type Client = SupabaseClient<Database>;

function env(key: string): string {
  return process.env[key] ?? "";
}

/**
 * Computes the SHA-256 hex digest of a string.
 * Reusable — used by both the auth layer and token creation API.
 */
export async function sha256Hex(input: string): Promise<string> {
  const hashBuffer = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(input),
  );
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Generates a cryptographically random MCP access token.
 * Format: `<prefix>_<32-random-hex-chars>`
 *
 * Use this in your token creation API endpoint.
 */
export function generateToken(prefix: string = "app"): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  const hex = Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `${prefix}_${hex}`;
}

/**
 * Validates an access token and returns a service-role Supabase client
 * scoped to the authenticated user.
 *
 * 1. SHA-256 hash the raw token
 * 2. Look up the hash in mcp_tokens (via service-role client)
 * 3. Verify not revoked
 * 4. Update last_used_at
 * 5. Return service-role client + userId
 *
 * ⚠️ The returned client bypasses RLS. Every query MUST filter by userId.
 */
export async function authenticateToken(
  rawToken: string,
): Promise<{ client: Client; userId: string }> {
  const supabaseUrl = env("NEXT_PUBLIC_SUPABASE_URL") || env("SUPABASE_URL");
  const serviceKey = env("SUPABASE_SERVICE_ROLE_KEY");
  const anonKey =
    env("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") || env("SUPABASE_ANON_KEY");

  if (!supabaseUrl || !anonKey) {
    throw new Error(
      "Missing Supabase credentials. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
    );
  }
  if (!serviceKey) {
    throw new Error(
      "Missing SUPABASE_SERVICE_ROLE_KEY for token validation. " +
      "The MCP server uses the service role to bypass RLS and enforce user isolation in application code.",
    );
  }

  const tokenHash = await sha256Hex(rawToken);

  // Service-role client for auth queries (can read mcp_tokens)
  const admin = createClient(supabaseUrl, serviceKey);

  const { data: records, error: lookupError } = await admin
    .from("mcp_tokens")
    .select("user_id, id, revoked_at")
    .eq("token_hash", tokenHash);

  if (lookupError) {
    throw new Error(
      `Token validation failed: unable to verify access token. ${lookupError.message}`,
    );
  }

  if (!records || records.length === 0) {
    throw new Error(
      "Authentication failed: Invalid access token. " +
      "The token provided does not match any active token. " +
      "Generate a new token from the app's settings page.",
    );
  }

  const record = records[0] as {
    user_id: string;
    id: string;
    revoked_at: string | null;
  };

  if (record.revoked_at) {
    throw new Error(
      "Authentication failed: This access token has been revoked. " +
      "Generate a new token from the app's settings page.",
    );
  }

  // Update last_used_at — fire-and-forget (non-critical)
  await admin
    .from("mcp_tokens")
    .update({ last_used_at: new Date().toISOString() })
    .eq("id", record.id);

  // Return a fresh service-role client for data queries
  const client = createClient<Database>(supabaseUrl, serviceKey);
  return { client, userId: record.user_id };
}
```

### Critical design decisions:

1. **Service role client** — The MCP server uses the service role (not the anon key) for all queries. This means **RLS is bypassed** and user isolation must be enforced in application code. This is intentional because the MCP server already authenticated via its own token system.
2. **Every query filters by `user_id`** — Because RLS is bypassed, every read and write query must explicitly filter with `.eq("user_id", userId)`. Missing this filter is a data leak.
3. **Every write verifies ownership** — Before any write operation, do a pre-check query to confirm the target resource belongs to the authenticated user.
4. **`sha256Hex()` is a separate utility** — Extract it from `authenticateToken()` so it can be reused by your token creation API endpoint without duplicating the hash logic.
5. **`generateToken()` is provided** — Don't reimplement this in your app. Use this function in your token creation API.

---

## 6. Server Entry Point (stdio)

This is the local/development entry point. For production deployments, use the Streamable HTTP handler (Section 8).

`apps/mcp/src/index.ts`:

```typescript
#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { authenticateToken, type Client } from "./supabase.js";
import { registerAllTools } from "./register-tools.js";

async function main() {
  const token = process.env.YOUR_APP_ACCESS_TOKEN;
  if (!token) {
    console.error(
      "MCP server failed to start: YOUR_APP_ACCESS_TOKEN is not set.\n" +
      "Generate a token from your app's Settings → MCP Access Tokens page\n" +
      "and set it as the YOUR_APP_ACCESS_TOKEN environment variable.",
    );
    process.exit(1);
  }

  let client: Client;
  let userId: string;
  try {
    const result = await authenticateToken(token);
    client = result.client;
    userId = result.userId;
    console.error(
      `MCP server authenticated for user ${userId}. Starting tools...`,
    );
  } catch (authError) {
    console.error(
      "MCP server failed to start: authentication error.\n" +
      "Error details:",
      authError instanceof Error ? authError.message : String(authError),
    );
    process.exit(1);
  }

  const getClient = () => client;

  // ── Server ──────────────────────────────────────
  const server = new McpServer({
    name: "yourapp",
    version: "0.1.0",
    description: "Your app description — accounts, things, goals, and insights.",
  });

  // ── Register tools ──────────────────────────────
  registerAllTools(server, getClient, userId);

  // ── Connect ─────────────────────────────────────
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error(
    "MCP server encountered a fatal error and will exit.\n" +
    "Error details:",
    err instanceof Error
      ? `${err.name}: ${err.message}\n${err.stack}`
      : String(err),
  );
  process.exit(1);
});
```

**Patterns to note:**
- The server exits with a descriptive error if `TOKEN` is missing or invalid. This prevents a running-but-broken server.
- `getClient()` is a closure — the authenticated client is created once at startup and reused for all tool calls.
- Each domain gets its own registration function, centralized in `register-tools.ts`.

---

## 7. Centralized Tool Registration

As your tool count grows (20+, 30+), importing every domain directly in `index.ts` gets messy. Centralize registration in a single file:

`apps/mcp/src/register-tools.ts`:

```typescript
import { type McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { Client } from "./supabase.js";
import { registerThingTools } from "./tools/things.js";
import { registerCareTools } from "./tools/care.js";
import { registerJournalTools } from "./tools/journal.js";
import { registerDashboardTools } from "./tools/dashboard.js";
import { registerSearchTools } from "./tools/search.js";

export function registerAllTools(
  server: McpServer,
  getClient: () => Client,
  userId: string,
) {
  registerThingTools(server, getClient, userId);
  registerCareTools(server, getClient, userId);
  registerJournalTools(server, getClient, userId);
  registerDashboardTools(server, getClient, userId);
  registerSearchTools(server, getClient, userId);
}
```

Both the stdio entry point and the HTTP handler import this same file, ensuring tool registration is always consistent across transports.

---

## 8. Streamable HTTP / Vercel Transport

This is the **production transport** — deployed on Vercel so remote agents (Claude Desktop, ChatGPT, Cursor) can connect without running a local process.

`apps/mcp/src/vercel-handler.ts`:

```typescript
/**
 * Vercel Serverless Handler for MCP Server.
 *
 * Uses Streamable HTTP transport so AI agents connect via URL + token.
 * No service role key needed on the client — it stays in Vercel env vars.
 *
 * Usage in AI agent config:
 *   URL: https://your-app.vercel.app/api/mcp
 *   Auth: Authorization: Bearer <personal-access-token>
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport }
  from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { authenticateToken } from "./supabase.js";
import { registerAllTools } from "./register-tools.js";

/**
 * Handles an incoming MCP-over-HTTP request.
 *
 * 1. Extracts the bearer token from the Authorization header
 * 2. Validates it against the DB (SHA-256 hash lookup)
 * 3. Creates a fresh McpServer with tools scoped to the authenticated user
 * 4. Processes the JSON-RPC message and returns the response
 */
export async function handleMcpRequest(request: Request): Promise<Response> {
  // ── Auth ────────────────────────────────────────
  const authHeader = request.headers.get("authorization") || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";

  if (!token) {
    return new Response(
      JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message:
            "Authentication required. Include an Authorization: Bearer <token> header " +
            "with a valid MCP access token from your app's Settings page.",
        },
        id: null,
      }),
      {
        status: 401,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  let userId: string;
  try {
    const result = await authenticateToken(token);
    userId = result.userId;
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Invalid access token";
    return new Response(
      JSON.stringify({
        jsonrpc: "2.0",
        error: { code: -32000, message: `Authentication failed: ${msg}` },
        id: null,
      }),
      {
        status: 401,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  // ── Server setup (per-request — fresh transport per request) ──
  const client = (await authenticateToken(token)).client;

  const server = new McpServer({
    name: "yourapp",
    version: "0.1.0",
    description: "Your app — things, care, journal, dashboard.",
  });

  registerAllTools(server, () => client, userId);

  // ── Stateless transport (one request per transport) ──
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
  });

  await server.connect(transport);
  return transport.handleRequest(request);
}
```

### Next.js API Route Gateway

This is the bridge between your Next.js app and the MCP server. Place it at `src/app/api/mcp/route.ts`:

```typescript
/**
 * MCP Server — Vercel HTTP Endpoint (Streamable HTTP)
 *
 * AI agents connect here with their personal access token.
 * The service role key stays server-side in Vercel env vars.
 *
 * Configure your AI agent with:
 *   url: https://your-app.vercel.app/api/mcp
 *   headers: { Authorization: "***" }
 */
import { handleMcpRequest } from "@/lib/mcp/vercel-handler";
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  return handleMcpRequest(request);
}

export async function GET(request: NextRequest) {
  return handleMcpRequest(request);
}
```

**Key details:**
- `runtime = "nodejs"` — The MCP SDK uses Node.js APIs (`crypto.subtle`, HTTP streams). Edge runtime won't work.
- `dynamic = "force-dynamic"` — Prevent Vercel from caching MCP responses.
- Both GET and POST are handled — some MCP clients use GET to establish connections, POST for JSON-RPC messages.
- The `handleMcpRequest` function handles auth, creates a per-request McpServer, and processes the message.

### Import Path Note

The vercel handler lives in `apps/mcp/src/` but is imported by the Next.js app at `src/app/api/mcp/route.ts`. You have two options:

1. **Duplicate the handler** in your Next.js app's `src/lib/mcp/` — simpler, avoids cross-package imports.
2. **Use TypeScript project references** or workspace symlinks — cleaner for monorepos but more setup.

OpenLedger uses approach 1 with a shared `mcp-auth.ts` and `register-tools.ts` duplicated in both `apps/mcp/src/` and `src/lib/mcp/`. The tradeoff is duplication, but the MCP server code rarely changes so it's negligible.

---

## 9. Writing Tools — The Pattern

Every tool follows the same structure. Here is the canonical template:

```typescript
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { Client } from "../supabase.js";

export function registerDomainTools(
  server: McpServer,
  getClient: () => Client,
  userId: string,
) {
  // ── READ (list) ──────────────────────────────────────────────────
  server.tool(
    "list_things",                    // Tool name — lowercase, snake_case
    "List all your things... Use this to get an overview of everything on your account. Returns name, category, and status.",  // Tool description — see rules below
    {
      // Zod schema — each parameter is a named field with a `.describe()`
      thingId: z.string().optional().describe("Optional filter by thing ID"),
      limit: z.number().optional().default(20).describe("Max results to return (default 20, max 100)"),
    },
    async ({ thingId, limit }) => {   // Handler — destructure params
      let query = getClient()
        .from("things")
        .select("*")
        .eq("user_id", userId);       // REQUIRED: user isolation

      if (thingId) query = query.eq("thing_id", thingId);

      const { data, error } = await query.order("created_at");

      if (error) throw new Error("Failed to list things: " + error.message);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data ?? [], null, 2) }],
      };
    },
  );

  // ── READ (single) ────────────────────────────────────────────────
  server.tool(
    "get_thing",
    "Get a specific thing by its ID. Use this when you need the complete details of a single thing rather than a list.",
    {
      thingId: z.string().describe("The ID of the thing to retrieve"),
    },
    async ({ thingId }) => {
      const { data, error } = await getClient()
        .from("things")
        .select("*")
        .eq("id", thingId)
        .eq("user_id", userId)        // REQUIRED: user isolation
        .single();

      if (error) throw new Error(
        "Thing not found or access denied. Verify the thing ID is correct.",
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    },
  );

  // ── WRITE (create) ───────────────────────────────────────────────
  server.tool(
    "create_thing",
    "Create a new thing with a name and optional details. Returns the created record with its assigned ID. Use this when you want to add something new.",
    {
      name: z.string().min(1).describe("The name of the thing (e.g. 'My Monstera', 'Emergency Fund')"),
      category: z.string().optional().describe("Optional category. Use list_categories to see available options."),
      notes: z.string().optional().describe("Optional private notes about this thing"),
    },
    async ({ name, category, notes }) => {
      const { data, error } = await getClient()
        .from("things")
        .insert({
          name,
          user_id: userId,            // REQUIRED: set user on create
          category: category ?? null,
          notes: notes ?? null,
        })
        .select()
        .single();

      if (error) throw new Error(`Failed to create thing: ${error.message}`);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    },
  );

  // ── WRITE (update — with ownership check) ───────────────────────
  server.tool(
    "update_thing",
    "Update an existing thing's fields. Only the fields you provide are changed. Use this to rename, recategorize, or change notes.",
    {
      thingId: z.string().describe("The ID of the thing to update"),
      name: z.string().optional().describe("New name"),
      notes: z.string().optional().describe("New notes"),
    },
    async ({ thingId, name, notes }) => {
      const updates: Record<string, unknown> = {};
      if (name !== undefined) updates.name = name;
      if (notes !== undefined) updates.notes = notes;

      if (Object.keys(updates).length === 0) {
        return {
          content: [{ type: "text" as const, text: "No fields provided to update." }],
        };
      }

      // OWNERSHIP CHECK: verify the resource belongs to this user
      const { data: existing, error: checkError } = await getClient()
        .from("things")
        .select("id")
        .eq("id", thingId)
        .eq("user_id", userId)
        .single();

      if (checkError || !existing) {
        throw new Error("Thing not found or access denied");
      }

      const { data, error } = await getClient()
        .from("things")
        .update(updates)
        .eq("id", thingId)
        .select()
        .single();

      if (error) throw new Error("Failed to update thing: " + error.message);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    },
  );

  // ── WRITE (soft-delete) ──────────────────────────────────────────
  server.tool(
    "delete_thing",
    "Soft-delete a thing. It is not permanently removed and can be viewed by listing with includeDeleted set to true. Use this instead of permanent deletion.",
    {
      thingId: z.string().describe("The ID of the thing to delete"),
    },
    async ({ thingId }) => {
      // Ownership check first
      const { data: existing, error: checkError } = await getClient()
        .from("things")
        .select("id")
        .eq("id", thingId)
        .eq("user_id", userId)
        .single();

      if (checkError || !existing) {
        throw new Error("Thing not found or access denied");
      }

      const { error } = await getClient()
        .from("things")
        .update({ deleted_at: new Date().toISOString() })
        .eq("id", thingId);

      if (error) throw new Error(`Failed to delete thing: ${error.message}`);
      return {
        content: [{ type: "text" as const, text: `Thing ${thingId} deleted successfully.` }],
      };
    },
  );
}
```

### Tool Writing Rules

1. **Tool names** are `snake_case`, short, and verb-first: `list_things`, `get_thing`, `create_thing`.

2. **Tool descriptions** are the most important part — this is what the LLM reads to decide which tool to call.
   - Write complete sentences optimized for AI reading
   - **Tell the agent WHEN to use this tool** vs. alternatives: "Use this to see an overview... Use list_categories to see available options... Use this instead of list_things when looking for specific items."
   - **Mention what it returns**: "Returns name, category, and status."
   - **No markdown, no formatting** — just plain text.
   - ❌ `"List things"` — too short, the LLM has no context
   - ✅ `"List all your things with optional category filter. Returns name, category, creation date, and status. Use this to get an overview of everything on your account."`

3. **Parameter names** are `camelCase` (JavaScript convention) but the `.describe()` text reads naturally: `"The ID of the thing to retrieve"`. Also include **context for the parameter value**: "The category name (e.g. 'Groceries', 'Rent'). Use list_categories to see available options."

4. **Enums for constrained fields** — use `z.enum()` with a `as const` array for status values, categories, types:
   ```typescript
   const STATUSES = ["active", "inactive", "archived"] as const;
   status: z.enum(STATUSES).optional().describe("Filter by status: active, inactive, or archived"),
   ```

5. **Default values for optional parameters** — `z.number().optional().default(20)`.

6. **Output is always** `{ content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] }`.

7. **Error messages are descriptive strings** — the AI reads them and may self-correct: `"Failed to list things: " + error.message`. Never just `throw error`.

8. **`as const` after `"text"`** is required for TypeScript type inference: `{ type: "text" as const, text: ... }`.

9. **`.min(1)` on required strings** — prevents empty-string inserts: `z.string().min(1).describe("...")`.

---

## 10. User Data Isolation — The Critical Rules

Because the MCP server uses a **service-role Supabase client**, RLS policies are completely bypassed. Every query must enforce user isolation in application code.

### Rule 1: Every read query includes `.eq("user_id", userId)`

```typescript
// ✅ CORRECT — scoped to authenticated user
.from("things").select("*").eq("user_id", userId)

// ❌ WRONG — exposes ALL users' data
.from("things").select("*")
```

### Rule 2: Every create includes the userId

```typescript
// ✅ CORRECT — new record belongs to the authenticated user
.insert({ name: "Thing", user_id: userId })

// ❌ WRONG — record has no owner or belongs to wrong user
.insert({ name: "Thing" })
```

### Rule 3: Every mutation does a pre-check ownership query

```typescript
// ✅ CORRECT — verify ownership before update/delete
const { data: existing, error } = await client
  .from("things")
  .select("id")
  .eq("id", thingId)
  .eq("user_id", userId)
  .single();

if (!existing) throw new Error("Thing not found or access denied");

// ❌ WRONG — anyone with a valid token can modify anything
.from("things").update(data).eq("id", thingId)
```

### Rule 4: Soft deletes are always checked

Same ownership check as updates. Always verify before setting `deleted_at`.

### Rule 5: Categories / shared data needs NO user_id filter

If your app has shared reference data (categories, tags, species lists) that all users can read, omit the `user_id` filter on those queries.

---

## 11. Special Tool Patterns

### 11a. Search Tools

Search tools are read tools that take a free-text query and do `ilike` matching on multiple columns:

```typescript
server.tool(
  "search_things",
  "Search things by keyword matching against name, category, and notes. Use this instead of list_things when you need to find something specific but only remember partial details.",
  {
    query: z.string().min(1).describe("Search keyword to match against names, categories, and notes"),
    limit: z.number().optional().default(30).describe("Max results (default 30, max 100)"),
  },
  async ({ query, limit }) => {
    const cappedLimit = Math.min(limit ?? 30, 100);
    const q = `%${query}%`;
    const { data, error } = await getClient()
      .from("things")
      .select("*")
      .eq("user_id", userId)
      .or(`name.ilike.${q},category.ilike.${q},notes.ilike.${q}`)
      .order("name")
      .limit(cappedLimit);

    if (error) throw new Error(`Failed to search things: ${error.message}`);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(data ?? [], null, 2) }],
    };
  },
);
```

Always `.limit()` search results — unbounded ILIKE queries are expensive.

### 11b. Cross-Entity Search (search_everything)

For a unified search across multiple entity types. Fetches in parallel with `Promise.all` and returns a structured result:

```typescript
server.tool(
  "search_everything",
  "Search across all your data — things, accounts, and goals — by keyword. Use this as a unified search to find anything in your records.",
  {
    query: z.string().min(1).describe("Search keyword to match against names, descriptions, and notes across all entities"),
  },
  async ({ query }) => {
    const q = `%${query}%`;

    const [thingsResult, accountsResult, goalsResult] = await Promise.all([
      getClient()
        .from("things")
        .select("*")
        .eq("user_id", userId)
        .or(`name.ilike.${q},category.ilike.${q},notes.ilike.${q}`)
        .order("name")
        .limit(30),
      getClient()
        .from("accounts")
        .select("*")
        .eq("user_id", userId)
        .or(`name.ilike.${q}`)
        .limit(20),
      getClient()
        .from("goals")
        .select("*")
        .eq("user_id", userId)
        .ilike("name", q)
        .limit(20),
    ]);

    const results: Record<string, unknown[]> = {
      things: thingsResult.data ?? [],
      accounts: accountsResult.data ?? [],
      goals: goalsResult.data ?? [],
    };

    return {
      content: [{ type: "text" as const, text: JSON.stringify(results, null, 2) }],
    };
  },
);
```

Returns a structured object with named keys so the LLM can easily find the right section.

### 11c. Aggregate / Dashboard Tools

These tools compute summaries across multiple tables. They don't create or modify data — they return computed insights.

**Account Summary** — aggregate balances by type:

```typescript
server.tool(
  "get_account_summary",
  "Get a summary of all active accounts: total balance, net worth, and breakdown by account type. Use this for a quick financial overview.",
  {},
  async () => {
    const { data: accounts, error } = await getClient()
      .from("accounts")
      .select("*")
      .eq("user_id", userId);

    if (error) throw new Error(`Failed to get summary: ${error.message}`);

    const byKind: Record<string, { count: number; total: number }> = {};
    let totalBalance = 0;

    for (const acct of accounts ?? []) {
      const kind = acct.kind;
      if (!byKind[kind]) byKind[kind] = { count: 0, total: 0 };
      byKind[kind].count++;
      byKind[kind].total += (acct as { balance: number }).balance;
      totalBalance += (acct as { balance: number }).balance;
    }

    return {
      content: [{ type: "text" as const, text: JSON.stringify({
        totalAccounts: accounts?.length ?? 0,
        totalBalance,
        breakdownByType: byKind,
      }, null, 2) }],
    };
  },
);
```

**Monthly Summary** — compute income/expenses by month:

```typescript
server.tool(
  "get_monthly_summary",
  "Get income and expense totals for a specific month, broken down by category. Use this to see how much you earned, spent, and where the money went.",
  {
    month: z.string().optional().describe("Month in YYYY-MM format (e.g. '2026-06'). Defaults to the current month."),
  },
  async ({ month }) => {
    const targetMonth = month ?? new Date().toISOString().slice(0, 7);
    const startDate = `${targetMonth}-01`;
    const endDate = new Date(
      new Date(startDate).getFullYear(),
      new Date(startDate).getMonth() + 1,
      0,
    ).toISOString().slice(0, 10);

    const { data: transactions, error } = await getClient()
      .from("transactions")
      .select("amount, category")
      .eq("user_id", userId)
      .gte("date", startDate)
      .lte("date", endDate);

    if (error) throw new Error(`Failed to get monthly summary: ${error.message}`);

    // Compute totals and category breakdown...
    // Return { month, totalIncome, totalExpenses, netChange, byCategory }
  },
);
```

**Budget vs. Actual** — compare budgeted amounts against actual spending:

```typescript
server.tool(
  "get_budget_vs_actual",
  "Compare budgeted amounts against actual spending for a given month. Returns category-by-category breakdown showing budgeted, actual, and remaining. Use this to track budget adherence.",
  { month: z.string().optional().describe("Month in YYYY-MM format") },
  async ({ month }) => {
    // Fetch budgets AND transactions for the month in parallel
    const [budgetsResult, txResult] = await Promise.all([
      client.from("budgets").select("*").eq("user_id", userId).eq("month", targetMonth),
      client.from("transactions").select("amount, category").eq("user_id", userId)...
    ]);
    // Merge and compare...
  },
);
```

**Key patterns for dashboard tools:**
- Use `Promise.all` when fetching data from multiple tables
- Return computed structures, not raw rows
- Handle empty results gracefully (empty arrays, zero balances)
- Set reasonable defaults for optional month/year parameters

### 11d. Contribute / Increment Pattern

For tools that need to **increment a computed field** rather than replace it:

```typescript
server.tool(
  "contribute_to_goal",
  "Add a contribution amount to a savings goal, increasing its current progress. Use this when you want to record saving money toward a goal.",
  {
    goalId: z.string().describe("The ID of the goal to contribute to"),
    amount: z.number().positive().describe("The amount to add to the goal's current progress"),
  },
  async ({ goalId, amount }) => {
    // Ownership check + fetch current state
    const { data: goal, error: getError } = await getClient()
      .from("goals")
      .select("*")
      .eq("id", goalId)
      .eq("user_id", userId)
      .single();

    if (getError || !goal) throw new Error("Goal not found or access denied");

    // Increment (not replace)
    const newAmount = (goal as { current_amount: number }).current_amount + amount;
    const newStatus = newAmount >= (goal as { target_amount: number }).target_amount
      ? "completed"
      : "active";

    const { data, error } = await getClient()
      .from("goals")
      .update({ current_amount: newAmount, status: newStatus })
      .eq("id", goalId)
      .select()
      .single();

    if (error) throw new Error(`Failed to contribute: ${error.message}`);
    return {
      content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    };
  },
);
```

**Pattern:** read current value → compute new value → write back. Use this instead of requiring the agent to fetch-and-update in two steps.

### 11e. Rate-Limited Tools

For paid API calls (e.g., an AI identification service), implement a simple in-memory rate limiter:

```typescript
const RATE_LIMIT_WINDOW_MS = 60_000;
const MAX_CALLS_PER_WINDOW = 10;
let callTimestamps: number[] = [];

function checkRateLimit(): void {
  const now = Date.now();
  callTimestamps = callTimestamps.filter(ts => now - ts < RATE_LIMIT_WINDOW_MS);
  if (callTimestamps.length >= MAX_CALLS_PER_WINDOW) {
    const retryAfter = RATE_LIMIT_WINDOW_MS - (now - callTimestamps[0]);
    throw new Error(
      `Rate limit exceeded. Max ${MAX_CALLS_PER_WINDOW} calls per minute. Retry in ~${Math.ceil(retryAfter / 1000)}s.`,
    );
  }
  callTimestamps.push(now);
}
```

### 11f. Export / Data Dump Tools

Use `Promise.all` to fetch all user data in parallel:

```typescript
const [things, schedules, logs] = await Promise.all([
  client.from("things").select("*").eq("user_id", userId),
  client.from("schedules").select("*").eq("user_id", userId),
  client.from("logs").select("*").eq("user_id", userId),
]);
```

Return a structured JSON object with named keys.

---

## 12. Testing

### 12a. Test Structure

Two test files mirror the production code:

- **`auth.test.ts`** — Tests token validation logic (missing credentials, invalid tokens, revoked tokens, SHA-256 computation).
- **`tools.test.ts`** — Tests input schema validation (Zod parsing), output shape, user scoping, and ownership check errors.

### 12b. Mocking the Supabase Query Builder

The Supabase client's `.from().select().eq()...` chain is challenging to type correctly in tests. The key insight: make the chain object **thenable** (has a `.then()` method) so `await chain.eq(...)` resolves properly.

```typescript
function createMockDb() {
  const mockQuery: Record<string, vi.Mock> = {
    select: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    update: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    is: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    limit: vi.fn().mockReturnThis(),
    or: vi.fn().mockReturnThis(),
    single: vi.fn().mockReturnThis(),
    gte: vi.fn().mockReturnThis(),
    lte: vi.fn().mockReturnThis(),
    range: vi.fn().mockReturnThis(),
  };

  // Make the chain await-able
  const thenFn = vi.fn((resolve: (v: unknown) => unknown) =>
    resolve({ data: [], error: null }),
  );
  mockQuery["then"] = thenFn;

  for (const [key, mock] of Object.entries(mockQuery)) {
    if (key === "then") continue;
    mock.mockReturnValue(mockQuery);
  }

  return {
    mockClient: { from: vi.fn(() => mockQuery) },
    mockQuery,
  };
}
```

### 12c. What to Test

| Test Category | Examples |
|--------------|---------|
| **Input validation** | Missing required fields throw ZodError. Invalid enum values throw. Valid inputs parse correctly. |
| **Output shape** | Every tool returns `{ content: [{ type: "text", text: expect.any(String) }] }`. |
| **User scoping** | Read tools call `.eq("user_id", userId)`. Create tools set `user_id: userId`. |
| **Ownership checks** | Update/delete tools throw "not found or access denied" when pre-check returns null. |
| **Auth** | Missing env vars throw. Invalid tokens throw. Revoked tokens throw. Valid tokens return `{client, userId}`. |

---

## 13. Token Management API (Next.js)

Your web app needs API endpoints for users to create, list, and revoke MCP tokens.

### POST /api/mcp/tokens — Create Token

Use `generateToken()` and `sha256Hex()` from your auth layer.

```typescript
// src/app/api/mcp/tokens/route.ts
import { sha256Hex, generateToken } from "@/lib/mcp/auth"; // or from apps/mcp/src/supabase.ts
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const body = await request.json();
  const name = typeof body.name === "string" ? body.name.trim() : "";
  if (!name) {
    return NextResponse.json(
      { error: "Token name is required. Give your token a descriptive name." },
      { status: 400 },
    );
  }

  // Generate token
  const rawToken = generateToken("app"); // e.g. "app_abc123..."
  const tokenHash = await sha256Hex(rawToken);

  // Store hash + prefix
  const admin = createAdminClient();
  const { error: insertError } = await admin
    .from("mcp_tokens")
    .insert({
      name,
      user_id: user.id,
      token_hash: tokenHash,
      token_prefix: rawToken.slice(0, 10) + "...",
    });

  if (insertError) {
    return NextResponse.json(
      { error: `Failed to create token: ${insertError.message}` },
      { status: 500 },
    );
  }

  // Return raw token ONCE
  return NextResponse.json({
    token: rawToken,
    message: "Token created. This is the only time it will be shown. Save it now.",
  });
}
```

### GET /api/mcp/tokens — List Tokens

Returns metadata only — never expose `token_hash`:

```typescript
export async function GET() {
  // Auth check...
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("mcp_tokens")
    .select("id, name, token_prefix, last_used_at, created_at, revoked_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  return NextResponse.json({ tokens: data ?? [] });
}
```

### DELETE /api/mcp/tokens/[id] — Revoke Token

Sets `revoked_at` timestamp. The server rejects revoked tokens on auth.

```typescript
// src/app/api/mcp/tokens/[id]/route.ts
export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  // Auth check...
  const { id } = await params;

  // Verify the token belongs to the current user
  const admin = createAdminClient();
  const { data: existing } = await admin
    .from("mcp_tokens")
    .select("id, user_id")
    .eq("id", id)
    .single();

  if (!existing) return NextResponse.json({ error: "Token not found." }, { status: 404 });
  if (existing.user_id !== user.id) {
    return NextResponse.json({ error: "Access denied." }, { status: 403 });
  }

  await admin
    .from("mcp_tokens")
    .update({ revoked_at: new Date().toISOString() })
    .eq("id", id);

  return NextResponse.json({ message: "Token revoked successfully." });
}
```

---

## 14. MCP Tokens Panel UI Component

Your settings page needs a UI for users to create, list, and revoke tokens. Here's a reusable React component:

```tsx
"use client";

import { useState, useEffect } from "react";

interface McpToken {
  id: string;
  name: string;
  token_prefix: string;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
}

export function McpTokensPanel() {
  const [tokens, setTokens] = useState<McpToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTokenName, setNewTokenName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const loadTokens = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/mcp/tokens");
      if (!res.ok) throw new Error("Failed to load tokens");
      setTokens((await res.json()).tokens ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tokens");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTokens(); }, []);

  const handleCreate = async () => {
    const name = newTokenName.trim();
    if (!name || name.length > 100) return;
    try {
      setCreating(true);
      setNewToken(null);
      const res = await fetch("/api/mcp/tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setNewToken(data.token);
      setNewTokenName("");
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create token");
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      setRevokingId(id);
      const res = await fetch(`/api/mcp/tokens/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to revoke");
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke");
    } finally {
      setRevokingId(null);
    }
  };

  const activeTokens = tokens.filter((t) => !t.revoked_at);
  const revokedTokens = tokens.filter((t) => t.revoked_at);

  return (
    <div>
      <p style={{ marginBottom: 16, lineHeight: 1.5, fontSize: 14, color: "var(--text-secondary)" }}>
        MCP access tokens allow AI agents like Claude Code, ChatGPT, and others
        to read and write your data on your behalf.
        Tokens are stored as SHA-256 hashes — the raw token is shown once at creation.
      </p>

      {/* Create form */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <input
          type="text"
          value={newTokenName}
          onChange={(e) => setNewTokenName(e.target.value)}
          placeholder="Token name (e.g. Claude Code)"
          disabled={creating}
          maxLength={100}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button onClick={handleCreate} disabled={creating || !newTokenName.trim()}>
          {creating ? "Creating..." : "Create Token"}
        </button>
      </div>

      {/* New token display */}
      {newToken && (
        <div style={{ padding: 16, borderRadius: 8, border: "1px solid var(--accent)", marginBottom: 20 }}>
          <strong>⚠️ Copy this token now — it will never be shown again</strong>
          <code style={{ display: "block", padding: 12, wordBreak: "break-all", userSelect: "all" }}>
            {newToken}
          </code>
          <button onClick={() => navigator.clipboard.writeText(newToken)}>
            Copy to clipboard
          </button>
        </div>
      )}

      {/* Error */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Active tokens */}
      {activeTokens.map((token) => (
        <div key={token.id} style={{ display: "flex", justifyContent: "space-between" }}>
          <span>
            <strong>{token.name}</strong>
            <code style={{ marginLeft: 8 }}>{token.token_prefix}</code>
            <span style={{ marginLeft: 8, color: "var(--text-tertiary)" }}>
              {token.last_used_at ? `Last used: ${new Date(token.last_used_at).toLocaleDateString()}` : "Never used"}
            </span>
          </span>
          <button onClick={() => handleRevoke(token.id)} disabled={revokingId === token.id}>
            Revoke
          </button>
        </div>
      ))}

      {/* Empty state */}
      {!loading && activeTokens.length === 0 && !newToken && (
        <p style={{ fontStyle: "italic", color: "var(--text-tertiary)" }}>
          No MCP tokens configured. Create one above.
        </p>
      )}
    </div>
  );
}
```

**Key UI behaviors:**
- Token is shown once in a copy-able code block
- Active and revoked tokens are separated
- Token prefix (first 10 chars) identifies tokens without exposing hashes
- "Last used" date helps users know if a token is still in use

---

## 15. Agent Configuration

### Remote HTTP (production — preferred)

Use this when the MCP server is deployed (Vercel, etc.). No local process needed.

**Claude Code / Claude Desktop:**

```json
// ~/.claude/settings.json (global) or .claude/settings.local.json (project)
{
  "mcpServers": {
    "yourapp": {
      "url": "https://your-app.vercel.app/api/mcp",
      "headers": {
        "Authorization": "Bearer ***"  // Your personal token
      }
    }
  }
}
```

**Cursor:**
1. Settings → MCP → Add Server
2. URL: `https://your-app.vercel.app/api/mcp`
3. Headers: `{ "Authorization": "Bearer ***" }`

**ChatGPT (MCP support):**
Follow your client's instructions for configuring a Streamable HTTP MCP server with the URL and Authorization header above.

### Local stdio (development/debugging)

Use this when running the server locally.

**Hermes Agent:**

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  yourapp:
    command: "node"
    args: ["/path/to/apps/mcp/dist/index.js"]
```

Set env vars in `~/.hermes/.env`:
```bash
YOUR_APP_ACCESS_TOKEN=tok_abc123...
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sr_abc456...
```

**Claude Code:**

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "yourapp": {
      "command": "node",
      "args": ["/path/to/apps/mcp/dist/index.js"],
      "env": {
        "YOUR_APP_ACCESS_TOKEN": "tok_abc123...",
        "NEXT_PUBLIC_SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "sr_abc456..."
      }
    }
  }
}
```

**Cursor:**
Settings → MCP → Add Server → Command: `node /path/to/apps/mcp/dist/index.js`
Add the three env vars.

---

## 16. Common Pitfalls

1. **Missing `.eq("user_id", userId)` on a read query** — This is the #1 data leak. Every read, every write, every filter. If you forget it even once, the agent can read every user's data.

2. **Missing ownership check on a write query** — Without it, user A with a valid token can delete user B's data. The pattern is always: `select("id").eq("id", resourceId).eq("user_id", userId).single()` before the mutation.

3. **Generic error messages** — `throw error` or `throw new Error("Something went wrong")` gives the AI agent nothing to work with. Every error should say what failed and what the agent can do about it: `"Failed to list things: <specific error>. Check that your database connection is configured correctly."`

4. **Trying to use RLS instead of app-level isolation** — The service role bypasses RLS by design. Do not rely on RLS. The application layer is your security boundary.

5. **Not setting `as const` on `"text"`** — TypeScript will complain about the content array type. Always write `{ type: "text" as const, text: ... }`.

6. **Using `createClient` with the anon key** — The anon key cannot read the `mcp_tokens` table. You must use the service role key for auth queries and data queries.

7. **Not filtering soft-deleted records** — Always add `.is("deleted_at", null)` to read queries. Soft-deleted records should be invisible to agents.

8. **Tool names that don't match the function** — The LLM reads the tool name and description to choose the right tool. `list_things` is clear. `get_things_with_filter` is not. Keep names short and verbs precise.

9. **Forgetting `--include-all` on production migrations** — When pushing a new migration to an existing Supabase project, `supabase db push` only pushes migrations not yet recorded in the `_supabase_migrations` table. If you're running this for the first time on a production DB, you need `--include-all` — but that re-runs every migration including type creations. Apply new migrations directly via the Management API SQL endpoint to avoid conflicts.

10. **Writing a tool that returns empty arrays for everything** — If you have a knowledge base or diagnosis table, seed it with real data. An empty MCP server with 25 tools that all return `[]` is useless. Seed data is part of the MCP implementation.

11. **Tool descriptions that are too short** — "List things" is useless to an LLM. Every description should say what the tool does, what it returns, AND when to use it vs. alternatives.

12. **Not adding the `token_hash` index** — Without `create index on mcp_tokens(token_hash)`, every auth request scans the entire table. This is fine at 10 tokens but fails at 10,000 users.

13. **Using Edge Runtime for the MCP API route** — The MCP SDK needs `crypto.subtle` and Node.js streams. Edge Runtime doesn't support these. Always set `export const runtime = "nodejs"`.

14. **Vercel 10-second timeout** — Serverless functions on Vercel's Hobby plan have a 10-second timeout. Long-running MCP operations (large exports) may time out. Either keep responses fast or upgrade to Pro (60s/300s/900s).

---

## 17. Verification Checklist

Before deploying:

- [ ] Every read query includes `.eq("user_id", userId)`.
- [ ] Every create sets `user_id: userId`.
- [ ] Every update/delete has an ownership pre-check.
- [ ] Soft-deleted records are filtered with `.is("deleted_at", null)`.
- [ ] Tool descriptions are complete sentences optimized for AI reading — include "when to use" guidance.
- [ ] Error messages describe the failure and suggest next steps.
- [ ] All enum values are defined as `as const` arrays.
- [ ] Search tools have `.limit()` to prevent unbounded queries.
- [ ] `npm run typecheck` passes with zero errors.
- [ ] `npm run test` passes — all input validation, output shape, user scoping, and ownership tests.
- [ ] `npm run build` produces a clean `dist/` directory.

**Stdio server:**
- [ ] Server exits with code 1 when token is missing (clear error message).
- [ ] Server exits with code 1 when token is invalid ("Invalid access token").
- [ ] Server starts cleanly with a valid token and registers all tools.

**HTTP server:**
- [ ] `POST /api/mcp` without auth header returns 401.
- [ ] `POST /api/mcp` with invalid/revoked token returns 401.
- [ ] `POST /api/mcp` with valid token returns successful JSON-RPC response.
- [ ] API route is set to `runtime = "nodejs"` (not Edge).
- [ ] API route is set to `dynamic = "force-dynamic"`.

**Every tool:**
- [ ] Returns `{ content: [{ type: "text", text: <JSON> }] }`.
- [ ] Handles empty results gracefully (`[]` or `null`).

**Documentation:**
- [ ] Agent config exists for both remote HTTP and local stdio.
- [ ] Token creation API is documented.
- [ ] MCP Tokens Panel UI is integrated into your app's settings.

---

## 18. Real-World Audit

After deployment, run the following audit from an AI agent connected to the MCP server:

| # | Test | Expected |
|---|------|----------|
| 1 | List all things | Returns JSON array (empty is fine) |
| 2 | Get a specific thing by ID | Returns full record |
| 3 | Create a thing | Returns created record with ID |
| 4 | Update the thing's name | Returns updated record |
| 5 | List things to confirm the change | Updated name appears |
| 6 | Delete the thing | Returns success message |
| 7 | List things to confirm deletion | Thing no longer appears |
| 8 | Search by name | Returns matching results |
| 9 | Try accessing a non-existent thing | Returns "Thing not found" |
| 10 | Try updating something that doesn't exist | Returns "not found or access denied" |
| 11 | Try connecting with no token | Returns 401 / exit with error |
| 12 | Try connecting with an invalid token | Returns 401 / exit with error |
| 13 | Create a token, revoke it, then try to use it | Returns "revoked" error |

Each test should succeed with descriptive error messages on failure, not generic errors.

---

## Project References

- **MCP SDK docs**: https://github.com/modelcontextprotocol/typescript-sdk
- **OpenLedger reference implementation**: `apps/mcp/` in the OpenLedger repository
- **Auth pattern**: `apps/mcp/src/supabase.ts` — canonical token validation implementation
- **Tool patterns**: `apps/mcp/src/tools/` — accounts, transactions, categories, budgets, goals, dashboard, search
- **HTTP transport**: `apps/mcp/src/vercel-handler.ts` — Streamable HTTP + `handleMcpRequest`
- **API routes**: `src/app/api/mcp/` — gateway, token create/list/revoke
- **UI component**: `src/components/mcp-tokens-panel.tsx` — token management UI
- **Test patterns**: `apps/mcp/src/__tests__/`
- **Database migrations**: `supabase/migrations/20260624000002_openledger_mcp_tokens.sql` — token table schema

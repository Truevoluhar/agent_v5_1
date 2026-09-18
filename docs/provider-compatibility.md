# OpenAI and vLLM configuration

The runtime uses Chat Completions by default for orchestration, worker tools,
and final structured responses. Every chat request merges system
and developer instructions into one system message at index zero. This avoids the
`System message must be at the beginning` error from templates that reject a
second system message. Context retries use the same normalization.

New-session titles are derived locally from the first eight words of the prompt.
They do not make a separate provider request, so a title cannot delay a run,
consume model tokens, or emit a misleading connection warning before execution.

The OpenAI profile in `agent/config.yml` uses `gpt-4.1-mini`. The former internal
Qwen model ID is not an OpenAI model ID; changing the URL alone is insufficient.
The internal name and URL are preserved in `agent/config_vllm.yml`.

Both CLI and service load the repository `.env`, preserving variables already
provided by the process environment. `api_key` in YAML is an **environment variable
name**, not a secret value. OpenAI uses `OPENAI_API_KEY`; the internal profile uses
`VLLM_API_KEY` to avoid sending the OpenAI credential to an internal endpoint.
Set that variable to the internal server's token (or a nonempty placeholder if
that server does not require authentication).

To switch the chat service or CLI, set these variables and restart it:

```bash
export AGENT_CONFIG_PATH=agent/config_vllm.yml
python -m chat.api
```

The CLI honors the same `AGENT_CONFIG_PATH`. Alternatively, copy the desired
profile's settings into `agent/config.yml` and restart the process. Configuration
is loaded when the runner starts; an already-running service does not reload it.

Shared options are configured under top-level `llm`; a role's own `llm` mapping
can override them:

```yaml
llm:
  api_mode: chat_completions
  reasoning_effort: null
  timeout: 120
  verify_ssl: auto
  extra_body: {}
```

`reasoning_effort: null` omits reasoning parameters instead of assuming every model
accepts `medium`. Set a supported value explicitly when needed. Role
`temperature: null` similarly omits temperature. Provider-specific parameters,
such as supported chat-template settings, can be supplied through `extra_body`.
`verify_ssl: auto` disables certificate verification only when the base URL's exact
hostname is `api.openai.com`. Internal vLLM and every other hostname keep
verification enabled. Explicit `true` and `false` values remain supported, and a
CA-bundle path can be used for internal TLS through `llm.ca_bundle` or the
`VLLM_CA_BUNDLE` environment variable. The bundled vLLM profile uses `true`.

`api_mode: responses` remains available for workers on servers that support it.
The worker preserves stateless tool history and encrypted reasoning on that path.
Chat mode does not call `/responses`; it retains matching tool-call IDs and the
server's `reasoning_content`/`reasoning` fields when continuing a tool round.

## vLLM server requirements

The internal deployment must expose `/v1/chat/completions` with the correct served
model name, a compatible chat template, automatic tool calling with the parser
appropriate to its exact Qwen build, and JSON-schema structured output support.
These are server settings: a base-URL switch cannot fix a missing tool parser or
an incompatible template. Parser names and thinking options depend on the vLLM
version and model packaging; this change does not guess or alter that deployment.
See the official [vLLM API documentation](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
and [tool-calling configuration](https://docs.vllm.ai/en/latest/features/tool_calling/).
The common protocol follows [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).

## Live verification

Run the opt-in test with the same profile used by the application:

```bash
python scripts/live_smoke.py --config agent/config.yml
python scripts/live_smoke.py --config agent/config_vllm.yml
```

This makes real, billable model calls. It creates a temporary workspace containing
a synthetic ZIP, invokes the real runner, checks per-file README artifacts and
queue coverage, concrete usage examples, and reported artifact paths, and saves `report.json` alongside the workspace. It limits the
fixture to 1–10 files, the runner to eight steps, and each worker to 25 tool rounds.
Use `--embedding-cache /writable/cache` if Chroma's default cache is unavailable.

Unit tests additionally use the real SDK against a strict simulated server to
check one leading system message, context retries, structured decisions, multiple
tool calls, and vLLM reasoning replay. A simulated server establishes request
compatibility, not successful execution on a specific internal deployment.

Final-response synthesis also receives verified artifact paths from the durable work ledger. The complete evidence is saved in `.agent/work/*.report.json`, avoiding dependence on older chat messages that may have been compacted.

## Offline semantic memory

Chroma's default embedding function downloads an ONNX model the first time a
message is indexed. The Docker services set `AGENT_SEMANTIC_MEMORY=disabled` so a
container without external DNS can run normally. Durable SQLite session history,
recent-message context, summaries, and lexical retrieval remain available.

Set `AGENT_SEMANTIC_MEMORY=auto` after making the embedding model available to the
container if vector retrieval is wanted. The Compose file now defaults to `auto`
for both the CLI and chat service, while runtime failures still fall back to
SQLite and lexical retrieval. In auto mode, initialization, embedding, or query
failures disable vector retrieval for that process and emit one warning; they no
longer fail the run. `enabled` has the same runtime fallback but warns when
Chroma is not installed.

## Docker bridge without outbound access

In some managed development environments, Docker bridge containers cannot reach
external TCP endpoints even though the host and image builder can. Confirm this
before changing networking: DNS queries fail inside the running container and a
direct TCP connection to a host-resolved API address times out.

For this managed environment, the trusted local agent services use host
networking in the base Compose file:

```bash
docker compose up -d --force-recreate agent-api
```

There is no `8100:8100` mapping because `agent-api` binds directly to the host's
port 8100. Host networking removes Docker's network namespace isolation, so use it
only for the trusted local image. On deployments with working bridge egress,
remove `network_mode: host` and restore the `8100:8100` port mapping.

Validation for this change: 50 local tests passed. The final OpenAI smoke test
using `gpt-4.1-mini` completed in 47.1 seconds with 3/3 source tasks complete,
three verified READMEs containing correct examples, and a structured response
listing the actual output paths. An earlier attempt timed out; another exposed
missing example text and invented output paths, which the final test checks now
cover. The internal vLLM deployment was not contacted with the OpenAI credential;
its specific server configuration still requires the same live test internally.

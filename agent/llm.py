"""Provider-neutral request formatting for OpenAI and OpenAI-compatible servers."""
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

from openai import OpenAI, DefaultHttpxClient

from agent.messages import normalize_chat_messages


PUBLIC_OPENAI_API_HOSTS = frozenset({'api.openai.com'})


def safe_endpoint(base_url):
    """Return only scheme and host, never credentials, paths, or query data."""
    parsed = urlsplit(str(base_url or ""))
    if not parsed.scheme or not parsed.hostname:
        return "unconfigured"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def safe_exception_summary(exc, max_chars=1800):
    """Expose useful transport causes without leaking credentials."""
    parts = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen and len(parts) < 8:
        seen.add(id(current))
        text = " ".join(str(current).split()) or "no message"
        text = re.sub(r"(?i)(authorization[=: ]+bearer[ ]+)[^ ]+", r"\1[redacted]", text)
        text = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[redacted-api-key]", text)
        entry = f"{type(current).__name__}: {text}"
        if entry not in parts:
            parts.append(entry)
        current = current.__cause__ or current.__context__
    return " <- ".join(parts)[:max_chars]


def resolve_ssl_verification(base_url, configured='auto'):
    """Resolve TLS verification without weakening non-OpenAI endpoints."""
    if isinstance(configured, str) and configured.strip().lower() == 'auto':
        hostname = (urlsplit(str(base_url or '')).hostname or '').lower()
        return hostname not in PUBLIC_OPENAI_API_HOSTS
    return configured


def create_client(api_key, base_url, options=None):
    options = options or {}
    if not api_key:
        raise ValueError("Configured LLM API key is missing; check the api_key environment variable named in config")
    return OpenAI(
        api_key=api_key, **({'base_url': base_url} if base_url else {}),
        timeout=options.get('timeout', 120), max_retries=options.get('max_retries', 2),
        http_client=DefaultHttpxClient(
            verify=resolve_ssl_verification(base_url, options.get('verify_ssl', 'auto'))
        ),
    )


def generation_options(options, temperature, *, responses=False):
    result = {}
    if temperature is not None:
        result['temperature'] = temperature
    effort = options.get('reasoning_effort')
    if effort:
        result['reasoning' if responses else 'reasoning_effort'] = {'effort': effort} if responses else effort
    if options.get('extra_body'):
        result['extra_body'] = options['extra_body']
    return result


def _as_dict(item):
    if isinstance(item, dict):
        return item
    return item.model_dump(exclude_none=True) if hasattr(item, 'model_dump') else vars(item)


def items_to_chat(items, instructions):
    items = [_as_dict(item) for item in items]
    represented = {call['id'] for item in items if item.get('type') == 'chat_message'
                   for call in item['message'].get('tool_calls', [])}
    messages = []
    for item in items:
        kind = item.get('type')
        if kind == 'chat_message':
            messages.append(item['message'])
        elif kind == 'function_call':
            if item['call_id'] not in represented:
                call = {'id': item['call_id'], 'type': 'function',
                        'function': {'name': item['name'], 'arguments': item['arguments']}}
                if messages and messages[-1].get('tool_calls'):
                    messages[-1]['tool_calls'].append(call)
                else:
                    messages.append({'role': 'assistant', 'content': None, 'tool_calls': [call]})
        elif kind == 'function_call_output':
            messages.append({'role': 'tool', 'tool_call_id': item['call_id'], 'content': item['output']})
        elif item.get('role') in {'user', 'assistant', 'system', 'developer'}:
            messages.append({'role': item['role'], 'content': item.get('content', '')})
        else:
            raise ValueError(f'Unsupported item in chat-completions history: {kind}')
    return normalize_chat_messages(messages, instructions)


def create_tool_response(client, *, model, instructions, input, tools, options, temperature):
    """Keep the runtime's durable tool loop independent of the wire API."""
    mode = options.get('api_mode', 'chat_completions')
    if mode == 'responses':
        return client.responses.create(
            model=model, instructions=instructions, input=input, tools=tools,
            tool_choice='auto', store=False, include=['reasoning.encrypted_content'],
            **generation_options(options, temperature, responses=True),
        )
    if mode != 'chat_completions':
        raise ValueError('llm.api_mode must be chat_completions or responses')
    chat_tools = [{'type': 'function', 'function': {k: v for k, v in tool.items() if k != 'type'}} for tool in tools]
    completion = client.chat.completions.create(
        model=model, messages=items_to_chat(input, instructions),
        **({'tools': chat_tools, 'tool_choice': 'auto'} if chat_tools else {}),
        **generation_options(options, temperature),
    )
    choice = completion.choices[0]
    message = choice.message
    if choice.finish_reason == 'length':
        raise RuntimeError('Model output limit reached; increase server output budget or reduce the task size')
    if message.refusal:
        raise RuntimeError(f'Model refused the request: {message.refusal}')
    wire_message = {'role': 'assistant', 'content': message.content}
    calls = message.tool_calls or []
    if calls:
        wire_message['tool_calls'] = [call.model_dump(exclude_none=True) for call in calls]
    # vLLM reasoning parsers may return either field; retain it during tool replay.
    for name in ('reasoning_content', 'reasoning'):
        value = getattr(message, name, None)
        if value:
            wire_message[name] = value
    output = [SimpleNamespace(type='chat_message', message=wire_message)]
    output.extend(SimpleNamespace(type='function_call', name=call.function.name,
                                  arguments=call.function.arguments, call_id=call.id) for call in calls)
    return SimpleNamespace(output=output, output_text=message.content or '', status='completed')

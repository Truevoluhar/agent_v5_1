"""Chat message normalization shared by all provider paths."""

def normalize_chat_messages(messages, instructions=None):
    """Some chat templates accept exactly one system message, at index zero."""
    system = [instructions] if instructions else []
    conversation = []
    for original in messages:
        message = dict(original)
        if message.get('role') in {'system', 'developer'}:
            content = message.get('content')
            if content:
                system.append(str(content))
        else:
            conversation.append(message)
    return ([{'role': 'system', 'content': '\n\n'.join(system)}] if system else []) + conversation


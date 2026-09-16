import json

from agent.work_queue import WorkQueue
from agent.tools.tools_models import Tool, ToolResult


def work_queue_executor(workspace, action, task_id, text, root, pattern, artifacts, scope='default'):
    queue = WorkQueue(workspace, scope)
    if action == 'inventory':
        result = queue.inventory(root or '.', pattern or '**/*', text)
    elif action == 'add':
        result = queue.add(text)
    elif action == 'next':
        result = queue.claim()
    elif action == 'read':
        result = queue.read(task_id)
    elif action == 'complete':
        result = queue.finish(task_id, text, artifacts)
    elif action == 'fail':
        result = queue.fail(task_id, text)
    elif action == 'refresh':
        result = queue.refresh(task_id)
    elif action == 'verify':
        result = queue.verify()
    elif action == 'status':
        result = queue.summary()
    else:
        raise ValueError('Unknown work queue action')
    return ToolResult(ok=True, output=json.dumps(result, ensure_ascii=False))


WORK_QUEUE_TOOL = Tool(
    name='work_queue',
    description=('Durable session task ledger for large/multi-file work. Inventory snapshots all matching files without putting them in context. '
                 'next resumes/claims one task; read returns the next source chunk (repeat until eof); complete requires evidence and artifact paths. '
                 'Use add for non-file subtasks, fail for errors, refresh to reset changed/exhausted tasks, verify before finishing. '
                 'Unused fields: task_id=0, text/root/pattern="", artifacts=[].'),
    parameters={'type': 'object', 'properties': {
        'action': {'type': 'string', 'enum': ['inventory','add','next','read','complete','fail','refresh','verify','status']},
        'task_id': {'type': 'integer'}, 'text': {'type': 'string'},
        'root': {'type': 'string'}, 'pattern': {'type': 'string'},
        'artifacts': {'type': 'array', 'items': {'type': 'string'}},
    }, 'required': ['action','task_id','text','root','pattern','artifacts'], 'additionalProperties': False},
    executor=work_queue_executor,
)

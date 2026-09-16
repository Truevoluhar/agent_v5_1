"""Opt-in live model integration check using a synthetic ZIP in a temporary workspace.

Usage: python scripts/live_smoke.py --config agent/config.yml
This makes billable calls to the configured provider; never runs during unit tests.
"""
import argparse
import json
import re
from pathlib import Path
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.runner import AgentRunner, RunRequest
from agent.work_queue import WorkQueue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='agent/config.yml')
    parser.add_argument('--files', type=int, default=3)
    parser.add_argument('--embedding-cache', help='Optional writable Chroma model cache')
    args = parser.parse_args()
    if not 1 <= args.files <= 10:
        parser.error('--files must be between 1 and 10 for this bounded smoke test')
    if args.embedding_cache:
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = Path(args.embedding_cache)
    root = Path(tempfile.mkdtemp(prefix='agent-live-smoke-'))
    workspace = root / 'workspace'
    workspace.mkdir()
    with zipfile.ZipFile(workspace / 'source.zip', 'w') as archive:
        for n in range(args.files):
            archive.writestr(f'module_{n}.py', f'def add_{n}(value: int) -> int:\n    """Return value plus {n}."""\n    return value + {n}\n')
    runner = AgentRunner(args.config)
    runner.config.update(session=str(root / 'sessions'), memory=str(root / 'memory'),
                         agents_resources=str(Path(__file__).resolve().parents[1] / 'data/resources/agents'),
                         max_steps=8, max_worker_iterations=25)
    runner.config['llm'] = {**runner.config.get('llm', {}), 'timeout': 120, 'max_retries': 1}
    started = time.monotonic()
    events = []
    def emit(event):
        events.append(event.type)
        print('EVENT', event.type, flush=True)
    def no_input(question):
        raise RuntimeError('Smoke test unexpectedly requested user input')
    schema = {'type':'object','additionalProperties':False,'properties':{
        'summary':{'type':'string'},'documented_files':{'type':'integer'},
        'artifacts':{'type':'array','items':{'type':'string'}}},
        'required':['summary','documented_files','artifacts']}
    expected_paths = [f'docs/module_{n}.py/README.md' for n in range(args.files)]
    result = runner.run(
        RunRequest(username='live_smoke', workspace=str(workspace), response_schema=json.dumps(schema),
                   prompt=f'''The synthetic source.zip in this workspace contains exactly {args.files} Python source files.
Safely extract it into src/. Create a short PLAN.md and use work_queue inventory on src with pattern **/*.py.
For every source, claim and read it with work_queue until eof and write docs/<source filename>/README.md.
Required artifact paths, including the .py directory suffix: {json.dumps(expected_paths)}.
Each README must identify the function, describe its exact arithmetic and include one correct example.
Use quoted heredocs to preserve Markdown backticks and read back each saved artifact.
Verify each artifact and complete each queue item with evidence. Verify final coverage and finish.
Use only run_shell, work_queue, read_plan and create_or_update_plan. All needed inputs are provided.
Keep this small task focused. Do not ask for clarification or access anything outside this workspace.'''),
        emit=emit, wait_for_input=no_input, is_cancelled=lambda: time.monotonic() - started > 480,
    )
    state = WorkQueue(workspace, result.session_id).verify()
    artifacts = list((workspace / 'docs').rglob('README.md'))
    # Independent, minimal semantic check specific to this known fixture.
    artifact_checks = all((workspace / f'docs/module_{n}.py/README.md').is_file()
                          and re.search(rf'add_{n}\(\d+\)', (workspace / f'docs/module_{n}.py/README.md').read_text())
                          for n in range(args.files))
    passed = (result.status == 'completed' and state['counts'] == {'completed':args.files}
              and len(artifacts) == args.files and artifact_checks
              and result.final_response is not None
              and result.final_response.documented_files == args.files
              and all((workspace / name).is_file() for name in result.final_response.artifacts)
              and set(expected_paths).issubset(result.final_response.artifacts)
              and 'tool.completed' in events)
    report = {'passed':passed,'status':result.status,'error':result.error,
              'model':runner.config['orchestrator_agent']['model'],
              'api_mode':runner.config.get('llm', {}).get('api_mode', 'chat_completions'),
              'coverage':state,'artifact_count':len(artifacts), 'workspace':str(workspace),
              'elapsed_seconds':round(time.monotonic()-started, 1),
              'final_response':result.final_response.model_dump() if result.final_response else None}
    (root / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

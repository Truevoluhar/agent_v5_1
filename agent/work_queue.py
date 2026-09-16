"""Durable, session-scoped coverage ledger. Payloads stay on disk, not in chat."""
from __future__ import annotations

from contextlib import contextmanager
import codecs
import hashlib
import json
import sqlite3
from pathlib import Path


def workspace_file(workspace, name):
    root = Path(workspace).resolve()
    path = (root / name).resolve()
    if path != root and root not in path.parents:
        raise ValueError('Path must stay inside the workspace')
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


class WorkQueue:
    def __init__(self, workspace, scope='default'):
        self.root = Path(workspace).resolve()
        directory = workspace_file(self.root, '.agent/work')
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (hashlib.sha256(scope.encode()).hexdigest() + '.sqlite3')
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS context (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                    source TEXT UNIQUE, source_hash TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    cursor INTEGER NOT NULL DEFAULT 0,
                    evidence TEXT, artifacts TEXT NOT NULL DEFAULT '[]', error TEXT
                );
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def objective(self, prompt):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO context(key,value) VALUES('objective',?)", (prompt,))
            original = db.execute("SELECT value FROM context WHERE key='objective'").fetchone()['value']
        return original if original == prompt else original + "\nCurrent follow-up: " + prompt

    def inventory(self, root, pattern, instruction):
        base = workspace_file(self.root, root)
        if not base.is_dir():
            raise ValueError('Inventory root must be a directory')
        added = 0
        with self.connect() as db:
            for path in base.glob(pattern):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(self.root)
                if any(p in {'.agent', '.git', 'node_modules', 'venv', '__pycache__'} for p in relative.parts):
                    continue
                path = workspace_file(self.root, str(relative))
                added += db.execute(
                    'INSERT OR IGNORE INTO tasks(title, source, source_hash) VALUES(?,?,?)',
                    (instruction, str(relative), digest(path)),
                ).rowcount
        return {'added': added, **self.summary()}

    def add(self, title):
        if not title.strip():
            raise ValueError('Task title is required')
        with self.connect() as db:
            cursor = db.execute('INSERT INTO tasks(title) VALUES(?)', (title,))
            return {'id': cursor.lastrowid}

    def summary(self):
        with self.connect() as db:
            counts = {row['status']: row['n'] for row in db.execute('SELECT status, count(*) n FROM tasks GROUP BY status')}
            tasks = [dict(row) for row in db.execute(
                "SELECT id,substr(title,1,500) title,source,status,attempts,cursor,substr(error,1,500) error FROM tasks WHERE status != 'completed' ORDER BY id LIMIT 8")]
        return {'total': sum(counts.values()), 'counts': counts, 'remaining': sum(n for s, n in counts.items() if s != 'completed'), 'next': tasks}

    def claim(self, max_attempts=3):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            # An interrupted item is resumed before claiming more work.
            row = db.execute("SELECT * FROM tasks WHERE status='running' ORDER BY id LIMIT 1").fetchone()
            if row is None:
                row = db.execute("SELECT * FROM tasks WHERE status IN ('pending','failed') AND attempts < ? ORDER BY id LIMIT 1", (max_attempts,)).fetchone()
                if row is not None:
                    db.execute("UPDATE tasks SET status='running', attempts=attempts+1 WHERE id=?", (row['id'],))
            if row is None:
                return None
            return dict(db.execute('SELECT * FROM tasks WHERE id=?', (row['id'],)).fetchone())

    def read(self, task_id, max_chars=4000):
        if not 4 <= max_chars <= 12000:
            raise ValueError('max_chars must be between 4 and 12000')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            task = db.execute("SELECT * FROM tasks WHERE id=? AND status='running'", (task_id,)).fetchone()
            if task is None or task['source'] is None:
                raise ValueError('Claim a file task before reading it')
            path = workspace_file(self.root, task['source'])
            if task['cursor'] == 0 and digest(path) != task['source_hash']:
                raise ValueError('Source changed since inventory; refresh the task before reading')
            # Byte offsets allow bounded reads even for multi-gigabyte sources.
            with path.open('rb') as stream:
                stream.seek(task['cursor'])
                chunk = stream.read(max_chars)
                decoder = codecs.getincrementaldecoder('utf-8')()
                content = decoder.decode(chunk, final=stream.tell() == path.stat().st_size)
                end = stream.tell() - len(decoder.getstate()[0])
            db.execute('UPDATE tasks SET cursor=? WHERE id=?', (end, task_id))
            return {'source': task['source'], 'offset': task['cursor'], 'next_offset': end,
                    'eof': end == path.stat().st_size, 'content': content}

    def finish(self, task_id, evidence, artifacts):
        if not evidence.strip():
            raise ValueError('Completion requires verification evidence')
        records = []
        for name in artifacts:
            path = workspace_file(self.root, name)
            if not path.is_file() or not path.stat().st_size:
                raise ValueError(f'Missing or empty artifact: {name}')
            records.append({'path': name, 'sha256': digest(path)})
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            task = db.execute("SELECT * FROM tasks WHERE id=? AND status='running'", (task_id,)).fetchone()
            if task is None:
                raise ValueError('Task must be running')
            if task['source']:
                path = workspace_file(self.root, task['source'])
                if digest(path) != task['source_hash'] or task['cursor'] < path.stat().st_size:
                    raise ValueError('Read the entire unchanged source before completing this task')
                if not records:
                    raise ValueError('File tasks require an output artifact (documentation or findings)')
            db.execute("UPDATE tasks SET status='completed', evidence=?, artifacts=?, error=NULL WHERE id=?",
                       (evidence, json.dumps(records), task_id))
        return {'completed': task_id}

    def fail(self, task_id, error):
        if not error.strip():
            raise ValueError('Failure reason is required')
        with self.connect() as db:
            changed = db.execute("UPDATE tasks SET status='failed', error=? WHERE id=? AND status='running'", (error, task_id)).rowcount
            if not changed:
                raise ValueError('Task must be running')
        return {'failed': task_id}

    def refresh(self, task_id):
        with self.connect() as db:
            task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
            if task is None:
                raise ValueError('Unknown task')
            source_hash = digest(workspace_file(self.root, task['source'])) if task['source'] else None
            db.execute("UPDATE tasks SET status='pending',source_hash=?,cursor=0,attempts=0,evidence=NULL,artifacts='[]',error=NULL WHERE id=?", (source_hash, task_id))
        return {'reset': task_id}

    def completion_report(self):
        """Give final synthesis actual artifact paths, not just recent chat claims."""
        with self.connect() as db:
            rows = [dict(row) for row in db.execute(
                "SELECT id,title,source,evidence,artifacts FROM tasks WHERE status='completed' ORDER BY id")]
        for row in rows:
            row['artifacts'] = json.loads(row['artifacts'])
        report_path = self.path.with_suffix('.report.json')
        report_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        artifacts = sorted({artifact['path'] for row in rows for artifact in row['artifacts']})
        return {'completed_tasks': len(rows), 'artifact_count': len(artifacts),
                'artifact_paths': artifacts[:25], 'paths_truncated': len(artifacts) > 25,
                'full_report': str(report_path.relative_to(self.root))}

    def verify(self):
        invalid = []
        with self.connect() as db:
            for task in db.execute("SELECT * FROM tasks WHERE status='completed'"):
                try:
                    if task['source'] and digest(workspace_file(self.root, task['source'])) != task['source_hash']:
                        raise ValueError('Source changed')
                    for artifact in json.loads(task['artifacts']):
                        if digest(workspace_file(self.root, artifact['path'])) != artifact['sha256']:
                            raise ValueError('Artifact changed')
                except (OSError, ValueError) as exc:
                    invalid.append(task['id'])
                    db.execute("UPDATE tasks SET status='failed',error=? WHERE id=?", (str(exc), task['id']))
        return {'invalidated': invalid, **self.summary()}

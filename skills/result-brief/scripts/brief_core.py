#!/usr/bin/env python3
"""Build a self-contained review brief from a frozen base and working-tree states.

Python 3.9+, Git. Never writes the real index; --verify stores tree objects only.
See references/structure.md for commit plans, snapshots and validation.
Renames are conservatively shown as D+A.
"""
import argparse
import datetime
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile

TEMPLATE = Path(__file__).resolve().parent.parent / 'assets' / 'template.html'
MODES = {'100644', '100755', '120000'}
KINDS = {'fix', 'refactor', 'test', 'feat', 'chore', 'docs'}
SECTIONS = {
    'planning': {'requirements', 'scenarios', 'acceptance', 'decisions'},
    'result': {'changes', 'metrics', 'impact', 'requirements', 'review-focus', 'verification',
               'merge-checklist', 'follow-up'},
}
VERIFIERS = {'script', 'implementer', 'independent', 'human', 'none'}
ASSERTION_RE = re.compile(r'#expect|#require|@Test\b|\bfunc test|\bXCT(?:Assert|Fail|Unwrap)|\bassert\w*\(|\bexpect\(')
TEST_PATH_RE = re.compile(r'(^|/)(tests?|__tests__)(/|$)|tests?\.[^/]+$', re.I)
RUNTIME_PATH_RE = re.compile(r'\.(?:xcscheme|xctestplan|pbxproj)$|(^|/)Scripts/')
UI_PATH_RE = re.compile(r'(^|/)Views?/|View\.swift$|\.(?:xib|storyboard)$')
SENSITIVE = (
    ('개인 키', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('GitHub 토큰', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}')),
    ('API 키', re.compile(r'\b(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})')),
    ('비밀 값', re.compile(r'(?i)\b(?:api[_-]?key|client[_-]?secret|password|passwd|access[_-]?token)\b["\']?\s*[:=]\s*["\'][^"\'\s$]{12,}["\']')),
    ('주민등록번호', re.compile(r'\b\d{6}-[1-4]\d{6}\b')),
)
HUNK_RE = re.compile(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@.*$')


def git(*args, allowed=(0,)):
    r = subprocess.run(['git', *args], capture_output=True)
    if r.returncode not in allowed:
        raise ValueError(f"git {args[0]} 실패 ({r.returncode}): {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def repo_path(value):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('경로는 비어 있지 않은 문자열이어야 함')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or '.git' in p.parts or str(p) != value or value == '.':
        raise ValueError(f'정규화된 저장소 상대 경로 필요: {value!r}')
    return value


def read_state(path, directory_is_absent=False):
    """Never follow symlinks, including a symlink in a parent directory."""
    p = Path(path)
    for parent in p.parents:
        if parent.is_symlink():
            raise ValueError(f'상위 경로가 심볼릭 링크임: {path}')
    try:
        mode = p.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    if stat.S_ISLNK(mode):
        return ('120000', os.fsencode(os.readlink(p)))
    if directory_is_absent and stat.S_ISDIR(mode):
        return None  # A Git file at this path was replaced by a directory.
    if not stat.S_ISREG(mode):
        raise ValueError(f'지원하지 않는 파일 타입: {path}')
    return ('100755' if mode & stat.S_IXUSR else '100644', p.read_bytes())


def base_states(base):
    states = {}
    for record in git('ls-tree', '-rz', '--full-tree', base).split(b'\0'):
        if not record:
            continue
        meta, path = record.split(b'\t', 1)
        mode, kind, oid = meta.decode('ascii').split()
        if mode not in MODES or kind != 'blob':
            raise ValueError(f'지원하지 않는 Git 객체 (submodule 등): {os.fsdecode(path)}')
        states[os.fsdecode(path)] = (mode, git('cat-file', 'blob', oid))
    return states


def working_states(base):
    if git('ls-files', '-u', '-z'):
        raise ValueError('merge conflict를 먼저 해결해야 함')
    paths = set(base)
    for record in git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0'):
        if record:
            paths.add(os.fsdecode(record))
    return {p: read_state(repo_path(p), directory_is_absent=True) for p in sorted(paths)}


def is_header_only(hunk):
    # Keep all changes visible, including compiler/linter directives and licenses.
    return False


def diff_entry(path, old, new):
    entry = dict(path=path, oldPath=None, status='A' if old is None else 'D' if new is None else 'M',
                 oldMode=old[0] if old else None, newMode=new[0] if new else None,
                 binary=False, hunks=[], add=0, **{'del': 0})
    a, b = old[1] if old else b'', new[1] if new else b''
    entry['oldSize'], entry['newSize'] = len(a), len(b)
    entry['oldHash'], entry['newHash'] = (hashlib.sha256(x).hexdigest() if s else None for x, s in ((a, old), (b, new)))
    try:
        a.decode('utf-8'); b.decode('utf-8')
        entry['binary'] = b'\0' in a or b'\0' in b
    except UnicodeDecodeError:
        entry['binary'] = True
    if entry['binary'] or a == b:
        return entry
    with tempfile.TemporaryDirectory() as tmp:
        left, right = Path(tmp) / 'a', Path(tmp) / 'b'
        left.write_bytes(a); right.write_bytes(b)
        raw = git('diff', '--no-index', '--no-ext-diff', '--no-textconv', '--no-color', '--text',
                  '--', str(left), str(right), allowed=(0, 1)).decode('utf-8')
    hunk = None
    # Split on LF only: preserve CR and other source characters.
    for line in raw.split('\n'):
        match = HUNK_RE.match(line)
        if match:
            hunk = dict(oldStart=int(match[1]), newStart=int(match[2]), header=line, lines=[], noise=False)
            entry['hunks'].append(hunk)
        elif hunk is not None and line[:1] in (' ', '+', '-'):
            hunk['lines'].append([line[0], line[1:]])
            if line[0] == '+': entry['add'] += 1
            if line[0] == '-': entry['del'] += 1
        elif hunk is not None and line.startswith('\\ No newline'):
            hunk['lines'].append(['!', 'No newline at end of file'])
    return entry


def differences(before, after):
    return [diff_entry(p, before.get(p), after.get(p)) for p in sorted(set(before) | set(after))
            if before.get(p) != after.get(p)]


def load_plan(path):
    plan = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(plan, dict) or not isinstance(plan.get('commits'), list):
        raise ValueError('plan.commits 배열 필요')
    prefix = plan.get('prefix', '')
    if not isinstance(prefix, str) or (prefix and (not prefix.endswith('/') or not repo_path(prefix[:-1]))):
        raise ValueError('prefix는 빈 문자열 또는 /로 끝나는 상대 디렉터리여야 함')
    for c in plan['commits']:
        if not isinstance(c, dict) or not isinstance(c.get('message'), str) or not c['message'].split('\n')[0].strip():
            raise ValueError('각 커밋에 비어 있지 않은 message 제목 필요')
        if not isinstance(c.get('files'), list) or not c['files']:
            raise ValueError('각 커밋에 비어 있지 않은 files 배열 필요')
        if not isinstance(c.get('kind', 'chore'), str) or c.get('kind', 'chore') not in KINDS:
            raise ValueError('지원하지 않는 commit kind')
        for k in ('group', 'impact', 'verify', 'review', 'requires', 'revert'):
            if k in c and not isinstance(c[k], str): raise ValueError(f'{k}는 문자열이어야 함')
        if 'risk' in c:
            r = c['risk']
            if not isinstance(r, dict) or r.get('level') not in ('high', 'medium', 'low') or not isinstance(r.get('note', ''), str):
                raise ValueError('risk.level / risk.note 형식 오류')
        for item in c['files']:
            if isinstance(item, str): repo_path(item)
            elif isinstance(item, dict) and set(item) <= {'path', 'mode', 'delete'}:
                repo_path(item.get('path'))
                if 'mode' in item and (not isinstance(item['mode'], str) or item['mode'] not in MODES): raise ValueError('지원하지 않는 mode')
                if 'delete' in item and not isinstance(item['delete'], bool): raise ValueError('delete는 boolean이어야 함')
                if item.get('delete') and 'mode' in item: raise ValueError('delete와 mode는 함께 사용할 수 없음')
            else: raise ValueError('files 항목은 경로 또는 {path, mode?, delete?}여야 함')
    return plan


def plan_commits(plan, plan_path, base, work, issues):
    state, commits, planned = dict(base), [], set()
    root = Path(plan_path).parent.resolve() / 'snapshots'
    prefix = plan.get('prefix', '')
    for n, c in enumerate(plan['commits'], 1):
        entries, seen = [], set()
        for item in c['files']:
            item = {'path': item} if isinstance(item, str) else item
            p = item['path']
            candidates = list(dict.fromkeys((prefix + p, p)))
            matches = [q for q in candidates if q in base or q in work or q in state or os.path.lexists(root / str(n) / q)]
            if len(matches) != 1: raise ValueError(f'plan 경로가 없거나 모호함: {p!r}; 후보 {matches}')
            path = matches[0]
            if path in seen: raise ValueError(f'커밋 {n}에 중복 경로: {path}')
            seen.add(path); planned.add(path)
            snap = root / str(n) / path
            exists = os.path.lexists(snap)
            if item.get('delete'):
                if exists: raise ValueError(f'delete와 snapshot 충돌: {path}')
                value = None
            else:
                value = read_state(snap) if exists else work.get(path)
                if 'mode' in item:
                    if value is None: raise ValueError(f'mode를 적용할 내용이 없음: {path}')
                    value = (item['mode'], value[1])
            old = state.get(path)
            if old != value: entries.append(diff_entry(path, old, value))
            else: issues.append(f'커밋 {n}에 실제 변경이 없는 파일: {path}')
            state[path] = value
        commits.append(dict(n=n, group=c.get('group', ''), kind=c.get('kind', 'chore'),
                            message=c['message'], title=c['message'].split('\n')[0], files=entries,
                            **{k:c[k] for k in ('risk','impact','verify','review','requires','revert') if k in c}))
    for p in sorted(set(base) | set(work) | set(state)):
        if base.get(p) != work.get(p) and p not in planned: issues.append(f'어느 커밋에도 없는 변경: {p}')
        if state.get(p) != work.get(p): issues.append(f'마지막 커밋 뒤 내용/mode가 작업 트리와 다름: {p}')
    return commits


class BodyCheck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.issues, self.ids, self.tabs, self.commit_tabs, self.checks = [], set(), [], [], set()
        self.links = []
        self.embeds = 0
        self.images = 0
        self.screenshot_na = False
        self.summary = False
        self.stats = []
        self.stack = []
        self.reserved = set(re.findall(r'id="([^"{}]+)"', TEMPLATE.read_text(encoding="utf-8")))
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        in_merge = a.get('id') == 'merge-checklist' or any(x[1] == 'merge-checklist' for x in self.stack)
        if tag == 'tr' and in_merge and not any(x[0] == 'thead' for x in self.stack):
            if a.get('data-check-kind') not in ('human', 'automated', 'criterion'):
                self.issues.append('머지 판정 행에 data-check-kind 유형 필요')
            if 'data-verdict' not in a:
                self.issues.append('머지 판정 행에 data-verdict 필요')
            if not a.get('data-basis', '').strip():
                self.issues.append('머지 판정 행에 data-basis 필요')
        in_verification = a.get('id') == 'verification' or any(x[1] == 'verification' for x in self.stack)
        if tag == 'tr' and in_verification and not any(x[0] == 'thead' for x in self.stack):
            verifier = a.get('data-verifier')
            if verifier not in VERIFIERS:
                self.issues.append('검증 행에 data-verifier 필요 (script|implementer|independent|human|none)')
            elif verifier != 'none' and not a.get('data-verifier-name', '').strip():
                self.issues.append('검증 행에 실제 검증자 data-verifier-name 필요')
        if tag == 'p' and 'sub' in a.get('class', '').split(): self.summary = True
        if tag == 'img' and a.get('src', '').startswith('data:'): self.images += 1
        if 'data-screenshot-na' in a: self.screenshot_na = bool(a['data-screenshot-na'].strip())
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append((tag, a.get('id')))

        if tag == 'a' and a.get('href', '').startswith('#'):
            self.links.append(a['href'][1:])
        if tag == 'script' and a.get('type') != 'application/json':
            self.issues.append('본문에는 실행 스크립트를 넣을 수 없음')
        if a.get('id') in self.reserved: self.issues.append(f'템플릿 예약 id 충돌: {a["id"]}')
        if 'id' in a:
            if a['id'] in self.ids: self.issues.append(f'중복 HTML id: {a["id"]}')
            self.ids.add(a['id'])
        if a.get('data-tab') is not None: self.tabs.append(a['data-tab'])
        if a.get('data-commit') is not None: self.commit_tabs.append(a['data-commit'])
        if tag == 'input' and a.get('type') == 'checkbox':
            key = a.get('data-check-id')
            if not key or key in self.checks: self.issues.append('checkbox에 고유 data-check-id 필요')
            self.checks.add(key)
        if 'data-placeholder' in a: self.issues.append('예시 placeholder가 남아 있음')
        if 'data-stat' in a: self.stats.append(a['data-stat'])
        if 'data-verdict' in a:
            verdict = a['data-verdict']
            if verdict not in ('met', 'unmet', 'unknown', 'na'): self.issues.append('data-verdict 상태 오류')
            if not a.get('data-basis', '').strip(): self.issues.append('판정에 data-basis 출처 필요')
            if verdict == 'met' and not a.get('data-evidence', '').strip(): self.issues.append('충족 판정에 data-evidence 필요')
            if verdict == 'na' and not a.get('data-reason', '').strip(): self.issues.append('해당 없음에 data-reason 필요')
            if verdict == 'met' and (a.get('data-human') == 'true' or a.get('data-check-kind') == 'human'):
                if not a.get('data-actor', '').strip() or not a.get('data-time', '').strip():
                    self.issues.append('사람 검토 완료에는 실제 검토자와 시각 필요')
        if 'diff-embed' in a.get('class', '').split():
            self.embeds += 1
            if not a.get('data-file'): self.issues.append('diff-embed에 data-file 필요')
            if 'data-hunks' in a and 'data-match' in a: self.issues.append('data-hunks와 data-match는 하나만 사용')
        if tag in ('script', 'img', 'iframe', 'link', 'source', 'video', 'audio'):
            url = a.get('src') or a.get('href')
            if url and not url.startswith('data:'): self.issues.append(f'외부 리소스 금지: {tag}')

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def repo_file(entry):
    # --strip-prefix는 표시만 바꾸므로 분류는 저장소 경로로 한다.
    return entry.get('repoPath', entry['path'])


def check_body(content, commits, issues, mode='result', files=()):
    check = BodyCheck(); check.feed(content)
    issues.extend(check.issues)
    if mode == 'result':
        if check.summary: issues.append('첫 화면 요약 문장(.sub)은 넣지 않음')
        if 'auto-facts' in check.ids: issues.append('auto-facts는 자동 기록용 id임')
        if any(UI_PATH_RE.search(repo_file(f)) for f in files) and not (check.images or check.screenshot_na):
            issues.append('UI 변경에 스크린샷 필요 (사유가 있으면 data-screenshot-na)')
    if 'overview' not in check.tabs: issues.append('overview 탭 필요')
    for section in sorted(SECTIONS[mode] - check.ids): issues.append(f'{mode} 필수 섹션 누락: {section}')
    if mode == 'result':
        if 'all' not in check.tabs or 'file-browser' not in check.ids: issues.append('result에는 all 탭과 file-browser 필요')
    elif check.commit_tabs or check.embeds or check.stats or 'all' in check.tabs or 'file-browser' in check.ids:
        issues.append('planning에는 실제 diff/커밋 탭/변경 통계를 넣을 수 없음')
    if len(check.tabs) != len(set(check.tabs)): issues.append('중복 data-tab')
    if len(check.commit_tabs) != len(set(check.commit_tabs)): issues.append('중복 data-commit')
    if any(x not in {str(c['n']) for c in commits} for x in check.commit_tabs): issues.append('계획에 없는 커밋 탭')
    generated = {f'c{c["n"]}' for c in commits} | {f'c{c["n"]}-diff' for c in commits}
    if check.ids & generated: issues.append('자동 생성 id와 본문 id 충돌')
    targets = check.ids | set(check.tabs) | generated
    for link in check.links:
        if link and link not in targets: issues.append(f'존재하지 않는 내부 링크: #{link}')
    if any(re.fullmatch(r'c\d+', x) for x in check.tabs): issues.append('cN 탭 이름은 자동 커밋 탭용으로 예약됨')
    if '[REPLACE]' in content: issues.append('미완성 placeholder가 남아 있음')


def sensitive_findings(files, commits, content):
    found = set()
    entries = [*files, *(entry for c in commits for entry in c['files'])]
    sources = [(entry['path'], line[1]) for entry in entries for hunk in entry['hunks'] for line in hunk['lines']]
    sources += [('본문', line) for line in content.split('\n')]
    for path, text in sources:
        for name, pattern in SENSITIVE:
            if pattern.search(text): found.add((path, name))
    return sorted(found)


def reject_sensitive(findings):
    # --draft로도 통과시키지 않는다. 초안 표시는 노출을 막지 못한다.
    messages = [f'민감 정보 의심: {path} ({name})' for path, name in findings]
    if messages: raise ValueError('\n'.join(messages))


def working_tree_id():
    """Same value before and after committing identical content."""
    index = os.fsdecode(git('rev-parse', '--git-path', 'index')).strip()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp) / 'index'
        if Path(index).exists(): shutil.copy2(index, temp)
        env = {**os.environ, 'GIT_INDEX_FILE': str(temp)}
        for args in (['add', '-A'], ['write-tree']):
            r = subprocess.run(['git', *args], capture_output=True, env=env)
            if r.returncode != 0: raise ValueError(f"git {args[0]} 실패: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode().strip()


def load_verify(path, issues):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(record, dict) or record.get('verdict') not in ('pass', 'fail'):
        raise ValueError('--verify 기록에 verdict(pass|fail) 필요')
    record['current'] = record.get('tree') == working_tree_id()
    if not record['current']: issues.append('테스트 판정 기록이 현재 작업 트리와 다름; 다시 실행하세요')
    if record.get('source') != 'run': issues.append('외부 로그 판정은 테스트 증거가 아님; 실제로 실행하세요')
    record['earlier'] = same_tree_runs(Path(path).parent / 'history.jsonl', record.get('tree'), record.get('finished_at'))
    return record


def same_tree_runs(path, tree, latest):
    if not path.exists(): return []
    runs = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return [r for r in runs if r.get('tree') == tree and r.get('finished_at') != latest]


def load_review(path, issues):
    """First line is `tree <id>`; the rest is the reviewer's verbatim output."""
    head, _, body = Path(path).read_text(encoding='utf-8').partition('\n')
    if head != f'tree {working_tree_id()}': issues.append('리뷰 기록이 현재 작업 트리와 다름; 다시 리뷰하세요')
    if not body.strip(): issues.append('리뷰 원문이 비어 있음')
    return body


# 라벨과 template의 table.grid 색 클래스(a 초록, b 빨강)
FILE_STATUS = {'A': ('추가', 'a'), 'M': ('수정', ''), 'D': ('삭제', 'b')}


def folder_tree(files):
    """Changed files as a directory tree; directory keys end with `/`, chains of single subdirectories are collapsed."""
    root = {}
    for f in files:
        *dirs, name = PurePosixPath(f['path']).parts
        node = root
        for d in dirs: node = node.setdefault(d + '/', {})
        node[name] = f
    def totals(node):
        add = rem = count = 0
        for k, v in node.items():
            a, r, c = totals(v) if k.endswith('/') else (v['add'], v['del'], 1)
            add += a; rem += r; count += c
        return add, rem, count
    rows = []
    def walk(node, indent, top):
        items = sorted(node.items(), key=lambda kv: (not kv[0].endswith('/'), kv[0]))
        for i, (name, v) in enumerate(items):
            last = i == len(items) - 1
            branch = '' if top else ('└─ ' if last else '├─ ')
            if name.endswith('/'):
                while len(v) == 1 and next(iter(v)).endswith('/'):
                    child = next(iter(v)); name += child; v = v[child]
                add, rem, count = totals(v)
                rows.append((indent + branch, name, (f'파일 {count}', ''), add, rem))
                walk(v, '' if top else indent + (' ' * 3 if last else '│  '), False)
            else:
                rows.append((indent + branch, name, FILE_STATUS.get(v['status'], (v['status'], '')), v['add'], v['del']))
    walk(root, '', True)
    add, rem, count = totals(root)
    td = lambda text, cls: f'<td class="{cls}">{html.escape(text)}</td>' if cls else f'<td>{html.escape(text)}</td>'
    body = ''.join(f'<tr><td><span class="mono">{html.escape(p)}</span><code>{html.escape(n)}</code></td>{td(*s)}'
                   f'{td(f"+{a}", "a" if a else "")}{td(f"-{r}", "b" if r else "")}</tr>' for p, n, s, a, r in rows)
    return (f'<p class="mono count">파일 {count} · <span class="p">+{add}</span> <span class="m">-{rem}</span></p><div class="card table-wrap"><table class="grid files">'
            f'<thead><tr><th>경로</th><th>상태</th><th>추가</th><th>삭제</th></tr></thead><tbody>{body}</tbody></table></div>')


def watched_files_table(files):
    rows = [f for f in files if TEST_PATH_RE.search(repo_file(f)) or RUNTIME_PATH_RE.search(repo_file(f))]
    if not rows: return '<p>테스트와 실행 설정 파일 변경 없음.</p>'
    body = ''.join(f'<tr><td><code>{html.escape(f["path"])}</code></td><td>+{f["add"]}</td><td>-{f["del"]}</td></tr>' for f in rows)
    return ('<div class="card table-wrap"><table class="grid files"><thead><tr><th>테스트·실행 설정 파일</th><th>추가</th><th>삭제</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def earlier_runs_table(record):
    if record is None or not record['earlier']: return ''
    body = ''.join(f'<tr><td>{html.escape(str(r.get("finished_at", "")))}</td><td>{html.escape(str(r.get("verdict", "")))}</td><td>{html.escape(str(r.get("reason", "")))}</td><td>{html.escape(str(r.get("failures", "")))}</td></tr>' for r in record['earlier'])
    return ('<h3>같은 코드의 이전 실행</h3><div class="card table-wrap"><table class="grid"><thead><tr><th>시각</th><th>판정</th><th>사유</th><th>실패</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def review_block(body):
    if body is None: return '<p>Codex 리뷰 기록 없음.</p>'
    return f'<pre class="msg-full prose card">{html.escape(body)}</pre>'


def test_changes_table(files):
    rows = [(f['path'], line[0], line[1].strip()) for f in files if TEST_PATH_RE.search(repo_file(f))
            for hunk in f['hunks'] for line in hunk['lines']
            if line[0] in '+-' and ASSERTION_RE.search(line[1])]
    if not any(TEST_PATH_RE.search(repo_file(f)) for f in files): return '<p>테스트 파일 변경 없음.</p>'
    if not rows: return '<p>기대값 패턴 자동 탐지 없음. 미확인이므로 테스트 파일 diff를 직접 확인한다.</p>'
    removed = sum(1 for r in rows if r[1] == '-')
    body = ''.join(f'<tr><td><code>{html.escape(p)}</code></td><td>{"삭제" if k == "-" else "추가"}</td><td><code>{html.escape(t)}</code></td></tr>' for p, k, t in rows)
    return (f'<p>기대값·테스트 선언 추가 {len(rows) - removed}줄, 삭제 {removed}줄.</p><div class="card table-wrap"><table class="grid">'
            f'<thead><tr><th>파일</th><th>변경</th><th>줄</th></tr></thead><tbody>{body}</tbody></table></div>')


def verify_table(record):
    if record is None: return '<p>자동 판정 기록 없음.</p>'
    passed = record['verdict'] == 'pass'
    values = [('사유', record.get('reason', '')), ('테스트', record.get('tests', '')), ('실패', record.get('failures', '')),
              ('하한', record.get('floor', '')), ('커밋', str(record.get('sha', ''))[:12]),
              ('작업 트리', '일치' if record['current'] else '낡음'), ('실행 시각', record.get('finished_at', ''))]
    cells = ''.join(f'<div><dt>{k}</dt><dd>{html.escape(str(v))}</dd></div>' for k, v in values)
    failed = ''.join(f'<li><code>{html.escape(str(x))}</code></li>' for x in record.get('failed_tests', []))
    return (f'<div class="card verdict {"pass" if passed else "fail"}"><span class="pill {"ok" if passed else "must"}">판정 {"통과" if passed else "실패"}</span>'
            f'<dl class="commit-meta">{cells}</dl>' + (f'<div><b class="small">실패한 테스트</b><ul>{failed}</ul></div>' if failed else '') + '</div>')


def automatic_section(files, verify, review=None):
    return ('<section id="auto-facts" data-toc="자동 기록"><header><h2><span class="idx"></span>자동 기록</h2></header>'
            '<p class="lede">이 절은 빌더가 생성한다. 모델이 쓴 문장이 없다.</p>'
            f'<h3>테스트 판정</h3>{verify_table(verify)}{earlier_runs_table(verify)}<h3>폴더 diff</h3>{folder_tree(files)}'
            f'<h3>테스트와 실행 설정 변경</h3>{watched_files_table(files)}'
            f'<h3>테스트 기대값 변경</h3>{test_changes_table(files)}'
            f'<h3>Codex 리뷰 원문</h3>{review_block(review)}</section>')


def with_automatic_section(content, section):
    tab = re.search(r'<div[^>]*data-tab\s*=\s*["\']?overview["\']?[^>]*>', content)
    if not tab: raise ValueError('overview 탭 필요')
    hero = re.compile(r'\s*<header\s+class\s*=\s*["\']?hero["\']?.*?</header>', re.S).match(content, tab.end())
    at = hero.end() if hero else tab.end()
    return content[:at] + section + content[at:]


def main(mode):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('content'); ap.add_argument('out')
    ap.add_argument('--base', default=None); ap.add_argument('--title'); ap.add_argument('--plan')
    ap.add_argument('--strip-prefix', default=None)
    ap.add_argument('--verify', help='Scripts/verify-tests.sh가 남긴 JSON 기록')
    ap.add_argument('--review', help='첫 줄이 tree <id>이고 나머지가 리뷰 원문인 파일')
    ap.add_argument('--draft', action='store_true', help='불완전한 계획/본문을 초안 배너와 함께 출력')
    args = ap.parse_args()
    args.mode = mode
    content_path, out_path = Path(args.content).resolve(), Path(args.out).resolve()
    plan_path = Path(args.plan).resolve() if args.plan else None
    verify_path = Path(args.verify).resolve() if args.verify else None
    review_path = Path(args.review).resolve() if args.review else None
    for source in (content_path, plan_path, verify_path, review_path):
        if source is not None and (out_path == source or (out_path.exists() and source.exists() and out_path.samefile(source))):
            raise ValueError('출력은 입력 파일과 달라야 함')
    issues = []
    root = Path.cwd()
    base_sha = head = None
    base, work, files, commits, plan = {}, {}, [], [], None
    if args.mode == 'planning':
        if args.base is not None or plan_path or args.strip_prefix is not None or args.verify or args.review:
            raise ValueError('planning에는 --base / --plan / --strip-prefix / --verify / --review를 사용할 수 없음')
    else:
        root = Path(os.fsdecode(git('rev-parse', '--show-toplevel')).strip())
        os.chdir(root)
        # Artifact inputs/outputs must not contaminate the very change being reported.
        for p in (content_path, out_path, plan_path):
            if p is None: continue
            try: rel = p.relative_to(root).as_posix()
            except ValueError: continue
            if git('ls-files', '-z', '--', rel) or not git('check-ignore', '--', rel, allowed=(0, 1)):
                raise ValueError(f'보고서 입력/출력은 저장소 밖 또는 Git ignored 경로에 두세요: {rel}')
        base_sha = git('rev-parse', '--verify', '--end-of-options', (args.base or 'HEAD') + '^{commit}').decode().strip()
        head = git('rev-parse', 'HEAD').decode().strip()
        base = base_states(base_sha); work = working_states(base)
        files = differences(base, work)
        plan = load_plan(plan_path) if plan_path else None
        commits = plan_commits(plan, plan_path, base, work, issues) if plan else []
    prefix = args.strip_prefix if args.strip_prefix is not None else (plan or {}).get('prefix', '')
    if prefix and (not prefix.endswith('/') or not repo_path(prefix[:-1])): raise ValueError('strip-prefix는 /로 끝나는 상대 디렉터리여야 함')
    def display(entries):
        used = set()
        for f in entries:
            f['repoPath'] = f['path']
            if prefix and f['path'].startswith(prefix): f['path'] = f['path'][len(prefix):]
            if f['path'] in used: raise ValueError('prefix 제거 후 경로 충돌')
            used.add(f['path'])
    display(files)
    for c in commits: display(c['files'])
    content = content_path.read_text(encoding='utf-8')
    check_body(content, commits, issues, args.mode, files)
    if args.mode == 'result':
        if files and not plan: issues.append('변경이 있으면 커밋 계획(--plan) 필요')
        reject_sensitive(sensitive_findings(files, commits, content))
        verify = load_verify(verify_path, issues) if verify_path else None
        review = load_review(review_path, issues) if review_path else None
        evidence = '\n'.join(p.read_text(encoding='utf-8') for p in (verify_path, review_path) if p)
        if verify: evidence += '\n' + json.dumps(verify['earlier'], ensure_ascii=False)
        reject_sensitive(('증거 파일', name) for _, name in sensitive_findings([], [], evidence))
        content = with_automatic_section(content, automatic_section(files, verify, review))
    if issues and not args.draft: raise ValueError('\n'.join(issues))
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.S)
    title = args.title or (re.sub(r'<[^>]+>', '', title_match[1]).strip() if title_match else '작업 보고서')
    fingerprint = hashlib.sha256(json.dumps([args.mode,str(root),base_sha,head,files,commits,content], ensure_ascii=True, sort_keys=True).encode()).hexdigest()
    data = dict(mode=args.mode, files=files, commits=commits, reportId=fingerprint, base=base_sha, head=head, draft=args.draft, issues=issues)
    payload = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if args.mode == 'result':
        branch = git('branch', '--show-current').decode().strip() or '(detached)'
        generated = f'결과 브리프 · 생성 {stamp} · 기준 {html.escape(args.base or "HEAD")} ({base_sha}) ↔ 작업 트리 · HEAD {head} · 브랜치 {html.escape(branch)} · 보고서 {fingerprint[:12]}'
    else:
        generated = f'기획 브리프 · 생성 {stamp} · 구현/검증 결과 아님 · 보고서 {fingerprint[:12]}'
    if args.draft:
        content = '<div class="callout" role="alert"><b>초안 · 승인용으로 사용하지 마세요</b><ul>' + ''.join(f'<li>{html.escape(x)}</li>' for x in issues) + '</ul></div>' + content
    values = dict(TITLE=html.escape(title), GENERATED=generated, DIFF_DATA=payload, CONTENT=content)
    output = re.sub(r'\{\{(TITLE|GENERATED|DIFF_DATA|CONTENT)\}\}', lambda m: values[m[1]], TEMPLATE.read_text(encoding='utf-8'))
    # Detect edits during generation instead of attaching stale evidence to a report.
    if args.mode == 'result' and (work != working_states(base) or head != git('rev-parse', 'HEAD').decode().strip()): raise ValueError('생성 도중 작업 트리/HEAD가 변경됨; 다시 생성하세요')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=out_path.parent, delete=False) as f:
        temp_path = Path(f.name)
        f.write(output)
    try: os.replace(temp_path, out_path)
    finally:
        if temp_path.exists(): temp_path.unlink()
    for issue in issues: print(f'초안 경고: {issue}', file=sys.stderr)
    print(f'{out_path}: 파일 {len(files)}개, 커밋 {len(commits)}개 · 보고서 {fingerprint[:12]}')


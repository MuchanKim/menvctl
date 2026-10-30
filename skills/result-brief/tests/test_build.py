"""Regression tests use disposable repositories; never touch the user's index."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'build.py'
spec = importlib.util.spec_from_file_location('brief', SCRIPT.parent / 'brief_core.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
RESULT_SECTIONS = ''.join(f'<section id="{name}">Recorded scope: fixture</section>' for name in sorted(b.SECTIONS['result']))
BODY = RESULT_SECTIONS + '<div class="tab-page" data-tab="overview"><h1>Regression</h1></div><div class="tab-page" data-tab="all"><div id="file-browser"></div></div>'


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path.cwd()
        self.repo = tempfile.TemporaryDirectory(); self.artifacts = tempfile.TemporaryDirectory()
        self.addCleanup(self.repo.cleanup); self.addCleanup(self.artifacts.cleanup)
        self.addCleanup(os.chdir, self.cwd)
        os.chdir(self.repo.name)
        self.g('init', '-q'); self.g('config', 'user.name', 'Test'); self.g('config', 'user.email', 'test@example.invalid')
        self.write('seed', b'old\n'); self.commit()
        self.base = b.base_states('HEAD')
        self.body = Path(self.artifacts.name) / 'body.html'; self.body.write_text(BODY)
        self.out = Path(self.artifacts.name) / 'report.html'
        self.plan_path = Path(self.artifacts.name) / 'commits.json'
    def g(self, *args):
        return subprocess.run(['git', *args], check=True, capture_output=True).stdout
    def write(self, path, content):
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(content)
    def commit(self):
        self.g('add', '.'); self.g('commit', '-qm', 'fixture')
    def entries(self):
        return b.differences(self.base, b.working_states(self.base))
    def plan(self, files):
        return {'commits': [{'message': 'Change', 'files': files}]}
    def run_cli(self, plan=None, *extra):
        extra = list(extra)
        script = SCRIPT
        if '--mode' in extra:
            index = extra.index('--mode'); mode = extra[index + 1]
            del extra[index:index + 2]
            if mode == 'planning': script = SCRIPT.parents[2] / 'plan-brief/scripts/build.py'
        cmd = [sys.executable, '-B', str(script), str(self.body), str(self.out)]
        if plan is not None:
            self.plan_path.write_text(json.dumps(plan)); cmd += ['--plan', str(self.plan_path)]
        return subprocess.run(cmd + list(extra), capture_output=True, text=True)
    def payload(self):
        import re
        return json.loads(re.search(r'id="diff-data">(.*?)</script>', self.out.read_text(), re.S)[1])
    def test_unicode_space_tab_newline_paths(self):
        names = ['한글.txt', 'space name', 'tab\tname', 'line\nname', 'quote"name']
        for name in names: self.write(name, b'new\n')
        self.assertEqual({f['path'] for f in self.entries()}, set(names))
        self.commit(); self.base = b.base_states('HEAD')
        for name in names: self.write(name, b'changed\n')
        self.assertEqual({f['path'] for f in self.entries()}, set(names))
    def test_duplicate_basenames_preserve_all_deletions(self):
        for name in ['a/x', 'b/x']: self.write(name, name.encode())
        self.commit(); self.base = b.base_states('HEAD')
        Path('a/x').unlink(); Path('b/x').unlink(); self.write('c/x', b'unrelated')
        self.assertEqual([(x['path'], x['status']) for x in self.entries()], [('a/x','D'),('b/x','D'),('c/x','A')])
    def test_binary_new_and_modified(self):
        self.write('image', b'\0\xff'); self.commit(); self.base = b.base_states('HEAD')
        self.write('image', b'\0\xfe'); self.write('new.bin', b'\xff')
        result = self.run_cli(self.plan(['image', 'new.bin']))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(f['binary'] for f in self.payload()['files']))
        self.assertEqual(len(self.payload()['commits'][0]['files']), 2)
    def test_mode_only_preserved(self):
        Path('seed').chmod(0o755)
        r = self.run_cli(self.plan(['seed'])); self.assertEqual(r.returncode, 0, r.stderr)
        f = self.payload()['commits'][0]['files'][0]
        self.assertEqual((f['oldMode'], f['newMode'], f['hunks']), ('100644','100755',[]))
    def test_symlink_target_not_followed(self):
        os.symlink('/unavailable/secret', 'link')
        f = self.entries()[0]
        self.assertEqual(f['newMode'], '120000')
        self.assertIn('/unavailable/secret', str(f['hunks']))
    def test_semantic_comments_visible(self):
        self.write('seed', b'// swift-tools-version: 6.0\n')
        self.assertFalse(self.entries()[0]['hunks'][0]['noise'])
    def test_base_metadata_is_not_head(self):
        self.g('branch','baseline'); base_sha = self.g('rev-parse','HEAD').decode().strip()
        self.write('seed', b'next\n'); self.commit()
        r = self.run_cli(None, '--base', 'baseline'); self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(self.payload()['base'],base_sha); self.assertNotEqual(self.payload()['head'],base_sha)
    def test_missing_plan_fails_without_overwrite(self):
        self.write('seed',b'new\n'); self.out.write_text('previous report')
        r=self.run_cli({'commits':[]}); self.assertEqual(r.returncode,2)
        self.assertEqual(self.out.read_text(),'previous report')
    def test_draft_explicitly_labeled(self):
        self.write('seed',b'new\n'); r=self.run_cli({'commits':[]},'--draft')
        self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(self.payload()['draft'])
        self.assertTrue(self.payload()['issues'])
    def test_cumulative_snapshots(self):
        self.write('seed',b'final\n')
        snap=Path(self.artifacts.name)/'snapshots/1/seed'; snap.parent.mkdir(parents=True); snap.write_bytes(b'middle\n')
        plan={'commits':[{'message':'First','files':['seed']},{'message':'Second','files':['seed']}]}
        r=self.run_cli(plan); self.assertEqual(r.returncode,0,r.stderr)
        lines=self.payload()['commits'][1]['files'][0]['hunks'][0]['lines']
        self.assertIn(['-','middle'],lines); self.assertIn(['+','final'],lines)
    def test_missing_intermediate_snapshot_fails_noop_commit(self):
        self.write('seed',b'final\n')
        r=self.run_cli({'commits':[{'message':'First','files':['seed']},{'message':'Second','files':['seed']}]})
        self.assertEqual(r.returncode,2)
    def test_final_snapshot_mismatch(self):
        self.write('seed',b'final\n')
        snap=Path(self.artifacts.name)/'snapshots/1/seed';snap.parent.mkdir(parents=True);snap.write_bytes(b'wrong\n')
        self.assertEqual(self.run_cli(self.plan(['seed'])).returncode,2)
    def test_intermediate_delete_and_restore(self):
        self.write('seed',b'restored\n')
        r=self.run_cli({'commits':[{'message':'Delete','files':[{'path':'seed','delete':True}]},{'message':'Restore','files':['seed']}]})
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual([c['files'][0]['status'] for c in self.payload()['commits']],['D','A'])
    def test_unresolved_base_is_fatal(self):
        self.assertEqual(self.run_cli(None,'--base','missing-ref').returncode,2)
    def test_path_escape_rejected(self):
        self.assertEqual(self.run_cli(self.plan(['../outside'])).returncode,2)
    def test_duplicate_plan_paths_rejected(self):
        self.write('seed',b'new\n');self.assertEqual(self.run_cli(self.plan(['seed','seed'])).returncode,2)
    def test_ambiguous_prefix_rejected(self):
        self.write('App/seed',b'app\n');self.write('seed',b'new\n')
        p=self.plan(['seed']);p['prefix']='App/'
        self.assertEqual(self.run_cli(p).returncode,2)
    def test_unignored_report_input_rejected(self):
        self.body=Path.cwd()/'body.html';self.body.write_text(BODY)
        self.assertEqual(self.run_cli().returncode,2)
    def test_placeholder_rejected(self):
        self.body.write_text(BODY.replace('Regression','<span data-placeholder>Example</span>'))
        self.assertEqual(self.run_cli().returncode,2)
    def test_orphan_commit_tab_rejected(self):
        self.body.write_text(BODY+'<div class="tab-page" data-commit="1"></div>')
        self.assertEqual(self.run_cli().returncode,2)
    def test_external_resource_rejected(self):
        self.body.write_text(BODY+'<script src="https://example.invalid/a.js"></script>')
        self.assertEqual(self.run_cli().returncode,2)
    def test_fingerprint_changes_with_content_and_checklist(self):
        self.write('seed',b'new\n');self.assertEqual(self.run_cli().returncode,0);first=self.payload()['reportId']
        self.write('seed',b'newer\n');self.assertEqual(self.run_cli().returncode,0);second=self.payload()['reportId']
        self.assertNotEqual(first,second)
        self.body.write_text(BODY+'<input type="checkbox" data-check-id="new-check">')
        self.assertEqual(self.run_cli().returncode,0);self.assertNotEqual(second,self.payload()['reportId'])
    def test_script_close_in_code_is_escaped(self):
        self.write('seed',b'</script><script>alert(1)</script>\n');self.assertEqual(self.run_cli().returncode,0)
        self.assertNotIn('</script><script>alert',self.out.read_text())
    def test_no_final_newline_preserved(self):
        self.write('seed',b'new');f=self.entries()[0]
        self.assertIn(['!','No newline at end of file'],f['hunks'][0]['lines'])
    def test_staged_version_is_not_reported_as_working_version(self):
        self.write('seed', b'staged\n'); self.g('add','seed'); self.write('seed', b'working\n')
        self.assertEqual(self.run_cli().returncode,0)
        lines=self.payload()['files'][0]['hunks'][0]['lines']
        self.assertIn(['+','working'],lines);self.assertNotIn(['+','staged'],lines)
    def test_empty_file_addition_and_deletion(self):
        self.write('empty',b'');self.assertEqual(self.entries()[0]['status'],'A')
        self.commit();self.base=b.base_states('HEAD');Path('empty').unlink()
        self.assertEqual(self.entries()[0]['status'],'D')
    def test_dangling_internal_link_rejected(self):
        self.body.write_text(BODY+'<a href="#c1">Missing commit</a>')
        self.assertEqual(self.run_cli().returncode,2)
    def test_executable_body_script_rejected(self):
        self.body.write_text(BODY+'<script>alert(1)</script>')
        self.assertEqual(self.run_cli().returncode,2)
    def test_snapshot_explicit_mode(self):
        self.write('seed',b'new\n');Path('seed').chmod(0o755)
        snap=Path(self.artifacts.name)/'snapshots/1/seed';snap.parent.mkdir(parents=True);snap.write_bytes(b'new\n')
        r=self.run_cli(self.plan([{'path':'seed','mode':'100755'}]));self.assertEqual(r.returncode,0,r.stderr)
    def test_duplicate_checkbox_ids_rejected(self):
        self.body.write_text(BODY+'<input type="checkbox" data-check-id="same"><input type="checkbox" data-check-id="same">')
        self.assertEqual(self.run_cli().returncode,2)
    def planning_body(self):
        return '<div class="tab-page" data-tab="overview"><h1>Plan</h1>' + ''.join(f'<section id="{name}">Unconfirmed fixture</section>' for name in sorted(b.SECTIONS['planning'])) + '</div>'
    def test_planning_outside_repository(self):
        self.body.write_text(self.planning_body())
        os.chdir(self.artifacts.name)
        r=self.run_cli(None,'--mode','planning');self.assertEqual(r.returncode,0,r.stderr)
        data=self.payload();self.assertEqual(data['mode'],'planning');self.assertIsNone(data['head']);self.assertEqual(data['files'],[])
        self.assertIn('구현/검증 결과 아님',self.out.read_text())
    def test_planning_rejects_result_options(self):
        self.body.write_text(self.planning_body())
        for extra in [('--base','HEAD'),('--strip-prefix','App/')]:
            self.assertEqual(self.run_cli(None,'--mode','planning',*extra).returncode,2)
        self.assertEqual(self.run_cli(self.plan(['seed']),'--mode','planning').returncode,2)
    def test_planning_rejects_diff_embeds(self):
        self.body.write_text(self.planning_body()+'<div class="diff-embed" data-file="seed"></div>')
        self.assertEqual(self.run_cli(None,'--mode','planning').returncode,2)
    def test_result_requires_review_and_merge_sections(self):
        self.body.write_text(BODY.replace('id="merge-checklist"','id="other"'))
        self.assertEqual(self.run_cli().returncode,2)
    def test_fulfilled_verdict_requires_evidence(self):
        self.body.write_text(BODY+'<div data-verdict="met" data-basis="R1">Met</div>')
        self.assertEqual(self.run_cli().returncode,2)
        self.body.write_text(BODY+'<div data-verdict="met" data-basis="R1" data-evidence="logs/test.txt">Met</div>')
        self.assertEqual(self.run_cli().returncode,0)
    def test_human_review_requires_actor_and_time(self):
        self.body.write_text(BODY+'<div data-verdict="met" data-basis="repo rule" data-evidence="review log" data-human="true">Reviewed</div>')
        self.assertEqual(self.run_cli().returncode,2)
    def test_na_requires_reason(self):
        self.body.write_text(BODY+'<div data-verdict="na" data-basis="R1">N/A</div>')
        self.assertEqual(self.run_cli().returncode,2)

    def test_scaffolds_require_replacement_but_allow_draft_preview(self):
        for mode, skill in [('planning','plan-brief'),('result','result-brief')]:
            self.body.write_text((SCRIPT.parents[2]/skill/'assets/example/content.html').read_text())
            self.assertEqual(self.run_cli(None,'--mode',mode).returncode,2)
            r=self.run_cli(None,'--mode',mode,'--draft')
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(self.payload()['issues'], ['예시 placeholder가 남아 있음'])

    def test_common_resources_do_not_drift(self):
        plan = SCRIPT.parents[2] / 'plan-brief'
        result = SCRIPT.parent.parent
        for rel in ['scripts/brief_core.py','scripts/check_browser.mjs','assets/template.html']:
            self.assertEqual((plan/rel).read_bytes(),(result/rel).read_bytes(),rel)
    def test_each_package_runs_without_sibling(self):
        import shutil
        for skill, body in [('plan-brief',self.planning_body()),('result-brief',BODY)]:
            with tempfile.TemporaryDirectory() as isolated:
                target=Path(isolated)/skill
                shutil.copytree(SCRIPT.parents[2]/skill,target)
                self.body.write_text(body)
                r=subprocess.run([sys.executable,'-B',str(target/'scripts/build.py'),str(self.body),str(self.out)],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)

    def test_output_alias_preserves_input(self):
        original = self.body.read_bytes()
        sub = self.body.parent / 'sub'; sub.mkdir()
        alias = self.body.parent / 'alias'; alias.symlink_to(self.body.parent, target_is_directory=True)
        for output in [sub/'..'/self.body.name, alias/self.body.name]:
            self.out = output
            r = self.run_cli()
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertEqual(self.body.read_bytes(), original)
    def test_output_hardlink_preserves_input(self):
        original = self.body.read_bytes()
        os.link(self.body, self.out)
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.body.read_bytes(), original)
    def test_template_ids_rejected(self):
        for identifier in ['diff-data', 'main', 'theme-btn', 'toc-list']:
            self.body.write_text(BODY+f'<div id="{identifier}">not json</div>')
            self.assertEqual(self.run_cli().returncode, 2)
    def test_legitimate_placeholder_words_allowed(self):
        self.body.write_text(self.planning_body().replace('Plan', 'TODO 앱의 model-id 및 TBD 표시 요구'))
        self.assertEqual(self.run_cli(None,'--mode','planning').returncode, 0)
    def test_file_directory_transition_both_directions(self):
        Path('seed').unlink(); self.write('seed/settings.json', b'{}')
        self.assertEqual([(x['path'],x['status']) for x in self.entries()], [('seed','D'),('seed/settings.json','A')])
        self.commit(); self.base=b.base_states('HEAD')
        Path('seed/settings.json').unlink();Path('seed').rmdir();self.write('seed',b'restored')
        self.assertEqual([(x['path'],x['status']) for x in self.entries()], [('seed','A'),('seed/settings.json','D')])
    def merge_body(self, row):
        return BODY.replace('id="merge-checklist">Recorded scope: fixture', 'id="merge-checklist"><table><thead><tr><th>Condition</th></tr></thead><tbody>'+row+'</tbody></table>')
    def test_merge_rows_cannot_omit_metadata(self):
        for row in ['<tr><td>사람 승인 완료</td></tr>', '<tr data-verdict="unknown" data-basis="R1"><td>Unknown type</td></tr>']:
            self.body.write_text(self.merge_body(row))
            self.assertEqual(self.run_cli().returncode,2)
    def test_human_merge_row_requires_record(self):
        row='<tr data-check-kind="human" data-verdict="met" data-basis="Rule 1" data-evidence="review.log" ATTR><td>Reviewed</td></tr>'
        self.body.write_text(self.merge_body(row.replace('ATTR','')))
        self.assertEqual(self.run_cli().returncode,2)
        self.body.write_text(self.merge_body(row.replace('ATTR','data-actor="Reviewer" data-time="2026-10-30"')))
        self.assertEqual(self.run_cli().returncode,0)
    def test_merge_checklist_without_tbody_still_checked(self):
        self.body.write_text(self.merge_body('<tr><td>Approved</td></tr>').replace('<tbody>','').replace('</tbody>',''))
        self.assertEqual(self.run_cli().returncode,2)

    def test_schema_wrong_types_fail_cleanly(self):
        for plan in [{'commits':{}},self.plan([5]),self.plan([{'path':'seed','mode':[]}]),{'commits':[{'message':'x','files':['seed'],'kind':[]}]},{'commits':[{'message':'x','files':['seed'],'risk':{'level':'invalid'}}]}]:
            r=self.run_cli(plan);self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)

if __name__ == '__main__': unittest.main()

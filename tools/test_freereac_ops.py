# SPDX-License-Identifier: GPL-3.0-or-later
"""tools/freereac_ops.py on throwaway git repos: the public-tree guard, the resolver rungs and the
ops export. Run: python3 -m unittest discover -s tools -p 'test_*.py'"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freereac_ops as fo  # noqa: E402

MOVED = ['x-re/FINDINGS.md', 'x-re/decode_x.py', 'session-2026-09-01/timeline.txt']


def sh(cwd, *args):
    subprocess.run(['git', '-c', 'commit.gpgsign=false', *args], cwd=cwd, check=True,
                   capture_output=True)


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(text)


class Fixture(unittest.TestCase):
    """<tmp>/pub: a repo whose base commit holds MOVED, whose tip moved them out."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pub = os.path.join(self.tmp, 'pub')
        os.makedirs(self.pub)
        sh(self.pub, 'init', '-q', '-b', 'main')
        sh(self.pub, 'config', 'user.email', 't@example.com')
        sh(self.pub, 'config', 'user.name', 'T')
        write(self.pub, 'README.md', 'captures\n')
        write(self.pub, 'x-re/cap.pcap', 'pointer\n')
        for p in MOVED:
            write(self.pub, p, 'internal %s\n' % p)
        sh(self.pub, 'add', '-A')
        sh(self.pub, 'commit', '-qm', 'base')
        self.base = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.pub, capture_output=True,
                                   text=True).stdout.strip()
        sh(self.pub, 'rm', '-q', *MOVED)
        write(self.pub, fo.MOVES, '# base %s\n%s\n' % (self.base, '\n'.join(MOVED)))
        sh(self.pub, 'add', '-A')
        sh(self.pub, 'commit', '-qm', 'move')
        env = {k: v for k, v in os.environ.items() if not k.startswith('FREEREAC_')}
        self.env = mock.patch.dict(os.environ, env, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)

    def run_check(self):
        buf = io.StringIO()
        n = fo.check(self.pub, out=buf)
        return n, buf.getvalue()

    def add(self, rel, text):
        write(self.pub, rel, text)
        sh(self.pub, 'add', rel)

    def make_ops(self, root, paths=MOVED):
        for p in paths:
            write(root, os.path.join(fo.OPS_SUBDIR, p), 'internal %s\n' % p)


class Classifier(unittest.TestCase):
    def test_rule(self):
        for p in ('m200-headamp-re/DECODE.md', 'captures/role-x.notes.txt', 's1608-bank/README.md',
                  'a/plan.json', 'x-re/find.py', 'p/etf/wire.err', 'h/overnight.trace',
                  'analysis/2026-09-13-note.md', 'CAPTURE-PLAN-x.md'):
            self.assertTrue(fo.belongs_in_ops(p), p)
        for p in ('README.md', 'MANIFEST.md', 'BUILDING.md', 'LICENSE', 'analysis/README.md',
                  'analysis/reac_pcap.py', 'analysis/rows.jsonl', 'analysis/x.json',
                  'capture-role-change.sh', 'captures/a.pcap', 'tools/ops-moves.txt',
                  '.github/workflows/check.yml', 'analysis/up_slots'):
            self.assertFalse(fo.belongs_in_ops(p), p)

    def test_slug(self):
        self.assertEqual(fo.slug('m200-s4000-width-re/FINDINGS.md'), 'm200-s4000-width-re/FINDINGS')


class Check(Fixture):
    def test_clean_tree_passes_and_names_the_skip(self):
        n, out = self.run_check()
        self.assertEqual(n, 0, out)
        self.assertIn('OPS-ABSENT moves-resolve: skipped', out)
        self.assertIn('CHECK OK', out)

    def test_moved_path_still_public_fails(self):
        self.add('x-re/FINDINGS.md', 'back\n')
        n, out = self.run_check()
        self.assertIn('STILL-PUBLIC x-re/FINDINGS.md', out)
        self.assertGreater(n, 0)

    def test_new_write_up_fails(self):
        self.add('y-re/FINDINGS.md', 'new vendor RE\n')
        n, out = self.run_check()
        self.assertIn('INTERNAL y-re/FINDINGS.md', out)

    def test_citation_by_file_fails_and_slug_passes(self):
        self.add('analysis/tool.py', '# see x-re/FINDINGS.md and decode_x.py\n')
        n, out = self.run_check()
        self.assertIn('CITES analysis/tool.py:1 x-re/FINDINGS.md', out)
        self.assertIn('CITES analysis/tool.py:1 x-re/decode_x.py', out)
        self.assertEqual(n, 2, out)
        self.add('analysis/tool.py', '# see x-re/FINDINGS and x-re/decode_x\n')
        self.assertEqual(self.run_check()[0], 0)

    def test_generic_session_name_is_not_a_bare_citation(self):
        self.add('README.md', 'each session keeps a timeline.txt\n')
        self.assertEqual(self.run_check()[0], 0)
        self.add('README.md', 'see session-2026-09-01/timeline.txt\n')
        self.assertIn('CITES README.md:1 session-2026-09-01/timeline.txt', self.run_check()[1])

    def test_require_ops_fails_when_absent(self):
        os.environ['FREEREAC_REQUIRE_OPS'] = '1'
        n, out = self.run_check()
        self.assertIn('OPS-ABSENT moves-resolve: FREEREAC_REQUIRE_OPS=1', out)
        self.assertEqual(n, 1)

    def test_env_rung_resolves_every_move(self):
        ops = os.path.join(self.tmp, 'elsewhere')
        self.make_ops(ops)
        os.environ['FREEREAC_OPS'] = ops
        n, out = self.run_check()
        self.assertEqual(n, 0, out)
        self.assertIn('OPS OK 3 moved paths', out)
        self.assertEqual(fo.resolve('x-re/FINDINGS', self.pub),
                         os.path.join(ops, 'reac-captures', 'x-re', 'FINDINGS.md'))

    def test_sibling_rung_and_half_moved_fails(self):
        sib = os.path.join(self.tmp, 'freereac-ops')
        self.make_ops(sib, MOVED[:2])
        self.assertEqual(fo.ops_root(self.pub), sib)
        n, out = self.run_check()
        self.assertIn('UNRESOLVED session-2026-09-01/timeline', out)
        self.assertEqual(n, 1, out)
        os.environ['FREEREAC_OPS'] = os.path.join(self.tmp, 'nope')
        self.assertIsNone(fo.ops_root(self.pub), 'a set but missing $FREEREAC_OPS never falls through')

    def test_resolve_absent(self):
        self.assertIsNone(fo.resolve('x-re/FINDINGS', self.pub))


class Export(Fixture):
    def ops_repo(self, seeded):
        ops = os.path.join(self.tmp, 'freereac-ops')
        os.makedirs(ops)
        sh(ops, 'init', '-q', '-b', 'main')
        sh(ops, 'config', 'user.email', 't@example.com')
        sh(ops, 'config', 'user.name', 'T')
        sh(ops, 'config', 'commit.gpgsign', 'false')
        if seeded:
            write(ops, 'README.md', 'ops\n')
            sh(ops, 'add', '-A')
            sh(ops, 'commit', '-qm', 'seed')
        return ops

    def ls(self, ops, ref):
        return subprocess.run(['git', 'ls-tree', '-r', ref], cwd=ops, capture_output=True,
                              text=True).stdout

    def test_export_onto_main_is_byte_identical_and_idempotent(self):
        ops = self.ops_repo(seeded=True)
        buf = io.StringIO()
        c = fo.export(ops, repo=self.pub, out=buf)
        self.assertIn('EXPORT lane/docs-reac-captures', buf.getvalue())
        tree = self.ls(ops, fo.BRANCH)
        self.assertIn('\tREADME.md\n', tree)
        for p in MOVED:
            src = subprocess.run(['git', 'rev-parse', '%s:%s' % (self.base, p)], cwd=self.pub,
                                 capture_output=True, text=True).stdout.strip()
            self.assertIn('%s\treac-captures/%s\n' % (src, p), tree)
        parent = subprocess.run(['git', 'rev-parse', fo.BRANCH + '^'], cwd=ops,
                                capture_output=True, text=True).stdout.strip()
        main = subprocess.run(['git', 'rev-parse', 'main'], cwd=ops, capture_output=True,
                              text=True).stdout.strip()
        self.assertEqual(parent, main)
        buf = io.StringIO()
        self.assertEqual(fo.export(ops, repo=self.pub, out=buf), c)
        self.assertIn('EXPORT EXISTS', buf.getvalue())
        # the exported checkout is what `check` then resolves through the sibling rung
        subprocess.run(['git', '-c', 'advice.detachedHead=false', 'checkout', '-q', fo.BRANCH],
                       cwd=ops, check=True)
        self.assertEqual(self.run_check()[0], 0)

    def test_export_signs_when_commit_gpgsign_is_set(self):
        ops = self.ops_repo(seeded=True)
        sh(ops, 'config', 'commit.gpgsign', 'true')
        sh(ops, 'config', 'gpg.program', os.path.join(self.tmp, 'no-gpg'))
        with self.assertRaises(SystemExit) as e:
            fo.export(ops, repo=self.pub, out=io.StringIO())
        self.assertIn('commit-tree', str(e.exception), 'the export asked gpg to sign, and gpg failed')

    def test_export_into_empty_ops_is_a_root_commit(self):
        ops = self.ops_repo(seeded=False)
        fo.export(ops, repo=self.pub, out=io.StringIO())
        self.assertEqual(len(self.ls(ops, fo.BRANCH).splitlines()), len(MOVED))

    def test_each_path_is_taken_from_its_own_base(self):
        self.add('plans/old-plan.md', 'a plan the tip never carried\n')
        sh(self.pub, 'commit', '-qm', 'plan')
        older = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.pub, capture_output=True,
                               text=True).stdout.strip()
        sh(self.pub, 'rm', '-q', 'plans/old-plan.md')
        write(self.pub, fo.MOVES, '# base %s\n%s\n# base %s\nplans/old-plan.md\n'
              % (self.base, '\n'.join(MOVED), older))
        sh(self.pub, 'add', '-A')
        sh(self.pub, 'commit', '-qm', 'drop plan')
        self.assertEqual(fo.moved_paths(self.pub), MOVED + ['plans/old-plan.md'])
        ops = self.ops_repo(seeded=False)
        fo.export(ops, repo=self.pub, out=io.StringIO())
        tree = self.ls(ops, fo.BRANCH)
        self.assertIn('\treac-captures/plans/old-plan.md\n', tree)
        self.assertEqual(len(tree.splitlines()), len(MOVED) + 1)
        msg = subprocess.run(['git', 'log', '-1', '--format=%B', fo.BRANCH], cwd=ops,
                             capture_output=True, text=True).stdout
        self.assertIn(','.join(sorted((self.base[:12], older[:12]))), msg)

    def test_a_path_before_any_base_is_refused(self):
        write(self.pub, fo.MOVES, 'x-re/FINDINGS.md\n# base %s\n' % self.base)
        with self.assertRaises(SystemExit) as e:
            fo.read_moves(self.pub)
        self.assertIn('comes before any "# base <sha>" line', str(e.exception))

    def test_export_refuses_a_base_the_rewrite_took_away(self):
        ops = self.ops_repo(seeded=True)
        write(self.pub, fo.MOVES, '# base %s\n%s\n' % ('e' * 40, '\n'.join(MOVED)))
        with self.assertRaises(SystemExit) as e:
            fo.export(ops, repo=self.pub, out=io.StringIO())
        self.assertIn('backup/pre-rewrite-2026-10-01', str(e.exception))

    def test_export_refuses_a_path_missing_at_base(self):
        ops = self.ops_repo(seeded=True)
        write(self.pub, fo.MOVES, '# base %s\nnot/there.md\n' % self.base)
        with self.assertRaises(SystemExit) as e:
            fo.export(ops, repo=self.pub, out=io.StringIO())
        self.assertIn('not/there.md is not in', str(e.exception))


class History(Fixture):
    """The rewrite's drop list and the guard that keeps the rewritten history clean."""

    def commit(self, msg):
        sh(self.pub, 'commit', '-qm', msg)

    def drops(self, *revs):
        out, err = io.StringIO(), io.StringIO()
        n = fo.history(revs or ('--all',), self.pub, out=out, err=err)
        return n, out.getvalue().split(), err.getvalue()

    def guard(self, *revs):
        buf = io.StringIO()
        n = fo.history_check(revs or ('HEAD',), self.pub, out=buf)
        return n, buf.getvalue()

    def test_drop_list_is_every_moved_path_even_deleted_ones(self):
        n, paths, err = self.drops()
        self.assertEqual((n, err), (0, ''))
        self.assertEqual(paths, sorted(MOVED))

    def test_an_internal_path_off_the_list_is_refused_by_name(self):
        sh(self.pub, 'checkout', '-q', '-b', 'side')
        self.add('CAPTURE-PLAN-z.md', 'a plan\n')
        self.commit('plan')
        sh(self.pub, 'rm', '-q', 'CAPTURE-PLAN-z.md')
        self.commit('drop plan')
        sh(self.pub, 'checkout', '-q', 'main')
        self.assertEqual(self.drops('main')[0], 0, 'the side branch is not in main')
        n, paths, err = self.drops()
        self.assertEqual(n, 1)
        self.assertIn('UNLISTED CAPTURE-PLAN-z.md', err)
        self.assertIn('CAPTURE-PLAN-z.md', paths)

    def test_guard_is_red_on_the_old_history_and_names_the_paths(self):
        n, out = self.guard()
        self.assertEqual(n, len(MOVED), out)
        self.assertIn('HISTORY-INTERNAL x-re/FINDINGS.md: added in %s' % self.base[:12], out)
        self.assertIn('HISTORY FAILED 3', out)

    def test_guard_is_green_on_a_clean_history_and_red_on_an_add_and_delete(self):
        sh(self.pub, 'checkout', '-q', '--orphan', 'clean')
        sh(self.pub, 'rm', '-rq', '--cached', '.')
        self.add('README.md', 'captures\n')
        self.add('x-re/cap.pcap', 'pointer\n')
        self.add(fo.MOVES, '# base %s\n%s\n' % (self.base, '\n'.join(MOVED)))
        self.add('a' * 40, 'a 40-hex file name is a file, not a commit\n')
        self.commit('rewritten')
        n, out = self.guard()
        self.assertEqual(n, 0, out)
        self.assertIn('HISTORY OK 1 commits', out)
        self.add('y-re/FINDINGS.md', 'back\n')
        self.commit('oops')
        sh(self.pub, 'rm', '-q', 'y-re/FINDINGS.md')
        self.commit('undo')
        n, out = self.guard()
        self.assertIn('HISTORY-INTERNAL y-re/FINDINGS.md', out)
        self.assertEqual(n, 1, out)

    def test_a_file_a_merge_adds_is_seen(self):
        sh(self.pub, 'checkout', '-q', '-b', 'side')
        self.add('side.pcap', 'x\n')
        self.commit('side')
        sh(self.pub, 'checkout', '-q', 'main')
        sh(self.pub, 'merge', '-q', '--no-ff', '--no-commit', 'side')
        self.add('s-2026-01-01/timeline.txt', 'only the merge adds this\n')
        self.commit('merge')
        self.assertIn('s-2026-01-01/timeline.txt', fo.history_paths(['HEAD'], self.pub))


class RealTree(unittest.TestCase):
    """This repository, before its history rewrite and after it: the move list's first group is
    exactly the rule applied at its base, every later group is history-only internal files, every
    internal path the history carries is listed, and the tree is clean."""

    def setUp(self):
        gone = [b[:12] for b in sorted({b for b, _ in fo.read_moves()}) if not fo.has_commit(b)]
        if gone and self._testMethodName in ('test_the_list_is_the_rule_at_base',
                                             'test_later_groups_are_history_only_internal_files'):
            self.skipTest('bases %s rewritten away; the history tests hold instead' % ','.join(gone))

    def test_the_list_is_the_rule_at_base(self):
        moves = fo.read_moves()
        base = moves[0][0]
        paths = [p for b, p in moves if b == base]
        tree = fo.git('ls-tree', '-r', '--name-only', base).decode().splitlines()
        self.assertEqual(sorted(p for p in tree if fo.belongs_in_ops(p)), sorted(paths))

    def test_later_groups_are_history_only_internal_files(self):
        moves = fo.read_moves()
        first = fo.git('ls-tree', '-r', '--name-only', moves[0][0]).decode().splitlines()
        for base, p in moves:
            if base == moves[0][0]:
                continue
            self.assertTrue(fo.belongs_in_ops(p), p)
            self.assertNotIn(p, first, '%s reached the move: list it in the first group' % p)
            self.assertTrue(fo.git('ls-tree', base, '--', p).strip(), '%s is not in %s' % (p, base))

    def test_every_internal_path_in_the_history_is_listed(self):
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(fo.history(('HEAD',), out=out, err=err), 0, err.getvalue())

    def test_once_the_base_is_gone_the_history_carries_nothing_listed(self):
        base = fo.read_moves()[0][0]
        # gone from HEAD's history; a clone that fetched the backup tag still has the commit
        if subprocess.run(['git', 'merge-base', '--is-ancestor', base, 'HEAD'], cwd=fo.REPO,
                          capture_output=True).returncode == 0:
            self.skipTest('base %s still in the history: it is not rewritten yet' % base[:12])
        buf = io.StringIO()
        self.assertEqual(fo.history_check(('HEAD',), out=buf), 0, buf.getvalue())

    def test_the_public_tree_is_clean(self):
        env = {k: v for k, v in os.environ.items() if k != 'FREEREAC_REQUIRE_OPS'}
        with mock.patch.dict(os.environ, env, clear=True):
            buf = io.StringIO()
            self.assertEqual(fo.check(out=buf), 0, buf.getvalue())


if __name__ == '__main__':
    unittest.main()

"""Executable acceptance tests for local preparation; no live account calls."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'bot_profiles/_build_profiles.py'


def profile(niche='cooking', timezone='America/New_York'):
    return {
        'schema_version': 1,
        'creator': {'display_name': 'User'},
        'brand': {'name': 'Everyday Kitchen' if niche == 'cooking' else 'Code Lessons', 'signature': ''},
        'niche': niche,
        'audience': 'Beginner home cooks' if niche == 'cooking' else 'Beginning software developers',
        'pillars': ['Learn', 'Practice', 'Progress'],
        'timezone': timezone,
        'schedule': {'checkin': '08:00', 'nudge': '09:00', 'idea': '10:00', 'days': 'daily'},
    }


def bindings():
    data = json.loads((ROOT / 'ids.json').read_text())
    rows = [data['head']] + data['specialists'] + data['standalone'] + data['group_chats']
    for n, row in enumerate(rows, 1):
        row['id'] = f'00000000-0000-4000-8000-{n:012d}'
    return data


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def build(self, data=None, ids=None, mode='deploy', out=None):
        p, b = self.base / 'profile.json', self.base / 'ids.json'
        p.write_text(json.dumps(data if data is not None else profile()))
        b.write_text(json.dumps(ids if ids is not None else bindings()))
        return subprocess.run([sys.executable, str(BUILDER), '--mode', mode,
                               '--profile', str(p), '--ids', str(b), '--output', str(out or self.base / 'bundle')],
                              text=True, capture_output=True)

    def test_two_niches_are_bound_without_cross_contamination(self):
        for niche, tz, expected, absent in [
            ('cooking', 'America/New_York', 'Everyday Kitchen', 'Code Lessons'),
            ('software education', 'Europe/Berlin', 'Code Lessons', 'Everyday Kitchen'),
        ]:
            out = self.base / niche
            r = self.build(profile(niche, tz), out=out)
            self.assertEqual(r.returncode, 0, r.stderr)
            master = (out / '01_MASTER_CONFIG.md').read_text()
            self.assertIn(expected, master)
            self.assertIn(niche, master)
            self.assertIn(tz, master)
            prompts = list((out / 'bot_profiles').glob('*.md'))
            self.assertEqual(len(prompts), 15)  # 14 bots + routine instructions
            text = '\n'.join(x.read_text() for x in out.rglob('*.md'))
            self.assertNotIn(absent, text)
            self.assertNotIn('{{', text)
            self.assertIn('08:00', (out / 'bot_profiles/routines.md').read_text())
            self.assertIn('unknown', master.lower())
            self.assertIn('SendToAgent', text)
            self.assertEqual((out / 'manifest.json').exists(), True)

    def test_incomplete_profile_cannot_create_or_replace_output(self):
        out = self.base / 'bundle'
        data = profile(); data['timezone'] = None
        r = self.build(data)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertFalse(out.exists())
        out.mkdir(); (out / 'keep').write_text('unchanged')
        r = self.build(data)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((out / 'keep').read_text(), 'unchanged')

    def test_rejects_duplicate_ids_and_incomplete_membership(self):
        ids = bindings(); ids['specialists'][0]['id'] = ids['head']['id']
        self.assertNotEqual(self.build(ids=ids).returncode, 0)
        ids = bindings(); ids['group_chats'][0]['members'] = ['head']
        self.assertNotEqual(self.build(ids=ids).returncode, 0)

    def test_rejects_bad_schedule_zone_and_compile_tokens_in_user_input(self):
        for key, value in [('timezone', 'Not/AZone'), ('niche', '{{bindings.head}}')]:
            data = profile(); data[key] = value
            self.assertNotEqual(self.build(data).returncode, 0)
        for times in [('25:00', '09:00', '10:00'), ('10:00', '09:00', '08:00')]:
            data = profile(); data['schedule'].update(zip(('checkin', 'nudge', 'idea'), times))
            self.assertNotEqual(self.build(data).returncode, 0)

    def test_deterministic_and_failed_build_does_not_damage_existing_bundle(self):
        out = self.base / 'bundle'
        r = self.build(); self.assertEqual(r.returncode, 0, r.stderr)
        before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob('*') if p.is_file()}
        r = self.build(); self.assertEqual(r.returncode, 0, r.stderr)
        after = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        bad = profile(); bad['audience'] = ''
        self.assertNotEqual(self.build(bad).returncode, 0)
        self.assertEqual(before, {str(p.relative_to(out)): p.read_bytes() for p in out.rglob('*') if p.is_file()})

    def test_malformed_optional_values_fail_before_output(self):
        for field,value in [('post_windows', []), ('brand', {'name': 123}),
                            ('voice', {'style': []}), ('banks', {'hashtags': {'tiktok': [123]}}),
                            ('creator', {'confirmed_facts': 'made-up'}),
                            ('approvals', {'operator': ''})]:
            data=profile();data[field]=value
            r=self.build(data)
            self.assertNotEqual(r.returncode,0,field)
            self.assertFalse((self.base/'bundle').exists())

    def test_unowned_or_modified_output_is_never_replaced(self):
        out=self.base/'bundle';out.mkdir()
        (out/'manifest.json').write_text('{}')
        (out/'important.txt').write_text('keep this')
        r=self.build()
        self.assertNotEqual(r.returncode,0)
        self.assertEqual((out/'important.txt').read_text(),'keep this')
        import shutil
        shutil.rmtree(out)
        self.assertEqual(self.build().returncode,0)
        (out/'personal-notes.txt').write_text('keep this too')
        self.assertNotEqual(self.build().returncode,0)
        self.assertEqual((out/'personal-notes.txt').read_text(),'keep this too')

    def test_only_selected_overlapping_schedules_can_collide(self):
        data=profile();data['schedule']['days']='weekdays'
        data['phases']={'2':True,'3':False}
        data['schedule'].update(comments='18:00',research='08:00')
        r=self.build(data)
        self.assertEqual(r.returncode,0,r.stderr)
        data=profile();data['schedule']['comments']='08:00'
        r=self.build(data)
        self.assertEqual(r.returncode,0,r.stderr)
        data['phases']={'2':True,'3':False};data['schedule']['research']='12:00'
        self.assertNotEqual(self.build(data).returncode,0)

    def test_refuses_output_inside_source_tree(self):
        r = self.build(out=ROOT / 'agents')
        self.assertNotEqual(r.returncode, 0)

    def test_dst_keeps_local_wall_clock_and_zone(self):
        for tz, before, after in [('America/New_York', (2026, 3, 7), (2026, 3, 9)),
                                   ('Europe/Berlin', (2026, 3, 28), (2026, 3, 30))]:
            out = self.base / tz.replace('/', '-')
            r = self.build(profile(timezone=tz), out=out)
            self.assertEqual(r.returncode, 0, r.stderr)
            schedules = json.loads((out / 'schedule.json').read_text())
            morning = schedules[0]
            self.assertEqual((morning['time'], morning['timezone']), ('08:00', tz))
            first = datetime(*before, 8, tzinfo=ZoneInfo(morning['timezone']))
            second = datetime(*after, 8, tzinfo=ZoneInfo(morning['timezone']))
            self.assertNotEqual(first.utcoffset(), second.utcoffset())
            self.assertFalse(any(s['enabled'] for s in schedules))


if __name__ == '__main__':
    unittest.main()

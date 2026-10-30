import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_engine import profile, bindings
try:
    from setup_state import Journal
except ImportError:
    Journal = None


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Journal, 'Resumable setup journal is not implemented')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'instance/state.json'
        self.p = profile()

    def new(self):
        return Journal(self.path, self.p)

    def test_invalid_profile_has_no_state_or_resources(self):
        bad = profile(); bad['niche'] = None
        with self.assertRaises(ValueError): Journal(self.path, bad)
        self.assertFalse(self.path.exists())

    def test_interrupted_setup_resumes_without_duplicate_bindings(self):
        j = self.new()
        j.bind('head', 'bot-1', 'created', 'native tool returned bot-1')
        j = self.new()
        j.bind('head', 'bot-1', 'created', 'verified existing bot-1')
        self.assertEqual(len(j.data['resources']), 1)
        self.assertEqual(j.pending_resources()[0], 'tiktok_hook_search')
        with self.assertRaises(ValueError): j.bind('head', 'unrelated', 'created', 'different bot')
        with self.assertRaises(ValueError): j.bind('ig_thumbnail', 'bot-1', 'created', 'duplicate')
        with self.assertRaises(ValueError): j.bind('ig_thumbnail', 'bot-2', 'found', 'same name')
        self.assertFalse(j.status()['ready_to_activate'])

    def complete(self):
        j = self.new()
        for row in [bindings()['head']] + bindings()['specialists'] + bindings()['standalone'] + bindings()['group_chats']:
            j.bind(row['key'], row['id'], 'created', 'tool receipt')
        # Capture all bindings as the compiler consumes them.
        exported = j.export_ids()
        self.assertEqual(len(exported['group_chats'][0]['members']), 5)
        import subprocess
        from test_engine import BUILDER
        root=self.path.parent
        (root/'profile.json').write_text(json.dumps(self.p)); (root/'ids.json').write_text(json.dumps(exported))
        r=subprocess.run([sys.executable,str(BUILDER),'--mode','deploy','--profile',str(root/'profile.json'),'--ids',str(root/'ids.json'),'--output',str(root/'bundle')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        j.set_bundle(root/'bundle')
        for cap in j.REQUIRED_CAPABILITIES:j.capability(cap,True,'verified tool capability')
        for row in j.export_ids()['group_chats']:
            members=[j.data['resources'][key]['id'] for key in row['members']]
            j.verify(row['key'],'native membership listing',members=members)
        for key in [x for x in j.data['resources'] if not x.startswith('group_')]:
            j.install(key,'native durable instruction delivery receipt')
            j.verify(key,'bot confirmed its role and current master')
        for key in ('checkin','nudge','idea'):j.routine(key,'routine-'+key,'saved schedule inspected', '08:00' if key=='checkin' else '09:00' if key=='nudge' else '10:00','America/New_York','daily')
        j.record_test('live',True,'test transcript: all checks in acceptance.md passed')
        return j

    def test_activation_requires_live_evidence_not_simulation(self):
        j=self.complete()
        self.assertTrue(j.status()['ready_to_activate'])
        j.record_test('simulation',True,'offline fixture only')
        self.assertFalse(j.status()['ready_to_activate'])
        with self.assertRaises(ValueError):j.activate('enabled')
        j.record_test('live',True,'real run verified')
        j.activate('native switch state: all selected routines active')
        self.assertEqual(j.status()['activation'], 'enabled')

    def test_unsupported_capability_and_missing_membership_block_activation(self):
        j=self.complete()
        j.capability('group_messaging',False,'unsupported in this harness')
        self.assertFalse(j.status()['ready_to_activate'])
        with self.assertRaises(ValueError):j.activate('claim')
        with self.assertRaises(ValueError):j.verify('group_tiktok','wrong members',members=['outsider'])

    def test_configuration_update_requires_verified_pause_and_reinstallation(self):
        j=self.complete(); j.activate('native enabled switch')
        changed=profile();changed['schedule']['nudge']='09:15'
        j=Journal(self.path,changed)
        self.assertEqual(j.status()['activation'],'needs_pause')
        self.assertFalse(j.status()['ready_to_activate'])
        with self.assertRaises(ValueError):j.install('head','attempt without pause')
        j.pause('native listing: all deployment routines paused')
        self.assertEqual(j.status()['activation'],'inactive')
        self.assertFalse(j.status()['ready_to_activate'])

    def test_profile_update_preserves_routine_ids_for_reconciliation(self):
        j=self.complete(); j.activate('native active state')
        changed=profile();changed['schedule']['nudge']='09:15'
        j=Journal(self.path,changed)
        self.assertEqual(j.data['routines']['nudge']['id'], 'routine-nudge')
        self.assertNotIn('hash', j.data['routines']['nudge'])
        j.pause('all instance routines observed paused')
        # Existing resource identity remains, even though schedule/install receipts are invalid.
        with self.assertRaises(ValueError):
            j.routine('nudge','replacement','receipt','09:15','America/New_York','daily')

    def test_explicit_replacement_invalidates_evidence_and_preserves_other_resources(self):
        j=self.complete();j.activate('native switches enabled')
        self.assertTrue(callable(getattr(j,'replace',None)), 'Explicit replacement command is missing')
        with self.assertRaises(ValueError):j.replace('head',j.data['resources']['head']['id'],'new-head','selected','receipt')
        j.pause('actual instance routines observed paused')
        old=j.data['resources']['head']['id'];other=j.data['resources']['ig_thumbnail']['id']
        with self.assertRaises(ValueError):j.replace('head','wrong-prior-id','new-head','selected','receipt')
        j.replace('head',old,'new-head','selected','user selected replacement; native result verified')
        self.assertEqual(j.data['resources']['head']['id'],'new-head')
        self.assertEqual(j.data['resources']['ig_thumbnail']['id'],other)
        self.assertFalse(j.status()['ready_to_activate'])
        self.assertIsNone(j.data['bundle'])
        self.assertEqual(j.data['routines']['checkin']['id'],'routine-checkin')
        j.replace('checkin','routine-checkin','replacement-checkin','created','replacement routine observed paused')
        self.assertEqual(j.data['routines']['checkin']['id'],'replacement-checkin')
        j=Journal(self.path,self.p)
        self.assertEqual(j.data['resources']['head']['id'],'new-head')
        self.assertEqual(len(j.data['replacements']),2)

    def test_schedule_must_match_profile_and_ids_are_unique(self):
        j=self.complete()
        with self.assertRaises(ValueError): j.routine('nudge','routine-other','receipt','08:00','UTC','daily')
        with self.assertRaises(ValueError): j.routine('nudge','routine-checkin','receipt','09:00','America/New_York','daily')

if __name__=='__main__':unittest.main()

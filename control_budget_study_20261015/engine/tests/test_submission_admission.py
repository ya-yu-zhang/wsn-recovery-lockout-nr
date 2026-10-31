import unittest
import numpy as np
from test_base_controller import obs
from wsn.controller import Controller,INITIAL
from wsn.installation import Installation

POLICY='linucb_event_scalar4_failure_current_low4_noop_retry_mask'

def fresh():
 o=obs()
 for r in o['reports']:
  if r['node']<2:r.update(current_n=25,current_failed=0)
 return o

class AdmissionTests(unittest.TestCase):
 def test_low4_physical_model_and_projection(self):
  c=Controller(POLICY);self.assertEqual(c.bandit.A.shape,(4,4,4))
  x=[1,.2,.3,.4,10,20,30,40,50];c.bandit.update(2,x,.7)
  self.assertTrue(np.allclose(c.bandit.A[2],np.eye(4)+np.outer(x[:4],x[:4])))
  self.assertEqual(c.bandit.scores(x),c.bandit.scores(x[:4]+[0]*5))
 def test_identical_route_allowed_with_observed_evidence(self):
  c=Controller(POLICY);self.assertEqual(c.hold_admission(fresh(),INITIAL),(True,'identical_confirmed_feasible_route'))
 def test_changed_path_rejected(self):
  c=Controller(POLICY);self.assertFalse(c.hold_admission(fresh(),((0,4,5,9),(1,4,5,9)))[0])
 def test_missing_source_rejected(self):
  c=Controller(POLICY);o=fresh();o['reports']=[r for r in o['reports'] if r['node']!=0]
  self.assertFalse(c.hold_admission(o,INITIAL)[0])
 def test_missing_route_node_rejected(self):
  c=Controller(POLICY);o=fresh();o['reports']=[r for r in o['reports'] if r['node']!=2]
  self.assertFalse(c.hold_admission(o,INITIAL)[0])
 def test_current_failure_rejected(self):
  c=Controller(POLICY);o=fresh();o['reports'][0]['current_failed']=5
  self.assertFalse(c.hold_admission(o,INITIAL)[0])
 def test_insufficient_evidence_is_not_safe(self):
  c=Controller(POLICY);o=fresh();o['reports'][0]['current_n']=0
  self.assertFalse(c.hold_admission(o,INITIAL)[0])
 def test_unconfirmed_or_timeout_install_rejected(self):
  c=Controller(POLICY);c.installation=Installation(2,1,INITIAL,2)
  self.assertFalse(c.hold_admission(fresh(),INITIAL)[0]);c.installation.closed=True;c.installation.outcome='confirmation_timeout'
  self.assertFalse(c.hold_admission(fresh(),INITIAL)[0])
 def test_unknown_version_rejected(self):
  c=Controller(POLICY);o=fresh();o['reports'][0]['version']=100
  self.assertFalse(c.hold_admission(o,c.view(o)[0] and INITIAL)[0])
 def test_native_hold_contract_with_real_search_cost(self):
  c=Controller(POLICY);o=fresh()
  # Equal geometry and low queue favor an unchanged route in local search.
  for r in o['reports']:r['mean_J_ns']=0
  reply,row=c.step(o);d=row['decision']
  self.assertTrue(d.get('admitted_hold'));self.assertTrue(reply.startswith('-3 '))
  self.assertIsNone(d['paths']);self.assertEqual(d['install_budget_bytes'],0)
  self.assertGreater(d['fe'],0);self.assertEqual(d['declared_search_delay_ns'],d['fe']*20_000)
  self.assertNotIn(d['decision'],c.version_paths);self.assertEqual(c.installations,[])

if __name__=='__main__':unittest.main()

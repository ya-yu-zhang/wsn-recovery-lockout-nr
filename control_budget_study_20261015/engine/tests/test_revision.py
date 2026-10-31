import unittest,json
from test_base_controller import obs
from wsn.controller import Controller,INITIAL
from wsn.operator_search import search_operator

POLICY='linucb_event_scalar4_failure_current_ops_low4_noop_cache20_retry_mask'

class RevisionTests(unittest.TestCase):
 def test_native_json_roundtrip_preserves_replay(self):
  from audit_closed_loop import clean
  c=Controller(POLICY);o=obs(20)
  for r in o['reports']:r['buckets']=[[1,25],[2,25],[3,25]]
  o['timely_buckets']={'1':[25,20],'2':[25,20]}
  _,row=c.step(o)
  self.assertEqual(clean(row),clean(json.loads(json.dumps(row))))
 def test_unconfirmed_install_has_unknown_service(self):
  from wsn.installation import Installation
  c=Controller(POLICY);c.installation=Installation(1,10_000_000_000,INITIAL,2);o=obs(20)
  for r in o['reports']:r['buckets']=[[1,25],[2,25],[3,25]]
  o['timely_buckets']={'1':[25,25],'2':[25,25]}
  self.assertEqual(c.view(o)[-1]['settled_service']['reason'],'installation_unconfirmed')
 def test_original_class_is_retained(self):
  self.assertEqual(type(Controller('linucb')).__name__,'Controller')
 def test_idempotent_hold_does_not_claim_safe_service(self):
  c=Controller('force3_scalar_failure_current_ops_noop_cache20_retry_mask');o=obs()
  for r in o['reports']:
   if r['node']<2:r.update(current_n=0,current_failed=0)
  reply,row=c.step(o)
  self.assertTrue(reply.startswith('-3 '));self.assertTrue(row['decision']['admitted_hold'])
  self.assertFalse(row['event']['settled_service']['known']);self.assertEqual(c.installations,[])
 def test_sparse_feedback_is_unknown(self):
  c=Controller(POLICY);o=obs(20)
  for r in o['reports']:r['buckets']=[[1,4],[2,4],[3,4]]
  o['timely_buckets']={'1':[4,4],'2':[4,4]}
  self.assertFalse(c.view(o)[-1]['settled_service']['known'])
 def test_settled_source_counts_expose_downstream_failure(self):
  c=Controller(POLICY);o=obs(20)
  for r in o['reports']:
   r['buckets']=[[1,25],[2,25],[3,25]]
   if r['node']<2:r.update(current_n=50,current_failed=0)
  o['timely_buckets']={'1':[25,3],'2':[25,2]}
  ev=c.view(o)[-1];self.assertTrue(ev['poor_settled_service'])
  self.assertEqual(ev['settled_service']['worst_timely'],.1)
 def test_version_change_discards_prechange_buckets(self):
  c=Controller(POLICY);c.version_paths[1]=INITIAL;o=obs(20)
  for r in o['reports']:
   r['buckets']=[[1,25],[2,25],[3,25]]
   if r['node']<2:r['version']=1
  self.assertFalse(c.view(o)[-1]['settled_service']['known'])
 def test_future_received_report_rejected(self):
  c=Controller(POLICY);o=obs();o['reports'][0]['received_ns']=o['time_ns']+1
  with self.assertRaises(ValueError):c.step(o)
 def test_no_unselected_objective_evaluations_and_cache_accounted(self):
  c=Controller(POLICY);a=set(range(10));d,r=c.constraint_view(a,10)
  d2,r2=c.constraint_view(a,15)
  self.assertEqual(r['unselected_objective_evaluations'],0);self.assertLess(r2['candidate_pair_freshness_checks'],r['candidate_pair_freshness_checks'])
  self.assertTrue(all(len(x)<=64 for x in d.values()))
 def test_distinct_actions_choose_different_routes(self):
  c=Controller(POLICY);o=obs();reports,fresh,active,x,event=c.view(o)
  for n in (2,3):fresh[n]['depth']=12;fresh[n]['mean_J_ns']=40_000_000
  candidates=[INITIAL,((0,4,5,9),(1,8,6,7,9)),((0,4,5,9),(1,4,5,9))]
  chosen=[search_operator(a,candidates,fresh,active,c.points,c.current,{'known':False})[0] for a in range(4)]
  self.assertGreater(len(set(chosen)),1)
 def test_unselected_rewards_do_not_update_bandit(self):
  c=Controller(POLICY);c.constraint_view(set(range(10)),10)
  self.assertEqual(c.bandit.updates,[0,0,0,0])

if __name__=='__main__':unittest.main()

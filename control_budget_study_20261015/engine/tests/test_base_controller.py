import unittest
import numpy as np
from wsn.base_controller import Controller,LinUCB,POINTS,CATALOG


def obs(t=10,missing=False):
    rs=[]
    for n in range(9):
        if missing and n==2:continue
        rs.append(dict(node=n,stamp_ns=int((t-1)*1e9),received_ns=int((t-.5)*1e9),depth=0,n=1,mean_J_ns=5_000_000,cca=2,busy=0,failed=0,version=0,ctrl_bytes=0,buckets=[[int(t//5)-1,5]]))
    return dict(time_ns=int(t*1e9),reports=rs,timely_buckets={})


class Tests(unittest.TestCase):
    def test_selected_arm_only(self):
        m=LinUCB();x=np.ones(9);old=m.A.copy();m.update(2,x,.7)
        self.assertEqual(m.updates,[0,0,1,0]);self.assertTrue(np.array_equal(m.A[0],old[0]));self.assertTrue(np.array_equal(m.A[1],old[1]));self.assertTrue(np.array_equal(m.A[3],old[3]))
    def test_deterministic_tie(self):self.assertEqual(LinUCB().select(np.ones(9)),0)
    def test_future_report_rejected(self):
        o=obs();o['reports'][0]['received_ns']=11_000_000_000
        with self.assertRaises(ValueError):Controller('linucb').step(o)
    def test_pending_prevents_second_action(self):
        c=Controller('linucb');c.step(obs());reply,row=c.step(obs(15));self.assertEqual(reply,'-1 0 0');self.assertIsNone(row['decision'])
    def test_memory_run_isolation(self):
        a=Controller('linucb');b=Controller('linucb');a.memory.append(((0,4,5,9),(1,4,5,9)));self.assertEqual(len(b.memory),1)
    def test_catalog_simple_routes(self):
        for ps in CATALOG:
            for f,p in enumerate(ps):self.assertEqual((p[0],p[-1]),(f,9));self.assertEqual(len(p),len(set(p)));self.assertLessEqual(len(p),7)
    def test_local_repair_excludes_missing_node(self):
        c=Controller('fixed_local');reply,row=c.step(obs(missing=True));self.assertIsNotNone(row['decision']['paths']);self.assertTrue(all(2 not in p for p in row['decision']['paths']))
    def test_missing_source_feedback_no_update(self):
        c=Controller('linucb');c.step(obs());o=obs(20);o['reports']=[r for r in o['reports'] if r['node'] not in (0,1)];c.step(o);self.assertEqual(c.bandit.updates,[0,0,0,0]);self.assertIsNone(c.feedbacks[0]['reward'])
    def test_action_failure_still_charged(self):
        c=Controller('fixed_history');reply,row=c.step(obs(missing=True));self.assertIsNone(row['decision']['paths']);self.assertGreater(row['decision']['fe'],0)

    def test_profile_age_is_not_death(self):
        o=obs(20)
        for r in o['reports']:
            if r['node']==2:r['stamp_ns']=9_000_000_000;r['received_ns']=9_500_000_000
        a=Controller('linucb','full5').view(o);b=Controller('linucb','hybrid5_10').view(o)
        self.assertEqual(a[4]['observation_states']['2'],'expired');self.assertEqual(b[4]['observation_states']['2'],'fresh')
    def test_unknown_is_distinct_from_expired(self):
        v=Controller('linucb').view(obs(missing=True));self.assertEqual(v[4]['observation_states']['2'],'unknown')
    def test_paid_attempts_all_four_with_real_feedback(self):
        c=Controller('linucb_paid','hybrid5_10')
        for i,t in enumerate((10,20,30,40)):
            o=obs(t)
            if i:
                bucket=c.pending['bucket']
                for r in o['reports']:r['buckets'].append([bucket,10])
                o['timely_buckets'][str(bucket)]=[9,8]
            _,row=c.step(o);self.assertEqual(row['decision']['action'],i)
            self.assertEqual(row['decision']['selection_phase'],'paid_warmup')
        self.assertEqual(c.warmup_attempts,[0,1,2,3]);self.assertEqual(c.bandit.updates,[1,1,1,0])
        self.assertLessEqual(sum(d['fe'] for d in c.logs),96)
        self.assertLessEqual(sum(d['install_budget_bytes'] for d in c.logs),7992)
    def test_paid_does_not_train_from_unselected_rewards(self):
        c=Controller('linucb_paid');c.step(obs());self.assertEqual(c.bandit.updates,[0]*4)
        self.assertEqual(c.warmup_attempts,[0])
    def test_paid_requires_fresh_sources(self):
        c=Controller('linucb_paid');o=obs();o['reports']=[r for r in o['reports'] if r['node']!=0]
        reply,row=c.step(o);self.assertEqual(reply,'-1 0 0');self.assertEqual(c.warmup_attempts,[])
    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):Controller('linucb','unsupported')

    def test_mask_blocks_infeasible_history_even_if_optimistic(self):
        c=Controller('linucb_mask');c.bandit.b[1]=100
        _,row=c.step(obs(missing=True));self.assertFalse(row['constraints']['available'][1]);self.assertNotEqual(row['decision']['action'],1);self.assertIsNotNone(row['decision']['paths'])
    def test_mask_no_arm_does_not_open_feedback_window(self):
        c=Controller('linucb_mask');o=obs();o['reports']=[r for r in o['reports'] if r['node']!=0]
        reply,row=c.step(o);self.assertEqual(reply,'-1 0 0');self.assertEqual(row['rejection'],'all_arms_infeasible');self.assertIsNone(c.pending);self.assertGreater(row['constraints']['candidate_pair_freshness_checks'],0)
    def test_mask_never_calls_objective_for_unchosen_arms(self):
        c=Controller('linucb_mask')
        def forbidden(*args):raise AssertionError('objective called by constraint check')
        c.score=forbidden;domains,row=c.constraint_view(set(range(10)),10_000_000_000)
        self.assertEqual(row['unselected_objective_evaluations'],0);self.assertEqual(row['available'],[True]*4);self.assertGreater(row['candidate_pair_freshness_checks'],0)
    def test_mask_can_escalate_when_local_and_memory_impossible(self):
        c=Controller('linucb_mask');o=obs();o['reports']=[r for r in o['reports'] if r['node'] in (0,1,4,5)]
        _,row=c.step(o);self.assertEqual(row['constraints']['available'],[False,False,True,True]);self.assertEqual(row['decision']['action'],2)
    def test_event_exploration_does_not_force_stable_actions(self):
        c=Controller('linucb_event_mask');_,r=c.step(obs());self.assertEqual(r['decision']['selection_phase'],'event_policy')
        reply,r=c.step(obs(20));self.assertEqual(reply,'-1 0 0');self.assertEqual(c.event_attempts,[])
    def test_event_exploration_requires_actual_observed_event(self):
        c=Controller('linucb_event_mask');c.step(obs());c.step(obs(20));o=obs(30)
        for r in o['reports']:r['cca']=5;r['busy']=4
        _,r=c.step(o);self.assertEqual(r['decision']['selection_phase'],'event_exploration');self.assertGreater(r['event']['busy'],.35)
    def test_event_budget_and_unique_attempts(self):
        c=Controller('linucb_event_mask')
        for t in range(10,91,10):
            o=obs(t)
            for r in o['reports']:r['cca']=5;r['busy']=4
            if c.pending:
                b=c.pending['bucket']
                for r in o['reports']:r['buckets'].append([b,10])
                o['timely_buckets'][str(b)]=[8,7]
            c.step(o)
        attempts=[d for d in c.logs if d['selection_phase']=='event_exploration']
        self.assertEqual(len(attempts),4);self.assertEqual(len(set(d['action'] for d in attempts)),4)
        self.assertLessEqual(sum(d['fe'] for d in attempts),96);self.assertLessEqual(sum(d['install_budget_bytes'] for d in attempts),7992)
    def test_period_tag_freshness_only_uses_reported_information(self):
        o=obs(20)
        for r in o['reports']:
            if r['node']==2:r['stamp_ns']=9_000_000_000;r['received_ns']=9_500_000_000;r['period_s']=10
        self.assertEqual(Controller('linucb_mask','path_priority').view(o)[4]['observation_states']['2'],'fresh')
        for r in o['reports']:
            if r['node']==2:r['period_s']=5
        self.assertEqual(Controller('linucb_mask','path_priority').view(o)[4]['observation_states']['2'],'expired')
        self.assertEqual(Controller('linucb_mask','path_priority16').view(o)[4]['observation_states']['2'],'fresh')

if __name__=='__main__':unittest.main()

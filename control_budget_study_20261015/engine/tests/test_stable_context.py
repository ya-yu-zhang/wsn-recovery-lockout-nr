import copy,unittest
from wsn.controller import Controller
from test_base_controller import obs

POLICY='linucb_event_scalar4_failure_current_ops_ctx6_noop_cache20_retry_freshfixed_mask'

def settled():
    o=obs(20)
    for r in o['reports']:
        r['buckets']=[[1,25],[2,25],[3,25]]
        if r['node']<2:r['depth']=8
    o['timely_buckets']={'1':[25,3],'2':[25,2]}
    return o

class StableContextTests(unittest.TestCase):
    def test_queue_keeps_meaning_when_service_becomes_unknown(self):
        known=settled();unknown=copy.deepcopy(known)
        for r in unknown['reports']:r['buckets']=[]
        x=Controller(POLICY).view(known)[3];y=Controller(POLICY).view(unknown)[3]
        self.assertEqual(x[:4],y[:4]);self.assertEqual(x[3],.5)
        self.assertAlmostEqual(x[4],.9);self.assertEqual(x[5],0.)
        self.assertEqual(y[4:], [0.,1.])
    def test_known_perfect_service_is_distinct_from_unknown(self):
        o=settled();o['timely_buckets']={'1':[25,25],'2':[25,25]}
        self.assertEqual(Controller(POLICY).view(o)[3][4:],[0.,0.])
        for r in o['reports']:r['buckets']=[]
        self.assertEqual(Controller(POLICY).view(o)[3][4:],[0.,1.])
    def test_selected_feedback_updates_six_dimensional_model(self):
        c=Controller(POLICY);o=settled();_,row=c.step(o)
        self.assertEqual(len(row['decision']['context']),6)
        self.assertEqual(c.bandit.A.shape,(4,6,6))
        c.bandit.update(row['decision']['action'],row['decision']['context'],.5)
        self.assertEqual(sum(c.bandit.updates),1)
    def test_legacy_model_retains_four_dimensional_behavior(self):
        c=Controller(POLICY.replace('ctx6','low4'))
        self.assertEqual(c.bandit.A.shape,(4,4,4))
        self.assertAlmostEqual(c.view(settled())[3][3],.9)
    def test_projection_conflict_rejected(self):
        with self.assertRaises(ValueError):Controller(POLICY.replace('ctx6','ctx6_low4'))
    def test_freshness_is_independent_of_report_schedule(self):
        for profile in ('hybrid5_10','lease10_20'):
            fixed=Controller(POLICY,profile)
            scaled=Controller(POLICY.replace('freshfixed','freshscaled'),profile)
            self.assertEqual(fixed.fresh_limit(2,{'period_s':20}),16_000_000_000)
            self.assertEqual(scaled.fresh_limit(2,{'period_s':20}),32_000_000_000)
            self.assertEqual(fixed.fresh_limit(0,{'period_s':20}),8_000_000_000)
    def test_invalid_freshness_config_rejected(self):
        with self.assertRaises(ValueError):Controller(POLICY.replace('freshfixed','freshfixed_freshscaled'))
        c=Controller(POLICY.replace('freshfixed','freshscaled'))
        with self.assertRaises(ValueError):c.fresh_limit(2,{'period_s':-1})

if __name__=='__main__':unittest.main()

import unittest,math
from wsn.controller import Controller
from wsn.mechanism_controller import hop_reference
from wsn.topology import geometry
from wsn.base_controller import catalog_for
BASE='force0_scalar4_failure_current_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_observable_installexit_reviewmechanism_scoreonly_ctx6_noop_cache20_retry_freshfixed_mask'
class ReviewMechanismTests(unittest.TestCase):
    def test_install_deadline_is_only_changed_treatment(self):
        a=Controller(BASE);b=Controller(BASE.replace('_scoreonly_','_install15_scoreonly_'))
        self.assertEqual((a.install_exit_ns,b.install_exit_ns),(10_000_000_000,15_000_000_000))
        self.assertEqual((a.retry_limit,b.retry_limit),(1,1));self.assertFalse(a.is_bandit);self.assertFalse(b.is_bandit)
    def test_no_exposure_in_fixed_controls(self):
        for n in range(4):
            c=Controller(BASE.replace('force0','force'+str(n)));self.assertEqual(c.exploration_cap,0);self.assertFalse(c.is_bandit)
    def test_hop_tie_is_deterministic(self):
        a=((0,2,9),(1,3,9));b=((0,4,9),(1,5,9));p,rows,meta=hop_reference([b,a],a,{'known':False})
        self.assertEqual(p,a);self.assertEqual(len(rows),2);self.assertEqual(meta['mode'],'geometry_hop_reference')
    def test_hop_uses_total_hops(self):
        a=((0,2,3,9),(1,2,3,9));b=((0,4,9),(1,5,9));self.assertEqual(hop_reference([a,b],a,{'known':False})[0],b)
    def test_hop_poor_service_uses_same_alternative_rule(self):
        a=((0,2,9),(1,3,9));b=((0,4,5,9),(1,4,5,9));self.assertEqual(hop_reference([a,b],a,{'known':True,'worst_timely':.7})[0],b)
    def test_empty_pool(self):self.assertIsNone(hop_reference([],None,{'known':False})[0])
    def test_review_layouts_are_deterministic_and_valid(self):
        for seed in range(1031301,1031305):
            g=geometry('review_'+str(seed));self.assertEqual(g,geometry('review_'+str(seed)));self.assertEqual(set(g),set(range(10)))
            for a,b in [(0,2),(1,2),(2,3),(3,9)]:self.assertLessEqual(math.dist(g[a],g[b]),55)
            self.assertTrue(catalog_for(tuple(sorted(g.items()))))
    def test_unregistered_layout_rejected(self):
        with self.assertRaises(ValueError):geometry('review_1031309')
if __name__=='__main__':unittest.main()

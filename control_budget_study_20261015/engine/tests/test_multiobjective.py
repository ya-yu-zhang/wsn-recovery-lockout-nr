import unittest
from unittest.mock import patch
from wsn.multiobjective import dominates,frontier,hypervolume,objectives,search
from wsn.base_controller import Controller,POINTS,INITIAL
from test_base_controller import obs

class MultiobjectiveTests(unittest.TestCase):
    def test_strict_dominance(self):
        self.assertTrue(dominates((.1,.2),(.1,.3)));self.assertFalse(dominates((.1,.2),(.1,.2)));self.assertFalse(dominates((.1,.5),(.2,.3)))
    def test_known_front_and_duplicate(self):
        rows=[dict(paths=(i,),objectives=z,score=0) for i,z in enumerate(((.1,.8,.2),(.8,.1,.2),(.9,.9,.3),(.1,.8,.2)))]
        self.assertEqual([r['paths'] for r in frontier(rows)],[(0,),(1,)])
    def test_exact_hv_union(self):
        self.assertAlmostEqual(hypervolume([(.2,.8),(.8,.2)],(1.,1.)),.28)
        self.assertAlmostEqual(hypervolume([(.2,.8,.5),(.8,.2,.5)],(1.,1.,1.)),.14)
    def test_hv_empty_and_reference_guard(self):
        self.assertEqual(hypervolume([]),0)
        with self.assertRaises(ValueError):hypervolume([(1.2,0,0)])
        with self.assertRaises(ValueError):hypervolume([(float('nan'),0,0)])
    def test_fixed_normalization_and_missing(self):
        c=Controller('linucb_mask');_,fresh,active,_,_=c.view(obs());z=objectives(INITIAL,fresh,active,POINTS)
        self.assertTrue(all(0<=v<=1 for v in z));self.assertIsNone(objectives(INITIAL,fresh,active-{2},POINTS))
        for r in fresh.values():r.update(depth=16,cca=1,busy=1,mean_J_ns=500_000_000)
        self.assertEqual(objectives(INITIAL,fresh,active,POINTS)[:2],(.5,.5))
    def test_scalar_and_pareto_tradeoff(self):
        candidates=[((0,2,9),(1,2,9)),((0,4,9),(1,4,9))]
        zs=[(.0,.8,.1),(.4,.4,.4)]
        with patch('wsn.multiobjective.objectives',side_effect=zs):a,ea,sa=search(candidates,{},set(),POINTS,'scalar')
        with patch('wsn.multiobjective.objectives',side_effect=zs):b,eb,sb=search(candidates,{},set(),POINTS,'pareto')
        self.assertEqual(a,candidates[0]);self.assertEqual(b,candidates[1]);self.assertEqual(sa['proxy_hypervolume'],sb['proxy_hypervolume']);self.assertEqual(len(sb['archive']),2)
    def test_same_pool_and_fe_all_arms(self):
        a=Controller('linucb_event_scalar4_mask');b=Controller('linucb_event_pareto4_mask');o=obs();_,fresh,active,_,_=a.view(o)
        da,_=a.constraint_view(active,o['time_ns']);db,_=b.constraint_view(active,o['time_ns']);self.assertEqual(da,db)
        for arm,limit in enumerate((8,8,16,64)):
            _,ea,_=search(da[arm],fresh,active,POINTS,'scalar');_,eb,_=search(db[arm],fresh,active,POINTS,'pareto')
            self.assertEqual(len(ea),len(eb));self.assertLessEqual(len(ea),limit)
    def test_cap_budget_and_missing_does_not_refund(self):
        for cap in (0,2,4):
            c=Controller(f'linucb_event_pareto{cap}_mask')
            for t in range(10,91,10):
                o=obs(t)
                for r in o['reports']:r.update(cca=5,busy=4)
                c.step(o)
            ds=[d for d in c.logs if d['selection_phase']=='event_exploration']
            self.assertLessEqual(len(ds),cap);self.assertEqual(len(set(d['action'] for d in ds)),len(ds));self.assertLessEqual(sum(d['fe'] for d in ds),96)
            self.assertEqual(sum(c.bandit.updates),0)
    def test_only_selected_arm_objective_evaluation(self):
        c=Controller('linucb_event_pareto4_mask')
        with patch('wsn.multiobjective.objectives',wraps=objectives) as f:
            _,row=c.step(obs());self.assertEqual(f.call_count,row['decision']['fe']);self.assertEqual(row['constraints']['unselected_objective_evaluations'],0)

if __name__=='__main__':unittest.main()

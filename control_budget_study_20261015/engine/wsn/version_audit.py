"""Independent event-order reconstruction; does not call the online collector."""
from collections import defaultdict, deque


def reconstruct(messages, jobs, extended,source_only=False,epoch_certificate=False):
    native = {tuple(map(int, r[:3])): r for r in jobs if r[1] < 2}
    generated = {}
    versions = {0: 0, 1: 0}
    installed_ns={0:0,1:0}
    paths = {0: [0, 2, 3, 9], 1: [1, 2, 3, 9]}
    history = defaultdict(deque)
    terminal = set()
    reports = {}
    old_completions = 0
    simultaneous = 0
    last_time = -1
    for message in messages:
        now = message['time_ns']
        assert now >= last_time, 'nonmonotonic protocol order'
        last_time = now
        kind = message['kind']
        if kind == 'install_applied':
            source = message['source']
            assert message['version'] > versions[source]
            versions[source] = message['version']
            installed_ns[source]=now
            paths[source] = message['path']
        elif kind == 'generated':
            key = message['flow'], message['sequence']
            assert key not in generated
            assert message['version'] == versions[key[0]]
            assert message['path'] == paths[key[0]]
            generated[key] = message
        elif kind == 'mac_job_completed':
            key = message['node'], message['flow'], message['sequence']
            assert key in native and key not in terminal
            row = native[key]
            gen = generated[key[1], key[2]]
            assert message['generation_version'] == gen['version']
            assert message['generated_ns'] == gen['time_ns'] == int(row[3])
            assert now == int(row[4] + row[5]) and message['status'] == int(row[8])
            terminal.add(key)
            history[key[0]].append((now, row, gen['version']))
            if key[0] == key[1] and gen['version'] != versions[key[0]]:
                old_completions += 1
        elif kind == 'report_generated':
            report = message['report']
            node = report['node']
            assert report['stamp_ns'] == now
            past = history[node]
            while past and past[0][0] < now - 20_000_000_000:
                past.popleft()
            simultaneous += sum(end == now for end, _, _ in past)
            expected = dict(n=len(past), mean_J_ns=sum(int(r[5]) for _, r, _ in past)//len(past) if past else 0,
                            cca=sum(int(r[10]) for _, r, _ in past),
                            busy=sum(int(r[11]) for _, r, _ in past),
                            failed=sum(r[8] != 0 for _, r, _ in past))
            assert {k: report[k] for k in expected} == expected
            if node < 2:
                assert report['version'] == versions[node]
                current = [r for _, r, version in past if version == versions[node] and r[1] == node]
            else:
                current = []
            if extended and (not source_only or node<2):
                assert report['current_n'] == len(current)
                assert report['current_failed'] == sum(r[8] != 0 for r in current)
            else:
                assert 'current_n' not in report and 'current_failed' not in report
            if epoch_certificate and node<2:
                first=(installed_ns[node]+4_999_999_999)//5_000_000_000
                assert report['epoch_first_bucket']==first
                assert report['buckets'][0]==[2**32-1,first]
                for b,n in report['buckets'][1:]:
                    expected=sum(g['flow']==node and g['time_ns']//5_000_000_000==b for g in generated.values()) if b!=2**32-1 else 0
                    assert n==expected,'incorrect closed generation bucket'
            reports[node, now] = report
    assert terminal == set(native), 'terminal metadata does not cover all application jobs'
    return reports, dict(terminal_application_jobs=len(terminal),
                         old_version_source_completions=old_completions,
                         coincident_completions_in_reports=simultaneous,
                         report_snapshots=len(reports),
                         version_counts_independently_reconstructed=True)

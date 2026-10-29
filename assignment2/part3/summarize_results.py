"""Reproducible Part 3 tables and compact report figures from successful runs."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ALGORITHMS = ('cubic', 'reno', 'bbr')
COLORS = ('#2878b5', '#cf5c26', '#258d65')
METRICS = (('snd_cwnd', 'Window (segments)'), ('rtt_ms', 'RTT (ms)'),
           ('retrans_interval', 'Retransmissions / interval'), ('goodput_mbps', 'Goodput (Mbps)'))


def load_successful(results_dir):
    root = Path(results_dir)
    runs = pd.read_csv(root / 'part3_runs.csv')
    samples = pd.read_csv(root / 'part3_samples.csv')
    selected = pd.read_csv(root / 'part3_destinations.csv')
    good = runs[runs.status.eq('ok')].merge(selected[['host', 'port']], on=['host', 'port'])
    if not good.requested_algorithm.eq(good.actual_algorithm).all():
        raise ValueError('A successful run used an unexpected algorithm')
    data = samples.merge(good[['run_id', 'actual_algorithm']], on='run_id',
                         suffixes=('', '_verified'), validate='many_to_one')
    if data.empty:
        raise ValueError('No successful selected-path samples to summarize')
    if not data.actual_algorithm.eq(data.actual_algorithm_verified).all():
        raise ValueError('Sample/run algorithm mismatch')
    data['goodput_mbps'] = data.goodput_bps / 1e6
    data['rtt_ms'] = data.rtt_us / 1000
    return data


def escape(value):
    return str(value).replace('_', r'\_').replace('&', r'\&').replace('%', r'\%')


def write_tables(data, root):
    keys = ['site', 'host', 'port', 'actual_algorithm']
    summary = data.groupby(keys).agg(
        samples=('goodput_mbps', 'count'), repetitions=('rep', 'nunique'),
        minimum=('goodput_mbps', 'min'), median=('goodput_mbps', 'median'),
        mean=('goodput_mbps', 'mean'), p95=('goodput_mbps', lambda x: x.quantile(.95)),
        mean_rtt_ms=('rtt_ms', 'mean')).reset_index()
    summary.to_csv(root / 'part3_summary.csv', index=False)
    lines = [r'\begin{tabular}{llrrrrr}', r'\hline',
             r'Destination & Algorithm & Runs & Min & Median & Mean & P95 \\', r'\hline']
    for row in summary.itertuples():
        lines.append(f'{escape(row.site)} & {row.actual_algorithm.upper()} & {row.repetitions} & '
                     f'{row.minimum:.2f} & {row.median:.2f} & {row.mean:.2f} & {row.p95:.2f} ' + r'\\')
    lines += [r'\hline', r'\end{tabular}']
    (root / 'part3_summary.tex').write_text('\n'.join(lines)+'\n')
    per_run = data.groupby(keys + ['rep', 'run_id']).agg(
        mean_mbps=('goodput_mbps', 'mean'), mean_rtt_ms=('rtt_ms', 'mean'),
        min_rtt_ms=('rtt_ms', 'min'), mean_cwnd=('snd_cwnd', 'mean'),
        retransmissions=('retrans_interval', 'sum')).reset_index()
    per_run.to_csv(root / 'part3_per_run.csv', index=False)
    # Only compare repetitions where all three algorithms completed on that path.
    complete = per_run.groupby(['host', 'port', 'rep']).actual_algorithm.nunique()
    complete = complete[complete.eq(3)].reset_index()[['host', 'port', 'rep']]
    paired = per_run.merge(complete, on=['host', 'port', 'rep'])
    paired.to_csv(root / 'part3_matched_runs.csv', index=False)
    means = paired.groupby(['site', 'actual_algorithm'])[['mean_mbps', 'mean_rtt_ms']].mean()
    lines = [r'\begin{tabular}{lrrrrrr}', r'\hline',
             r'& \multicolumn{3}{c}{Goodput (Mbps)} & \multicolumn{3}{c}{RTT (ms)} \\',
             r'Destination & CUBIC & Reno & BBR & CUBIC & Reno & BBR \\', r'\hline']
    for site in sorted(paired.site.unique()):
        vals = [means.loc[(site, a), m] for m in ('mean_mbps','mean_rtt_ms') for a in ALGORITHMS]
        lines.append(escape(site)+' & '+' & '.join(f'{v:.2f}' for v in vals)+r' \\')
    lines += [r'\hline', r'\end{tabular}']
    (root / 'part3_matched_summary.tex').write_text('\n'.join(lines)+'\n')
    return summary


def style(ax):
    ax.grid(alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)


def compact_plots(data, destination, plots_dir):
    chosen = data[data.host.eq(destination[0]) & data.port.eq(destination[1])]
    if set(chosen.actual_algorithm) != set(ALGORITHMS):
        raise ValueError('Representative destination lacks an algorithm')
    plt.rcParams.update({'font.size': 10})
    for scatter, filename in ((False, 'part3_timeseries.pdf'), (True, 'part3_scatter.pdf')):
        rows = METRICS[:3] if scatter else METRICS
        fig, axes = plt.subplots(len(rows), 3, figsize=(13, 8.3), layout='constrained')
        for col, algorithm in enumerate(ALGORITHMS):
            subset = chosen[chosen.actual_algorithm.eq(algorithm)]
            for row, (metric, label) in enumerate(rows):
                ax = axes[row, col]
                for index, (rep, values) in enumerate(subset.groupby('rep')):
                    values = values.sort_values('elapsed_s')
                    if scatter:
                        ax.scatter(values[metric], values.goodput_mbps, s=12, alpha=.55,
                                   color=COLORS[index % 3], label=f'Run {rep}')
                    else:
                        ax.plot(values.elapsed_s, values[metric], lw=1.1, alpha=.8,
                                color=COLORS[index % 3], label=f'Run {rep}')
                top = max(1., chosen[metric].max()*1.05)
                if scatter:
                    ax.set(xlabel=label, ylabel='Goodput (Mbps)', xlim=(0, top),
                           ylim=(0, max(1., chosen.goodput_mbps.max()*1.05)))
                else:
                    ax.set(xlabel='Elapsed time (s)', ylabel=label,
                           xlim=(0, chosen.elapsed_s.max()*1.02), ylim=(0, top))
                if row == 0:
                    ax.set_title(algorithm.upper(), fontweight='bold')
                    ax.legend(frameon=False, fontsize=8, loc='best')
                style(ax)
        fig.suptitle(f'{destination[0]}:{destination[1]} | identical scales across algorithms', fontsize=12)
        fig.savefig(plots_dir / filename)
        plt.close(fig)
    groups = list(data.groupby(['site', 'host', 'port']))
    nrows = (len(groups) + 1) // 2
    fig, axes = plt.subplots(nrows, 2, figsize=(11, 2.4*nrows),
                             squeeze=False, layout='constrained')
    for ax, ((site, host, port), subset) in zip(axes.flat, groups):
        for algorithm, color in zip(ALGORITHMS, COLORS):
            for i, (_, run) in enumerate(subset[subset.actual_algorithm.eq(algorithm)].groupby('run_id')):
                run = run.sort_values('elapsed_s')
                ax.plot(run.elapsed_s, run.goodput_mbps, lw=.9, alpha=.65,
                        color=color, label=algorithm.upper() if i == 0 else None)
        ax.set_title(f'{site} | {host}:{port}', fontsize=8)
        ax.set(xlabel='Elapsed time (s)', ylabel='Goodput (Mbps)', ylim=(0, None))
        style(ax)
    for ax in list(axes.flat)[len(groups):]:
        ax.set_visible(False)
    axes[0,0].legend(frameon=False, fontsize=8)
    fig.suptitle('All successful selected-path runs; separate vertical scale per destination')
    fig.savefig(plots_dir / 'part3_all_goodput.pdf')
    plt.close(fig)


def make_report_outputs(results_dir, plots_dir, destination):
    root, plots = Path(results_dir), Path(plots_dir)
    plots.mkdir(parents=True, exist_ok=True)
    data = load_successful(root)
    summary = write_tables(data, root)
    compact_plots(data, destination, plots)
    print(f'Part 3 summary: {len(data)} samples, {len(summary)} destination/algorithm rows')

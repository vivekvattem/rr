"""Build the submission report from existing aggregate model outputs."""
from pathlib import Path
import html

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from pdf_branding import draw_watermark

rl_config.invariant = 1
NAVY = colors.HexColor('#101c40')
PINK = colors.HexColor('#db2877')
MUTED = colors.HexColor('#546176')
PALE = colors.HexColor('#f5f3f6')


def build_report(root, rankings, robustness, audit, evidence, eligible_counts):
    """Preserve model results while presenting only the Round 1 methodology."""
    root = Path(root)
    styles = getSampleStyleSheet()
    for name, settings in {
        'TitleRR': dict(fontName='Helvetica-Bold', fontSize=25, leading=29,
                        spaceAfter=12),
        'SubRR': dict(fontName='Helvetica-Bold', fontSize=12, leading=15,
                      spaceBefore=10, spaceAfter=6, keepWithNext=True),
        'BodyRR': dict(fontName='Helvetica', fontSize=9.2, leading=12.4,
                       spaceAfter=7),
        'SmallRR': dict(fontName='Helvetica', fontSize=8, leading=10.7,
                        spaceAfter=6, textColor=MUTED),
        'CellRR': dict(fontName='Helvetica', fontSize=8, leading=10.3),
        'HeadRR': dict(fontName='Helvetica-Bold', fontSize=7.8, leading=10,
                       textColor=colors.white),
    }.items():
        settings.setdefault('textColor', NAVY)
        styles.add(ParagraphStyle(name=name, **settings))

    story = []

    def esc(value):
        return html.escape(str(value))

    def para(text, style='BodyRR'):
        story.append(Paragraph(text, styles[style]))

    def title(section, text):
        para(section.upper(), 'SmallRR')
        para(text, 'TitleRR')

    def sub(text):
        para(text, 'SubRR')

    def table(headers, rows, widths):
        cells = [[Paragraph(esc(v), styles['HeadRR']) for v in headers]]
        cells += [[Paragraph(esc(v), styles['CellRR']) for v in row] for row in rows]
        result = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
        result.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, -1), (-1, -1), 0.6, colors.HexColor('#dddee6')),
        ]))
        story.extend([result, Spacer(1, 7)])

    def new_page():
        story.append(PageBreak())

    included = audit['included']
    title('SupeRR Selector Season 2 | Round 1', 'Reliable Players Under Pressure')
    para('METHODOLOGY REPORT AND FINAL RANKINGS', 'SmallRR')
    sub('Objective')
    para('Measure how batters and bowlers perform in demanding match situations, '
         'compare that performance with their usual levels, and identify players '
         'who combine strong pressure performance with evidence across matches.')
    sub('Study at a glance')
    table(['Component', 'Scope'], [
        ['Data', 'Supplied IPL and T20I delivery records from 2022 onwards'],
        ['Analysis sample', f"{included['deliveries']:,} delivery records across "
                            f"{included['matches']} matches"],
        ['Eligible players', f"{eligible_counts['batters']} batters and {eligible_counts['bowlers']} bowlers under the declared sample rules"],
        ['Final output', '10 ranked batters and 10 ranked bowlers'],
        ['Reliability checks', '400 match bootstrap samples and five alternative model specifications'],
    ], [126, 365])
    sub('Analytical approach')
    for text in [
        '<b>1. Reconstruct the situation.</b> Calculate the score, wickets and legal balls remaining '
        'using only deliveries before the current ball.',
        '<b>2. Identify pressure.</b> Combine urgency, wicket depletion and scoring difficulty. '
        'Apply the same situation label to the batter and bowler.',
        '<b>3. Measure performance.</b> Adjust scoring and dismissals for match context, then '
        'compare each player with their own ordinary-performance baseline.',
        '<b>4. Rank and validate.</b> Combine pressure quality and improvement over the personal '
        'baseline, shrink small samples and penalise uncertainty. Test sensitivity to '
        'the pressure threshold, competition coverage and utility weights.',
    ]:
        para(text)
    sub('Main findings')
    para(f"<b>{esc(rankings['batters'][0]['name'])}</b> leads the batting rankings with a score of "
         f"<b>{rankings['batters'][0]['pressure_score']:.2f}</b>. "
         f"<b>{esc(rankings['bowlers'][0]['name'])}</b> leads bowling with "
         f"<b>{rankings['bowlers'][0]['pressure_score']:.2f}</b>. The IPL-only leaders are "
         'Shreyas Iyer and Sunil Narine. Competition coverage and sample eligibility '
         'therefore materially affect the results.')
    para('The rankings describe historical performance under the declared model. '
         'Confidence intervals overlap, especially near the top-10 boundary; '
         'small score differences should be interpreted cautiously.')

    for category in ['batters', 'bowlers']:
        new_page()
        title('Final rankings | IPL and T20I combined', 'Top 10 '+category)
        para('Players are ordered by the final score. <b>Pressure</b> is the adjusted pressure '
             'index; <b>Usual</b> is the player\'s ordinary index adjusted to their pressure-phase '
             'mix; <b>Lift</b> is Pressure minus Usual. N and M are pressure opportunities and '
             'pressure matches. The interval describes uncertainty in the score.')
        table(['#', 'Player', 'Score', 'Pressure', 'Usual', 'Lift', 'N', 'M', '95% interval'], [
            [x['rank'], x['name'], f"{x['pressure_score']:.2f}",
             f"{x['absolute_pressure_index']:.2f}", f"{x['own_ordinary_index']:.2f}",
             f"{x['change']:+.2f}", x['pressure_deliveries'], x['pressure_matches'],
             f"{x['ci_low']:.2f}-{x['ci_high']:.2f}"] for x in rankings[category]
        ], [24, 128, 42, 48, 48, 40, 38, 32, 91])
        sub('Evidence supporting the ordering')
        if category == 'batters':
            para('Suryakumar Yadav combines high scoring output with a low dismissal rate. '
                 'Dinesh Karthik ranks second overall. Shreyas Iyer ranks third overall '
                 'and first in the IPL-only analysis. '
                 'Tim David and Heinrich Klaasen remain highly ranked despite slightly negative '
                 'lift because their absolute pressure performance is strong. Mark Chapman\'s '
                 'pressure evidence comes entirely from T20Is. Karthik\'s retirement does '
                 'not affect the evaluation of his historical performance.')
            headers = ['Player', 'Runs / 100', 'Peer runs / 100', 'Dismissal %', 'Peer dismissal %', 'Positive matches']
        else:
            para('Mustafizur Rahman leads on pressure quality and improvement over his own baseline. '
                 'Rashid Khan\'s 685 pressure attempts across 69 matches provide a broader sample. '
                 'Lockie Ferguson\'s combined result depends more heavily on T20Is than IPL. '
                 'Sunil Narine leads the IPL-only analysis. Varun Chakravarthy\'s broad sample '
                 'supports his position above Matheesha Pathirana after the uncertainty penalty. '
                 'Taskin Ahmed has no IPL pressure observations in the supplied data.')
            headers = ['Player', 'Economy', 'Peer economy', 'Wicket %', 'Peer wicket %', 'Positive matches']
        sub('Observed pressure outcomes')
        table(headers, [
            [x['name'], f"{x['pressure_run_rate']:.1f}", f"{x['peer_run_rate']:.1f}",
             f"{x['dismissal_pct']:.1f}%", f"{x['peer_wicket_pct']:.1f}%",
             f"{x['positive_match_pct']:.0f}%"] for x in rankings[category]
        ], [145, 65, 72, 66, 76, 67])
        if category == 'batters':
            para('Runs are reported per 100 non-wide opportunities, including no-balls. '
                 'Dismissal percentage counts actual striker dismissals per opportunity. '
                 'These opportunities differ from official balls faced.', 'SmallRR')
        else:
            para('Economy is charged runs per six legal balls. Wicket percentage is '
                 'bowler-credited wickets per attempted delivery, including illegal deliveries. '
                 'Byes and leg-byes are excluded from bowler charges.', 'SmallRR')
        para('Peer rates are ordinary-performance expectations matched to the observed pressure '
             'contexts. The positive-match percentage counts pressure matches with average '
             'utility above the ordinary peer expectation. Intervals use whole-match resampling '
             'with fixed peer references. Indices and lift are rounded independently after calculation.', 'SmallRR')

    new_page()
    title('Methodology | Pressure definition', 'Define pressure before the ball')
    para('Sort deliveries by match, innings and delivery sequence. Reconstruct each state '
         'from preceding records. A delivery-sequence number includes illegal deliveries '
         'and must not be treated as a legal-ball count. Both sides receive the same '
         'pressure label; batting and bowling outcomes are evaluated separately.')
    para('<b>Notation:</b> L = legal balls remaining; W = wickets lost; '
         'U = 1 - L/120; D = min(W/7, 1). Phases are powerplay (0-35 legal balls used), '
         'middle (36-89) and death (90-119). clip(x, a, b) limits x to the range [a, b].')
    sub('Expected scoring rate')
    para('Estimate scoring par b separately for IPL and T20I in each phase, using strictly '
         'earlier calendar years. Add 300 legal-ball pseudo-observations at declared prior '
         'rates of 1.25, 1.25 and 1.65 runs per ball for powerplay, middle and death. '
         'These priors supply the entire reference for 2022. E is cumulative phase par '
         'through the legal balls already used.')
    para('<b>Resource-adjusted rate: b* = b × clip(1 - 0.06 × max(W - 2, 0), 0.58, 1)</b>')
    sub('First innings: scoring deficit and resource pressure')
    para('<b>F = clip((E - score)/(15 + 0.20 × E), 0, 1)</b><br/>'
         '<b>P1 = 0.40 × U + 0.35 × F + 0.25 × D</b>')
    para('Late overs alone contribute at most 0.40. To cross the pressure threshold, '
         'the innings must also trail scoring par or have lost sufficient wickets. '
         'This captures the difficulty of building a total with limited time and resources.')
    sub('Second innings: required scoring rate in a live chase')
    para('<b>R = (runs required / L) / b*</b><br/>'
         '<b>P2 = 0.45 × min(R/1.4, 1) + 0.35 × U + 0.20 × D</b><br/>'
         'Apply P2 only when 0.65 &lt;= R &lt;= 1.80; otherwise set P2 to zero. '
         'The gate excludes very easy chases and exceptionally implausible demands. '
         'It is a declared heuristic rather than a calibrated win probability.')
    para('<b>Classification:</b> P &gt;= 0.62 indicates high pressure. All other included '
         'deliveries form the ordinary-performance sample. The target is the first-innings '
         'total plus one; revised and DLS matches are excluded.')
    sub('Illustrative contrasts')
    table(['State after 16 overs', 'Calculation using prior rates', 'Class'], [
        ['Chasing 181; 130/4', '51 off 24; b* = 1.452; R = 1.46; P = 0.84', 'High'],
        ['Chasing 181; 160/1', '21 off 24; R = 0.53; outside the live-chase gate', 'Ordinary'],
        ['Batting first; 105/5', 'E = 122.4; F = 0.44; P = 0.65', 'High'],
        ['Batting first; 150/2', 'E = 122.4; F = 0; P = 0.39', 'Ordinary'],
    ], [169, 255, 67])
    para('These examples explain the definition; they are illustrative states rather than '
         'observations selected from the dataset.', 'SmallRR')

    new_page()
    title('Methodology | Performance measurement', 'Measure quality and personal lift')
    sub('Contextual ordinary-performance references')
    para('Fit batting and bowling references separately using ordinary deliveries. '
         'Batting-role bands are positions 1-3, 4-6 and 7+; bowling roles are pace and spin. '
         'The hierarchy is phase × role (300 prior observations at 1.35 runs and 0.055 '
         'wickets per opportunity), then competition type × season × innings × phase × '
         'role × wicket-loss band (150 observations towards the parent), then the same '
         'context with opposition team (250 observations towards the parent). '
         'Wicket-loss bands are 0-2, 3-5 and 6+. Remove the entire current match from '
         'every peer level. Competition type means IPL or T20I; split-year season labels are preserved.')
    para('These references use historical ordinary outcomes across the study window. '
         'They are retrospective context adjustments. Only pressure classification and '
         'scoring par are restricted to pre-delivery information and earlier years. '
         'Sparse venue effects are not fitted.')
    sub('Delivery utility')
    para('<b>Batter u = 0.65 × (bat runs - peer runs)/1.70<br/>'
         '- 0.35 × (striker out - peer out)/0.22</b><br/>'
         '<b>Bowler u = 0.60 × (peer charged runs - charged runs)/1.70<br/>'
         '+ 0.40 × (credited wicket - peer wicket)/0.22</b>')
    para('The run and wicket scales, 1.70 and 0.22, are declared normalisation constants. '
         'Batter utility rewards scoring and dismissal avoidance; bowler utility rewards '
         'run prevention and credited wickets. Caught, bowled, LBW, stumped and hit-wicket '
         'dismissals credit the bowler. Run-outs, retired outs and obstruction do not. '
         'Only an actual dismissal of the striker is charged to the batter.')
    sub('Shrinkage and final score')
    para('Within each phase, shrink the player\'s ordinary residual towards zero: '
         '<b>O_phase = sum(u_ordinary)/(n_ordinary + 100)</b>. '
         'O is the mean of these phase estimates weighted by the player\'s pressure exposure. '
         'Shrink pressure quality towards the contextual peer reference using '
         '<b>A = sum(u_pressure)/(n_pressure + 150)</b>. The distinct priors reduce '
         'the influence of small ordinary and pressure samples.')
    para('<b>Pressure index = 50 + 20 × A</b><br/>'
         '<b>Usual index = 50 + 20 × O; Lift = 20 × (A - O)</b><br/>'
         '<b>Score = 50 + 20 × [0.80 × A + 0.20 × (A - O)] - 0.35 × SE</b>')
    para('SE is the match-bootstrap standard deviation of the score before the penalty. '
         'The 80:20 weighting favours strong absolute pressure performance while '
         'rewarding improvement over the player\'s usual level. The index is not a '
         'percentage; 50 is the contextual peer reference before the uncertainty penalty.')
    sub('Sample rules and candidate eligibility')
    para('Batters require at least <b>120 pressure opportunities, 12 pressure matches and '
         '200 ordinary opportunities</b>. Bowlers require <b>180 pressure attempts, '
         '15 pressure matches and 240 ordinary attempts</b>. Batting opportunities exclude '
         'wides but include no-balls; bowling attempts include illegal deliveries. '
         'Economy uses legal balls. Segment estimates require 30 pressure and 30 ordinary '
         'observations across at least four pressure matches.')
    para('All supplied players who meet the sample rules are eligible, including retired '
         'players. Retirement, franchise retention and auction availability do not '
         'exclude a player from this historical study. The same eligibility policy '
         'applies to every sensitivity model. There is no minimum IPL-exposure rule '
         'for the combined rankings. These rules yield '
         f"{eligible_counts['batters']} eligible batters and {eligible_counts['bowlers']} bowlers.")

    new_page()
    title('Validation | Consistency and sensitivity', 'Test reliability across matches')
    para('Use <b>400 joint whole-match bootstrap samples</b> with seed <b>202711</b>. '
         'A sampled match receives the same multiplicity for every player and for '
         'pressure and ordinary observations. Recompute A, O and player ranks while '
         'holding peer references, priors and the eligible candidate set fixed. '
         'Report conditional 95% score intervals and the frequency of top-10 inclusion.')
    for category in rankings:
        sub(category.capitalize()+': rank under alternative specifications')
        rows = []
        for x in rankings[category]:
            ranks = [robustness[category][label]['official_ranks'].get(str(x['player_id']))
                     for label in ['Broader pressure', 'Stricter pressure', 'IPL only']]
            rows.append([f"{x['rank']}. {x['name']}", f"{100*x['top10_probability']:.0f}%",
                         *['-' if v is None else str(v) for v in ranks]])
        table(['Final order', 'Top-10 frequency', 'P >= 0.57', 'P >= 0.67', 'IPL only'],
              rows, [200, 91, 68, 68, 64])
    para('A dash indicates insufficient exposure under that specification. '
         'Changing the threshold or competition coverage changes both the context '
         'references and the eligible cohort. Retired players remain eligible under '
         'the same sample rules.', 'SmallRR')
    para('Suryakumar Yadav and Shreyas Iyer remain strong across specifications. '
         'Chapman and Rana fall below the sample rules at the stricter threshold. '
         'Mustafizur remains first under both alternative thresholds; Ferguson and '
         'Taskin fall below the stricter sample rules. IPL-only results favour '
         'Shreyas Iyer and Sunil Narine.')
    para('Changing run/wicket weights to 75/25 and 50/50 retains '
         f"{robustness['batters']['Scoring-heavy weights']['overlap']}/10 and "
         f"{robustness['batters']['Wicket-heavy weights']['overlap']}/10 batting selections, and "
         f"{robustness['bowlers']['Scoring-heavy weights']['overlap']}/10 and "
         f"{robustness['bowlers']['Wicket-heavy weights']['overlap']}/10 bowling selections. "
         'The intervals and inclusion frequencies quantify conditional stability, '
         'rather than the probability of future elite performance.')

    new_page()
    title('Worked example | Reconstructing pressure', 'From match state to pressure score')
    x = evidence['real_example']
    para(f"<b>{esc(x['home_team'])} v {esc(x['away_team'])}</b>, "
         f"{esc(x['competition'])}, {esc(x['date'])}. Before <b>{esc(x['display_delivery'])}</b>, "
         f"{esc(x['striker'])} faces {esc(x['bowler'])}. The supplied deliveries provide "
         'the pre-ball state for the calculation.')
    table(['Score', 'Target', 'Legal balls left', 'Wickets in hand', 'Required rate'], [
        [f"{x['score_before']}/{x['wickets_lost']}", x['target'], x['balls_remaining'],
         x['wickets_in_hand'], f"{x['required_rate_per_over']:.2f} per over"]
    ], [83, 68, 110, 110, 120])
    sub('Calculation before the outcome')
    para(f"The earlier-year IPL death-phase par is b = {x['base_rpb']:.4f} runs per ball. "
         f"With {x['wickets_lost']} wickets lost, the resource factor is 0.76, giving "
         f"b* = {x['resource_rpb']:.4f}. Required demand is "
         f"R = ({x['runs_required']}/{x['balls_remaining']})/{x['resource_rpb']:.4f} "
         f"= <b>{x['demand_ratio']:.4f}</b>, within the live-chase gate. "
         f"U = {x['urgency']:.4f} and D = {x['depletion']:.4f}.")
    components = x['pressure_components']
    para('<b>P = 0.45 × min(R/1.4, 1) + 0.35 × U + 0.20 × D</b><br/>'
         f"<b>= {components['demand']:.4f} + {components['urgency']:.4f} "
         f"+ {components['wicket_depletion']:.4f} = {x['pressure']:.4f}</b>")
    para(f"This exceeds the {x['threshold']:.2f} threshold. The label uses only the "
         f"state before the delivery. Shashank subsequently scored {x['ball_runs']} runs; "
         'that outcome does not influence the classification.')
    sub('Comparable pressure situations')
    para('Select IPL chases in overs 16-20 with pre-ball P &gt;= 0.62 and the same '
         'live-chase gate. Exclude wides from batting opportunities. No outcome filter '
         'is applied; targets, opponents and wickets remaining may still differ.')
    table(['Batter', 'N / M', 'Runs / outs', 'Runs / 100', 'Pressure index', 'Lift'], [
        [z['name'], f"{z['pressure_deliveries']} / {z['pressure_matches']}",
         f"{z['runs']:.0f} / {z['wickets']}", f"{z['runs_per_100_attempts']:.1f}",
         f"{z['pressure_index']:.2f}", f"{z['change']:+.2f}"]
        for z in evidence['comparable_chase_death']
    ], [133, 62, 75, 75, 90, 56])
    z = evidence['comparable_chase_death'][0]
    w = z['without_example_match']
    close = evidence['closer_resource_subset']
    para(f"Shashank's cohort index is {z['pressure_index']:.2f}, compared with his "
         f"ordinary death-phase reference of {z['own_ordinary_index']:.2f}: "
         f"lift is {z['change']:+.2f}. Rapid raw scoring therefore does not imply "
         'a large improvement over his usual level.')
    para(f"Removing the entire example match leaves {w['runs']:.0f} runs from "
         f"{w['pressure_deliveries']} opportunities in {w['pressure_matches']} matches, "
         f"with {w['wickets']} dismissal. Restricting the full cohort to 3-6 wickets "
         f"in hand leaves {close['pressure_deliveries']} opportunities in "
         f"{close['pressure_matches']} matches. This narrower sample is below the "
         '30-opportunity rule, so it is described without an adjusted-index claim.')
    para(f"Reproduction key: match_id {x['match_id']}, innings {x['innings']}, "
         f"innings_ball_num {x['innings_ball_num']}. All state inputs use preceding "
         'deliveries. This example was selected after analysis and is explanatory; '
         'it is not a held-out validation test.', 'SmallRR')

    new_page()
    title('Data preparation | Coverage and quality', 'Build a consistent analysis sample')
    para('The six supplied CSVs contain 200,999 delivery records and 883 match records. '
         'Deliveries are available for 867 matches. The date range is 22 January 2022 '
         'to 1 November 2026. Eight season labels cover 2022-2026, including split-year '
         'labels. The data is selected coverage rather than a complete census of T20 cricket.')
    table(['Competition group', 'Raw delivery records', 'Treatment'], [
        ['IPL 2022-2026', '87,687', 'Include subject to quality filters'],
        ['Selected T20Is', '106,327', 'Include subject to quality filters'],
        ['Emerging Teams Asia Cup 2024', '3,519', 'Exclude: outside IPL/T20I scope'],
        ['Asia Cup Rising Stars 2025', '3,466', 'Exclude: outside IPL/T20I scope'],
    ], [205, 100, 186])
    sub('Identity joins and delivery accounting')
    para('Use player IDs rather than names for every join and ranking. Delivery-to-match, '
         'competition, team and player-mapping joins match all 200,999 records without '
         'row multiplication. Deduplicate the 40 repeated match/team/player XI keys '
         'before using membership. Missing XI membership is recorded rather than '
         'used to discard otherwise valid deliveries.')
    para('Team runs equal batter runs plus both extras fields. Wides, overstepping '
         'no-balls and the verified no-ball-like "other" category are illegal deliveries. '
         'All 264 "other" records carry a one-run penalty. Secondary no-ball extras '
         '(83 runs) are treated as byes or leg-byes and excluded from bowler charges. '
         'Twelve non-wicket dismissal identifiers are treated as non-outs. Ambiguous '
         'extras and unresolved match states trigger whole-match exclusions.')
    sub('Sequential exclusions')
    table(['Reason', 'Records removed', 'Matches affected'], [
        [item['reason'], f"{item['deliveries']:,}", item['matches']]
        for item in audit['exclusions_sequential'] if item['deliveries']
    ], [317, 91, 83])
    removed = 200999-included['deliveries']
    para(f"The final sample contains <b>{included['deliveries']:,} records in "
         f"{included['matches']} matches</b>. The exclusions remove {removed:,} "
         f"records ({100*removed/200999:.1f}%). Each record is counted once; match "
         'counts in the exclusion table need not sum because filters can affect '
         'different innings of the same match.')
    sub('Validation boundaries')
    para('Of 794 unrevised-looking result margins checked, 791 agree with reconstructed '
         'innings. Two disagreements reveal DLS matches in result text; one has an '
         'unresolved wicket margin. All three are excluded. Core scoring and identity '
         'fields are complete. Event fields are sparse, while speed and stroke data '
         'are unsuitable for a detailed skill model. Independent scorecard totals '
         'are absent, so margin agreement is an internal consistency check.')

    new_page()
    title('Interpretation', 'Limitations and reproducibility')
    for heading, text in [
        ('Pressure is a situation model.', 'The score approximates urgency and resource stress; '
         'it does not measure psychology or estimate win probability. First-innings pressure '
         'depends on scoring par rather than a known target.'),
        ('Historical references are retrospective.', 'Ordinary-performance baselines use the '
         'study window with the current match excluded. They support historical comparisons, '
         'rather than a prospective prediction claim.'),
        ('Competition and role coverage differ.', 'IPL and T20I opponents and venues vary. '
         'Context adjustment reduces these differences but cannot remove them. No explicitly '
         'named T20 World Cup appears in the supplied competition data. Exposure rules can '
         'exclude powerplay specialists and players with limited pressure opportunities.'),
        ('Uncertainty is conditional.', 'The bootstrap holds peer references and eligibility '
         'fixed. It omits uncertainty from reference estimation and model choice. Overlapping '
         'intervals mean nearby ordinal ranks are not statistically separated tiers.'),
        ('The study describes observed roles.', 'All seasons receive equal weight. Phase '
         'weights follow each player\'s observed exposure. Injury, availability, auction price, '
         'pitch dimensions and detailed fielding effects are outside the model.'),
    ]:
        para('<b>'+heading+'</b> '+text)
    sub('Reproducibility')
    para('Inputs are ball_by_ball.csv, matches.csv, competitions.csv, teams.csv, '
         'playing_eleven.csv and competition_team_player_mapping.csv. Reconstruct '
         'pre-delivery states; apply the sequential exclusions; estimate prior-year '
         'scoring par; classify pressure; fit ordinary peer references with the current '
         'match removed; calculate A, O and score; then bootstrap and sort by score. '
         'Rebuild the contextual references for each sensitivity specification.')
    para('The implementation records input SHA-256 hashes, join counts, missing values '
         'and exclusion totals. The fixed bootstrap seed is 202711. Final ranking '
         'names, IDs and scores are generated from a single output, rankings.json, '
         'which also supplies the dropdown-entry lists. The formulas, priors, sample '
         'thresholds and opportunity definitions are specified in this report.')
    def decorate(canvas, doc):
        draw_watermark(canvas, *A4)
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(PINK)
        canvas.rect(0, height-8, width, 8, fill=1, stroke=0)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(42, 25, 'SUPERR SELECTOR SEASON 2  |  ROUND 1  |  METHODOLOGY AND RANKINGS')
        canvas.drawRightString(width-42, 25, str(doc.page))
        canvas.restoreState()

    path = root/'output/pdf/rr_methodology_rankings.pdf'
    document = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=42, rightMargin=42,
        topMargin=35, bottomMargin=43,
        title='SupeRR Selector Season 2 - Pressure Performance Methodology and Rankings',
        author='',
    )
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return path

"""Shared, output-driven auction call text for the primary PDF and optional HTML."""
def phase(ev,cat,pid,name):
 return next(x for x in ev['phase_splits'][cat] if x['player_id']==pid and x['phase']==name)

def calls(ev,status):
 p=ev['players']['2756']['pooled'];t=ev['players']['3926']['pooled'];sd=phase(ev,'batters',2756,'Death')
 a=ev['players']['3653']['ipl_only'];b=ev['players']['360']['ipl_only'];ad=phase(ev,'bowlers',3653,'Death');bd=phase(ev,'bowlers',360,'Death')
 return [
  {'player_id':2756,'player':'Shashank Singh','decision':'Conditional target','role':'Indian No. 6; enter around overs 11-15 and bat through the death.',
   'strongest_evidence':f"Pressure index {p['absolute_pressure_index']:.2f} vs own ordinary {p['own_ordinary_index']:.2f} (lift {p['change']:+.2f}); {p['pressure_deliveries']} attempts / {p['pressure_matches']} matches. Comparable Indian finisher Tewatia: {t['absolute_pressure_index']:.2f} vs {t['own_ordinary_index']:.2f} ({t['pressure_deliveries']} / {t['pressure_matches']}). All these batting pressure attempts are IPL.",
   'what_changes':f"PBKS release and official listing required. Pass if RR keeps sufficient lower-order cover or needs a pure death specialist: Shashank's IPL death lift is {sd['change']:+.2f}. Intervals overlap with Tewatia.",
   'auction_action':status['2756']['auction_action'],'fallback':'Rahul Tewatia','fallback_id':3926},
  {'player_id':3653,'player':'Avesh Khan','decision':'Backup only','role':'Indian death-overs cover; provisional overs 17 and 19. Other overs need separate matchup evidence.',
   'strongest_evidence':f"Pooled rank {ev['players']['3653']['pooled']['rank']}; IPL-only rank {a['rank']}, score {a['pressure_score']:.2f}, lift {a['change']:+.2f}; {a['pressure_deliveries']} attempts / {a['pressure_matches']} matches. Bhuvneshwar: IPL rank {b['rank']}, score {b['pressure_score']:.2f}; death index {bd['pressure_index']:.2f} vs Avesh {ad['pressure_index']:.2f}.",
   'what_changes':"LSG release and official listing required. Promote only if RR needs Indian late-over cover after retention. Prefer Bhuvneshwar if new-ball cover also matters; neither is a proven superior buy. No middle-over upgrade claim.",
   'auction_action':status['3653']['auction_action'],'fallback':'Bhuvneshwar Kumar','fallback_id':360}]

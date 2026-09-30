import pandas as pd
from src.engine import reconcile_tickets

def test_legacy_unit_and_dedupe():
    df=pd.DataFrame([
        {"ticket_id":"T1","source_system":"legacy_fd","refund_amount_inr":250000},
        {"ticket_id":"T1","source_system":"helpdesk","refund_amount_inr":2500},
        {"ticket_id":"T2","source_system":"helpdesk","refund_amount_inr":1000},
    ])
    clean,audit=reconcile_tickets(df)
    assert len(clean)==2
    assert clean["refund_amount_clean"].sum()==3500
    assert audit["summary"]["exact_100x_pairs"]==1

def test_helpdesk_row_preferred():
    df=pd.DataFrame([
        {"ticket_id":"T1","source_system":"legacy_fd","refund_amount_inr":99900},
        {"ticket_id":"T1","source_system":"helpdesk","refund_amount_inr":999},
    ])
    clean,_=reconcile_tickets(df)
    assert clean.iloc[0]["source_system"]=="helpdesk"

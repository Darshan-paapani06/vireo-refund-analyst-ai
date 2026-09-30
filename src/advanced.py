from __future__ import annotations
import pandas as pd
import numpy as np


def build_advanced_views(pack, finance):
    refunds = finance['refunds'].copy()
    focus = finance['focus'].copy()
    orders = pack.orders.copy()
    # order context
    order_cols = [c for c in ['order_id','customer_id','sku','order_date','channel','qty','order_value_inr','lot_code'] if c in orders.columns]
    r = refunds.merge(orders[order_cols].add_prefix('order_'), left_on='order_id', right_on='order_order_id', how='left') if 'order_id' in refunds.columns and 'order_id' in orders.columns else refunds.copy()
    # product root cause
    product = r.groupby(['product_sku','product_name'], dropna=False, as_index=False).agg(
        refund_tickets=('ticket_id','nunique'), refund_amount=('refund_amount_clean','sum'),
        dual_cases=('replacement_issued', lambda s: int((s=='Y').sum()))
    )
    product['avg_refund'] = product['refund_amount']/product['refund_tickets'].replace(0,np.nan)
    product = product.sort_values('refund_amount', ascending=False)
    # lot signals if available
    lot_col = 'order_lot_code' if 'order_lot_code' in r.columns else None
    if lot_col:
        lots = r[r[lot_col].notna()].groupby([lot_col,'product_sku'], as_index=False).agg(
            refund_tickets=('ticket_id','nunique'), refund_amount=('refund_amount_clean','sum')
        ).sort_values('refund_amount', ascending=False)
    else:
        lots = pd.DataFrame(columns=['lot_code','product_sku','refund_tickets','refund_amount'])
    # channel
    channel = refunds.groupby('channel', as_index=False).agg(refund_tickets=('ticket_id','nunique'), refund_amount=('refund_amount_clean','sum')).sort_values('refund_amount', ascending=False)
    # team
    team = refunds.groupby('team', dropna=False, as_index=False).agg(refund_tickets=('ticket_id','nunique'), refund_amount=('refund_amount_clean','sum')).sort_values('refund_amount', ascending=False)
    # quarter comparison latest vs previous quarter
    f = finance['metrics']
    focus_start = pd.Timestamp(f['focus_period_start'])
    prev_start = focus_start - pd.offsets.QuarterBegin(startingMonth=((focus_start.month-1)//3)*3+1)
    # easier previous 3 calendar months
    prev_start = focus_start - pd.DateOffset(months=3)
    prev = refunds[(refunds['created_at']>=prev_start)&(refunds['created_at']<focus_start)]
    cur = focus
    def agg_reason(df):
        return df.groupby('refund_reason_code',as_index=False)['refund_amount_clean'].sum().rename(columns={'refund_amount_clean':'amount'})
    c=agg_reason(cur).rename(columns={'amount':'current'})
    p=agg_reason(prev).rename(columns={'amount':'previous'})
    drivers=c.merge(p,on='refund_reason_code',how='outer').fillna(0)
    drivers['delta']=drivers['current']-drivers['previous']
    drivers=drivers.sort_values('delta',ascending=False)
    compare={
        'current_total':float(cur['refund_amount_clean'].sum()), 'previous_total':float(prev['refund_amount_clean'].sum()),
        'delta':float(cur['refund_amount_clean'].sum()-prev['refund_amount_clean'].sum()),
        'pct':float((cur['refund_amount_clean'].sum()-prev['refund_amount_clean'].sum())/prev['refund_amount_clean'].sum()) if prev['refund_amount_clean'].sum() else None,
        'previous_label':f"{prev_start.strftime('%b %Y')}–{(focus_start-pd.Timedelta(days=1)).strftime('%b %Y')}"
    }
    # data quality
    dq=[]
    for col in ['order_id','agent_id','refund_reason_code','customer_message','agent_notes']:
        if col in refunds.columns:
            dq.append({'field':col,'missing':int(refunds[col].isna().sum()),'missing_pct':float(refunds[col].isna().mean())})
    return {'product':product,'lots':lots,'channel':channel,'team':team,'reason_drivers':drivers,'quarter_compare':compare,'data_quality':pd.DataFrame(dq)}

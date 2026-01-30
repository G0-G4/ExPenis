import logging
import sqlite3
from datetime import UTC, date, datetime

import pandas as pd
import panel as pn
import plotly.express as px
from panel.widgets import DatePicker

pn.config.template = 'material'
pn.extension("tabulator", "plotly")

DB_PATH = '/Users/g.grishenkov/projects/expenis/expenis.db'

def get_transactions(datetime_from: datetime, datetime_to: datetime):
    """Fetch transactions from database between specified dates"""
    try:
        cnx = sqlite3.connect(DB_PATH)
        # Convert to string format for SQLite
        from_str = datetime_from.strftime('%Y-%m-%d %H:%M:%S')
        to_str = datetime_to.strftime('%Y-%m-%d %H:%M:%S')

        query = """
                SELECT transactions.created_at as created_at,
                       transactions.user_id    as user_id,
                       accounts.name           as account,
                       categories.name         as category,
                       categories.type         as type,
                       amount,
                       description
                FROM transactions
                JOIN accounts on transactions.account_id = accounts.id
                JOIN categories on transactions.category_id = categories.id
                WHERE transactions.created_at BETWEEN ? AND ?
                ORDER BY transactions.created_at DESC \
                """
        df = pd.read_sql_query(query, cnx, params=[from_str, to_str])

        df['created_at'] = pd.to_datetime(df['created_at'])

        return df
    except Exception as e:
        logging.exception("Error fetching data: %s", str(e))
        return pd.DataFrame()
    finally:
        cnx.close()

# Create date pickers with initial values
start_date = DatePicker(
    name='Start Date',
    value=date.today().replace(day=1),  # First day of current month
    width=200
)

end_date = DatePicker(
    name='End Date',
    value=date.today(),  # Today
    width=200
)

def load_transactions(start, end):
    if isinstance(start, date):
        start = datetime.combine(start, datetime.min.time()).replace(tzinfo=UTC)
    if isinstance(end, date):
        end = datetime.combine(end, datetime.max.time()).replace(tzinfo=UTC)

    return get_transactions(start, end)

transactions_rx = pn.rx(load_transactions)(
    start_date,
    end_date
)

tabulator = pn.widgets.Tabulator(
    transactions_rx,
    pagination='local',
    page_size=20,
    sizing_mode='stretch_width',
    height=400,
    show_index=False
)

def create_chart(df):
    if df.empty or 'amount' not in df.columns or 'created_at' not in df.columns:
        return None

    # Aggregate by date
    df_copy = df.copy()
    df_copy['date'] = df_copy['created_at'].dt.date
    daily_totals = df_copy.groupby('date')['amount'].sum().reset_index()

    fig = px.bar(
        daily_totals,
        x='date',
        y='amount',
        title='Daily Transaction Amounts',
        labels={'amount': 'Amount', 'date': 'Date'}
    )
    fig.update_layout(height=300, margin=dict(t=30, b=20))
    return fig

chart_rx = pn.rx(create_chart)(transactions_rx)
chart_pane = pn.pane.Plotly(chart_rx, height=300)


col = pn.Column(
    pn.Row(start_date, end_date),
    # pn.pane.Markdown(summary_rx, sizing_mode='stretch_width'),
    tabulator,
    chart_pane,
    sizing_mode='stretch_width'
)



col.servable(title="Transaction Dashboard")
import logging
import sqlite3
from datetime import UTC, date, datetime

import pandas as pd
import panel as pn
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    start_date.rx.value,
    end_date.rx.value
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
    if df.empty or 'amount' not in df.columns or 'category' not in df.columns:
        return None

    # Separate income and expense
    income_df = df[df['type'] == 'income'].copy()
    expense_df = df[df['type'] == 'expense'].copy()
    
    # Group by category and sum amounts
    income_by_category = income_df.groupby('category')['amount'].sum().reset_index()
    expense_by_category = expense_df.groupby('category')['amount'].sum().abs().reset_index()
    
    # Create pie charts
    income_fig = px.pie(
        income_by_category,
        values='amount',
        names='category',
        title='Income by Category',
        hole=0.3
    )
    
    expense_fig = px.pie(
        expense_by_category,
        values='amount',
        names='category',
        title='Expenses by Category',
        hole=0.3
    )
    
    # Update layout for better display
    income_fig.update_traces(
        textinfo='percent+value',
        texttemplate='%{label}<br>%{percent:.1%}<br>%{value:,.2f}'
    )
    expense_fig.update_traces(
        textinfo='percent+value',
        texttemplate='%{label}<br>%{percent:.1%}<br>%{value:,.2f}'
    )
    
    # Create a row layout
    return pn.Row(
        pn.pane.Plotly(income_fig, height=400),
        pn.pane.Plotly(expense_fig, height=400),
        sizing_mode='stretch_width'
    )

chart_pane = pn.Column(pn.rx(create_chart)(transactions_rx), height=400)


col = pn.Column(
    pn.Row(start_date, end_date),
    # pn.pane.Markdown(summary_rx, sizing_mode='stretch_width'),
    tabulator,
    chart_pane,
    sizing_mode='stretch_width'
)



col.servable(title="Transaction Dashboard")

import panel as pn
from datetime import date, timedelta
import pandas as pd
from core.service import transaction_service, account_service
from core.models import Transaction
from core.helpers import format_amount

pn.extension()

class TransactionDashboard:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.start_date = date.today() - timedelta(days=30)
        self.end_date = date.today()

        # Initialize charts as empty placeholders
        self.income_chart = pn.pane.Markdown("Loading income data...")
        self.expense_chart = pn.pane.Markdown("Loading expense data...")
        self.time_series = pn.pane.Markdown("Loading transaction history...")

        # Create widgets
        self.date_range = pn.widgets.DateRangeSlider(
            name="Date Range",
            start=date.today() - timedelta(days=365),
            end=date.today(),
            value=(self.start_date, self.end_date)
        )
        self.refresh = pn.widgets.Button(name="🔄 Refresh", button_type="primary")
        self.stats_view = pn.indicators.Number(
            name="Net Balance",
            value=0,
            format="${value:,.0f}",
            colors=[(100, "red"), (0, "gray"), (100, "green")]
        )

        # Set up callbacks
        self.date_range.param.watch(self.update_data, "value")
        self.refresh.on_click(self.update_data)

        # Set up async update
        pn.state.onload(self.update_data)

    async def load_data(self):
        transactions = await transaction_service.get_transactions_for_period(
            self.user_id,
            self.start_date,
            self.end_date
        )
        accounts = await account_service.get_user_accounts_with_balance(self.user_id)
        return transactions, accounts

    def process_data(self, transactions, accounts):
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame([{
            'date': t.created_at,
            'amount': t.amount,
            'type': t.category.type,
            'category': t.category.name,
            'account': t.account.name
        } for t in transactions])

        # Calculate stats
        total_income = df[df['type'] == 'income']['amount'].sum()
        total_expense = df[df['type'] == 'expense']['amount'].sum()
        net_balance = sum(acc[1] for acc in accounts)

        return df, {
            'total_income': total_income,
            'total_expense': total_expense,
            'net_balance': net_balance
        }

    def update_data(self, event=None):
        async def _update():
            transactions, accounts = await self.load_data()
            df, stats = self.process_data(transactions, accounts)

            # Update stats
            self.stats_view.value = stats['net_balance']
            self.stats_view.name = f"Net Balance (Income: {format_amount(stats['total_income'])}, Expense: {format_amount(stats['total_expense'])})"

            # Update visualizations
            self.income_chart.object = self.create_chart(df[df['type'] == 'income'], "Income by Category")
            self.expense_chart.object = self.create_chart(df[df['type'] == 'expense'], "Expense by Category")
            self.time_series.object = self.create_time_series(df)
        
        pn.io.with_executor(None, _update)

    def create_chart(self, df, title):
        if df.empty:
            return pn.pane.Markdown(f"No {title.lower()} data available")

        grouped = df.groupby('category')['amount'].sum().sort_values()
        return pn.Bar(
            grouped,
            title=title,
            width=400,
            height=300
        )

    def create_time_series(self, df):
        if df.empty:
            return pn.pane.Markdown("No transaction data available")

        daily = df.groupby(['date', 'type'])['amount'].sum().unstack().fillna(0)
        return pn.Curve(
            daily,
            title="Daily Transactions",
            width=800,
            height=300,
            tools=['hover']
        )

    def view(self):
        return pn.Column(
            pn.Row(
                pn.Column(
                    self.date_range,
                    self.stats_view,
                    self.refresh
                ),
                pn.Column(
                    pn.Row(self.income_chart, self.expense_chart),
                    self.time_series
                )
            ),
            sizing_mode="stretch_width"
        )

    # Example usage

if __name__ == "__main__":
    dashboard = TransactionDashboard(user_id=1)  # Replace with actual user ID
    dashboard.view().servable()

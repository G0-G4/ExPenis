import altair as alt
import param
# from data_store import DataStore, CARD_STYLE
from panel.viewable import Viewer
import panel as pn

from datasource import CARD_STYLE, DataStore


class View(Viewer):
    data_store = param.ClassSelector(class_=DataStore)


class Table(View):
    columns = param.List(
        default=["p_name", "p_year", "t_state", "t_county", "t_manu", "t_cap", "p_cap"]
    )

    def __panel__(self):
        data = self.data_store.filtered[self.param.columns]
        return pn.widgets.Tabulator(
            data,
            pagination="remote",
            page_size=13,
            stylesheets=[CARD_STYLE.format(padding="10px")],
            margin=10,
        )


class Histogram(View):
    def __panel__(self):
        df = self.data_store.filtered
        df = df[df.t_manu.isin(self.data_store.top_manufacturers)]
        fig = (
            pn.rx(alt.Chart)(
                (df.rx.len() > 5000).rx.where(df.sample(5000), df),
                title="Capacity by Manufacturer",
            )
            .mark_circle(size=8)
            .encode(
                y="t_manu:N",
                x="p_cap:Q",
                yOffset="jitter:Q",
                color=alt.Color("t_manu:N").legend(None),
            )
            .transform_calculate(jitter="sqrt(-2*log(random()))*cos(2*PI*random())")
            .properties(
                height=400,
                width=600,
            )
        )
        return pn.pane.Vega(
            fig, stylesheets=[CARD_STYLE.format(padding="0")], margin=10
        )


class Indicators(View):
    def __panel__(self):
        style = {"stylesheets": [CARD_STYLE.format(padding="10px")]}
        return pn.FlexBox(
            pn.indicators.Number(
                value=self.data_store.total_capacity / 1e6,
                name="Total Capacity (GW)",
                format="{value:,.2f}",
                **style
            ),
            pn.indicators.Number(
                value=self.data_store.count,
                name="Count",
                format="{value:,.0f}",
                **style
            ),
            pn.indicators.Number(
                value=self.data_store.avg_capacity,
                name="Avg. Capacity (kW)",
                format="{value:,.2f}",
                **style
            ),
            pn.indicators.Number(
                value=self.data_store.avg_rotor_diameter,
                name="Avg. Rotor Diameter (m)",
                format="{value:,.2f}",
                **style
            ),
        )
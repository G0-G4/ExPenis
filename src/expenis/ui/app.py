import param
from panel.viewable import Viewer
from datasource import DataStore, get_turbines
from views import Indicators, Histogram, Table

import panel as pn

pn.extension("tabulator", "vega", throttled=True)

class App(Viewer):
    data_store = param.ClassSelector(class_=DataStore)

    title = param.String()

    views = param.List()

    def __init__(self, **params):
        super().__init__(**params)
        updating = self.data_store.filtered.rx.updating()
        updating.rx.watch(
            lambda updating: pn.state.curdoc.hold()
            if updating
            else pn.state.curdoc.unhold()
        )
        self._views = pn.FlexBox(
            *(view(data_store=self.data_store) for view in self.views), loading=updating
        )
        self._template = pn.template.MaterialTemplate(title=self.title)
        self._template.sidebar.append(self.data_store)
        self._template.main.append(self._views)

    def servable(self):
        if pn.state.served:
            return self._template.servable()
        return self

    def __panel__(self):
        return pn.Row(self.data_store, self._views)


data = get_turbines()
ds = DataStore(data=data, filters=["p_year", "p_cap", "t_manu"])

App(
    data_store=ds, views=[Indicators, Histogram, Table], title="Windturbine Explorer"
).servable()
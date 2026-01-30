import pandas as pd
import panel as pn
from panel.widgets import DatePicker
import plotly.express as px

pn.config.template = 'material'

x = pn.widgets.IntSlider(name='x', start=0, end=100)
background = pn.widgets.ColorPicker(name='Background', value='lightgray')

start_date = DatePicker()
end_date = DatePicker()

df = pd.DataFrame({
    'int': [1, 2, 3],
    'float': [3.14, 6.28, 9.42],
    'str': ['A', 'B', 'C'],
    'bool': [True, False, True],
}, index=[1, 2, 3])

categories = pn.widgets.MultiChoice(name='MultiSelect', value=['Apple', 'Pear'],
                                      options=['Apple', 'Banana', 'Pear', 'Strawberry'])

df_widget = pn.widgets.DataFrame(df, name='DataFrame')

pn.extension("plotly")

data = pd.DataFrame([
    ('Monday', 7), ('Tuesday', 4), ('Wednesday', 9), ('Thursday', 4),
    ('Friday', 4), ('Saturday', 4), ('Sunday', 4)], columns=['Day', 'Orders']
)

fig_responsive = px.line(data, x="Day", y="Orders")
fig_responsive.update_traces(mode="lines+markers", marker=dict(size=10), line=dict(width=4))
fig_responsive.layout.autosize = True

responsive = pn.pane.Plotly(fig_responsive, height=300)



def square(x):
    return f'{x} squared is {x ** 2}'


def styles(background):
    return {'background-color': background, 'padding': '0 10px'}


col = pn.Column(
    pn.Row(start_date, end_date, categories),
    df_widget,
    responsive
).servable()

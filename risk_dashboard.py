import pandas as pd
import numpy as np
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px

# Load the dataset (make sure this path is correct!)
df = pd.read_csv(r"C:\Users\greyson.surges\OneDrive - LinQuest Corporation\Desktop\risk_dashboard\Normalized_Force_Structure_Data.csv")

# Initialize app with LUX theme (light)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Force Structure Dashboard"

# Custom slider with tooltip
def styled_slider(id_, label, value):
    return html.Div([
        html.Label(label, className="fw-bold mb-1"),
        dcc.Slider(
            id=id_,
            min=0.1, max=5.0, step=0.1,
            value=value,
            tooltip={"placement": "bottom", "always_visible": True},
            marks={0.1: '0.1', 5.0: '5.0'}
        )
    ])

# Layout
app.layout = dbc.Container([

    # Title Section
    dbc.Card([
        dbc.CardBody([
            html.H1("Force Structure Risk Dashboard", className="text-center", style={
                "color": "#003366",
                "fontWeight": "bold",
                "fontSize": "2.5rem",
                "marginBottom": "0"
            })
        ])
    ], className="mb-4", style={"backgroundColor": "#f0f0f0", "border": "1px solid #ccc"}),

    # Risk Weights Sliders
    dbc.Card([
        dbc.CardBody([
            html.H5("Adjust Risk Weights", className="card-title mb-3"),
            dbc.Row([
                dbc.Col(styled_slider("w-mission", "Risk to Mission Weight", 1.0)),
                dbc.Col(styled_slider("w-force", "Risk to Force Weight", 1.0)),
                dbc.Col(styled_slider("w-acq", "Acquisition Risk Weight", 1.0)),
            ])
        ])
    ], className="mb-4"),

    # Filter Dropdown
    html.Label("Sort and Filter:", className="fw-bold"),
    dcc.Dropdown(
        id='filter-dropdown',
        options=[
            {'label': 'Lowest Total Risk', 'value': 'TotalRisk_asc'},
            {'label': 'Highest Total Risk', 'value': 'TotalRisk_desc'},
            {'label': 'Lowest Acquisition Risk', 'value': 'AcquisitionRisk_asc'},
            {'label': 'Highest Acquisition Risk', 'value': 'AcquisitionRisk_desc'},
            {'label': 'Lowest Probability of Success', 'value': 'ProbabilityOfSuccess_asc'},
            {'label': 'Highest Probability of Success', 'value': 'ProbabilityOfSuccess_desc'},
            {'label': 'Lowest Total Cost', 'value': 'TotalCost_asc'},
            {'label': 'Highest Total Cost', 'value': 'TotalCost_desc'},
            {'label': 'Lowest Risk-to-Cost Ratio', 'value': 'RiskToCostRatio_asc'},
            {'label': 'Highest Risk-to-Cost Ratio', 'value': 'RiskToCostRatio_desc'},
        ],
        value='TotalRisk_asc',
        className="mb-4"
    ),

    dcc.Store(id='weighted-data'),

    # Data Table
    dash_table.DataTable(
        id='force-structure-table',
        columns=[{"name": i, "id": i} for i in [
            "1-n", "InstanceID", "TotalCost", "RiskToMission", "RiskToForce",
            "AcquisitionRisk", "TotalRisk", "RiskToCostRatio", "ProbabilityOfSuccess"
        ]],
        data=[],
        sort_action="native",
        filter_action="native",
        row_selectable="single",
        page_size=10,
        tooltip_data=[],
        tooltip_duration=None,
        style_table={'overflowX': 'auto'},
        style_cell={
            'padding': '8px',
            'minWidth': '100px',
            'whiteSpace': 'normal'
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
        ]
    ),

    html.Br(),

    # Bar Chart & Details
    dbc.Row([
        dbc.Col(dcc.Graph(id='risk-breakdown-chart'), md=6),
        dbc.Col(html.Div(id='force-details', className='p-3 border bg-light'), md=6)
    ], className="mb-4"),

    # Scatter Plot
    html.H4("Cost vs Risk vs Probability of Success", className="text-center mt-4"),
    dcc.Graph(id='scatter-plot')
], fluid=True)

# Callback: Update weighted data
@app.callback(
    Output('weighted-data', 'data'),
    Input('w-mission', 'value'),
    Input('w-force', 'value'),
    Input('w-acq', 'value'),
    Input('filter-dropdown', 'value')
)
def update_scores(w_mission, w_force, w_acq, filter_option):
    temp_df = df.copy()
    temp_df["TotalRisk"] = (
        w_mission * temp_df["RiskToMission"] +
        w_force * temp_df["RiskToForce"] +
        w_acq * temp_df["AcquisitionRisk"]
    )
    temp_df["ProbabilityOfSuccess"] = temp_df["TotalRisk"].apply(lambda r: round(max(0.1, min(0.95, 1 - r / 3)), 2))
    temp_df["RiskToCostRatio"] = temp_df.apply(
        lambda row: round(row["TotalRisk"] / row["TotalCost"], 5) if row["TotalCost"] > 0 else float("inf"),
        axis=1
    )
    col, order = filter_option.split("_")
    temp_df.sort_values(by=col, ascending=(order == "asc"), inplace=True)
    temp_df.reset_index(drop=True, inplace=True)
    temp_df["1-n"] = temp_df.index + 1
    return temp_df.to_dict("records")

# Callback: Update table and tooltips
@app.callback(
    Output('force-structure-table', 'data'),
    Output('force-structure-table', 'tooltip_data'),
    Input('weighted-data', 'data')
)
def update_table(data):
    tooltips = [{"InstanceID": {"value": row.get("ForcePackage", ""), "type": "markdown"}} for row in data]
    return data, tooltips

# Callback: Update bar chart
@app.callback(
    Output('risk-breakdown-chart', 'figure'),
    Input('force-structure-table', 'selected_rows'),
    Input('weighted-data', 'data')
)
def display_risk_breakdown(selected_rows, data):
    if not selected_rows or not data:
        return px.bar(title="Select a Force Structure")
    row = data[selected_rows[0]]
    platforms = ["BomberA", "BomberB", "FighterA", "FighterB", "Tanker", "ISRDrone", "Satellite"]
    counts = [row.get(p, 0) for p in platforms]
    fig = px.bar(x=platforms, y=counts, text=counts,
                 title=f"Platform Composition: {row['InstanceID']}",
                 labels={"x": "Platform", "y": "Unit Count"})
    fig.update_traces(marker_color='steelblue', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', yaxis=dict(tick0=0))
    return fig

# Callback: Update force details
@app.callback(
    Output('force-details', 'children'),
    Input('force-structure-table', 'selected_rows'),
    Input('weighted-data', 'data')
)
def show_force_package_details(selected_rows, data):
    if not selected_rows or not data:
        return "Select an Instance to see Force Package Details."
    row = data[selected_rows[0]]
    platforms = ["BomberA", "BomberB", "FighterA", "FighterB", "Tanker", "ISRDrone", "Satellite"]
    lines = [f"{int(row[p])} × {p}" for p in platforms if p in row and int(row[p]) > 0]
    return html.Div([
        html.H5(f"Force Package: {row['InstanceID']}"),
        html.P(f"Total Cost: ${row['TotalCost']:,.0f}M"),
        html.P(f"Success Probability: {row['ProbabilityOfSuccess']*100:.0f}%"),
        html.P(f"Total Risk: {row['TotalRisk']:.2f}"),
        html.P(f"Risk-to-Cost Ratio: {row['RiskToCostRatio']:.5f}"),
        html.Ul([html.Li(l) for l in lines])
    ])

# Callback: Scatter Plot
@app.callback(
    Output('scatter-plot', 'figure'),
    Input('weighted-data', 'data')
)
def update_scatter(data):
    if not data:
        return px.scatter(title="Scatter Plot")
    df_plot = pd.DataFrame(data)
    fig = px.scatter(
        df_plot, x="TotalCost", y="TotalRisk",
        size="ProbabilityOfSuccess", color="ProbabilityOfSuccess",
        hover_name="InstanceID",
        labels={"TotalCost": "Total Cost", "TotalRisk": "Total Risk", "ProbabilityOfSuccess": "Success Probability"},
        title="Force Package Landscape: Cost vs Risk vs Success",
        color_continuous_scale="Tealgrn"
    )
    fig.update_layout(
        plot_bgcolor="#ffffff",
        xaxis=dict(showgrid=True, zeroline=False),
        yaxis=dict(showgrid=True, zeroline=False)
    )
    fig.update_traces(marker=dict(opacity=0.75, line=dict(width=0.5, color='DarkSlateGrey')))
    return fig

# Run the app
if __name__ == '__main__':
    import webbrowser
    webbrowser.open("http://127.0.0.1:8050/")
    app.run(debug=True, use_reloader=False)
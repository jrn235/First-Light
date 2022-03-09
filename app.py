from click import style
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import pymongo
import sqlite3
from lenspy import DynamicPlot
from constring import *


# Login Dependencies
# Manage database and users
from sqlalchemy import Table, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import select
from sqlalchemy.orm import Session
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, logout_user, current_user, LoginManager, UserMixin
# Manage password hashing
from werkzeug.security import generate_password_hash, check_password_hash
# Use to config server
import warnings
import configparser
import os
# Use for email check
import re

# For diplaying the data
import numpy as np
import json
from dash import dash_table as dt

# background color
colors = {
    'background': '#002D62',
    'text': '#FFFFFF'
}
# sidebar styling
SIDEBAR_STYLE = {
    'position': 'fixed',
    'top': 0,
    'left': 0,
    'bottom': 0,
    'width': '16rem',
    'padding': '2rem 1rem',
    'background-color': '#000173',
    'color': 'white'
}
# sidebar content styling
CONTENT_STYLE = {
    'margin-left': '18rem',
    'margin-right': '2rem',
    'padding': '2rem 1rem',
}
def updateLayout(graphFig):
    return graphFig.update_layout(
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text']
    )

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], prevent_initial_callbacks=False)
server = app.server
app.config.suppress_callback_exceptions = True

constring = con_string

#client = pymongo.MongoClient(constring)
#ztf = client.ztf.ztf
con = sqlite3.connect('pub_good_ztf_smallbodies.db', check_same_thread=False)
cursor = con.cursor()
warnings.filterwarnings("ignore")

# Connect to the userData SQLite database file
user_data_con = sqlite3.connect('userData.sqlite')
user_data_engine = create_engine('sqlite:///userData.sqlite')
user_data_db = SQLAlchemy()
class UserData(user_data_db.Model):
    id = user_data_db.Column(user_data_db.Integer, primary_key=True)
    username = user_data_db.Column(user_data_db.String(15), unique=False, nullable=False)
    ssnamenr = user_data_db.Column(user_data_db.String(50), unique=False)
UserData_tbl = Table('user_data', UserData.metadata)
# Creates the user_data table within the database
def create_userData_table():
    UserData.metadata.create_all(user_data_engine)
create_userData_table()

######################################################
### Account, login, and logout functionality setup ###
user_con = sqlite3.connect('data.sqlite')
engine = create_engine('sqlite:///data.sqlite')
db = SQLAlchemy()
config = configparser.ConfigParser()
# Create users class for interacting with users table
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))
Users_tbl = Table('users', Users.metadata)
# Fuction to create table using Users class
def create_users_table():
    Users.metadata.create_all(engine)
# Create the table
create_users_table()
# Config the server to interact with the database
# Secret Key is used for user sessions
server.config.update(
    SECRET_KEY=os.urandom(12),
    SQLALCHEMY_DATABASE_URI='sqlite:///data.sqlite',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)


db.init_app(server)
login_manager = LoginManager()
# This provides default implementations for the methods that Flask-#Login expects user objects to have
login_manager.init_app(server)
login_manager.login_view = '/login'
class Users(UserMixin, Users):
    pass
# Callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
###########################################

entireDF = ['jd', 'fid', 'pid', 'diffmaglim', 'ra', 'dec', 'magpsf', 'sigmapsf', 'chipsf',
    'magap', 'sigmagap', 'magapbig', 'sigmagapbig', 'distnr', 'magnr', 'fwhm', 'elong', 'rb', 'ssdistnr',
    'ssmagnr', 'id', 'night', 'obsdist', 'phaseangle', 'G', 'H', 'heliodist', 'antaresID']

# [('ztf',), ('orbdat',), ('desigs',), ('other_desig',)]
# magpsf and sigmapsf select through SQL
df = pd.DataFrame()

# Download Button
download_button = dbc.Row(
    [
        html.Button("Download CSV", id="btn_csv"),
        dcc.Download(id="download-dataframe-csv"),
    ],
    align="center",
)

# Search bar creation
search_bar = dbc.Row(
    [
        dbc.Col(dbc.Input(type="search", placeholder="Asteroid Search")),
        dbc.Col(
            dbc.Button(
                "Search", color="primary", className="ms-2", n_clicks=0
            ),
            width="auto",
        ),
    ],
    className="g-0 ms-auto flex-nowrap mt-3 mt-md-0",
    align="center",
)

# Top nav bar creation
topNavBar = dbc.Navbar(
    dbc.Container(
        [
            dbc.NavbarToggler(id="topNavBar-toggler", n_clicks=0),
            dbc.Collapse(
                search_bar,
                id="topNavBar_collapse",
                is_open=False,
                navbar=True,
            ),
            dbc.NavItem(dbc.NavLink("Login", href="/login", id="login-link", active="exact", style={"color": "#AFEEEE"})),
            dbc.NavItem(dbc.NavLink("Signup", href="/signup", id="signup-link", active="exact", style={"color": "#AFEEEE"}))
        ]
    ),
    color="dark",
    dark=True,
)

# Sidebar creation
sidebar = html.Div(
    [
        html.H1("Graphs", className="display-4"),
        html.Hr(),
        html.P(
            "Asteroid comparison through different attributes", className="lead"
        ),
        dbc.Nav(
            [
                # background color of pills: #a0faff
                dbc.NavItem(dbc.NavLink("Home", href="/", id="home-link", active="exact", style={"color": "#AFEEEE"})),
                dbc.NavItem(
                    dbc.NavLink("Account", href="/login", id="account-link", active="exact", style={"color": "#AFEEEE"})),
                dbc.NavItem(
                    dbc.DropdownMenu(label="Graphs", id="graph-link", style={"color": "#AFEEEE"}, nav=True,
                                     children=[dbc.DropdownMenuItem("Sigmapsf and Magpsf",
                                                                    href="/sigmapsf_magpsf"),
                                               dbc.DropdownMenuItem("DistNR and MagNR",
                                                                    href="/distnr_magnr"),
                                               dbc.DropdownMenuItem("Sigmapsf and Magpsf Scatter",
                                                                    href="/scatter"),
                                               ],
                                     )),
                dbc.NavItem(
                    dbc.NavLink("Documentation", href="/", id="document-link", active="exact",
                                style={"color": "#AFEEEE"})),
                dbc.NavItem(
                    dbc.NavLink("Links", href="/", id="links-link", active="exact", style={"color": "#AFEEEE"})),

            ],
            # makes the sidebar vertical instead of horizontal
            vertical=True,
            # gives the active link a blue highlight
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,

)

# Sign up page
create = html.Div([
            html.H1('Create User Account:'),
            dcc.Location(id='creation', refresh=True),
            dcc.Input(id="username", type="text", placeholder="user name", maxLength=15),
            dcc.Input(id="password", type="password", placeholder="password"),
            dcc.Input(id="confirmpassword", type="password", placeholder="confirm password"),
            dcc.Input(id="email", type="email", placeholder="email", maxLength=50),
            html.Button('Sign Up', id='signup_button', n_clicks=0),
            html.Div(id='create_user', children=[])
        ])  # end div

# Login page
login = html.Div([
            dcc.Location(id='url_login', refresh=True),
            html.H2('''Please log in to continue:''', id='h1'),

            dcc.Input(placeholder='Enter your username', type='text', id='uname-box'),
            dcc.Input(placeholder='Enter your password', type='password', id='pwd-box'),
            dcc.Input(placeholder='Confirm your password', type='password', id='con-pwd-box'),

            html.Button(children='Login', n_clicks=0, type='submit', id='login-button'),
            html.Div(id='login_output', children=[], style={})
        ])  # end div

# Account page
account = html.Div([
            dcc.Location(id='user_account', refresh=True),
            html.Div(id='account_output', children=[], style={}),  # end div
            html.Br(), html.Br(),
            html.Button('Logout', id='logout_button', n_clicks=0),
            html.Div(id='url_logout', children=[]) # end div
        ])  # end div

content = html.Div(id="page-content", children=[], style=CONTENT_STYLE)

app.layout = html.Div([
    dcc.Location(id="url"),
    topNavBar,
    sidebar,
    content,
    download_button
])

@app.callback(
    Output('ztf-dropdown', 'options'),
    [Input('ztf-attribute-dropdown', 'value')]
)

@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn_csv", "n_clicks"),
    prevent_initial_call=True,
)
def exportButton(n_clicks):
    return dcc.send_data_frame(df.to_csv, "sigmapsfDF.csv")

# call back for top Navigation bar
@app.callback(
    Output("topNavBar-collapse", "is_open"),
    [Input("topNavBar-toggler", "n_clicks")],
    [State("topNavBar_collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page_content(pathname):
    # if pathname is the main page show that main graph
    if pathname == "/":
        return [
            html.Div([

            ])
        ]
    elif pathname == "/graph":
        return [
            html.Div([
                dcc.Dropdown(
                    options = [{'label': i, 'value': i } for i in entireDF],
                    value = 'sigmapsf',
                    id = 'xaxis-column'),
                dcc.RadioItems(
                    options = [
                        {'label': 'Linear', 'value': 'Linear'},
                        {'label': 'Log', 'value': 'Log'}],
                    value = "Linear",
                    id = 'xaxis-type'
                )], style = {'width': '48%', 'display': 'inline-block'}
            ),
            html.Div([
                dcc.Dropdown(
                    options = [{'label': i, 'value': i } for i in entireDF],
                    value = 'magpsf',
                    id = 'yaxis-column'),
                dcc.RadioItems(
                    options = [
                        {'label': 'Linear', 'value': 'Linear'},
                        {'label': 'Log', 'value': 'Log'}],
                    value = "Linear",
                    id = 'yaxis-type'
                )], style = {'width': '48%', 'float': 'right', 'display': 'inline-block'}
            ),
            dcc.Graph(id = "heatmap"),
            html.Div(
                html.Pre(id = 'click-data')
            )
        ]

    elif pathname == "/scatter":
        return [
            html.Div([
                dcc.Dropdown(
                    options = [{'label': i, 'value': i } for i in entireDF],
                    value = 'sigmapsf',
                    id = 'xaxis-column'),
                dcc.RadioItems(
                    options = [
                        {'label': 'Linear', 'value': 'Linear'},
                        {'label': 'Log', 'value': 'Log'}],
                    value = "Linear",
                    id = 'xaxis-type'
                )], style = {'width': '48%', 'display': 'inline-block'}
            ),
            html.Div([
                dcc.Dropdown(
                    options = [{'label': i, 'value': i } for i in entireDF],
                    value = 'magpsf',
                    id = 'yaxis-column'),
                dcc.RadioItems(
                    options = [
                        {'label': 'Linear', 'value': 'Linear'},
                        {'label': 'Log', 'value': 'Log'}],
                    value = "Linear",
                    id = 'yaxis-type'
                )], style = {'width': '48%', 'float': 'right', 'display': 'inline-block'}
            ),
            dcc.Graph(id = "scatter"),
            html.Div(
                html.Pre(id = 'click-data')
            )
        ]

    elif pathname == '/asteroid':
        return [
            html.Div([
                html.Div(id = 'asteroid', children=[]),
                html.Button(id='save-button', children='Save Asteroid', n_clicks=0),
                html.Div(id='save-output', children=[])
            ]),
            html.Div([
                dcc.Dropdown(
                    options = [{'label': i, 'value': i } for i in entireDF],
                    value = 'jd',
                    id = 'xaxis_ast')
                    ], style = {'width': '48%', 'display': 'inline-block'}
            ),
            html.Div([
                dcc.Dropdown(
                    options = [{'label': i, 'value': i } for i in entireDF],
                    value = 'H',
                    id = 'yaxis_ast')
                    ], style = {'width': '48%', 'float': 'right', 'display': 'inline-block'}
            ),
            dcc.Graph(id = "scatter_ast"),
        ]

    elif pathname == '/login':
        if current_user.is_authenticated:
            return [
                    html.H1("Welcome " + current_user.username + "!"),
                    html.Br(), html.Br(),
                    html.Button('My Asteroids', id='select_button', n_clicks=0),
                    html.Br(), html.Br(),
                    html.Div(id='selection', children=[]),
                    html.Br(),
                    html.Button('Logout', id='logout_button', n_clicks=0),
                    html.Div(id='url_logout', children=[]) # end div
                    ]
        else:
            return [login]

    elif pathname == '/signup':
        return [create]

    elif pathname == "/account":
        if current_user.is_authenticated:
            return [account]
        else:
            return [login]

    else:
        return[html.H1('Error 404: Page not found')]

@app.callback(
    Output('save-output', 'children'),
    Input('save-button', 'n_clicks'),
    State('url', 'hash')
)
def save_asteroid(n_clicks, hash):
    if(n_clicks > 0):
        un = current_user.username
        hash = hash.replace("#", "")

        already_exists = select(UserData_tbl.c.id).where((UserData_tbl.c.username) == un).where((UserData_tbl.c.ssnamenr) == hash)
        connection = user_data_engine.connect()
        already_exists_result = connection.execute(already_exists)
        check_result = already_exists_result.first()

        if(check_result is None):
            ins = UserData_tbl.insert().values(username=un, ssnamenr=hash)

            # Insert the new user into the database
            connection.execute(ins)

            # Close the connection to the database
            connection.close()

            # Return to the home page
            return (html.H2('Asteroid Saved!'))

        else:
            return (html.H2('You already have this asteroid saved!'))


##########################################################################################################
#   This function uses the input username to query the database for all asteroids that correspond to it
#
#       Output: Into a Div with the ID 'selection'
#       Input: The username value entered into the select button when clicked
#       State: Saves the username
##########################################################################################################
@app.callback(
    Output('selection', 'children'),
    [Input('select_button', 'n_clicks')]
)
def displayUserData(n_clicks):

    # Query that elects the ssnamenr column values where the username column values match the inputted
    # username
    un = current_user.username
    query = select(UserData_tbl.c.ssnamenr).where(UserData_tbl.c.username == un)

    # Connect to the database
    with user_data_engine.connect() as connection:

        # Try to
        try:
            # Execute the query
            result = connection.execute(query)

        # There was an error
        except Exception as e:
                print(e)

        # The query executed
        else:

            # Create a list for the JSON data that needs to be passed into the dataframe
            json_list = []

            # Loop through each row queried
            for row in result:

                # Create a list for the row data
                row_list = []

                # Set the row data into a tuple
                row_data = (row[0])

                # Append row data into the row list and take out the square brackets [ ] around the data
                row_list.append(row_data.replace("[", "").replace("]", ""))

                # JSON serialize the data
                jsonString = json.dumps(row_list)

                # Append the JSON string while taking out the square brackets [ ] and quotes " " around
                # the data
                json_list.append(jsonString.replace("[", "").replace("]", "").replace('"', ""))

            # Disconnect from the database
            result.close()

            # Use numpy to put the JSON data into an Array
            clean_up = np.array(json_list)

            # Create a list for the asteroid links
            link_array = []

            # Loop through each value in the Array
            for value in clean_up:

            	# reformat the value to be an HTML link using an f string with HTML code and the value
            	value = f"<a href='/asteroid#{value}'>{value}</a>"

                # Append the link into the link list
            	link_array.append(value)

            # Create a Dataframe using the link data
            df = pd.DataFrame(link_array)

            # Set the column name to be ssnamenr
            df.columns = ['SSNAMENR']

            # Set the columns to be a dictionary with the column name and value, and for it to contain
            # HTML code
            columns = [{"name": i, "id": i, "presentation": "markdown"} for i in df.columns]

            # Set a data array to be the DataFrame split into dictionary records
            data_array = df.to_dict('records')

            # Return a Dash Datatable with the data centered
            return dt.DataTable(data=data_array, columns=columns, style_header={'textAlign': 'center'}, style_table={'minWidth': '100px', 'width': '100px', 'maxWidth': '100px'}, style_data={'paddingLeft': '25px', 'paddingTop': '20px'}, markdown_options={"html": True})



@app.callback(
    Output('click-data', 'children'),
    Input('scatter', 'clickData')
)
def click_scatter(clickData):
    if(clickData != None):
        click_data = clickData['points'][0]['hovertext']
        goto = dcc.Link(html.A(f'Go to {click_data}'), href = f'/asteroid#{click_data}')
        return goto

@app.callback(
    Output('heatmap', 'figure'),
    Input('xaxis-column', 'value'),
    Input('yaxis-column', 'value'))
def update_heatmap(xaxis_column_name, yaxis_column_name):
    filter_query = {}
    ztf_query = {xaxis_column_name: 1, yaxis_column_name: 1}
    ztf_heat = ztf.find(
        filter_query,
        ztf_query)

    df = pd.DataFrame(ztf_heat, columns=(xaxis_column_name, yaxis_column_name))

    print(df)

    fig = px.density_heatmap(df, x = xaxis_column_name, y = yaxis_column_name,
                            nbinsx = 25, nbinsy = 25, text_auto = True)

    fig.update_xaxes(title=xaxis_column_name)
    fig.update_yaxes(title=yaxis_column_name)

    updateLayout(fig)
    return fig

@app.callback(
    Output('scatter', 'figure'),
    Input('xaxis-column', 'value'),
    Input('yaxis-column', 'value'))
def update_scatter(xaxis_column_name, yaxis_column_name):
    df = pd.read_sql(f"SELECT {xaxis_column_name}, {yaxis_column_name}, id FROM ztf WHERE ssnamenr == 4000 OR ssnamenr == 5000", con)

    fig = px.scatter(df, x = xaxis_column_name, y = yaxis_column_name,
                        hover_name = 'id')

    fig.update_xaxes(title=xaxis_column_name)
    fig.update_yaxes(title=yaxis_column_name)
    plot = DynamicPlot(fig, max_points=1000)

    updateLayout(fig)
    return plot.fig

@app.callback(
    Output('scatter_ast', 'figure'),
    Input('xaxis_ast', 'value'),
    Input('yaxis_ast', 'value'),
    Input('url', 'hash'))
def update_scatter_asteroid(xaxis_ast, yaxis_ast, hash):
    scatter_mong = ztf.find(
        { "id": int(hash[1:]) },
        { xaxis_ast, yaxis_ast }
    )

    df = pd.DataFrame(scatter_mong)

    fig = px.scatter(df, x = xaxis_ast, y = yaxis_ast)

    fig.update_xaxes(title=xaxis_ast)
    fig.update_yaxes(title=yaxis_ast)

    updateLayout(fig)
    return fig

@app.callback(
    Output('asteroid', 'children'),
    Input('url', 'hash')
)
def generate_asteroid_page(hash):
    return f'{hash[1:]}'

# Login functionality
@app.callback(
    [Output('create_user', "children")],
    [Input('signup_button', 'n_clicks')],
    [State('username', 'value'), State('password', 'value'), State('confirmpassword', 'value'), State('email', 'value')])
def insert_users(n_clicks, un, pw, cpw, em):

    # Hash the password
    hashed_password = generate_password_hash(pw, method='sha256')

    # Valid Email constraints
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Check if all the fields are not empty
    if un is not None and pw is not None and cpw is not None and em is not None:

        # Checks if no errors occur
        try:

            # Check if the password and confirm password values are the same
            if cpw == pw:

            	# Check if the email is valid
                if re.fullmatch(regex, em):

                    # Create a new user object for the database
                    ins = Users_tbl.insert().values(username=un,  password=hashed_password, email=em)

                    # Connect to the database
                    user_con = engine.connect()

                    # Insert the new user into the database
                    user_con.execute(ins)

                    # Close the connection to the database
                    user_con.close()

                    # Return to the home page
                    return [html.Div([html.H2('Account Successfully Created')])]
                else:

                    # Email is not valid
                    return [html.Div([html.H2('This email is not valid')])]

            # If the passwords do not match
            else:

               	# Print the error
                return [html.Div([html.H2('Passwords do not match')])]

        # Which error occured?
        except SQLAlchemyError as e:

            # To see error
            error = str(e.__dict__['orig'])

            # Username already in use
            if error == 'UNIQUE constraint failed: users.username':

                # Print the error
                return [html.Div([html.H2('This username is already taken')])]

            # Email already used
            elif error == 'UNIQUE constraint failed: users.email':

                return [html.Div([html.H2('There is already an account associated with this email')])]

    # If one or more of the fields are empty
    else:
        # Print the error
        return [html.Div([html.H2('A field is empty')])]

# Callback for logging in
@app.callback(
    Output('login_output', 'children'), [Input('login-button', 'n_clicks')],
    [State('uname-box', 'value'), State('pwd-box', 'value'), State('con-pwd-box', 'value')])
def login_to_account(n_clicks, input1, input2, input3):
    if n_clicks > 0:
        # Gets the username data from the database
        user = Users.query.filter_by(username=input1).first()

        # If the user exists
        if user:
            # Check the passwords to see if they match the recorded password in the database
            if check_password_hash(user.password, input2) and check_password_hash(user.password, input3):
                login_user(user)
                # All is good, continue
                return dcc.Location(pathname="/", id="home-link")
            # If one, or both, password(s) do not match
            else:
                # Print the error
                return [html.Div([html.H2('Incorrect Password')])]

        # If the username does not exist
        else:
            # Print the Error
            return [html.Div([html.H2('Incorrect Username')])]

# Callback for account page
@app.callback(
    Output('account_output', 'pathname'),
    [Input('account_button', 'n_clicks')])
def display_account():
    if n_clicks > 0:
        return '/account'

# Callback for logout
@app.callback(
    Output('url_logout', 'children'), [Input('logout_button', 'n_clicks')])
def logout_of_account(n_clicks):
    if n_clicks > 0:
        logout_user()
        return [html.H1("You've been logged out")]

# Callback for go back
@app.callback(
    Output('url', 'pathname'), [Input('back-button', 'n_clicks')])
def go_back(n_clicks):
    if n_clicks > 0:
        return '/'

if __name__ == '__main__':
    app.run_server(debug=False, port=8051)

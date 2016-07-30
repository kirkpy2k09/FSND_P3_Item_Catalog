from flask import Flask, render_template, request, redirect
from flask import make_response
from flask import g, jsonify, url_for, flash, session as login_session
from functools import wraps
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import random
import string
import httplib2
import json
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Main Page
@app.route('/')
@app.route('/restaurant/')
def showRestaurants():
    restaurants = session.query(Restaurant).all()
    # return "This page will show all my restaurants"
    return render_template('restaurants.html', restaurants=restaurants)


# Show a restaurant menu
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return render_template('menu.html', items=items, restaurant=restaurant)
    # return 'This page is the menu for restaurant %s' % restaurant_id


# JSON API
@app.route('/restaurant/menu/JSON')
def menuitemJSON():
    menuItems = session.query(MenuItem).all()
    return jsonify(menuItems=[m.serialize for m in menuItems])
	
# Login
@app.route('/login')
def login():
    # create a state token to prevent request forgery
    state = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for x in xrange(32))
    # store it in session for later use
    login_session['state'] = state
    return render_template('login.html', STATE = state)

# Logout
@app.route('/logout')
def logoutUser():
	session.pop('user_id', None)
	flash('User logged out')
	return redirect(url_for('showRestaurants'))
	
	
def logoutCleanup():
    """
    handles clean-up from logging out user
    """
    print "def logoutCleanup(): called"
    # Reset the user's sesson.
    del login_session['credentials']
    del login_session['gplus_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['logintime']
    del login_session['access_length']
    return redirect(url_for('showRestaurants'))


# Connect to google oAuth for authentication
@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Connect to the google oauth2 service for user authentication
    """
    print "def gconnect(): called"
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps(\
        	'Failed to upgrade the authorization code.'), \
        	401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'\
    	% access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps(\
        	"Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps(\
        	"Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(\
        	'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    # Grab the current time and length of time for the
    # access token to determine when it expires
    login_session['logintime'] = datetime.now()
    login_session['access_length'] = credentials.token_response["expires_in"]

    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    # store user data in session for later retrieval
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # Generate html for welcome message to display on successful login
    output = ''
    return output


# Disconnect from google oAuth for authentication
@app.route('/gdisconnect')
def gdisconnect():
    """
    Revoke a current user's Google oauth2 token and resets their login_session
    """
    print "def gdisconnect(): called"
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'),\
        	401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        return logoutCleanup()
    else:
        # Check to see if the access token has expired. 
        # This would cause an error when trying to revoke 
        # it since its already revoked. In this case, 
        # we can safely logout the user.
        if (datetime.now() - login_session['logintime']) > \
        	timedelta(seconds=login_session['access_length']):
            return logoutCleanup()

        # For whatever reason, the given token was invalid.
        response = make_response(json.dumps(\
        	'Failed to revoke token for given user.', \
        	400))
        response.headers['Content-Type'] = 'application/json'
        return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login', next=request.url))
    return decorated_function


# Create a new menu item
@app.route('/restaurant/<int:restaurant_id>/menu/new/', \
	methods=['GET', 'POST'])
@login_required
def newMenuItem(restaurant_id):
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],\
        					description=request.form[
                           'description'], price=request.form['price'], \
                           course=request.form['course'],\
                           	restaurant_id=restaurant_id)
        session.add(newItem)
        session.commit()

        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)

    return render_template('newMenuItem.html', restaurant=restaurant)
    
# Edit a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', \
	methods=['GET', 'POST'])
@login_required
def editMenuItem(restaurant_id, menu_id):
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['name']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, \
            	item=editedItem)

# Delete a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', \
	methods=['GET', 'POST'])
@login_required
def deleteMenuItem(restaurant_id, menu_id):
    itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteMenuItem.html', item=itemToDelete)


# Main Appliction Loop
if __name__ == '__main__':
		import uuid
		app.secret_key = str(uuid.uuid4())
		app.debug = False
		app.run(host = '0.0.0.0', port = 8000)

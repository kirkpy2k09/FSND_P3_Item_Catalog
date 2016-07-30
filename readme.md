Project 3 - Item Catalog
=========

##About

A web application that provides a list of items within a variety of categories and integrates third party registration and authentiation.
Authenticated users have the ability to post, edit, and delete their own items.

##Creator
Kirkland Poole

##Quick Start

1. Navigate to the vagrant environment

2. Run python database_setup.py to create the database

3. Run python lotsofmenus.py to populate the database

4. Run python application.py and navigate to http://127.0.0.1:8000/in your browser

Note: To Change/Update or Delete a menu item, you must authenticate using the login button and use your google+ account credentials.


References:
https://github.com/lobrown/Full-Stack-Foundations/tree/master/Lesson-4
http://flask.pocoo.org/docs/0.10/quickstart/#sessions
http://stackoverflow.com/questions/33400219/scroll-in-navigation-bar-doesnt-work-in-material-design-lite-v1-0-5/33464535
https://developers.google.com/api-client-library/python/guide/aaa_oauth#OAuth2WebServerFlow
https://developers.google.com/+/web/signin/#set_up_google_sign-in_for_google
http://flask.pocoo.org/docs/0.10/patterns/viewdecorators/
http://stackoverflow.com/questions/19797709/what-is-a-self-written-decorator-like-login-required-actually-doing

###Dependencies
This app was developed using Python 2.7.9 or above.
The pre-configured Vagrant Virtual Machine environment from github: https://github.com/udacity/fullstack-nanodegree-vm
The implemented database schema file and python files and web files.


from flask import render_template

def page_not_found(e):
    '''
    page_not_found()... not sure why we got a request for a non-existing URL
    '''
    return render_template('Error404.html'), 404

def server_error(e):
    '''
    server_error()... ammm Houston, we have a problem here
    '''
    return render_template('Error500.html'), 500

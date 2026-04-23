import sys
import os
import logging

# Passenger capte stdout comme réponse HTTP — tout rediriger vers stderr
sys.stdout = sys.stderr

sys.path.insert(0, os.path.dirname(__file__))
os.environ['FLASK_ENV'] = 'production'

logging.basicConfig(
    filename='/home/qpyq4619/intranet.limoud.org/error_flask.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

from app import create_app
application = create_app('production')

if __name__ == '__main__':
    application.run()

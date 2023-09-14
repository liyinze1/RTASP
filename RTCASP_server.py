from flask import Flask, request
from RTASP import *

app = Flask(__name__)

@app.route('/new', methods=['POST', 'GET'])
def index():wa
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8000)
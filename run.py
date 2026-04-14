import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from http.server import HTTPServer
from index import handler

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8000), handler)
    print('✓ Backend running at http://localhost:8000')
    server.serve_forever()
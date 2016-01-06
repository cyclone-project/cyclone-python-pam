#!/usr/bin/python
# !/usr/bin/env python
import SimpleHTTPServer
import SocketServer
import syslog


class MyRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_GET(self):
        self.path = '/sso.html'
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


Handler = MyRequestHandler
server = SocketServer.TCPServer(('0.0.0.0', 8080), Handler)

server.serve_forever()

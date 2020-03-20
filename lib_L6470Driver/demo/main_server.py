# Stepper Motor Demo - Main server
#   Zong-Sheng Wang


from flask import Flask, Blueprint, current_app, render_template
from flask_restful import Api, Resource, url_for, Resource, reqparse, fields, marshal, marshal_with
#from flask_cors import CORS

from socket import socket, AF_INET, SOCK_STREAM
from time import sleep
import threading

STP_HOST = '127.0.0.1'
#STP_HOST = '192.168.137.222'
STP_PORT = 6688
WEB_PORT = 8866

g_userdata = {'curPos': -1.0, 'swon': False, 'busy': False, 'uvlo': False,'ocd': False, 
    'thwrn': False, 'thsd': False, 'notperfcmd': False, 'wrongcmd': False}
    # holds the current pos, can adds busy status if necessary

###########################################
# A Thread to Monitoring Stepper's position
class PositionMonitorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._is_running = True
        self.skt = socket(AF_INET, SOCK_STREAM)

    def run(self):
        self.skt.connect((STP_HOST, STP_PORT))
        print (" + Stepper Motor Position Monitor Thread is running..")
        global  g_userdata
        #print(app.userdata)
        while self._is_running :            
            self.skt.send(b'p')     # get current position
            msg = self.skt.recv(8192)
            #if msg:
            idata = msg.decode()
            rdatas = idata.split('|')
            g_userdata['curPos'] = float(rdatas[0])
            g_userdata['swon'] = (rdatas[1] == 'T')
            g_userdata['busy'] = (rdatas[2] == 'T')
            g_userdata['uvlo'] = (rdatas[3] == 'T')
            g_userdata['ocd'] = (rdatas[4] == 'T')
            g_userdata['thwrn'] = (rdatas[5] == 'T')
            g_userdata['thsd'] = (rdatas[6] == 'T')
            g_userdata['notperfcmd'] = (rdatas[7] == 'T')
            g_userdata['wrongcmd'] = (rdatas[8] == 'T')

            #print(g_userdata)
            sleep(0.2)  

    def stop(self):
        self._is_running = False
        self.skt.shutdown(2)
        self.skt.close()


###########################################
#  serves as a stepper tcp client
class StepperTCPClient():
    def __init__(self):
        threading.Thread.__init__(self)
        self._is_running = True
        self.skt = socket(AF_INET, SOCK_STREAM)
        self.skt.connect((STP_HOST, STP_PORT))
        print (" + Stepper Motor TCP Client is running..")

    def __del__(self):
        self.skt.shutdown(2)
        self.skt.close()

    def setParams(self, maxSpd, minSpd, acc):
        print (" * setParams")
        payload = bytes('s|'+str(maxSpd)+'|'+str(minSpd)+'|'+str(acc), encoding='utf8')
        self.skt.send(payload)

    def jog(self, dir):
        print (" * Jog" + dir)
        payload = bytes('j|'+dir, encoding='utf8')
        self.skt.send(payload)

    def move(self, pos_cm):
        print (" * Move To " + str(pos_cm))
        payload = bytes('m|'+str(pos_cm), encoding='utf8')
        self.skt.send(payload)

    def home(self):
        print (" * Go home")
        #self.skt.send(b'h') #gohome
        self.skt.send(b'r') #searchhome

        


# type of return field 
json_return_field = {
    'status': fields.Boolean,
    'data': fields.Raw,
    'message': fields.String
}


######################################
# Flask API 
class StepperMotorAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        #self.reqparse.add_argument('start', type=bool, help='Parameter "start" must be a boolean', location='json')
        self.reqparse.add_argument('maxSpd', type=float, required=True, help='Parameter "maxSpd" must be a float', location='json')
        self.reqparse.add_argument('minSpd', type=float, required=True, help='Parameter "minSpd" must be a float', location='json')
        self.reqparse.add_argument('acc', type=float, required=True, help='Parameter "acc" must be a float', location='json')
        self.reqparse.add_argument('targetPos', type=float, help='Parameter "targetPos" must be a float', location='json')
        self.reqparse.add_argument('action', help='Parameter "action" must be a string', location='json')
        super(StepperMotorAPI, self).__init__()

    @marshal_with(json_return_field)
    def get(self):
        global g_userdata
        return {'status': True, 'data': g_userdata}

    @marshal_with(json_return_field)
    def post(self):
        args = self.reqparse.parse_args()
        message = '' 
        status = True   

        motor_agent.setParams(args['maxSpd'], args['minSpd'], args['acc'])
        if "jog" in args['action']:
            motor_agent.jog(args['action'][3])
            message = 'Jog Successfully!' 
        elif "move" in args['action']:
            motor_agent.move(args['targetPos']) 
            message = 'Move Successfully!' 
        elif "home" in args['action']:
            motor_agent.home() 
            message = 'Gohome Successfully!' 
        else:
            status = False
            message = 'Parameter Error!' 
 
        return {'status': status, 'message': message}

    @marshal_with(json_return_field)
    def put(self):
        return {'status': False, 'message': 'PUT not allow'}

    @marshal_with(json_return_field)
    def delete(self):
        return {'status': False, 'message': 'DELETE not allow'}


app = Flask(__name__, static_folder = "./webui/static", template_folder = "./webui")
#cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.add_url_rule('/', view_func=lambda: render_template("index.html"))

# config api class
api_bp = Blueprint('api', __name__)
api = Api(api_bp)
app.register_blueprint(api_bp, url_prefix='/api')
api.add_resource(StepperMotorAPI, '/stepper', endpoint='stepper')


if __name__ == '__main__':
    try:
        pos_mon = PositionMonitorThread()
        pos_mon.daemon = True
        pos_mon.start()

        motor_agent = StepperTCPClient()
        app.run(host='0.0.0.0', port=WEB_PORT, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print('\nReceived keyboard interrupt, quitting threads.\n')
        pos_mon.stop()

    

    

    

    
# Stepper Motor Demo - Stepper Server
#   Zong-Sheng Wang
import RPi.GPIO as GPIO
import spidev
from socketserver import BaseRequestHandler, TCPServer, ThreadingTCPServer
from time import sleep
import threading
from WZS.L6470Driver import L6470

PCR_PORT = 6688
STEPS_PER_CM = 62
g_is_accepted = True

RESET_PIN = 16
BUSY_PIN = 26
HOMESW_PIN = 19

# to handle the TCP connection
class ConnectionHandler(BaseRequestHandler):
    def handle(self):
        print('Got connection from', self.client_address)
        global g_is_accepted
        g_is_accepted = True
        
        while g_is_accepted:
            data = self.request.recv(8192)
            
            idata = data.decode()
            # set parameters by 's|MAX_SPEED|MIN_SPEED|ACC'
            if idata[0] == 's':
                params = idata.split('|')
                max_spd = float(params[1]) * STEPS_PER_CM
                min_spd = float(params[2]) * STEPS_PER_CM
                acc = float(params[3]) * STEPS_PER_CM
                print('Set MAX_SPEED = %.2fsteps/s, MIN_SPEED=%.2fsteps/s, ACC=%.2fsteps/s^2 \n ' % (max_spd, min_spd, acc))
                board_agent.setBoardParameters(max_spd, min_spd, acc)
                self.request.send(b'ok')
            # get current position in centimeter by 'p' 
            # and other information
            # curpos|SW_ON|BUSY|UVLO|OCD|THWRN|THSD|NOTPERFCMD|WRONGCMD
            elif idata[0] == 'p':
                cur_pos_cm = round(board_agent.getCurPosCM(), 2)
                
                payload = "{curpos}|{swon}|{busy}|{uvlo}|{ocd}|{thwrn}|{thsd}|{notperfcmd}|{wrongcmd}".format(
                    curpos = str(cur_pos_cm), swon = str(board_agent.isSwitchOn())[0], 
                    busy=str(board_agent.isBusy())[0], uvlo=str(board_agent.isUVLO())[0], 
                    ocd=str(board_agent.isOCD())[0], thwrn=str(board_agent.isTHWRN())[0], 
                    thsd=str(board_agent.isTHSD())[0], notperfcmd=str(board_agent.isNOTPERFCMD())[0], 
                    wrongcmd=str(board_agent.isWRONGCMD())[0]
                )
                print('Get Current: ' + payload)
                msg = bytes(payload, encoding='utf8')
                self.request.send(msg)
            # gohome by 'h'
            elif idata[0] == 'h':
                print('Go Home')
                board_agent.goHome()
                self.request.send(b'ok')
            # jog+/jog- by 'j|[+|-]'
            elif idata[0] == 'j':
                dir = idata.split('|')[1]
                print('Jog' + dir)
                if dir[0] == '+':
                    board_agent.jogPlus()
                elif dir[0] == '-':
                    board_agent.jogMinus()
                self.request.send(b'ok')
            # move by 'm|pos'
            elif idata[0] == 'm':
                pos_cm = float(idata.split('|')[1])
                print('Move to ' + str(pos_cm))
                board_agent.moveToCM(pos_cm)
                self.request.send(b'ok')
            # reset call searchhome by 'r'
            elif idata[0] == 'r':
                print('Search Home')
                board_agent.searchHome()
                self.request.send(b'ok')
                

class BoardAgent:
    def __init__(self, board):
        self.board = board
        self.board.configStepMode(L6470.STEP_FS)

    def searchHome(self):
        maxspd = self.board.getMaxSpeed()
        self.board.goUntil(0x00, L6470.FWD, maxspd) # MAX_SPEED
        goun_count = 0
        while self.board.busyCheck(): 
            if goun_count == 6: # to solve the case that starts from the position over touched the home switch, wait 3sec and stop
                self.board.softStop()  
            sleep(0.5)
            goun_count += 1

        self.board.releaseSw(0x00, L6470.REV)
        goun_count = 0
        while self.board.busyCheck(): 
            if goun_count == 2: # to solve the case that gountil reach the perfect position which causes releaseSw run continually
                self.board.softStop()  
            sleep(0.3)
            goun_count += 1
        self.goHome()

    def setBoardParameters(self, maxSpd, minSpd, acc):
        self.board.setMaxSpeed(maxSpd) 
        self.board.setMinSpeed(minSpd) 
        self.board.setAcc(acc)
        self.board.setDec(acc)

    def moveToCM(self, targetCm):
        rel_steps = int(targetCm * STEPS_PER_CM) - self.getCurPos() 
        while self.board.busyCheck(): sleep(0.1)
        if rel_steps > 0:
            self.board.move(L6470.REV, rel_steps)
        else:
            self.board.move(L6470.FWD, -rel_steps)
        while self.board.busyCheck(): sleep(0.1)
    
    def jogPlus(self):
        while self.board.busyCheck(): sleep(0.1)
        self.board.move(L6470.REV, 500)
        while self.board.busyCheck(): sleep(0.1)
        #board.releaseSw(0x00, L6470.FWD)
        #while board.busyCheck(): sleep(0.1)

    def jogMinus(self):
        while self.board.busyCheck(): sleep(0.1)
        self.moveToCM(0)
        while self.board.busyCheck(): sleep(0.1)

    def getCurPos(self):
        return -self.board.getPos() # getpos() return minus when go forward
    
    def getCurPosCM(self):
        return self.getCurPos() / STEPS_PER_CM
    
    def goHome(self):
        while self.board.busyCheck(): sleep(0.1)
        self.board.goHome()
        while self.board.busyCheck(): sleep(0.1)

    def isSwitchOn(self):
        #return GPIO.input(HOMESW_PIN) == GPIO.HIGH
        return (self.board.getStatus() & L6470.STATUS_SW_F) != 0
    
    def isBusy(self):
        return self.board.busyCheck()

    def isUVLO(self):
        return (self.board.getStatus() & L6470.STATUS_UVLO) == 0

    def isOCD(self):
        return (self.board.getStatus() & L6470.STATUS_OCD) == 0
    
    def isTHWRN(self):
        return (self.board.getStatus() & L6470.STATUS_TH_WRN) == 0
    
    def isTHSD(self):
        return (self.board.getStatus() & L6470.STATUS_TH_SD) == 0
    
    def isNOTPERFCMD(self):
        return (self.board.getStatus() & L6470.STATUS_NOTPERF_CMD) != 0
    
    def isWRONGCMD(self):
        return (self.board.getStatus() & L6470.STATUS_WRONG_CMD) != 0

    def checkMOTStatus(self):
        return (self.board.getStatus() & L6470.STATUS_MOT_STATUS)

def initSPI(bus, device):
	spi = spidev.SpiDev()
	spi.open(bus, device)
	spi.max_speed_hz = 4000000 # 500000  
	spi.mode = 3
	spi.lsbfirst = False
	return spi

if __name__ == '__main__':
    try:
        GPIO.setmode(GPIO.BCM)  # use GPIO number
        GPIO.setup(BUSY_PIN, GPIO.IN)
        
        spi = initSPI(0, 1)
        board = L6470(spi, RESET_PIN, BUSY_PIN)
        board_agent = BoardAgent(board)  
        board_agent.setBoardParameters(100, 50, 144)
        board_agent.searchHome()
    
        if board_agent.getCurPos() == 0:
            print('Motor Search Home Finshed!\n')

        srv = ThreadingTCPServer(('', PCR_PORT), ConnectionHandler)       
        print('Server running at 0.0.0.0:%d\n' % PCR_PORT)
        srv.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print('\nReceived keyboard interrupt, quitting threads.\n')
        g_is_accepted = False


    



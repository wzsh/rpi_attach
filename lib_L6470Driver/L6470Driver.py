#####################################################
# A simple library for L6470
#   Created by Zong-Sheng Wang @ 2019/05/20
# 
# L6470 class provides several command functions on datasheet as below
#   configStepMode(stepMode)
#		getStepMode()
#   setMaxSpeed(stepsPerSecond)
#   getMaxSpeed()
#   setMinSpeed(stepsPerSecond)
#   getMinSpeed()
#   setAcc(stepsPerSecond2)
#   setDec(stepsPerSecond2)
#   getPos()
#   move(dir, numSteps)
#   softStop()
#   hardStop()
#   resetPos()
#   releaseSw(action, dir)
#   goUntil(action, dir, stepsPerSec)
#   goHome()
#	busyCheck()
#	getStatus()

import spidev
import RPi.GPIO as GPIO
import math
from time import sleep

# L6470Base class contains some private support functions
# the functions of the class should not be invoked directly by programmer
class L6470Base:
	GET_PARAM = 0x20
	SET_PARAM = 0x00
	# configures
	MAX_SPEED = 0x07
	MIN_SPEED = 0x8
	STEP_MODE = 0x16	
	ACC = 0x05
	DECEL = 0x06
	# function register
	ABS_POS = 0x01
	MOVE = 0x40
	SOFT_STOP = 0xB0
	HARD_STOP = 0xB8
	RESET_POS = 0xD8
	GO_UNTIL = 0x82
	RELEASE_SW = 0x92
	GO_HOME = 0x70
	GET_STATUS = 0xD0
    
	def __init__(self, spi):
		self.spi = spi

	def SPIXfer(self, bytedata):
		temp = self.spi.xfer2([bytedata])
		return temp[0]
	
	def convertToBytes(self, data, size):
		return data.to_bytes(size, byteorder="little")

	def xferParam(self, value, bitLen):
		byteLen = math.ceil(bitLen/8)
		retVal = 0x00000000
		for i in range(byteLen):
			retVal <<= 8
			#pay_load = (value >> ((byteLen-i-1)*8)).to_bytes(4, byteorder="little")
			pay_load = self.convertToBytes(value >> ((byteLen-i-1)*8), 4)
			temp = self.SPIXfer(pay_load[0])
			retVal |= temp
		mask = 0xffffffff >> (32-bitLen)
		return retVal & mask
    
	def maxSpdCalc(self, stepsPerSec):
		temp = math.ceil(stepsPerSec*0.065536)
		if temp > 0x000003FF:
			return 0x000003FF
		else:
			return temp
    
	def minSpdCalc(self, stepsPerSec):
		temp = math.ceil(stepsPerSec / 0.238)
		if temp > 0x00000FFF:
			return 0x00000FFF
		else:
			return temp

	def accCalc(self, stepsPerSec2):
		temp = math.ceil(stepsPerSec2 * 0.137438)
		if temp > 0x00000FFF:
			return 0x00000FFF
		else:
			return temp
    
	def spdCalc(self, stepsPerSec):
		temp = int(stepsPerSec * 67.106)
		if temp > 0x000FFFFF:
			return 0x000FFFFF
		else:
			return temp
	

# L6470 class contains the interfaces and constants for programmer
class L6470(L6470Base):
	STEP_FS = 0x00
	# direction
	FWD = 0x01
	REV = 0x00
	STATUS_HIZ = 0x0001 # high when bridges are in HiZ mode
	STATUS_BUSY = 0x0002 # mirrors BUSY pin
	STATUS_SW_F = 0x0004 # low when switch open, high when closed
	STATUS_SW_EVN = 0x0008 # active high, set on switch falling edge, cleared by reading STATUS
	STATUS_DIR = 0x0010 # Indicates current motor direction. High is FWD, Low is REV.
	STATUS_NOTPERF_CMD = 0x0080 # Last command not performed.
	STATUS_WRONG_CMD = 0x0100 # Last command not valid.
	STATUS_UVLO = 0x0200 # Undervoltage lockout is active
	STATUS_TH_WRN = 0x0400 # Thermal warning
	STATUS_TH_SD = 0x0800 # Thermal shutdown
	STATUS_OCD = 0x1000 # Overcurrent detected
	STATUS_STEP_LOSS_A = 0x2000 # Stall detected on A bridge
	STATUS_STEP_LOSS_B = 0x4000 # Stall detected on B bridge
	STATUS_SCK_MOD = 0x8000 # Step clock mode is active

	STATUS_MOT_STATUS = 0x0060      # field mask
	STATUS_MOT_STATUS_STOPPED = (0x0000)<<5  #13 # Motor stopped
	STATUS_MOT_STATUS_ACCELERATION = (0x0001)<<5 # Motor accelerating
	STATUS_MOT_STATUS_DECELERATION = (0x0002)<<5 # Motor decelerating
	STATUS_MOT_STATUS_CONST_SPD = (0x0003)<<5 # Motor at constant speed
	
	def __init__(self, spi, resetPin, busyPin=-1):
		self.reset_pin = resetPin
		self.busy_pin = busyPin
		self.spi = spi
		
		if busyPin >= 0:
			GPIO.setup(self.busy_pin, GPIO.IN)
		GPIO.setup(self.reset_pin, GPIO.OUT)
		
		GPIO.output(self.reset_pin, GPIO.LOW)
		sleep(0.001)
		GPIO.output(self.reset_pin, GPIO.HIGH)

		L6470Base.__init__(self, spi)

	def __del__(self):
		GPIO.cleanup(self.reset_pin)

	def configStepMode(self, stepMode):
		pay_load = self.convertToBytes(self.STEP_MODE | self.GET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		stepModeConfig = self.xferParam(0, 8)
		stepModeConfig &= 0xF8
		stepModeConfig |= (stepMode&0x07)
	
		# Now push the change to the chip.
		pay_load = self.convertToBytes(self.STEP_MODE | self.SET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		self.xferParam(stepModeConfig, 8)

	def getStepMode(self):
		pay_load = self.convertToBytes(self.STEP_MODE | self.GET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		temp = self.xferParam(0, 8)
		return temp & 0x07

	def setMaxSpeed(self, stepsPerSecond):
		intSpeed = self.maxSpdCalc(stepsPerSecond)
		pay_load = self.convertToBytes(self.MAX_SPEED | self.SET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		self.xferParam(intSpeed, 10)

	def getMaxSpeed(self):
		#pay_load = (self.MAX_SPEED | self.GET_PARAM).to_bytes(1, byteorder="little")
		pay_load = self.convertToBytes(self.MAX_SPEED | self.GET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		temp = self.xferParam(0, 10)
		return (temp & 0x000003FF) / 0.065536

	def setMinSpeed(self, stepsPerSecond):
		intSpeed = self.minSpdCalc(stepsPerSecond)
		# keep LSPD_OPT
		pay_load = self.convertToBytes(self.MIN_SPEED | self.GET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		temp = self.xferParam(0, 13)
		temp &= 0x00001000
		# push the change
		pay_load = self.convertToBytes(self.MIN_SPEED | self.SET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		self.xferParam(intSpeed|temp, 13)
	
	def getMinSpeed(self):
		pay_load = self.convertToBytes(self.MIN_SPEED | self.GET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		temp = self.xferParam(0, 13)
		return (temp & 0x00000FFF) * 0.238

	def setAcc(self, stepsPerSecond2):
		intAcc = self.accCalc(stepsPerSecond2)
		pay_load = self.convertToBytes(self.ACC | self.SET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		self.xferParam(intAcc ,12)

	def setDec(self, stepsPerSecond2):
		intDec = self.accCalc(stepsPerSecond2)
		pay_load = self.convertToBytes(self.DECEL | self.SET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		self.xferParam(intDec ,12)

	def getPos(self):
		pay_load = self.convertToBytes(self.ABS_POS | self.GET_PARAM, 1)
		self.SPIXfer(pay_load[0])
		temp = self.xferParam(0, 22)

		if temp & 0x00200000:
			temp |= 0xffc00000
		return temp | (-(temp & 0x80000000))  # conver to signed int32

	def move(self, dir, numSteps):
		pay_load = self.convertToBytes(self.MOVE | dir, 1)
		self.SPIXfer(pay_load[0])
		if numSteps > 0x3FFFFF:
			numSteps = 0x3FFFFF
		pay_load = self.convertToBytes(numSteps, 3)
		#print(BytesToHex(pay_load))
		for i in range(2, -1, -1): # start, end-1, steps
			self.SPIXfer(pay_load[i])

	def softStop(self):
		self.SPIXfer(self.SOFT_STOP)

	def hardStop(self):
		self.SPIXfer(self.HARD_STOP)

	def resetPos(self):
		self.SPIXfer(self.RESET_POS)
	
	# action=0: RESET ABS_POS to 0x00, action=1: copy ABS_POS to MARK
	def releaseSw(self, action, dir):
		pay_load = self.convertToBytes(self.RELEASE_SW | action | dir, 1)
		self.SPIXfer(pay_load[0])

	def goUntil(self, action, dir, stepsPerSec):
		pay_load = self.convertToBytes(self.GO_UNTIL | action | dir, 1)
		self.SPIXfer(pay_load[0])
		intSpeed = self.spdCalc(stepsPerSec)
		if intSpeed > 0x3FFFFF:
			intSpeed = 0x3FFFFF
		pay_load = self.convertToBytes(intSpeed, 3)
		#print(BytesToHex(pay_load))
		for i in range(2, -1, -1): # start, end-1, steps
			self.SPIXfer(pay_load[i])

	def goHome(self):
		self.SPIXfer(self.GO_HOME)

	def busyCheck(self):
		if self.busy_pin == -1:
			return (self.getStatus() & self.STATUS_BUSY) == 0
		else:
			return GPIO.input(self.busy_pin) != GPIO.HIGH

	def getStatus(self):
		temp = 0
		self.SPIXfer(self.GET_STATUS)
		MSByte = self.SPIXfer(0)
		LSByte = self.SPIXfer(0)
		temp |= MSByte
		temp = (temp << 8) | LSByte
		return temp



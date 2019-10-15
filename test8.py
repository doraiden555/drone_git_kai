import numpy as np 
from numpy import linalg as la 
import time 
import spidev 
import sys 
import navio.util 
import navio.mpu9250 
import navio.adc
import navio.util
import navio.rcinput
import navio.pwm

del_t = 0.01 #sec 
g = 0 #m/s^2 
x_old = np.array([0,0,0,0,0,0,0,0,0],dtype=np.float) #m, m/s, rad 
omega = np.array([0,0,0],dtype=np.float) #rad/sec 
acc = np.array([0,0,-g],dtype=np.float) #m/s^2 
gamma = 500 # 0~1000 
P_old = np.identity(9)*gamma 
I_9 = np.identity(9) 
acc_noise=0.6
gyro_noise=0.0003468268
QQ = np.diag([0,0,0,acc_noise,acc_noise,acc_noise,gyro_noise,gyro_noise,gyro_noise]) 
RR = np.diag([0.5,0.5,0.5])


roll_max_angle  = 30 *np.pi/180 #rad
pitch_max_angle = 30 *np.pi/180 #rad
e_roll_old = 0 #default

ll = 165 #mm
Ct = 0.0374
Cm = 0.3428
CC = Cm / Ct
Kp_roll = 16.088
Kd_roll = 10.242

imu = navio.mpu9250.MPU9250()
rcin = navio.rcinput.RCInput()

alfa = np.array([0.8,0.8,0.8],dtype=np.float)
m9a_low_old = np.array([0,0,9.81],dtype=np.float)
m9g_low_old = np.array([0,0,0],dtype=np.float)


##############################################
navio.util.check_apm()
adc = navio.adc.ADC()
results = [0] * adc.channel_count

pwm1 = navio.pwm.PWM(0)
pwm1.set_period(400)

pwm2 = navio.pwm.PWM(1)
pwm2.set_period(400)

pwm3 = navio.pwm.PWM(2)
pwm3.set_period(400)

pwm4 = navio.pwm.PWM(3)
pwm4.set_period(400)

if imu.testConnection():
    print("Connection established: True") 
else:
    sys.exit("Connection established: False") 
imu.initialize() 
time.sleep(1)
##############################################

while True:
    start =time.time()
    
    m9a, m9g, m9m = imu.getMotion9() #measure
    #results[5] = adc.read(5) #measure

    m9a_low = alfa*m9a_low_old + (1-alfa)*m9a
    m9g_low = alfa*m9g_low_old + (1-alfa)*m9g

    m9a_low_old = m9a_low
    m9g_low_old = m9g_low
        
#    print "{:+7.3f}".format(-x_new[:,0][7]*180/np.pi),",","{:+7.3f}".format(x_new[:,0][6]*180/np.pi),",","{:+7.3f}".format(x_new[:,0][8]*180/np.pi)
    print "{:+7.3f}".format(m9g[0]),",","{:+7.3f}".format(m9g[1]),",","{:+7.3f}".format(m9g[2])#,",","{:+7.3f}".format(m9a_low[1])

#########################################################################################

    
    roll  = (float(rcin.read(3))-1514) * roll_max_angle / 410
    pitch = (float(rcin.read(1))-1514) * pitch_max_angle / 410
    throt = (float(rcin.read(2))-1104) * 14000 / 820

#    print roll,pitch,throt

#    print "{:+7.3f}".format(e_roll*180/np.pi),",","{:+7.3f}".format(e_roll_dot*180/np.pi)
     
    f_total    = throt
#    print int(tau_roll)

    omega2_1 = f_total/ (4*Ct) # - tau_pitch/ll - tau_yaw/CC) / (4*Ct)
    omega2_2 = f_total/ (4*Ct) # - tau_pitch/ll + tau_yaw/CC) / (4*Ct)
    omega2_3 = f_total/ (4*Ct) # + tau_pitch/ll - tau_yaw/CC) / (4*Ct)
    omega2_4 = f_total/ (4*Ct) # + tau_pitch/ll + tau_yaw/CC) / (4*Ct)

    if   omega2_1 < 0:
        omega2_1 = 0
    if omega2_1 > 110000:
        omega2_1 = 110000
    if omega2_2 < 0:
        omega2_2 = 0
    if omega2_2 > 110000:
        omega2_2 = 110000
    if omega2_3 < 0:
        omega2_3 = 0
    if omega2_3 > 110000:
        omega2_3 = 110000
    if omega2_4 < 0:
        omega2_4 = 0
    if omega2_4 > 110000:
        omega2_4 = 110000
    
#    print omega2_1,omega2_2,omega2_3,omega2_4

    omega_1 = np.sqrt(omega2_1+1)
    omega_2 = np.sqrt(omega2_2+1)
    omega_3 = np.sqrt(omega2_3+1)
    omega_4 = np.sqrt(omega2_4+1)
    
    duty1 = 1.8616*omega_1 + 1056.5
    duty2 = 1.8616*omega_2 + 1056.5
    duty3 = 1.8616*omega_3 + 1056.5
    duty4 = 1.8616*omega_4 + 1056.5

#    print int(duty1) , int(duty2)
    
    pwm1.set_duty_cycle(int(duty1)*0.001)
    pwm2.set_duty_cycle(int(duty2)*0.001)
    pwm3.set_duty_cycle(int(duty3)*0.001)
    pwm4.set_duty_cycle(int(duty4)*0.001)

    elapsed_time = time.time() - start
#    print elapsed_time
    sleep_time = 0.01 - elapsed_time
    time.sleep(sleep_time)
    

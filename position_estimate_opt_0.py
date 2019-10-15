import numpy as np
from numpy import linalg as la
import time
import spidev
import sys
import navio.util
import navio.mpu9250
import navio.adc
import navio.util
import serial
import threading
import VL53L0X

import csv
import datetime

del_t = 0.01 #sec
g = 0 #m/s^2
x_old = np.array([0,0,0,0,0,0,0,0,0],dtype=np.float) #m, m/s, rad
omega = np.array([0,0,0],dtype=np.float) #rad/sec
acc = np.array([0,0,-g],dtype=np.float) #m/s^2
gamma = 800 # 0~1000
P_old = np.identity(9)*gamma
I_9 = np.identity(9)
acc_noise=0.001
gyro_noise=0.0003468268
QQ = np.diag([0,0,0,acc_noise,acc_noise,acc_noise,gyro_noise,gyro_noise,gyro_noise])
RR = np.diag([0.4,0.4,0.4,0.01,0.1,0.1])

alfa = np.array([0.8244,0.8244,0.8244],dtype=np.float)
m9a_low_old = np.array([0,0,0],dtype=np.float)
m9g_low_old = np.array([0,0,0],dtype=np.float)

st = datetime.datetime.fromtimestamp(time.time()).strftime('%m_%d_%H-%M-%S')+".csv"
f = open("./logs/Angle_opt_test"+st, "w")
logger = csv.writer(f)
logger.writerow(('timestamp','pitch','roll','yaw','x_es','y_es','z_es','vx_es','vy_es','vz_es','deltaX','deltaY','deltaX_sum','deltaY_sum','height'))


global DD

ser = serial.Serial("/dev/ttyAMA0" , 9600)

def compute():

    global DD, height, deltaX, deltaY, deltaX_sum, deltaY_sum, deltaX_sum_ar, deltaY_sum_ar, time_lap, x_new
    data = None
    DD = None
    time_b = 0
    deltaX_sum = 0
    deltaY_sum = 0

    while 1:
        data = ser.readline()
        DD=data.split(",")
        DD[4]= DD[4].strip('\r\n')
        height  = int(DD[0]) * 0.001 #m
        deltaX = -float(DD[2])  * 0.001  #m/s
        deltaY = -float(DD[1])  * 0.001  #m/s
        deltaX_sum_ar = float(DD[3])  * 0.001
        deltaY_sum_ar = float(DD[4])  * 0.001
        time_lap = time.time() - time_b
        time_b = time.time()
        deltaX_sum = deltaX_sum + deltaX * 0.042
        deltaY_sum = deltaY_sum + deltaY * 0.042 

        #time.sleep(0.042)

        

##############################################
imu = navio.mpu9250.MPU9250()

navio.util.check_apm()
adc = navio.adc.ADC()
results = [0] * adc.channel_count

if imu.testConnection():
    print("Connection established: True")
else:
    sys.exit("Connection established: False")
imu.initialize()
time.sleep(1)
##############################################
i = 0
gyro_x=0
gyro_y=0
gyro_z=0

while i<100:

    m9a, m9g, m9m = imu.getMotion9()

    gyro_x = gyro_x + m9g[0]
    gyro_y = gyro_y + m9g[1]
    gyro_z = gyro_z + m9g[2]

    g = g + np.sqrt(m9a[0]*m9a[0] + m9a[1]*m9a[1] + m9a[2]*m9a[2])

    i= i+1

    time.sleep(0.05)

bias_gyro_x = gyro_x/100
bias_gyro_y = gyro_y/100
bias_gyro_z = gyro_z/100
g=g/100

print(bias_gyro_x,bias_gyro_y,bias_gyro_z,g)
print('Calibration end')

time.sleep(0.5)

th1 = threading.Thread(target=compute)
th1.start()

time.sleep(1)

print u'start? (y/n)'

start_flag = raw_input('>>')

if start_flag != "y":
    print('end!!')


ser.write(b'A')

while start_flag == "y":
    start =time.time()
    global deltaX, deltaX_sum, deltaY, deltaY_sum, height, time_lap, deltaX_sum_ar, deltaY_sum_ar, x_new

    s_phi = np.sin(x_old[6])
    c_phi = np.cos(x_old[6])
    s_the = np.sin(x_old[7])
    c_the = np.cos(x_old[7])
    t_the = np.tan(x_old[7])
    s_psi = np.sin(x_old[8])
    c_psi = np.cos(x_old[8])


    x_pre = np.array([[x_old[0]+x_old[3]*del_t],
                      [x_old[1]+x_old[4]*del_t],
                      [x_old[2]+x_old[5]*del_t],
                      [x_old[3]+c_the*c_psi*acc[0]*del_t+(s_the*c_psi*s_phi-s_psi*c_phi)*acc[1]*del_t+(s_the*c_psi*c_phi+s_psi*s_phi)*acc[2]*del_t],
                      [x_old[4]+c_the*s_psi*acc[0]*del_t+(s_the*s_psi*s_phi+c_psi*c_phi)*acc[1]*del_t+(s_the*s_psi*c_phi-c_psi*s_phi)*acc[2]*del_t],
                      [x_old[5]-s_the*acc[0]*del_t+c_the*s_phi*acc[1]*del_t+c_the*c_phi*acc[2]*del_t+g*del_t],
                      [x_old[6] + omega[0]*del_t+s_phi*t_the*omega[1]*del_t + c_phi*t_the*omega[2]*del_t],
                      [x_old[7] + c_phi*omega[1]*del_t - s_phi*omega[2]*del_t],
                      [x_old[8] + s_phi/c_the*omega[1]*del_t + c_phi/c_the*omega[2]*del_t]
                      ],dtype=np.float)
    #print x_old[3]+c_the*c_psi*acc[0]*del_t+(s_the*c_psi*s_phi-s_psi*c_phi)*acc[1]*del_t+(s_the*c_psi*c_phi+s_psi*s_phi)*acc[2]*del_t
########################################################################################

    AA = np.array([[1,0,0,del_t,0,0,0,0,0],
                   [0,1,0,0,del_t,0,0,0,0],
                   [0,0,1,0,0,del_t,0,0,0],
                   [0,0,0,1,0,0, (s_the*c_psi*c_phi+s_psi*s_phi)*acc[1]*del_t + (-s_the*c_psi*s_phi+s_psi*c_phi)*acc[2]*del_t,
                                 -s_the*c_psi*acc[0]*del_t + c_the*c_psi*s_phi*acc[1]*del_t + c_the*c_psi*c_phi*acc[2]*del_t,
                                 -c_the*s_psi*acc[0]*del_t + (-s_the*s_psi*s_phi-c_psi*c_phi)*acc[1]*del_t + (-s_the*s_psi*c_phi+c_psi*s_phi)*acc[2]*del_t],
                   [0,0,0,0,1,0, (s_the*s_psi*c_phi-c_psi*s_phi)*acc[1]*del_t + (-s_the*s_psi*s_phi-c_psi*c_phi)*acc[2]*del_t,
                                 -s_the*s_psi*acc[0]*del_t + c_the*s_psi*s_phi*acc[1]*del_t + c_the*s_psi*s_phi*acc[2]*del_t,
                                  c_the*c_psi*acc[0]*del_t + (s_the*s_psi*s_phi-s_psi*c_phi)*acc[1]*del_t + (s_the*c_psi*c_phi+s_psi*s_phi)*acc[2]*del_t],
                   [0,0,0,0,0,1, c_the*c_phi*acc[1]*del_t - c_the*s_phi*acc[2]*del_t, -c_the*acc[0]*del_t - s_the*s_phi*acc[1] - s_the*c_phi*acc[2]*del_t,0],
                   [0,0,0,0,0,0, 1+c_phi*t_the*omega[1]*del_t-s_phi*t_the*omega[2]*del_t, s_phi/(c_the*c_the)*omega[1]*del_t+c_phi/(c_the*c_the)*omega[2]*del_t,0],
                   [0,0,0,0,0,0, -s_phi*omega[1]*del_t-c_phi*omega[2]*del_t,1,0],
                   [0,0,0,0,0,0, c_phi/c_the*omega[1]*del_t-s_phi/c_the*omega[2]*del_t, s_phi*t_the/c_the*omega[1]*del_t+c_phi*t_the/c_the*omega[2]*del_t,0]
                   ],dtype=np.float)

    s_phi_pre = np.sin(x_pre[6])
    c_phi_pre = np.cos(x_pre[6])
    s_the_pre = np.sin(x_pre[7])
    c_the_pre = np.cos(x_pre[7])


    CC = np.array([[0,0,0,0,0,0,0,c_the_pre*g,0],
                   [0,0,0,0,0,0,-c_the_pre*c_phi_pre*g,s_the_pre*s_phi_pre*g,0],
                   [0,0,0,0,0,0, c_the_pre*s_phi_pre*g,s_the_pre*c_phi_pre*g,0],
                   [0,0,1,0,0,0,0,0,0],
                   [0,0,0,1,0,0,0,0,0],
                   [0,0,0,0,1,0,0,0,0]
                   ],dtype=np.float)

#########################################################################################
    P_pre = AA.dot(P_old.dot(AA.T)) + QQ

    G1 = la.inv(CC.dot(P_pre.dot(CC.T)) + RR)
    GG = P_pre.dot((CC.T).dot(G1))
#########################################################################################
    h_pre = np.array([[s_the_pre*g],
                      [-c_the_pre*s_phi_pre*g],
                      [-c_the_pre*c_phi_pre*g],
                      [x_pre[:,0][2]],
                      [x_pre[:,0][3]],
                      [x_pre[:,0][4]]
                      ], dtype=np.float)

    m9a, m9g, m9m = imu.getMotion9() #measure

    m9a_low = m9a_low_old * alfa + m9a * (1-alfa)
    m9g_low = m9g_low_old * alfa + m9g * (1-alfa)


    m9a_low_old = m9a_low
    m9g_low_old = m9g_low

    acc = np.array([-m9a_low[0],-m9a_low[1],-m9a_low[2]])

    

    omega = np.array([(m9g[0]-bias_gyro_x),(m9g[1]-bias_gyro_y),m9g[2]-bias_gyro_z])

    # DD[4]= DD[4].strip('\r\n')
    # height  = int(DD[0]) * 0.001
    # deltaX = float(DD[1])*0.001
    # deltaY = float(DD[2])*0.001
    # deltaX_sum = float(DD[3])*0.001
    # deltaY_sum = float(DD[4])*0.001


    yy = np.array([[-m9a_low[0]],
                   [-m9a_low[1]],
                   [-m9a_low[2]],
                   [height],
                   [deltaX],
                   [deltaY]
                   ],dtype=np.float)

    P_new = (I_9-GG.dot(CC)).dot(P_pre)
    x_new = x_pre + GG.dot(yy-h_pre)
   

    #print "{:+7.3f}".format(x_new[:,0][0]),",","{:+7.3f}".format(x_new[:,0][1]),",","{:+7.3f}".format(x_new[:,0][2])
    #print "{:+7.3f}".format(x_new[:,0][6]),",","{:+7.3f}".format(x_new[:,0][7]),",","{:+7.3f}".format(x_new[:,0][8]),",","{:+7.3f}".format(deltaX_sum),",","{:+7.3f}".format(deltaY_sum)
    print "{:+7.3f}".format(x_new[:,0][6]),"{:+7.3f}".format(x_new[:,0][7]),"{:+7.3f}".format(x_new[:,0][8]),"{:+7.3f}".format(deltaX),"{:+7.3f}".format(deltaY),"{:+7.3f}".format(deltaX_sum),"{:+7.3f}".format(deltaY_sum), "{:+7.3f}".format(deltaX_sum_ar), "{:+7.3f}".format(deltaY_sum_ar),"{:+7.3f}".format(height),"{:+7.3f}".format(time_lap)
    
    row = ( "{:6.3f}".format(time.time()), "{:+7.3f}".format(x_new[:,0][6]),"{:+7.3f}".format(x_new[:,0][7]),"{:+7.3f}".format(x_new[:,0][8]),"{:+7.3f}".format(x_new[:,0][0]),"{:+7.3f}".format(x_new[:,0][1]),"{:+7.3f}".format(x_new[:,0][2]),"{:+7.3f}".format(x_new[:,0][3]),"{:+7.3f}".format(x_new[:,0][4]),"{:+7.3f}".format(x_new[:,0][5]),"{:+7.3f}".format(deltaX),"{:+7.3f}".format(deltaY),"{:+7.3f}".format(deltaX_sum),"{:+7.3f}".format(deltaY_sum),"{:+7.3f}".format(height))
    logger.writerow(row)


    elapsed_time = time.time() - start

    

    if elapsed_time < 0.01:

        sleep_time = 0.01 - elapsed_time
        time.sleep(sleep_time)

    P_old = P_new#[:,0]
    x_old = x_new[:,0]

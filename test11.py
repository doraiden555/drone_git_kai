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
acc_noise=0.01
gyro_noise=0.0003468268
QQ = np.diag([0,0,0,acc_noise,acc_noise,acc_noise,gyro_noise,gyro_noise,gyro_noise]) 
RR = np.diag([0.1,0.1,0.1])


roll_max_angle  = 20 *np.pi/180 #rad
pitch_max_angle = 20 *np.pi/180 #rad
yawrate_max     = 90 *np.pi/180 #rad/sec

e_roll_old  = 0 #default
e_pitch_old = 0

ll = 165 #mm
Ct = 0.0374
Cm = 0.3428
CC1 = Cm / Ct
Kp_roll  = 197
Kd_roll  = 100
Kp_pitch = 231.5
Kd_pitch = 120
Kp_yaw   = 80

imu = navio.mpu9250.MPU9250()

alfa = np.array([0.9,0.9,0.9],dtype=np.float)
m9a_low_old = np.array([0,0,9.81],dtype=np.float)
m9g_low_old = np.array([0,0,0],dtype=np.float)


##############################################
navio.util.check_apm()

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

    time.sleep(0.1)

bias_gyro_x = gyro_x/100
bias_gyro_y = gyro_y/100
bias_gyro_z = gyro_z/100
g=g/100
print(bias_gyro_x,bias_gyro_y,bias_gyro_z,g)
print('Calibration end')

time.sleep(0.5)

while True:
    start =time.time()
    
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
                   [0,0,0,0,0,0, c_phi/c_the*omega[1]*del_t-s_phi/c_the*omega[2]*del_t, s_phi*t_the/c_the*omega[1]*del_t+c_phi*t_the/c_the*omega[2]*del_t,1]
                   ],dtype=np.float)

    s_phi_pre = np.sin(x_pre[6])
    c_phi_pre = np.cos(x_pre[6])
    s_the_pre = np.sin(x_pre[7])
    c_the_pre = np.cos(x_pre[7])

    CC = np.array([[0,0,0,0,0,0,0,c_the_pre*g,0],
                   [0,0,0,0,0,0,-c_the_pre*c_phi_pre*g,s_the_pre*s_phi_pre*g,0],
                   [0,0,0,0,0,0, c_the_pre*s_phi_pre*g,s_the_pre*c_phi_pre*g,0],
                   ],dtype=np.float)
    
#########################################################################################
    P_pre = AA.dot(P_old.dot(AA.T)) + QQ
    
    G1 = la.inv(CC.dot(P_pre.dot(CC.T)) + RR)
    GG = P_pre.dot((CC.T).dot(G1))
######################################################################################### 
    h_pre = np.array([s_the_pre*g,
                      -c_the_pre*s_phi_pre*g,
                      -c_the_pre*c_phi_pre*g
                      ], dtype=np.float)
    m9a, m9g, m9m = imu.getMotion9() #measure
    #results[5] = adc.read(5) #measure

    m9a_low = m9a_low_old * alfa + m9a * (1-alfa)
    m9g_low = m9g_low_old * alfa + m9g * (1-alfa)

    m9a_low_old = m9a_low
    m9g_low_old = m9g_low
    
    omega = np.array([(m9g[0]-bias_gyro_y),(m9g[1]-bias_gyro_x),m9g[2]-bias_gyro_z])

    yy = np.array([[-m9a_low[0]],
                   [-m9a_low[1]],
                   [-m9a_low[2]]])

    P_new = (I_9-GG.dot(CC)).dot(P_pre)
    x_new = x_pre + GG.dot(yy-h_pre)
#    print "{:+7.3f}".format(-m9a[1]),",","{:+7.3f}".format(m9a[0]),",","{:+7.3f}".format(-m9a[2])
#    print yy
#    print "{:+7.3f}".format(omega[0]),",","{:+7.3f}".format(omega[1]),",","{:+7.3f}".format(omega[2])   
    print "{:+7.3f}".format(x_new[:,0][6]*180/np.pi),",","{:+7.3f}".format(x_new[:,0][7]*180/np.pi),",","{:+7.3f}".format(x_new[:,0][8]*180/np.pi)
#    print "{:+7.3f}".format(m9a_low[0]),",","{:+7.3f}".format(m9a_low[1]),",","{:+7.3f}".format(m9a_low[2])

#########################################################################################

    elapsed_time = time.time() - start
    #print elapsed_time

    if elapsed_time < 0.01:
        
        sleep_time = 0.01 - elapsed_time
        time.sleep(sleep_time)
    
    P_old = P_new[:,0]
    x_old = x_new[:,0]

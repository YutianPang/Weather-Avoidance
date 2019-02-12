#!/home/anaconda3 python
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 2, 2019
Last Modified on Feb 11, 2019

@author: Nan Xu
@modified: Yutian Pang

"""

import math
import time
import pandas as pd
from utils import *
import numpy as np
from netCDF4 import Dataset


def lat2y(a):
    Radius = 6378137.0  # Radius of Earth
    return math.log(math.tan(math.pi / 4 + math.radians(a) / 2)) * Radius


def lot2x(a):
    Radius = 6378137.0  # Radius of Earth
    return math.radians(a) * Radius


class weather_cube_generator(object):

    def __init__(self, cfg):
        self.cube_size = cfg['cube_size']
        self.resize_ratio = cfg['resize_ratio']
        self.weather_path = cfg['weather_path']
        self.date = cfg['date']
        self.downsample_ratio = cfg['downsample_ratio']
        self.call_sign = cfg['call_sign']
        print("Processing flight {}_{}".format(self.date, self.call_sign))

        self.traj = pd.read_csv(cfg['trajectory_path'])
        self.traj = self.traj.iloc[::self.downsample_ratio, :].reset_index()  # downsample trajectory

    def get_cube(self):

        y_max, y_min, x_max, x_min = lat2y(58.874), lat2y(19.356), lot2x(-61.651), lot2x(-134.349)

        dim = np.int32(np.linspace(1, len(self.traj)-1, len(self.traj)-1))
        nn = np.int32(np.linspace(1, self.cube_size, self.cube_size))
        nn2 = np.int32(np.linspace(2, self.cube_size, self.cube_size-1))

        s_y = np.linspace(y_min, y_max, int(3520/self.resize_ratio))
        s_x = np.linspace(x_min, x_max, int(5120/self.resize_ratio))

        step_x = s_x[1] - s_x[0]
        step_y = s_y[1] - s_y[0]

        weather_tensor = []
        point_t = []

        x = self.traj['LONGITUDE']
        y = self.traj['LATITUDE']
        t = self.traj['UNIX TIME']

        start = time.time()

        #for i in range(1, 10):
        for i in dim:

            # compute index
            print("Working on Point {}/{}".format(1+i, len(self.traj)))

            # check weather file exists at time i
            weather_file = check_convective_weather_files(self.weather_path, t[i])
            data = Dataset(weather_file)
            values = np.squeeze(data.variables['ECHO_TOP'])

            # search direction
            dx_ = x[i] - x[i-1] + 1e-8
            dire_x = dx_/np.abs(dx_)
            dy_ = y[i] - y[i-1] + 1e-8
            dire_y = dy_ / np.abs(dy_)

            # Line 1  Along the Traj
            slope_m = (lat2y(y[i]) - lat2y(y[i-1]) + 1e-8) / (lot2x(x[i]) - lot2x(x[i-1]) + 1e-8)
            angle_m = math.atan(slope_m)

            # Line 2 Bottom Boundary
            slope_b = -(lot2x(x[i]) - lot2x(x[i-1]) + 1e-8) / (lat2y(y[i]) - lat2y(y[i-1]) + 1e-8)
            angle_b = math.atan(slope_b)

            delta_Xb = np.abs(step_x * self.cube_size * math.cos(angle_b))
            Y_b = lambda s: slope_b * (s - lot2x(x[i])) + lat2y(y[i])
            Xb_2 = lot2x(x[i]) + 0.5 * delta_Xb  # x-coord right-bottom corner
            Yb_2 = Y_b(Xb_2)  # y-coord right-bottom corner

            # point count
            h = 0

            # store 20x20 values
            weather_v = np.zeros((self.cube_size**2, 1))

            # save weather values at traj point
            x_p = np.int(round((lot2x(x[i]) - x_min)/step_x))
            y_p = np.int(round((lat2y(y[i]) - y_min) / step_y))
            point_t_values = values[values.shape[0] - self.resize_ratio*y_p][self.resize_ratio*x_p]
            point_t.append((x_p, y_p, point_t_values))

            # Loop to generate all points coordinates
            for i in nn:

                d_x0 = np.abs(step_y * math.cos(angle_m))
                d_y0 = np.abs(step_y * math.sin(angle_m))

                Xb_2i = np.int(round((Xb_2 - x_min) / step_x))
                Yb_2i = np.int(round((Yb_2 - y_min) / step_y))

                point = (Xb_2i, Yb_2i)

                weather_v[h] = values[values.shape[0] - self.resize_ratio*Yb_2i][self.resize_ratio*Xb_2i]

                h = h + 1

                for j in nn2:

                    d_x = np.abs(step_x * math.cos(angle_b))

                    Y_b2 = lambda s: slope_b * (s - Xb_2) + Yb_2
                    x_ = Xb_2 - d_x * (j - 1)
                    y_ = Y_b2(x_)

                    x_i = np.int(round((x_ - x_min) / step_x))
                    y_i = np.int(round((y_ - y_min) / step_y))

                    point = (x_i, y_i)  # index of weather

                    weather_v[h] = values[values.shape[0] - self.resize_ratio*y_i][self.resize_ratio*x_i]

                    h = h + 1

                Xb_2 = Xb_2 + dire_x * d_x0
                Yb_2 = Yb_2 + dire_y * d_y0

            weather_v = weather_v.reshape(self.cube_size, self.cube_size)
            weather_tensor.append(weather_v)

        print("Total time for one trajectory is: ", time.time() - start)

        # save data
        np.save('weather data/ET/{}_{}'.format(self.date, self.call_sign), weather_tensor)
        np.save('weather data/ET_point/{}_{}'.format(self.date, self.call_sign), point_t)


if __name__ == '__main__':
    
    cfg ={'cube_size': 20,
          'resize_ratio': 1,
          'downsample_ratio': 5,
          'date': 20170405,
          'call_sign': 'AAL1',
          'weather_path': '/mnt/data/Research/data/'}
    cfg['trajectory_path'] = 'track_point_{}_JFK2LAX/{}_{}.csv'.format(cfg['date'], cfg['call_sign'], cfg['date'])

    fun = weather_cube_generator(cfg)
    fun.get_cube()



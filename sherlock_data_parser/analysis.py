# This file can filter all the data and divide them into two part. 
# One is the deviation correlated with weather while another one is not.

import numpy as np
import os
import csv
import itertools
from shapely.geometry import LineString
import math


def clear_all():

    folder = './corr_weather'
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            # elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)

    folder = './uncorr_weather'
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            # elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)

    # remove y_train_corr.csv
    if os.path.exists("y_train_corr.csv"):
        os.remove("y_train_corr.csv")
    else:
        print("The file y_train_corr.csv does not exist")

    # remove y_train_uncorr.csv
    if os.path.exists("y_train_uncorr.csv"):
        os.remove("y_train_uncorr.csv")
    else:
        print("The file y_train_uncorr.csv does not exist")


if __name__ == '__main__':

    clear_all()

    threshold = 1

    # load npy file name in a list
    x_train_list = sorted([x.split('.')[0] for x in os.listdir("x_train_npy/")], key=int)

    # load csv files
    csv_f1 = csv.reader(open('y_train.csv'))
    csv_f2 = csv.reader(open('start_and_end.csv'))

    # load lat and lon
    lat = np.load('lat.npy')
    lon = np.load('lon.npy')

    # npy file sequence index
    c = 0

    for y_train, start_end in itertools.izip(csv_f1, csv_f2):

        # load x train array
        x_train = np.load("x_train_npy/" + x_train_list[c] + ".npy")

        r1 = (float(start_end[10]) - float(start_end[8]))/100
        r2 = (float(start_end[11]) - float(start_end[9]))/100

        x1 = round((float(start_end[4]) - float(start_end[8]))/r1)
        x2 = round((float(start_end[6]) - float(start_end[8]))/r1)

        y1 = round((float(start_end[5]) - float(start_end[9]))/r2)
        y2 = round((float(start_end[7]) - float(start_end[9]))/r2)

        [x1, x2, y1, y2] = np.clip([x1, x2, y1, y2], 0, 99)

        ls = LineString([(x1, y1), (x2, y2)])

        xy = []
        for f in range(0, int(math.ceil(ls.length)) + 1):
            p = ls.interpolate(f).coords[0]
            pr = map(round, p)
            if pr not in xy:
                xy.append(pr)

        diagonal_idx = np.array(xy, 'i')

        sum = 0
        for i in range(len(diagonal_idx)):
            sum += x_train[diagonal_idx[i, 0], diagonal_idx[i, 1]]


        if sum >= threshold:

            np.save('corr_weather/' + str(c) + '.npy', x_train)

            with open('y_train_corr.csv', 'a') as f1:
                f1writer = csv.writer(f1, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                f1writer.writerow(np.asarray(start_end[0:2] + y_train + start_end[2:4]))
        else:

            np.save('uncorr_weather/' + str(c) + '.npy', x_train)

            with open('y_train_uncorr.csv', 'a') as f2:
                f2writer = csv.writer(f2, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                f2writer.writerow(np.asarray(start_end[0:2] + y_train + start_end[2:4]))

        c += 1




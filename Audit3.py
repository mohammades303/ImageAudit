__author__ = 'Mohammad'

import cv2
import csv
from matplotlib import pyplot as plt
import numpy as np
import os.path
import glob
from Orientation_check import Orientation
from Detect_colorChecker import detect_card
from Color_correction import Color_corect
import datetime
from time import mktime
from time import time
from scipy import ndimage
import colorbalance
from PIL import Image



Color_Th = 120 # a value between 0 and 255
template = cv2.imread('card4.jpg',0)
'''
EXPT_ID = 'BVZ0068'
LOCATION = 'GC37L'
INTERVAL = '5'
SUNRISE = '7'
SUNSET = '18'
EXPT_START = '2016_04_10'
EXPT_END = '2016_04_20'
'''
EXPT_ID = 'BVZ0051'
LOCATION = 'GC035L'
INTERVAL = '20'
SUNRISE = '4'
SUNSET = '5'
EXPT_START = '2015_06_19'
EXPT_END = '2015_06_20'

Main_folder = '/network/phenocam-largedatasets/a_data/TimeStreams/Borevitz/' + EXPT_ID + '/originals/'
Folder_rest = EXPT_ID + '-' + LOCATION + '-C01~fullres-orig'

start_date = datetime.datetime.strptime(EXPT_START,'%Y_%m_%d')
end_date = datetime.datetime.strptime(EXPT_END,'%Y_%m_%d')

Hours_range = np.linspace(int((SUNRISE)),int((SUNSET)),int((SUNSET))-int((SUNRISE))+1)
Minutes_range = np.arange(0,60,int((INTERVAL)))


#start_time = datetime.datetime.strptime(EXPT_START+'_'+SUNRISE+'_00_00','%Y_%m_%d_%H_%M_%S')
#end_time = datetime.datetime.strptime(EXPT_END+'_'+SUNSET+'_00_00','%Y_%m_%d_%H_%M_%S')

with open(EXPT_ID+'-ImageAudit.csv', 'wb') as ff:
    writer = csv.writer(ff)
    #tempp = 'TIMEDATE','TIMESTAMP', 'FileExists', 'Rsum', 'Gsum','Bsum','TotalColorSum', 'Orientation', 'Card check', 'MeanErrorAll', 'SDErrorAll', 'AllErrors'
    tempp = 'TIMEDATE','TIMESTAMP', 'FileExists', 'Rsum', 'Gsum', 'Bsum', 'TotalColorSum', 'Orientation', 'Card check', 'MeanErrorAll', 'SDErrorAll'
    Color_names = '1-DrkTone Error', '2-LtTone Error', '3-SkyBlue Error', '4-TreeGreen Error', '5-LtBlue Error', '6-Blu-Green Error',\
    '7-Orange Error', '8-MedBlu Error', '9-LtRed Error', '10-Purple Error', '11-Yel-Grn Error', '12-Org-Yel Error',\
    '13-Blue Error', '14-Green Error', '15-Red Error', '16-Yellow Error', '17-Magenta Error', '18-Cyan Error',\
    '19-White Error', '20-LtGrey Error', '21-Grey Error', '22-DrkGrey Error', '23-Charcoal Error', '24-Black Error'

    #writer.writerow( (tempp) )
    #for ttt in range(12):
    #    ttt2 = ttt*2
    #    tempp = tempp + ('Error' + str(ttt2 + 1),'Error' + str(ttt2 + 2))
    tempp = tempp + Color_names
    writer.writerow( (tempp) )
    i = 0
    for Days in range(int(str((end_date-start_date).days))+1):
        Good_scale_found = 0
        #Study_datetime = start_date + datetime.timedelta(days = Days)
        for Hours in Hours_range:
            #Study_datetime = Study_datetime + datetime.timedelta(hours = Hours)
            for Minutes in Minutes_range:
                Study_datetime = start_date + datetime.timedelta(days = Days)
                Study_datetime = datetime.datetime.combine(Study_datetime, datetime.time(int(Hours),int(Minutes)))#datetime.timedelta(minutes = Minutes) + datetime.timedelta(hours = Hours) + datetime.timedelta(days = Days)
                print(Study_datetime)
                Linux_time = mktime(Study_datetime.timetuple())
                #Study_datetime.minute = Study_datetime.minute + Minutes #datetime.timedelta(minutes = Minutes)
                Study_year = str(Study_datetime.year)
                if Study_datetime.month > 9:
                    Study_month = str(Study_datetime.month)
                else:
                    Study_month = '0' + str(Study_datetime.month)
                if Study_datetime.day > 9:
                    Study_day = str(Study_datetime.day)
                else:
                    Study_day = '0' + str(Study_datetime.day)
                if Study_datetime.hour > 9:
                    Study_hour = str(Study_datetime.hour)
                else:
                    Study_hour = '0' + str(Study_datetime.hour)
                if Study_datetime.minute > 9:
                    Study_minute = str(Study_datetime.minute)
                else:
                    Study_minute = '0' + str(Study_datetime.minute)
                study_folder = Main_folder + Folder_rest + '/' + Study_year + '/' + Study_year + '_' + Study_month + '/' \
                    + Study_year + '_' + Study_month + '_' + Study_day + '/'  \
                    + Study_year + '_' + Study_month + '_' + Study_day + '_' + Study_hour + '/'
                study_file = Folder_rest + '_' + Study_year + '_' + Study_month + '_' + Study_day + '_' + Study_hour + '_' \
                             + Study_minute + '_00_00.jpg'
                full_file_address = study_folder + study_file
                if not os.path.isfile(full_file_address):
                    writer.writerow( (Linux_time,study_file[-26:-4], 0) )
                else:
                    img = cv2.imread(full_file_address)
                    #img = Image.open(full_file_address)
                    #exif = img._getexif()
                    #print(exif[274])
                    #print(exif)
                    if img is None:
                        writer.writerow( (Linux_time,study_file[-26:-4], -1) )
                    #height = np.size(img,0)
                    #width = np.size(img,1)
                    else:
                        b,g,r = cv2.split(img)
                        #plt.imshow(g)
                        #plt.show()
                        Rsum =  np.sum(r>Color_Th)
                        Gsum =  np.sum(g>Color_Th)
                        Bsum =  np.sum(b>Color_Th)
                        TotSum = Rsum + Gsum + Bsum
                        if TotSum>10000:
                            height = np.size(img,0)
                            width = np.size(img,1)
                            if height>width:
                                #img = ndimage.rotate(img, 90)
                                img = np.rot90(img)
                                Orient_dc = 2
                            else:
                                Orient_dc = 0
                            #t = time()
                            orientation = Orientation(img)
                            #print(time() - t)
                            if Good_scale_found == 0:
                                card, similarity_ind, DEG, SCALE, startX, startY, endX, endY = detect_card(img,template,orientation,0.5)
                            else:
                                #t = time()
                                card, similarity_ind, DEG, SCALE, _, _, _, _ = detect_card(img,template,orientation,0.5,[SCALE-0.005, SCALE, SCALE+0.005],[DEG-0.5, DEG, DEG+0.5],startX, startY, endX, endY)
                                #print(time()-t)
                            if similarity_ind > 13000000: #this values is true for scale of 0.5 in calling detect_card
                                Good_scale_found = 1
                                card_rotated_180, mean_error, std_error, Errors = Color_corect(card,orientation)
                                if card_rotated_180 == 1:
                                    card_check = -1
                                elif card_rotated_180 == 0:
                                    card_check = 1
                                Correction_error_mean = mean_error
                                Correction_error_std = std_error
                            else:
                                card_check = 0;
                                Correction_error_mean = ''
                                Correction_error_std = ''
                                Errors = ''
                        else:
                            Orient_dc = ''
                            orientation = ''
                            card_check = ''
                            Correction_error_mean = ''
                            Correction_error_std = ''
                            Errors = ''
                        writer.writerow( (Linux_time,study_file[-26:-4], 1, Rsum, Gsum, Bsum, TotSum, orientation + Orient_dc, card_check, Correction_error_mean, Correction_error_std) + tuple(map(str,Errors)) )
                        #writer.writerow( (Linux_time,study_file[-26:-4], 1, Rsum, Gsum, Bsum, TotSum, orientation + Orient_dc, card_check, Correction_error_mean, Correction_error_std) )

                i=i+1
                print(i)
ff.close()




__author__ = 'Mohammad'

import sys
import os
import logging
import datetime
from time import strptime, strftime, mktime, localtime, struct_time, time, sleep
from docopt import (docopt, DocoptExit)
import csv

import cv2
from matplotlib import pyplot as plt
import numpy as np
import os.path
import glob

from Orientation_check import Orientation
from Detect_colorChecker import detect_card, crop_card
from Color_correction import Color_correct_and_write
from scipy import ndimage
import colorbalance
from PIL import Image

# Constants

DATE_NOW_CONSTANTS = {"now", "current"}
COLOR_THRESHOLD = 120 # a value between 0 and 255


OPTS = """
USAGE:
    run-audit (-g CONFIG | -c CONFIG)
    run-audit (-h | --help)
OPTIONS:
    -h --help   Show this screen.
    -g CONFIG   Generate sample config file
    -c CONFIG   Path to configuration file
    
"""

def date(x):
    """Converter / validator for date field."""
    if isinstance(x, datetime.date):
        return x
    if x.lower() in DATE_NOW_CONSTANTS:
        return datetime.date.today()
    try:
        return datetime.datetime.strptime(x, "%Y_%m_%d")
    except:
        raise ValueError

def bool_str(x):
    """Converts a string to a boolean, even yes/no/true/false."""
    if isinstance(x, bool):
        return x
    elif isinstance(x, int):
        return bool(x)
    elif (len(x) ==0):
        return False
    x = x.strip().lower()
    if x in {"t", "true", "y", "yes", "f", "false", "n", "no"}:
        return x in {"t", "true", "y", "yes"}
    return bool(int(x))


def int_time_hr_min(x):
    """Validator for time field."""
    if isinstance(x, tuple):
        return x
    return (int(x) // 100, int(x) % 100)


def path_exists(x):
    """Validator for path field."""
    # x = x.replace('\\', '/')
    if os.path.exists(x):
        return os.path.join(x, '', '')
    raise ValueError("path '%s' doesn't exist" % x)
	
def file_exists(x):
    """Validator for path field."""
    if os.path.isfile(x):
        return x
    if len(x)<1:
        #raise ValueError("ColorCard path missing")
        return None
    else:
        raise ValueError("file '%s' doesn't exist" % x)
        # return (False,x)


def pad_str(x):
    """Pads a numeric string to two digits."""
    if len(str(x)) == 1:
        return '0' + str(x)
    return str(x)


def remove_underscores(x):
    """Replaces '_' with '-'."""
    return x.replace("_", "-")


def mode_list(x):
    """Ensure x is a vaild method."""
    if x not in {"extensive", "daily", "first"}:
        raise ValueError
    return x

class CameraFields(object):
    """Validate input and translate between exif and config.csv fields."""
    # Validation functions, then schema, then the __init__ and execution
    ts_csv_fields = (
        ('use', 'USE', bool_str),
        ('expt', 'EXPT', remove_underscores),
		('location', 'LOCATION', remove_underscores),
		('cam_num', 'CAM_NUM', pad_str),
		('source', 'SOURCE', path_exists),
        ('expt_start', 'EXPT_START', date),
        ('expt_end', 'EXPT_END', date),
		('interval', 'INTERVAL', int), #In minute
        ('sunrise', 'SUNRISE', int_time_hr_min),
        ('sunset', 'SUNSET', int_time_hr_min),
        ('destination', 'DESTINATION', path_exists),
		('colorcard_template','COLORCARD_TEMPLATE', file_exists),
		('colorcard_detection_mode','COLORCARD_DETECTION_MODE',mode_list),
		('report_rgb','REPORT_RGB', bool_str),
		('report_orientation','REPORT_ORIENTATION', bool_str),
		('report_colorcard','REPORT_COLORCARD', bool_str),
		('report_colorcard_detection_accuracy','REPORT_COLORCARD_DETECTION_ACCURACY', bool_str),
		('report_color_correction_error','REPORT_COLOR_CORRECTION_ERROR', bool_str),
		('report_all_correction_errors','REPORT_ALL_CORRECTION_ERRORS', bool_str),
		('report_num_QR_codes','REPORT_NUM_QR_CODES',bool_str),
		('write_colorcards','WRITE_COLORCARDS', bool_str),
		('write_corrected_colorcards','WRITE_CORRECTED_COLORCARDS', bool_str)
		)

    TS_CSV = dict((a, b) for a, b, c in ts_csv_fields)
    CSV_TS = {v: k for k, v in TS_CSV.items()}
    CSV_dict = []
    REQUIRED = {"destination", "expt", "cam_num", "expt_end", "source", "use",
                "expt_start", "interval", "location", "sunset", "sunrise"}
    SCHEMA = dict((a, c) for a, b, c in ts_csv_fields)

    def __init__(self, csv_config_dict):
        """Store csv settings as object attributes and validate."""
        csv_config_dict = {self.CSV_TS[k]: v for k, v in
                           csv_config_dict.items() if k in self.CSV_TS}
        
        # Ensure required properties are included, and no unknown attributes
        if not all(key in csv_config_dict for key in self.REQUIRED):
            raise ValueError('CSV config dict lacks required key/s.')
        if not all(csv_config_dict[key] for key in self.REQUIRED):
            raise ValueError('CSV config dict lacks required value/s.')
        # Set default properties
        if not csv_config_dict['colorcard_detection_mode']:
            csv_config_dict['colorcard_detection_mode']='first'		
		# Converts dict keys and calls validation function on each value
        csv_config_dict = {k: self.SCHEMA[k](v)
                           for k, v in csv_config_dict.items()}
        '''
		for key in self.REQUIRED:
            print(csv_config_dict[key])
		'''
        # Set object attributes from config
        for k, v in csv_config_dict.items():
            setattr(self, self.CSV_TS[k] if k in self.CSV_TS else k, v)
        self.CSV_dict = csv_config_dict
        # Localise pathnames
        def local(p):
            """Ensure that pathnames are correct for this system."""
            return p.replace(r'\\', '/').replace('/', os.path.sep)
        self.destination = local(self.destination)
        self.source = local(self.source)
        #print(self.source)		

        #log.debug("Validated camera '{}'".format(csv_config_dict))
		

def parse_config_csv(filename):
    if filename is None:
        raise StopIteration	
    with open(filename) as fh:
        config = csv.DictReader(fh)
        for camera in config:
            try:
                camera = CameraFields(camera)
                yield(camera.CSV_dict)
            except ValueError as e:
                print ("Error on csv entry", e)
                continue


def Write_ColorCard(info,card,study_file_name):
    dest_folder = info['destination']+info['expt']+'-'+info['location']+'-'+'DetectedColorCards/'
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    cv2.imwrite(dest_folder+study_file_name.replace('~fullres-orig','-ColorCard'),card)        

    
   
def Gen_audit_fields(info):
    output = 'TIMEDATE','TIMESTAMP', 'FileExists'
    if info['report_rgb']:
        output = output + ('Rsum', 'Gsum','Bsum','TotalColorSum',)
    if info['report_orientation']:
        output = output + ('Orientation',)
    if info['report_num_QR_codes']:
        output = output + ('NumQRCodes',)
    if info['report_colorcard']:
        output = output + ('CardCheck',)
    if info['report_colorcard_detection_accuracy']:
        output = output + ('CardDetectionAccuracy',)
    if info['report_color_correction_error']:
        output = output + ('MeanColorCorrectionError','SDColorCorrectionError',)
    if info['report_all_correction_errors']:
        Color_names = ('1-DrkTone Error', '2-LtTone Error', '3-SkyBlue Error', '4-TreeGreen Error', '5-LtBlue Error', '6-Blu-Green Error',\
        '7-Orange Error', '8-MedBlu Error', '9-LtRed Error', '10-Purple Error', '11-Yel-Grn Error', '12-Org-Yel Error',\
        '13-Blue Error', '14-Green Error', '15-Red Error', '16-Yellow Error', '17-Magenta Error', '18-Cyan Error',\
        '19-White Error', '20-LtGrey Error', '21-Grey Error', '22-DrkGrey Error', '23-Charcoal Error', '24-Black Error',)
        output = output + Color_names
    return(output)

def StudyFile_time_and_path_gen(start_date, Days, Hours, Minutes, Main_folder, info):
    Common_folder = info['expt'] + '-' + info['location'] + '-C01~fullres-orig'
    Study_datetime = start_date + datetime.timedelta(days = Days)
    Study_datetime = datetime.datetime.combine(Study_datetime, datetime.time(int(Hours),int(Minutes)))
    Linux_time = mktime(Study_datetime.timetuple())
    Study_year = str(Study_datetime.year)
    Study_month = pad_str(Study_datetime.month)
    Study_day = pad_str(Study_datetime.day)
    Study_hour = pad_str(Study_datetime.hour)
    Study_minute = pad_str(Study_datetime.minute)
    study_folder = Main_folder + Study_year + '/' + Study_year + '_' + Study_month + '/' \
        + Study_year + '_' + Study_month + '_' + Study_day + '/'  \
        + Study_year + '_' + Study_month + '_' + Study_day + '_' + Study_hour + '/'
    study_file_name = Common_folder + '_' + Study_year + '_' + Study_month + '_' + Study_day + '_' + Study_hour + '_' \
                 + Study_minute + '_00_00.jpg'
    study_file_datetime =  study_file_name[-26:-4]
    return(Linux_time, study_file_datetime, study_folder, study_file_name)

def Process_images(info,Main_folder):
    start_date = info['expt_start']
    end_date = info['expt_end']
    SUNRISE = info['sunrise'][0]
    SUNSET = info['sunset'][0]
    INTERVAL = info['interval']
    Hours_range = np.linspace(SUNRISE,SUNSET,SUNSET-SUNRISE+1)
    Minutes_range = np.arange(0,60,INTERVAL)
    template_orig = cv2.imread(info['colorcard_template'],0)
    Audit_file_name = 'ImageAudit-'+info['expt']+'-'+info['location']+'-'+datetime.datetime.strftime(info['expt_start'],"%Y_%m_%d")+'-TO-'+datetime.datetime.strftime(info['expt_end'],"%Y_%m_%d")+'.csv'
    Good_card_found = 0
    with open(info['destination'] + Audit_file_name, 'wb') as f:
        writer = csv.writer(f)
        Audit_fields = Gen_audit_fields(info)
        writer.writerow( Audit_fields )
        i = 0
        for Days in range(int(str((end_date-start_date).days))+1):
            if info['colorcard_detection_mode'] == 'daily':
                Good_card_found = 0
            for Hours in Hours_range:
                for Minutes in Minutes_range:
                    # t = time()
                    study_file_Linux_time, study_file_datetime, study_folder, study_file_name = StudyFile_time_and_path_gen(start_date, Days, Hours, Minutes, Main_folder, info)
                    full_file_address = study_folder + study_file_name
                    print(full_file_address)
                    if not os.path.isfile(full_file_address):
                        if not os.path.isfile(full_file_address.replace('jpg','JPG')):
                            writer.writerow( (study_file_Linux_time,study_file_datetime, 0) )
                            break
                        else:
                            full_file_address = full_file_address.replace('jpg','JPG')
                    img = cv2.imread(full_file_address)
                    if img is None:
                        writer.writerow( (study_file_Linux_time,study_file_datetime, -1) )
                    else:
                        Audit_output = study_file_Linux_time,study_file_datetime, 1
                        b,g,r = cv2.split(img)
                        Rsum =  np.sum(r>COLOR_THRESHOLD)
                        Gsum =  np.sum(g>COLOR_THRESHOLD)
                        Bsum =  np.sum(b>COLOR_THRESHOLD)
                        TotSum = Rsum + Gsum + Bsum
                        if info['report_rgb']:
                            Audit_output = Audit_output + (Rsum, Gsum, Bsum, TotSum,)
                        if TotSum>10000: # To avoid processing of all black images
                            height = np.size(img,0)
                            width = np.size(img,1)
                            if height>width:
                                img = np.rot90(img)
                                orientation_dc = 2
                            else:
                                orientation_dc = 0
                            orientation = Orientation(img)
                            if orientation == 1:
                                template = np.rot90(template_orig,2)
                            else:
                                template = template_orig
                            if info['report_orientation']:
                                Audit_output = Audit_output + (orientation + orientation_dc,)
                            if info['report_num_QR_codes']:
                                    # to be complated later
                                Audit_output = Audit_output + (0,)
                            if info['report_colorcard'] or info['report_colorcard_detection_accuracy'] or info['report_color_correction_error'] or info['report_all_correction_errors'] or info['write_colorcards'] or info['write_corrected_colorcards'] or info['write_corrected_images']: 
                                if Good_card_found == 0 or info['colorcard_detection_mode'] == 'extensive':
                                    card, similarity_ind, DEG, SCALE, startX, startY, endX, endY = detect_card(img,template,0.5)
                                elif info['colorcard_detection_mode'] == 'daily' or info['colorcard_detection_mode'] == 'first':
                                    card, similarity_ind, DEG, SCALE, _, _, _, _ = detect_card(img,template,0.5,[SCALE-0.005, SCALE, SCALE+0.005],[DEG-0.5, DEG, DEG+0.5],startX, startY, endX, endY)
                                    flag = 1
                                # else: 
                                #     card, similarity_ind = crop_card(img,SCALE,DEG,startX1, startY1, endX1, endY1,startX, startY, endX, endY) # similarity_ind will be 'NA' in this case
                                if info['write_colorcards']:
                                    Write_ColorCard(info,card,study_file_name)

                                if similarity_ind > 0.35: 
                                    card_rotated_180, mean_error, std_error, Errors = Color_correct_and_write(card,orientation,info,study_file_name)
                                    if mean_error < 35:
                                        Good_card_found = 1
                                    if card_rotated_180 == 1:
                                        card_check = -1
                                    elif card_rotated_180 == 0:
                                        card_check = 1
                                    Correction_error_mean = mean_error
                                    Correction_error_std = std_error
                                else:
                                    card_check = 0;
                                    Good_card_found = 0
                                    Correction_error_mean = ''
                                    Correction_error_std = ''
                                    Errors = ''
                                if info['report_colorcard']:
                                    Audit_output = Audit_output + (card_check,)
                                if info['report_colorcard_detection_accuracy']:
                                    Audit_output = Audit_output + (similarity_ind,)
                                if info['report_color_correction_error']:
                                    Audit_output = Audit_output + (Correction_error_mean,Correction_error_std,)
                                if info['report_all_correction_errors'] :
                                    Audit_output = Audit_output + tuple(map(str,Errors))
                        writer.writerow( Audit_output )
                        #writer.writerow( (Linux_time,study_file[-26:-4], 1, Rsum, Gsum, Bsum, TotSum, orientation + Orient_dc, card_check, Correction_error_mean, Correction_error_std) )
                    # print(time()-t)
                    i=i+1
                    print(i)        		
    f.close()

def Check_ColorCard_requirements(info):
    if info['report_colorcard'] or info['report_colorcard_detection_accuracy'] or info['report_color_correction_error'] or info['report_all_correction_errors']:
        if info['colorcard_template'] is None:
            raise ValueError("ColorCard path missing")
        
			
def Main_study_folder_gen(info):
	
    Main_folder = info['source'] + info['expt'] + '/originals/' + info['expt'] + '-' + info['location'] + '-C' + info['cam_num'] + '~fullres-orig/'
    return(Main_folder)
	
	#Folder_rest = EXPT_ID + '-' + LOCATION + '-C01~fullres-orig'

def gen_config(fname):
    """Write example config and exit if a filename is passed."""
    if fname is None:
        return
    with open(fname, "w") as f:
        f.write(",".join(l[1] for l in CameraFields.ts_csv_fields) + "\n")
    sys.exit()

def main(ConfigFile):
    info = parse_config_csv(ConfigFile)
    for row in info:
        if row['use']:
            try:
                Check_ColorCard_requirements(row)
            except ValueError as e:
                print ("Error on csv entry", e)
                continue	
            Main_folder = Main_study_folder_gen(row)
            if os.path.exists(Main_folder):
                print("Processing images in '%s' from %s to %s"%(Main_folder,datetime.datetime.strftime(row['expt_start'],"%Y-%m-%d"),datetime.datetime.strftime(row['expt_end'],"%Y-%m-%d")))
                Process_images(row,Main_folder)			
            else:
                print("Path '%s' dosen't exist"%Main_folder)
        
if __name__ == '__main__':
    opts = docopt(OPTS)
    # print(opts)
    if (opts["-g"]) is not None:
        gen_config(opts["-g"])
    elif opts["-c"] is not None:
        main(opts["-c"])
	

__author__ = 'Mohammad'

import numpy as np
import cv2
import matplotlib.pylab as plt
from scipy import ndimage
import colorbalance

def Color_corect(card, orientation):
    card_rotated_180 = 0
    CardRGB = cv2.cvtColor(card, cv2.COLOR_BGR2RGB)
    actual_colors = colorbalance.get_colorcard_colors(CardRGB,grid_size=[6, 4])
    cnt_color = 0
    if orientation == 0:
            actual_colors = actual_colors[:, ::-1]
    #print(actual_colors)
    if np.sum(actual_colors[:, 8])> np.sum(actual_colors[:, -9]):
        cnt_color = cnt_color + 1
    if np.sum(actual_colors[:, 5])> np.sum(actual_colors[:, -6]):
        cnt_color = cnt_color + 1
    if np.sum(actual_colors[:, 0])< np.sum(actual_colors[:, -1]):
        cnt_color = cnt_color + 1
    if cnt_color >= 2:
        card_rotated_180 = 1
        actual_colors = actual_colors[:, ::-1]
    true_colors = colorbalance.ColorCheckerRGB_CameraTrax

    color_alpha, color_constant, color_gamma = colorbalance.get_color_correction_parameters(true_colors,actual_colors,'gamma_correction')
    corrected_colors = colorbalance._gamma_correction_model(actual_colors, color_alpha, color_constant, color_gamma)
    diff_colors = true_colors - corrected_colors
    errors = np.sqrt(np.sum(diff_colors * diff_colors, axis=0)).tolist()
    #print(np.mean(errors),np.median(errors))
    #ImageRGBCorrected = colorbalance.correct_color(CardRGB, color_alpha,color_constant, color_gamma)
    # get back to RBG order for OpenCV
    #ImageCorrected = cv2.cvtColor(ImageRGBCorrected, cv2.COLOR_RGB2BGR)
    return(card_rotated_180,np.mean(errors),np.std(errors),errors)
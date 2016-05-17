__author__ = 'Mohammad'

import numpy as np
import argparse
import imutils
import glob
import cv2
import matplotlib.pylab as plt
from scipy import ndimage

# this function searches for color card ('card') in the image ('img').
# The sizes of 'card' and the card in the image are assumed to be almost similar (scale factors in [0.9,1.1] are tested)
# 'orient' is the Oreintation of the image which
# 0<'scale'<=1 is to control the speed (and also accuracy) of detecting the color checker. when it is '1', 'iamge' and the 'card' are
# processed unchanged. Otherwise, they are resized accordingly.

def detect_card(img_orig,card_orig,orient,scale=1,search_scale=np.linspace(0.9, 1.1, 41),search_degree=np.arange(-3,3.5,0.5),startX=None, startY=None, endX=None, endY=None):

    card = cv2.Canny(card_orig, 50, 50)
    img = cv2.resize(img_orig,(0,0), fx=scale, fy=scale)
    card = cv2.resize(card,(0,0), fx=scale, fy=scale)
    (H_card, W_card) = card.shape[:2]
    (H_img, W_img) = img.shape[:2]
    (H_orig, W_orig) = img_orig.shape[:2]

    if orient == 1:
        img_cropped = img[int(H_img*.35):int(0.55*H_img),int(W_img*0.45):int(0.6*W_img),:]
        orig_cropped = img_orig[int(H_orig*.35):int(0.55*H_orig),int(W_orig*0.45):int(0.6*W_orig),:]
        #cropped = [int(H_img*.35),int(0.55*H_img),int(W_img*0.45),int(0.6*W_img)]
    else:
        img_cropped = img[int(H_img*.45):int(0.65*H_img),int(W_img*0.40):int(0.55*W_img),:]
        orig_cropped = img_orig[int(H_orig*.45):int(0.65*H_orig),int(W_orig*0.40):int(0.55*W_orig),:]

    if startX is not None:
        orig_cropped = orig_cropped[startY-20:endY+20,startX-20:endX+20,:]
        img_cropped = img_cropped[int((startY-20)*scale):int((endY+20)*scale),int((startX-20)*scale):int((endX+20)*scale),:]

    gray = cv2.cvtColor(img_cropped, cv2.COLOR_BGR2GRAY)
    found = None

    for degree in search_degree:
        if degree != 0:
            gray_rot = ndimage.rotate(gray, degree)
        else:
            gray_rot = gray
        for scale2 in search_scale:
            # resize the image according to the scale, and keep track
            # of the ratio of the resizing
            resized = imutils.resize(gray_rot, width = int(gray.shape[1] * scale2))
            r = gray_rot.shape[1] / float(resized.shape[1])
            # if the resized image is smaller than the template, then break
            # from the loop
            if resized.shape[0] < H_card or resized.shape[1] < W_card:
                break

            # detect edges in the resized, grayscale image and apply template
            # matching to find the template in the image
            edged = cv2.Canny(resized, 50, 50)
            result = cv2.matchTemplate(edged, card, cv2.TM_CCOEFF)
            (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)


            # if we have found a new maximum correlation value, then ipdate
            # the bookkeeping variable
            if found is None or maxVal > found[0]:
                found = (maxVal, maxLoc, r, degree, scale2)
                #print(scale2)

    if found is None:
        return(orig_cropped,0)
    else:
        (maxVal, maxLoc, r, deg, SCALE) = found
        print(found)
        (startX, startY) = (int((((maxLoc[0]) * r) + 0) / scale), int((maxLoc[1] * r + 0) / scale))
        (endX, endY) = (int(((maxLoc[0] + W_card) * r + 0) / scale), int(((maxLoc[1] + H_card) * r + 0) / scale))

        output_img = ndimage.rotate(orig_cropped, deg)
        output_img = output_img[startY:endY,startX:endX,:]

        return(output_img,maxVal, deg, SCALE,startX, startY, endX, endY )






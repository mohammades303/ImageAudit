__author__ = 'Mohammad'
import numpy as np
import cv2

def Orientation(img):
    Default_h = 1280
    #Default_h = 600

    height = np.size(img,0)
    width = np.size(img,1)
    img = cv2.resize(img, (int(width*Default_h/height), Default_h))

    height = np.size(img,0)
    width = np.size(img,1)

    b1,g1,r1 = cv2.split(img)
    median = cv2.medianBlur((b1>200)*b1,13)
    blur = cv2.blur(median,(9,9))
    kernel = np.ones((3,3),np.uint8)
    opening = cv2.morphologyEx(blur,cv2.MORPH_CLOSE,kernel, iterations = 2)
    kernel = np.ones((23,23),np.uint8)
    opening = cv2.morphologyEx(opening,cv2.MORPH_OPEN,kernel, iterations = 2)

    #ret, markers = cv2.connectedComponents(np.uint8(opening>90))

    if np.sum(opening[int(height*0.33):int(height*0.66),0:int(width*0.2)]>90)>(np.sum(opening[int(height*0.33):int(height*0.66),-1*int(width*0.2):-1]>90)):
        output = 0
    else:
        output = 1
    return(output)

    #print(np.sum(opening[int(height*0.33):int(height*0.66),0:int(width*0.2)]>90),np.sum(opening[int(height*0.33):int(height*0.66),-1*int(width*0.2):-1]>90))
    #print(np.sum(b1[int(height*0.33):int(height*0.66),0:int(width*0.2)]>200),np.sum(b1[int(height*0.33):int(height*0.66),-1*int(width*0.2):-1]>200))


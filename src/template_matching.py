# -*- coding: UTF-8 -*-
import cv2
import numpy

def single_match_gray(img, template, threshval, admitval, return_minval=False):
    outcome = False

    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    (retval, img) = cv2.threshold(img, threshval, 255, cv2.THRESH_BINARY)

    if (int(template.shape[2])!=1):
        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    (retval, template) = cv2.threshold(template, threshval, 255, cv2.THRESH_BINARY)
    match = cv2.matchTemplate(img, template, cv2.TM_SQDIFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(match)

    if (minVal<=admitval):
        outcome = True

    if (return_minval==True):
        return (outcome, minVal)
    else:
        return outcome

def single_match_rgb(img, template, threshval, admitval):
    outcome = False
    avgVal = 0

    img = cv2.split(img)
    template = cv2.split(template)

    for i in range(len(img)):
        ix = img[i]
        (retval, ix) = cv2.threshold(ix, threshval, 255, cv2.THRESH_BINARY)
        tx = template[i]
        (retval, tx) = cv2.threshold(tx, threshval, 255, cv2.THRESH_BINARY)
        match = cv2.matchTemplate(ix, tx, cv2.TM_SQDIFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(match)
        avgVal += minVal

    avgVal /= 3
    if (avgVal<=admitval):
        outcome = True
    return outcome

def multi_loc_gray(img, template, threshval, admitval, return_minval=False):
    outcome = []

    try:
        if (int(img.shape[2])!=1):
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except:
        pass

    (retval, img) = cv2.threshold(img, threshval, 255, cv2.THRESH_BINARY)

    try:
        if (int(template.shape[2])!=1):
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    except:
        pass

    (retval, template) = cv2.threshold(template, threshval, 255, cv2.THRESH_BINARY)

    match = cv2.matchTemplate(img, template, cv2.TM_SQDIFF_NORMED)
    for y in range(match.shape[0]):
        for x in range(match.shape[1]):
            if (match[y][x]<=admitval):
                outcome.append((y, x))

    if (return_minval==True):
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(match)
        return (outcome, minVal)
    else:
        return outcome

def point_collapse(locs_lst, range):
    new_locs_lst = []
    sym_point = None
    while (len(locs_lst)!=0):
        del_point = []
        if (sym_point==None):
            sym_point = locs_lst.pop(0)
        for loc in locs_lst:
            if ((loc[0]-sym_point[0])**2+(loc[1]-sym_point[1])**2<range**2):
                del_point.append(loc)
        for point in del_point:
            locs_lst.pop(locs_lst.index(point))
        new_locs_lst.append(sym_point)
        sym_point = None

    return new_locs_lst

def hue_filter(img, colers):
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    (h, s, v) = cv2.split(img_hsv)
    for y in range(h.shape[0]):
        for x in range(h.shape[1]):
            if (int(h[y][x]) not in colers):
                img_hsv[y][x] = (0, 0, 255)
    return cv2.cvtColor(img_hsv, cv2.COLOR_HSV2BGR)

def hue_filter(img, colors):
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    (h, s, v) = cv2.split(img_hsv)
    for y in range(h.shape[0]):
        for x in range(h.shape[1]):
            if (int(h[y][x]) not in colors):
                img[y][x] = (255, 255, 255)
    return img

def facility_num_filter(img, num_templates):
    img = hue_filter(img, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32])
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    img_fin = numpy.zeros((img.shape[0], img.shape[1], 1), img.dtype)
    for y in range(img_hsv.shape[0]):
        for x in range(img_hsv.shape[1]):
            if (img_hsv[y][x][1]<80 and img_hsv[y][x][2]>200):
                img_fin[y][x] = 255
            else:
                img_fin[y][x] = 0

    (contours, _) = cv2.findContours(img_fin, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    areas = []
    max_area = 0
    for i in range(len(contours)):
        area = cv2.contourArea(contours[i])
        if (area<250):
            areas.append((i, area))
    try:
        max_area = sorted(areas, key=lambda pair:pair[1], reverse=True)[0][1]
    except:
        return 0

    avalible_contours = []
    for i in range(len(areas)):
        if (areas[i][1]/max_area>=0.4 and areas[i][1]<=max_area):
            avalible_contours.append(i)

    chars = []

    for i in avalible_contours:
        blank = numpy.ones(img_fin.shape, img_fin.dtype) * 255
        mask = numpy.ones(img.shape, img.dtype) * 255
        cv2.drawContours(mask, contours, i, (0, 255, 0), cv2.FILLED)

        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                pix = (int(mask[y][x][0]), int(mask[y][x][1]), int(mask[y][x][2]))
                if (pix==(0, 255, 0)):
                    blank[y][x] = img_fin[y][x]
        blank = cv2.dilate(blank, (5, 5))

        num_match = False
        num = None
        for template in num_templates:
            locs = multi_loc_gray(blank, template["img"], 200, 0.18)
            locs = point_collapse(locs, 3)
            if (len(locs)!=0):
                if (num_match==False):
                    num_match = True
                    num = (template["name"], locs[0][1])
                else:
                    similar_templates = [template["name"], num[0]]
                    best_match = None
                    best_val = 1
                    for t in num_templates:
                        if (t["name"] in similar_templates):
                            if (multi_loc_gray(blank, t["img"], 200, 0.18, True)[1]<best_val):
                                best_match = t["name"]
                    num = (best_match, num[1])

        if (num_match==True):
            chars.append(num)


    string = ""
    for char in sorted(chars, key=lambda pair:pair[1]):
        if (char[0]=="plus"):
            continue
        else:
            string += char[0]
    if (len(string)>=3):
        if (int(string)>100):
            string = string[:2]
    try:
        string = int(string)
    except:
        string = 10

    return string

if (__name__=="__main__"):
    img = cv2.imread("0syWF4v.png")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    (retval, gray) = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    cv2.imwrite("test.png", gray)
    cv2.imshow("img", gray)
    cv2.waitKey()
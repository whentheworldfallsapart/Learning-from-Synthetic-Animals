
from __future__ import print_function, absolute_import

import os
import numpy as np
import json
import random
import math

import torch
import torch.utils.data as data

from pose.utils.osutils import *
from pose.utils.imutils import *
from pose.utils.transforms import *
from pose.utils.evaluation  import final_preds
import pose.models as models

import glob
import cv2
from tqdm import tqdm
import scipy.misc
import scipy.ndimage
from scipy.io import loadmat
import imageio


def load_animal(data_dir='./', animal='horse'):
    """
    Output:
    img_list: Nx3   # each image is associated with a shot-id and a shot-id frame_id,
                    # e.g. ('***.jpg', 100, 2) means the second frame in shot 100.
    anno_list: Nx3  # (x, y, visiblity)
    """

    range_path = os.path.join(data_dir, 'behaviorDiscovery2.0/ranges', animal, 'ranges.mat')
    landmark_path = os.path.join(data_dir, 'behaviorDiscovery2.0/landmarks', animal)

    img_list = []  # img_list contains all image paths
    anno_list = [] # anno_list contains all anno lists
    range_file = loadmat(range_path)

    for video in range_file['ranges']:
        # range_file['ranges'] is a numpy array [Nx3]: shot_id, start_frame, end_frame
        shot_id = video[0]
        landmark_path_video = os.path.join(landmark_path, str(shot_id)+'.mat')

        if not os.path.isfile(landmark_path_video):
            continue
        landmark_file = loadmat(landmark_path_video)

        for frame in range(video[1], video[2]+1): # ??? video[2]+1
            frame_id = frame - video[1]
            img_name = '0'*(8-len(str(frame))) + str(frame) + '.jpg'
            img_list.append([img_name, shot_id, frame_id])
            
            coord = landmark_file['landmarks'][frame_id][0][0][0][0]
            vis = landmark_file['landmarks'][frame_id][0][0][0][1]
            landmark = np.hstack((coord, vis))
            anno_list.append(landmark[:18,:])
            
    return img_list, anno_list

def dataset_filter(anno_list):
    """
    output:
    idxs: valid_idxs after filtering
    """
    num_kpts = anno_list[0].shape[0]
    idxs = []
    for i in range(len(anno_list)):
        s = sum(anno_list[i][:,2])
        if s>num_kpts//2:
            idxs.append(i)
    return idxs

def im_to_torch(img):
    img = np.transpose(img, (2, 0, 1)) # C*H*W
    img = to_torch(img).float()
    if img.max() > 1:
        img /= 255
    return img

def get_cropped_dataset(img_folder, img_list, anno_list, img_idxs, animal):
    count = 0
    for i in tqdm(range(len(img_list))):
    
        img = scipy.misc.imread(os.path.join(img_folder, 'behaviorDiscovery2.0/', animal, img_list[i][0]), mode='RGB')
        img_new_path = 'crop_'+img_list[i][0]
        frame = img.copy()
        img = im_to_torch(img)
        
        # get correct scale and center
        if i in img_idxs:
            x_min = float(np.min(anno_list[img_idxs[count]][:,0] \
                                 [anno_list[img_idxs[count]][:,0]>0]))
            x_max = float(np.max(anno_list[img_idxs[count]][:,0] \
                                 [anno_list[img_idxs[count]][:,0]>0]))
            y_min = float(np.min(anno_list[img_idxs[count]][:,1] \
                                 [anno_list[img_idxs[count]][:,1]>0]))
            y_max = float(np.max(anno_list[img_idxs[count]][:,1] \
                                 [anno_list[img_idxs[count]][:,1]>0]))
            c = torch.Tensor(( (x_min+x_max)/2.0, (y_min+y_max)/2.0 ))
            s = max(x_max-x_min, y_max-y_min)/200.0 * 1.5    
            rot = 0
    
            inp = crop(img, c, s, [256, 256], rot)
    
            frame = torch.Tensor(frame.transpose(2,0,1))
            frame = crop(frame, c, s, [256, 256], rot)
            frame = (frame.numpy().transpose(1,2,0))*255
            frame = np.uint8(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            count += 1
            
        imageio.imwrite('./animal_data/real_animal_crop/real_' + animal + '_crop/'+img_new_path, frame)
    print('number of cropped '+animal+': ', count)
    return None

if __name__== "__main__":
    animals = ['horse', 'tiger']
    img_folder = './animal_data/'
    for animal in animals:
        img_list, anno_list = load_animal(data_dir=img_folder, animal=animal)
        img_idxs = dataset_filter(anno_list)
        print(len(img_idxs))

        if not os.path.exists(os.path.join(img_folder, 'real_animal_crop',  'real_'+animal+'_crop')):
            os.makedirs(os.path.join(img_folder, 'real_animal_crop', 'real_'+animal+'_crop'))
 
        get_cropped_dataset(img_folder, img_list, anno_list, img_idxs, animal) 

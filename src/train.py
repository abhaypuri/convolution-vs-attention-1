"""
A script to train a machine learning model on tinyimagenet
"""
#imports
from __future__ import print_function, division
from argparse import ArgumentParser

import torch
import torch.nn as nn
import os
import torch.backends.cudnn as cudnn
from torchvision import models #double naming Warning
from torchinfo import summary

from sklearn.metrics import classification_report

#import local classes/functions
from models.coatnet import coatnet_0
from utils.utils import seed_all, freemem
from data.load_data import print_datamap, dataload
from models.default_train import model_default_train, model_save_load
from visualization.visual import visualize_loss_acc, shape_bias, confusion_matrix_hm, visualize_model

cudnn.benchmark = True

#plt.ion()   # interactive mode

#set device
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f'device: {device}')
print(torch.cuda.device_count())
print(torch.cuda.get_device_name(0))

#seed for reproducibility
rng = seed_all(123)

#defaults
batch_size_default = 32 #geirhos used 256 (could use if memory available)
class_size = 207

#args
def add_args(parser):
    """
    Add arguments to parser
    """
    parser.add_argument(
        "--train",
        default=False,
        action='store_true', #'store_false' if want default to false
        help="Train or Test",
    )
    parser.add_argument(
        "--model",
        default='resnet',
        type=str,
        help="Model name",
    )
    parser.add_argument(
        "--pretrain",
        default=False,
        action='store_true',
        help="Load pretrained model parameters",
    )
    parser.add_argument(
        "--load",
        default=False, #should be set to true when testing
        action='store_true',
        help="Load saved model parameters",
    )
    return parser

#main function
def main(args):

    #print tests
    #print_datamap()
    print(args)
    print()

    #load data
    _,dataloaders,dataset_sizes= dataload(batch_size=batch_size_default)
    
    # initialize model
    if args.model =='resnet':
        net = models.resnet50(pretrained=args.pretrain)
        # Set the size of each output sample to class_size
        net.fc = nn.Linear(net.fc.in_features, class_size)
    #no model for vit or convnext on torchvision yet
    elif args.model =='vit':
        net = models.vit_b_32(pretrained=args.pretrain)
        net.heads.head = nn.Linear(in_features=net.heads.head.in_features, out_features=class_size, bias=True)
    elif args.model =='convnext':
        net = models.convnext_small(pretrained=args.pretrain)
        net.classifier[2] = nn.Linear(in_features=net.classifier[2].in_features, out_features=class_size, bias=True)
    elif args.model =='coatnet':
        #no pretrained models yet
        net = coatnet_0()
        net.fc = nn.Linear(in_features=net.fc.in_features, out_features=class_size, bias=True)
    
    print(f'Training on {args.model}')
    # Load model from save to scratch, if granted and exist
    model_name = args.model
   
    if os.name == 'nt': #windows
        path_to_model = os.path.abspath(f'../models/trained_models/{model_name}.pth')
    else: #linux
        home_path = os.path.expanduser('~')
        path_to_model = f'{home_path}/scratch/code-snapshots/convolution-vs-attention/models/trained_models/{model_name}.pth'
 
    print(path_to_model)

    if os.path.exists(path_to_model) and args.load:
        print('Model loaded!')
        net = model_save_load(save=False,model=net,path=path_to_model)

    # Training model
    if args.train:
        #summary(net, input_size=(batch_size_default, 3, 224, 224))
        freemem()

        #UNCOMMENT FOR TRAINING
        net,net_ls,net_as = model_default_train(net,dataloaders,dataset_sizes,device,epoch = 60)

        #save model
        model_save_load(model=net,path=path_to_model)

        #save loss acc plot
        visualize_loss_acc(net_ls,net_as,name=f'{args.model}_loss_acc_plot')

    #Visualize/test model
    else:

        # shape bias calculation
        shape_bias_dict, shape_bias_df, shape_bias_df_match = shape_bias(net,dataloaders)
        print(shape_bias_dict)
        # confusion matrix plot for shape biases
        confusion_matrix_hm(shape_bias_df['pred'],shape_bias_df['lab_shape'],name =f'{args.model}_shape_bias_all_cm')
        #confusion_matrix_hm(shape_bias_df['pred'],shape_bias_df['lab_shape'],name =f'{args.model}_shape_bias_corr_cm')
        #confusion_matrix_hm(shape_bias_df['pred'],shape_bias_df['lab_shape'],name =f'{args.model}_texture_bias_corr_cm')
        print('classification report shape bias')
        print(classification_report(shape_bias_df['lab_shape'], shape_bias_df['pred']))
        #classification_report(shape_bias_df['lab_texture'], shape_bias_df['pred'])

        # visualize sample predictions
        visualize_model(net,dataloaders, name=f'{args.model}_model_pred')


    print('done!')



if __name__ == "__main__":
    #arguments
    parser = ArgumentParser()
    parser = add_args(parser)
    args = parser.parse_args()

    #where the magic happens
    main(args)
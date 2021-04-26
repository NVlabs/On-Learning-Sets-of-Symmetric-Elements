# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.functional as F


class Conv1dBlock(nn.Module):
    def __init__(self, channels,args):
        super(Conv1dBlock, self).__init__()
        self.channels = channels
        # layers
        self.conv_1 = torch.nn.Conv1d(in_channels = channels[0], out_channels = channels[1], kernel_size = 1)
        self.conv_2 = torch.nn.Conv1d(in_channels = channels[1], out_channels = channels[2], kernel_size = 1)
        self.conv_3 = torch.nn.Conv1d(in_channels=channels[2], out_channels=channels[3], kernel_size=1)
        self.bn1 = torch.nn.BatchNorm1d(num_features=channels[1])
        self.bn2 = torch.nn.BatchNorm1d(num_features=channels[2])
        self.bn3 = torch.nn.BatchNorm1d(num_features=channels[3])

        # initializations
        torch.nn.init.xavier_normal_(self.conv_1.weight)
        torch.nn.init.xavier_normal_(self.conv_2.weight)
        torch.nn.init.xavier_normal_(self.conv_3.weight)


    def forward(self, x):
        b,n,c,l = x.size()
        x = x.view(n*b,c,l)
        x = F.relu(self.bn1(self.conv_1(x)))
        x = F.relu(self.bn2(self.conv_2(x)))
        x = F.relu(self.bn3(self.conv_3(x)))  # use nonlinearity in last layer since it goes into deepsets module
        return x



class Identity(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
    def forward(self, x):
        return x


class DeepSymmetricConv1dBlock(nn.Module):
    def __init__(self, channels,args):
        super(DeepSymmetricConv1dBlock, self).__init__()
        self.channels = channels
        self.use_max = args.use_max
        # layers
        self.conv_1 = torch.nn.Conv1d(in_channels = channels[0], out_channels = channels[1], kernel_size = 1)
        self.conv_2 = torch.nn.Conv1d(in_channels = channels[1], out_channels = channels[2], kernel_size = 1)
        self.conv_3 = torch.nn.Conv1d(in_channels=channels[2], out_channels=channels[3], kernel_size=1)
        self.bn1 = torch.nn.BatchNorm1d(num_features=channels[1])
        self.bn2 = torch.nn.BatchNorm1d(num_features=channels[2])
        self.bn3 = torch.nn.BatchNorm1d(num_features=channels[3])
        self.conv_1s = torch.nn.Conv1d(in_channels=channels[0], out_channels=channels[1], kernel_size=1)
        self.conv_2s = torch.nn.Conv1d(in_channels=channels[1], out_channels=channels[2], kernel_size=1)
        self.conv_3s = torch.nn.Conv1d(in_channels=channels[2], out_channels=channels[3], kernel_size=1)
        self.bn1s = torch.nn.BatchNorm1d(num_features=channels[1])
        self.bn2s = torch.nn.BatchNorm1d(num_features=channels[2])
        self.bn3s = torch.nn.BatchNorm1d(num_features=channels[3])


        # initializations
        torch.nn.init.xavier_normal_(self.conv_1.weight)
        torch.nn.init.xavier_normal_(self.conv_2.weight)
        torch.nn.init.xavier_normal_(self.conv_3.weight)
        torch.nn.init.xavier_normal_(self.conv_1s.weight)
        torch.nn.init.xavier_normal_(self.conv_2s.weight)
        torch.nn.init.xavier_normal_(self.conv_3s.weight)


    def forward(self, x):
        
        # Conv1
        b,n,c,l = x.size()
        x1 = self.bn1(self.conv_1(x.view(b*n, c, l)))
        if self.use_max:
            x2 = self.bn1s(self.conv_1s(torch.max(x, dim=1, keepdim=False)[0]))  # (b, c, l)
        else:
            x2 = self.bn1s(self.conv_1s(torch.sum(x, dim=1, keepdim=False)))

        x2 = x2.unsqueeze(1).repeat(1,n,1,1).view(b*n, self.channels[1], l)
        x = x1 + x2
        x = F.relu(x)
        x = x.view(b, n, self.channels[1], l)
        
        # Conv2
        b,n,c,l = x.size()
        x1 = self.bn2(self.conv_2(x.view(b*n, c, l)))
        if self.use_max:
            x2 = self.bn2s(self.conv_2s(torch.max(x, dim=1, keepdim=False)[0]))  # (b, c, l)
        else:
            x2 = self.bn2s(self.conv_2s(torch.sum(x, dim=1, keepdim=False)))

        x2 = x2.unsqueeze(1).repeat(1,n,1,1).view(b*n, self.channels[2], l)
        x = x1 + x2
        x = F.relu(x)
        x = x.view(b, n, self.channels[2], l)

        # Conv3        
        b,n,c,l = x.size()
        x1 = self.bn3(self.conv_3(x.view(b*n, c, l)))
        if self.use_max:
            x2 = self.bn3s(self.conv_3s(torch.max(x, dim=1, keepdim=False)[0]))  # (b, c, l)
        else:
            x2 = self.bn3s(self.conv_3s(torch.sum(x, dim=1, keepdim=False)))

        x2 = x2.unsqueeze(1).repeat(1,n,1,1).view(b*n, self.channels[3], l)
        x = x1 + x2
        x = F.relu(x)  # use nonlinearity in last layer since it goes into deepsets module        
        return x
    

class SridharConvBlock(nn.Module):
    def __init__(self, channels,args):
        super(SridharConvBlock, self).__init__()
        self.channels = channels
        # layers
        self.conv_1 = torch.nn.Conv1d(in_channels=channels[0], out_channels=channels[1], kernel_size=1)
        self.conv_2 = torch.nn.Conv1d(in_channels=channels[1], out_channels=channels[2], kernel_size=1)
        self.conv_3 = torch.nn.Conv1d(in_channels=channels[2], out_channels=channels[3], kernel_size=1)
        self.bn1 = torch.nn.BatchNorm1d(num_features=channels[1])
        self.bn2 = torch.nn.BatchNorm1d(num_features=channels[2])
        self.bn3 = torch.nn.BatchNorm1d(num_features=channels[3])

        # initializations
        torch.nn.init.xavier_normal_(self.conv_1.weight)
        torch.nn.init.xavier_normal_(self.conv_2.weight)
        torch.nn.init.xavier_normal_(self.conv_3.weight)

    def forward(self, x):

        b,n,c,l = x.size()
        
        x = self.conv_1(x.view(b*n, c, l))    
        x = x.view(b, n,self.channels[1],l)
        x_mean = x.mean(dim=1,keepdim=True)
        x = x-x_mean
        x = x.view(b*n,self.channels[1],l)
        x = self.bn1(x)
        x = F.relu(x)
        x = x.view(b,n,self.channels[1],l)

        b,n,c,l = x.size()
        x = self.conv_2(x.view(n * b, c, l))
        x = x.view(b, n, self.channels[2], l)
        x_mean = x.mean(dim=1, keepdim=True)
        x = x - x_mean
        x = x.view(b * n, self.channels[2], l)
        x = self.bn2(x)
        x = F.relu(x)
        x = x.view(b, n, self.channels[2], l)

        b,n,c,l = x.size()
        x = self.conv_3(x.view(n * b, c, l))
        x = x.view(b, n, self.channels[3], l)
        x_mean = x.mean(dim=1, keepdim=True)
        x = x - x_mean
        x = x.view(b * n, self.channels[3], l)
        x = self.bn3(x)
        x = F.relu(x)
        return x


class AittalaConvBlock(nn.Module):
    def __init__(self, channels,args):
        super(AittalaConvBlock, self).__init__()
        self.channels = channels
        # layers
        self.conv_1 = torch.nn.Conv1d(in_channels=channels[0], out_channels=channels[1], kernel_size=1)
        self.conv_2 = torch.nn.Conv1d(in_channels=2*channels[1], out_channels=channels[2], kernel_size=1)
        self.conv_3 = torch.nn.Conv1d(in_channels=2*channels[2], out_channels=channels[3], kernel_size=1)
        self.bn1 = torch.nn.BatchNorm1d(num_features=2*channels[1])
        self.bn2 = torch.nn.BatchNorm1d(num_features=2*channels[2])
        self.bn3 = torch.nn.BatchNorm1d(num_features=2*channels[3])

        # initializations
        torch.nn.init.xavier_normal_(self.conv_1.weight)
        torch.nn.init.xavier_normal_(self.conv_2.weight)
        torch.nn.init.xavier_normal_(self.conv_3.weight)

    def forward(self, x):

        b,n,c,l = x.size()
        x = self.conv_1(x.view(n*b,c,l))
        x = x.view(b, n,self.channels[1],l)
        x_max = x.max(dim=1,keepdim=True)[0]
        x_max = x_max.repeat(1,n,1,1)
        x = torch.cat([x, x_max],dim=2)
        x = x.view(b*n,2*self.channels[1],l)
        x = self.bn1(x)
        x = F.relu(x)
        x = x.view(b,n,2*self.channels[1],l)

        b,n,c,l = x.size()
        x = self.conv_2(x.view(n * b, c, l))
        x = x.view(b, n, self.channels[2], l)
        x_max = x.max(dim=1, keepdim=True)[0]
        x_max = x_max.repeat(1, n, 1, 1)
        x = torch.cat([x, x_max], dim=2)
        x = x.view(b * n, 2 * self.channels[2], l)
        x = self.bn2(x)
        x = F.relu(x)
        x = x.view(b, n, 2 * self.channels[2], l)

        b,n,c,l = x.size()
        x = self.conv_3(x.view(n * b, c, l))
        x = x.view(b, n, self.channels[3], l)
        x_max = x.max(dim=1, keepdim=True)[0]
        x_max = x_max.repeat(1, n, 1, 1)
        x = torch.cat([x, x_max], dim=2)
        x = x.view(b * n, 2 * self.channels[3], l)
        x = self.bn3(x)
        x = F.relu(x)
        return x
    

class DeepSetsBlock(nn.Module):
    def __init__(self,args,channels=(256, 128, 1)):
        super(DeepSetsBlock, self).__init__()
        use_bn = False
        # layers
        self.channels = channels
        self.fc_1 = torch.nn.Linear(in_features=self.channels[0], out_features=self.channels[0])
        self.fc_2 = torch.nn.Linear(in_features=self.channels[0], out_features=self.channels[1])
        self.fc_3 = torch.nn.Linear(in_features=self.channels[1], out_features=self.channels[2])
        self.fc_1s = torch.nn.Linear(in_features=self.channels[0], out_features=self.channels[0])
        self.fc_2s = torch.nn.Linear(in_features=self.channels[0], out_features=self.channels[1])
        self.fc_3s = torch.nn.Linear(in_features=self.channels[1], out_features=self.channels[2])

        if use_bn:
            self.bn1 = torch.nn.BatchNorm1d(256)
            self.bn2 = torch.nn.BatchNorm1d(128)
            self.bn1s = torch.nn.BatchNorm1d(256)
            self.bn2s = torch.nn.BatchNorm1d(128)
        else:
            self.bn1 = Identity()
            self.bn2 = Identity()
            self.bn1s = Identity()
            self.bn2s = Identity()
        # initializations
        torch.nn.init.xavier_normal_(self.fc_1.weight)
        torch.nn.init.xavier_normal_(self.fc_2.weight)
        torch.nn.init.xavier_normal_(self.fc_3.weight)
        torch.nn.init.xavier_normal_(self.fc_1s.weight)
        torch.nn.init.xavier_normal_(self.fc_2s.weight)
        torch.nn.init.xavier_normal_(self.fc_3s.weight)

    def forward(self, x):
        b, n, c = x.size()
        x_col = x.view(b * n, c)
        x1 = self.bn1(self.fc_1(x_col))  # (b*n, c_out)
        x2 = self.fc_1s(torch.max(x, dim=1, keepdim=False)[0])  # (b, c_out)
        x2 = self.bn1s(x2.view(b,1,self.channels[0]).repeat(1,n,1).view(b*n,self.channels[0]))
        x = x1 + x2
        x = F.elu(x)
        x = x.view(b,n,self.channels[0])

        x_col = x.view(b * n, self.channels[0])
        x1 = self.bn2(self.fc_2(x_col))
        x2 = self.fc_2s(torch.max(x, dim=1, keepdim=False)[0])
        x2 = self.bn2s(x2.view(b, 1, self.channels[1]).repeat(1, n, 1).view(b * n, self.channels[1]))
        x = x1 + x2
        x = F.elu(x)
        x = x.view(b, n, self.channels[1])

        x_col = x.view(b * n, self.channels[1])
        x1 = self.fc_3(x_col)
        x2 = self.fc_3s(torch.max(x, dim=1, keepdim=False)[0])
        x2 = x2.view(b, 1, self.channels[2]).repeat(1, n, 1).view(b * n, self.channels[2])
        x = x1 + x2
        x = x.view(b, n, self.channels[2])
        return x






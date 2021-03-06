import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import FloatTensor, Tensor, tensor
from typing import List, Tuple


def compute_iou(box1: Tensor, box2: Tensor) -> Tensor:
    """Compute the intersection over union of two set of boxes, each box is [x1,y1,x2,y2].
    Args:
      box1: (tensor) bounding boxes, sized [N,4].
      box2: (tensor) bounding boxes, sized [M,4].
    Return:
      (tensor) iou, sized [N,M].
    """
    N = box1.size(0)
    M = box2.size(0)

    lt = torch.max(
        # [N,2] -> [N,1,2] -> [N,M,2]
        box1[:, :2].unsqueeze(1).expand(N, M, 2),
        # [M,2] -> [1,M,2] -> [N,M,2]
        box2[:, :2].unsqueeze(0).expand(N, M, 2),
    )

    rb = torch.min(
        # [N,2] -> [N,1,2] -> [N,M,2]
        box1[:, 2:].unsqueeze(1).expand(N, M, 2),
        # [M,2] -> [1,M,2] -> [N,M,2]
        box2[:, 2:].unsqueeze(0).expand(N, M, 2),
    )

    wh = rb - lt  # [N,M,2]
    wh[wh < 0] = 0  # clip at 0
    inter = wh[:, :, 0] * wh[:, :, 1]  # [N,M]

    area1 = (box1[:, 2] - box1[:, 0]) * (box1[:, 3] - box1[:, 1])  # [N,]
    area2 = (box2[:, 2] - box2[:, 0]) * (box2[:, 3] - box2[:, 1])  # [M,]
    area1 = area1.unsqueeze(1).expand_as(inter)  # [N,] -> [N,1] -> [N,M]
    area2 = area2.unsqueeze(0).expand_as(inter)  # [M,] -> [1,M] -> [N,M]

    iou = inter / (area1 + area2 - inter)
    return iou


class YoloLoss(nn.Module):
    def __init__(self, S, B, l_coord, l_noobj):
        super(YoloLoss, self).__init__()
        self.S = S
        self.B = B
        self.l_coord = l_coord
        self.l_noobj = l_noobj
        self.device = torch.device(
            "cuda:0" if torch.cuda.is_available() else "cpu")

    def xywh2xyxy(self, boxes: Tensor) -> Tensor:
        """
        Parameters:
        boxes: (N,4) representing by x,y,w,h

        Returns:
        boxes: (N,4) representing by x1,y1,x2,y2

        if for a Box b the coordinates are represented by [x, y, w, h] then
        x1, y1 = x/S - 0.5*w, y/S - 0.5*h ; x2,y2 = x/S + 0.5*w, y/S + 0.5*h
        Note: Over here initially x, y are the center of the box and w,h are width and height.
        """
        ### CODE ###
        # Your code here
        boxes_ = torch.stack([boxes[:, 0]/self.S - boxes[:, 2] / 2, boxes[:, 1]/self.S - boxes[:, 3] / 2,
                             boxes[:, 0]/self.S + boxes[:, 2] / 2, boxes[:, 1]/self.S + boxes[:, 3] / 2], dim=1)

        return boxes_

    def find_best_iou_boxes(self, pred_box_list, box_target):
        """
        Parameters:
        box_pred_list : [(tensor) size (-1, 4) ...]
        box_target : (tensor)  size (-1, 5)

        Returns:
        best_iou: (tensor) size (-1, 1)
        best_boxes : (tensor) size (-1, 5), containing the boxes which give the best iou among the two (self.B) predictions

        Hints:
        1) Find the iou's of each of the 2 bounding boxes of each grid cell of each image.
        2) For finding iou's use the compute_iou function
        3) use xywh2xyxy to convert bbox format if necessary,
        Note: Over here initially x, y are the center of the box and w,h are width and height.
        We perform this transformation to convert the correct coordinates into bounding box coordinates.
        """

        ### CODE ###
        # Your code here
        box_target = self.xywh2xyxy(box_target)

        box_pred_01 = pred_box_list[0]
        box_pred_02 = pred_box_list[1]

        box_pred_1 = self.xywh2xyxy(pred_box_list[0]) 
        box_pred_2 = self.xywh2xyxy(pred_box_list[1])

        iou_1 = compute_iou(box_target, box_pred_1[:,0:4])
        iou_1 = torch.diag(iou_1,0)

        iou_2 = compute_iou(box_target, box_pred_2[:,0:4])
        iou_2 = torch.diag(iou_2,0)

        N = box_target.size()[0]
        #best_ious = torch.zeros((N,1))
        #best_boxes = torch.zeros((N,5))    # YOU SHOULDNT CREATE A NEW TENSOR FOR TENSORS THAT CARRY GRADIENT, THAT MESSES UP THE GRADIENT #
        best_ious = []
        best_boxes = []

        print(iou_1)
        print(iou_2)


        for i in range(N):
            if iou_1[i] > iou_2[i]:
                best_ious.append(iou_1[i])
                best_boxes.append(box_pred_01[i])
            else:
                best_ious.append(iou_2[i])
                best_boxes.append(box_pred_02[i]) 

        best_ious = torch.stack(best_ious).detach()#.cuda()
        best_boxes = torch.stack(best_boxes)#.cuda()
        print("best bbox", best_boxes)

        return best_ious, best_boxes

    def find_best_iou_boxes1(self, pred_box_list: Tensor, box_target: Tensor) -> Tuple[Tensor, Tensor]:
        """
        Parameters:
        box_pred_list : [(tensor) size (-1, 5) ...]
        box_target : (tensor)  size (-1, 4)

        Returns:
        best_iou: (tensor) size (-1, 1)
        best_boxes : (tensor) size (-1, 5), containing the boxes which give the best iou among the two (self.B) predictions

        Hints:
        1) Find the iou's of each of the 2 bounding boxes of each grid cell of each image.
        2) For finding iou's use the compute_iou function
        3) use xywh2xyxy to convert bbox format if necessary,
        Note: Over here initially x, y are the center of the box and w,h are width and height.
        We perform this transformation to convert the correct coordinates into bounding box coordinates.
        """

        ### CODE ###
        # Your code here

        box_pred = torch.stack(pred_box_list, 2)
        ious = torch.zeros(size=(box_target.size(0), self.B)).to(device=self.device)
        # print(target[0])
        # print("box pred:", box_pred)
        # print(box_target.size())
        for i in range(self.B):            
            d = compute_iou(self.xywh2xyxy(
                box_pred[:, :4, i]), self.xywh2xyxy(box_target))
            ious[:, i] = torch.diagonal(d)
        # print("ious:", ious)
        ious.detach_()
        best_iou, argmax = torch.max(ious, dim=1)
        best_bbox = torch.gather(
            box_pred, 2, argmax[:, None, None].expand(-1, 5, 1))
        # print(best_bbox)
        # best_iou.detach_()
        return best_iou, best_bbox.unsqueeze(2)

    def get_class_prediction_loss(self, classes_pred: Tensor, classes_target: Tensor, has_object_map: Tensor) -> float:
        """
        Parameters:
        classes_pred : (tensor) size (batch_size, S, S, 20)
        classes_target : (tensor) size (batch_size, S, S, 20)
        has_object_map: (tensor) size (batch_size, S, S)

        Returns:
        class_loss : scalar


        This is the probability prediction loss
        """
        ### CODE ###
        # Your code here

        loss = torch.sum(has_object_map.unsqueeze(
            3) * (classes_pred - classes_target) ** 2)

        return loss

    def get_no_object_loss(self, pred_boxes_list: List[Tensor], has_object_map: Tensor):
        """
        Parameters:
        pred_boxes_list: (list) [(tensor) size (N, S, S, 5)  for B pred_boxes]
        has_object_map: (tensor) size (N, S, S)

        Returns:
        loss : scalar

        Hints:
        1) Only compute loss for cell which doesn't contain object
        2) compute loss for all predictions in the pred_boxes_list list
        3) You can assume the ground truth confidence of non-object cells is 0
        """
        ### CODE ###
        # Your code here
        pred_boxes_list = [pred_boxes_list[x][:, :, :, 4][~has_object_map]
                           for x in range(self.B)]
        loss = 0.0
        for i in range(self.B):
            loss += torch.sum(pred_boxes_list[i] ** 2)
        return loss

    def get_contain_conf_loss(self, box_pred_conf: Tensor, box_target_conf: Tensor):
        """
        Parameters:
        box_pred_conf : (tensor) size (-1,1)
        box_target_conf: (tensor) size (-1,1)

        Returns:
        contain_loss : scalar

        Hints:
        The box_target_conf should be treated as ground truth, i.e., no gradient

        """
        # CODE
        # your code here

        loss = torch.sum((box_pred_conf - box_target_conf) ** 2)

        return loss

    def get_regression_loss(self, box_pred_response: Tensor, box_target_response: Tensor):
        """
        Parameters:
        box_pred_response : (tensor) size (-1, 4)
        box_target_response : (tensor) size (-1, 4)
        Note : -1 corresponds to ravels the tensor into the dimension specified
        See : https://pytorch.org/docs/stable/tensors.html#torch.Tensor.view_as

        Returns:
        reg_loss : scalar

        This is the box position, size regressor
        """
        # CODE
        # your code here
        # print(box_pred_response[:, 0:2].size())
        # print(box_target_response[:, 2:4].size())
        reg_loss = torch.sum((box_pred_response[:, 0:2] - box_target_response[:, 0:2]) ** 2) + torch.sum(
            (box_pred_response[:, 2:4] ** 0.5 - box_target_response[:, 2:4] ** 0.5) ** 2)

        return reg_loss

    def forward(self, pred_tensor: Tensor, target_boxes: Tensor, target_cls: Tensor, has_object_map: Tensor):
        """
        pred_tensor: (tensor) size(N,S,S,Bx5+20=30) N:batch_size
                      where B - number of bounding boxes this grid cell is a part of = 2
                            5 - number of bounding box values corresponding to [x, y, w, h, c]
                                where x - x_coord, y - y_coord, w - width, h - height, c - confidence of having an object
                            20 - number of classes

        target_boxes: (tensor) size (N, S, S, 4): the ground truth bounding boxes
        target_cls: (tensor) size (N, S, S, 20): the ground truth class
        has_object_map: (tensor, bool) size (N, S, S): the ground truth for whether each cell contains an object (True/False)

        Returns:
        loss_dict (dict): with key value stored for total_loss, reg_loss, containing_obj_loss, no_obj_loss and cls_loss
        """
        N = pred_tensor.size(0)
        total_loss = 0.0

        # split the pred tensor from an entity to separate tensors:
        # -- pred_boxes_list: a list containing all bbox prediction (list) [(tensor) size (N, S, S, 5)  for B pred_boxes]
        # -- pred_cls (containing all classification prediction)

        pred_boxes_list: List[Tensor] = [
            pred_tensor[:, :, :, 5*x:5*(x+1)] for x in range(self.B)]
        pred_cls: Tensor = pred_tensor[:, :, :, 5*self.B:]

        # compute classification loss
        cls_loss = self.get_class_prediction_loss(
            pred_cls, target_cls, has_object_map)

        # compute no-object loss
        no_obj_loss = self.get_no_object_loss(pred_boxes_list, has_object_map)

        # Re-shape boxes in pred_boxes_list and target_boxes to meet the following desires
        # 1) only keep having-object cells
        # 2) vectorize all dimensions except for the last one for faster computation
        # print(pred_boxes_list)

        pred_boxes_: List[Tensor] = [pred_boxes_list[x][has_object_map.unsqueeze(
            3).expand(-1, -1, -1, 5)].flatten().unsqueeze(1).reshape(-1, 5) for x in range(self.B)]
        target_boxes: Tensor = target_boxes[has_object_map.unsqueeze(
            3).expand((-1, -1, -1, 4))].flatten().unsqueeze(1).reshape(-1, 4)

        # print(target_boxes)

        # find the best boxes among the 2 (or self.B) predicted boxes and the corresponding iou
        best_pred_ious, best_pred_bbox = self.find_best_iou_boxes(
            pred_boxes_, target_boxes)
        # print("best iou", best_pred_ious)
        # compute regression loss between the found best bbox and GT bbox for all the cell containing objects
        reg_loss = self.get_regression_loss(
            best_pred_bbox[:, :4], target_boxes)
        # compute contain_object_loss
        # print(best_pred_bbox.size(), best_pred_ious.size())
        cont_obj_loss = self.get_contain_conf_loss(
            best_pred_bbox[:, 4], best_pred_ious)
        # compute final loss
        total_loss = self.l_coord * reg_loss + self.l_noobj * \
            no_obj_loss + cont_obj_loss + cls_loss


        # construct return loss_dict
        loss_dict = dict(
            total_loss=total_loss,
            reg_loss=reg_loss,
            containing_obj_loss=cont_obj_loss,
            no_obj_loss=no_obj_loss,
            cls_loss=cls_loss,
        )
        return loss_dict


def test():
    yl = YoloLoss(2, 2, 5, 0.5)
    N = 3
    torch.random.manual_seed(0)
    pred_tensor = torch.rand((N, 2, 2, 30), requires_grad=True)
    target_box = 0.5 * torch.ones((N, 2, 2, 4))
    target_cls = torch.zeros((N, 2, 2, 20))
    target_cls[:, :, :, 10] = 1
    obj_map = torch.BoolTensor(size=(N, 2, 2))
    obj_map[:, :, :] = False
    obj_map[:, 0, 0] = True
    # print(pred_tensor)
    loss = yl(pred_tensor, target_box, target_cls, obj_map)
    loss["total_loss"].backward()
    # print(pred_tensor.grad)
    print(loss)

test()

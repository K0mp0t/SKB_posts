from io import BytesIO
import numpy as np
from PIL import Image
import tensorflow as tf


class DeepLabModel(object):
    """Class to load deeplab model and run inference."""

    INPUT_TENSOR_NAME = 'ImageTensor:0'
    OUTPUT_TENSOR_NAME = 'SemanticPredictions:0'
    INPUT_SIZE = 513
    FROZEN_GRAPH_NAME = 'frozen_inference_graph'

    def __init__(self, tarball_path):
        """Creates and loads pretrained deeplab model."""
        self.graph = tf.Graph()

        graph_def = None
        graph_def = tf.compat.v1.GraphDef.FromString(open(tarball_path + "/frozen_inference_graph.pb", "rb").read())

        if graph_def is None:
            raise RuntimeError('Cannot find inference graph in tar archive.')

        with self.graph.as_default():
            tf.import_graph_def(graph_def, name='')

        self.sess = tf.compat.v1.Session(graph=self.graph)

    def run(self, image):
        """Runs inference on a single image.
    
        Args:
          image: A PIL.Image object, raw input image.
    
        Returns:
          resized_image: RGB image resized from original input image.
          seg_map: Segmentation map of `resized_image`.
        """

        width, height = image.size
        resize_ratio = 1.0 * self.INPUT_SIZE / max(width, height)
        target_size = (int(resize_ratio * width), int(resize_ratio * height))
        resized_image = image.convert('RGB').resize(target_size, Image.ANTIALIAS)
        batch_seg_map = self.sess.run(
            self.OUTPUT_TENSOR_NAME,
            feed_dict={self.INPUT_TENSOR_NAME: [np.asarray(resized_image)]})
        seg_map = batch_seg_map[0]

        return resized_image, seg_map


def seg(image_bytes, model_path, model_type=0):
    """remove background from image
    Parameters:
      image_bytes
      model_path
      model_type
    Return:
      Resized Image
      Mask
      Segmented Image
    """
    if image_bytes is None:
        raise RuntimeError("Bad parameters. Please specify input file path and output file path")

    modelType = "mobile_net_model"
    if model_type == 1:
        modelType = "xception_model"

    model = DeepLabModel("proto_v2/" + modelType)

    def run_visualization(image_bytes):
        """Inferences DeepLab model and visualizes result."""
        try:
            orignal_im = Image.open(BytesIO(image_bytes))
        except IOError:
            print('Cannot retrieve image.')
            return

        resized_im, seg_map = model.run(orignal_im)

        return orignal_im, seg_map

    visualization = run_visualization(image_bytes)

    del model

    return visualization


# returns height, width, and position of the top left corner of the largest
#  rectangle with the given value in mat
def max_size(mat, value=0):
    it = iter(mat)
    hist = [(el == value) for el in next(it, [])]
    max_size_start, start_row = max_rectangle_size(hist), 0
    for i, row in enumerate(it):
        hist = [(1 + h) if el == value else 0 for h, el in zip(hist, row)]
        mss = max_rectangle_size(hist)
        if area(mss) > area(max_size_start):
            max_size_start, start_row = mss, i + 2 - mss[0]
    return max_size_start[:2], (start_row, max_size_start[2])


# returns height, width, and start column of the largest rectangle that
#  fits entirely under the histogram
def max_rectangle_size(histogram):
    stack = []

    max_size_start = (0, 0, 0)  # height, width, start of the largest rectangle
    pos = 0  # current position in the histogram
    for pos, height in enumerate(histogram):
        start = pos  # position where rectangle starts
        while True:
            if not stack or height > stack[-1][1]:
                stack.append((start, height))  # push
            elif stack and height < stack[-1][1]:
                max_size_start = max(
                    max_size_start,
                    (stack[-1][1], pos - stack[-1][0], stack[-1][0]),
                    key=area)
                start, _ = stack.pop()
                continue
            break  # height == top().height goes here

    pos += 1
    for start, height in stack:
        max_size_start = max(max_size_start, (height, pos - start, start),
                             key=area)

    return max_size_start


def area(size): return size[0] * size[1]


def split_rectangle(pos, size):
    result = list()

    if size[0] // size[1] == 1 or size[1] // size[0] == 1:
        result.append(((pos[1], pos[0]), (size[1], size[0])))
        return result

    else:
        if size[0] > size[1]:
            for i in range(size[0] // size[1]):
                result.append(((pos[1], pos[0] + i * size[1]), (size[1], size[1])))
        else:
            for i in range(size[1] // size[0]):
                result.append(((pos[1] + i * size[0], pos[0]), (size[0], size[0])))

    return result


def get_empty_areas(mask, areas_count=1, scale=1):
    """
    Parameters:
        mask (:obj:`np.array`): The first parameter.
        areas_count (:obj:`int`, optional): The second parameter. Defaults to 1.
        scale:
    Return:
        list: ((pos_x, pos_y), (size_x, size_y)).
    """

    img = mask.copy()
    result = []

    def scale_and_int(n):
        return int(n * scale)

    for i in range(areas_count):
        size, pos = max_size(img)
        scaled_size, scaled_pos = list(map(scale_and_int, size)), list(map(scale_and_int, pos))

        if scaled_size[0] == 0 or scaled_size[1] == 0:
            break

        for x in range(pos[1], pos[1] + size[1]):
            for y in range(pos[0], pos[0] + size[0]):
                img[y, x] = 1

        if scaled_size[0] < 100 or scaled_size[1] < 100:
            continue

        result.extend(split_rectangle(scaled_pos, scaled_size))

    return result
